"""
AI-Powered Flashcard Generator with Large Content Support
==========================================================

Fixed version that handles:
1. Large textbooks (1MB+)
2. Malformed JSON responses
3. Content chunking for better processing
4. Robust error recovery

Dependencies:
    pip install requests colorama python-dotenv

Usage:
    from flashcard_generator import FlashcardGenerator
    
    generator = FlashcardGenerator(gemini_api_key="your_key")
    
    flashcards = generator.generate(
        content="Your study material here",
        difficulty="medium",
        card_count="auto"
    )
"""

import os
import json
import requests
from typing import List, Dict, Optional, Any, Literal
from dataclasses import dataclass, field
from datetime import datetime
import time
import re

# from colorama import Fore, Style, init (Removed for Render compatibility)
from api_key_manager import APIKeyManager, call_gemini_with_retry

# Dummy classes to replace colorama
class Fore:
    CYAN = ""
    GREEN = ""
    YELLOW = ""
    RED = ""
    BLUE = ""
    RESET = ""

class Style:
    RESET_ALL = ""

# init(autoreset=True)

# AI API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

# Content chunking settings
MAX_CONTENT_SIZE = 200000  # ~200KB per chunk for analysis
MAX_EXTRACTION_SIZE = 150000  # ~150KB per extraction


@dataclass
class Flashcard:
    """Represents a single flashcard"""
    front: str
    back: str
    card_type: Literal["qa", "definition", "cloze"]
    difficulty: Literal["easy", "medium", "hard"]
    explanation: str
    tags: List[str]
    source_reference: Optional[str] = None
    confidence_score: float = 0.0
    id: str = field(default_factory=lambda: f"card_{int(time.time() * 1000)}")
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class FlashcardSet:
    """Represents a complete flashcard set"""
    title: str
    cards: List[Flashcard]
    metadata: Dict[str, Any]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'cards': [
                {
                    'id': card.id,
                    'front': card.front,
                    'back': card.back,
                    'type': card.card_type,
                    'difficulty': card.difficulty,
                    'explanation': card.explanation,
                    'tags': card.tags,
                    'source_reference': card.source_reference,
                    'confidence_score': card.confidence_score,
                    'created_at': card.created_at
                }
                for card in self.cards
            ],
            'metadata': self.metadata,
            'generated_at': self.generated_at
        }
    
    def to_markdown(self) -> str:
        """Convert to markdown format"""
        md = f"# Flashcard Set: {self.title}\n\n"
        md += f"*Generated: {self.generated_at}*\n"
        md += f"*Total Cards: {len(self.cards)}*\n\n"
        
        # Group by difficulty
        for difficulty in ["easy", "medium", "hard"]:
            cards_at_level = [c for c in self.cards if c.difficulty == difficulty]
            if cards_at_level:
                md += f"\n## {difficulty.capitalize()} Cards ({len(cards_at_level)})\n\n"
                for i, card in enumerate(cards_at_level, 1):
                    md += f"### Card {i} [{card.card_type.upper()}]\n\n"
                    md += f"**Front:** {card.front}\n\n"
                    md += f"**Back:** {card.back}\n\n"
                    if card.explanation:
                        md += f"**Explanation:** {card.explanation}\n\n"
                    if card.tags:
                        md += f"**Tags:** {', '.join(card.tags)}\n\n"
                    md += "---\n\n"
        
        return md


class FlashcardGenerator:
    """
    AI-Powered Flashcard Generator with Large Content Support
    """
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        api_key_manager: Optional[APIKeyManager] = None,
        model_name: str = "gemini-2.0-flash",
        verbose: bool = True
    ):
        """Initialize the Flashcard Generator"""
        self.model_name = model_name
        self.verbose = verbose
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        
        if api_key_manager:
            self.api_key_manager = api_key_manager
        else:
            try:
                self.api_key_manager = APIKeyManager()
            except ValueError:
                if gemini_api_key:
                    self.api_key_manager = None
                    self.gemini_api_key = gemini_api_key
                else:
                    # If we have no Gemini keys, we might still have Groq
                    self.api_key_manager = None
                    self.gemini_api_key = gemini_api_key
                    if not self.groq_api_key:
                        raise ValueError(
                            "At least one API key (Gemini or Groq) is required."
                        )
        
        key_count = len(self.api_key_manager.get_key_list()) if self.api_key_manager else (1 if getattr(self, 'gemini_api_key', None) else 0)
        provider_info = f"Gemini ({key_count} keys)" if key_count > 0 else "No Gemini keys"
        if self.groq_api_key:
            provider_info += " + Groq"

        self._log(
            f"✓ Flashcard Generator initialized with {provider_info}",
            Fore.GREEN
        )
    
    def _log(self, message: str, color=Fore.YELLOW):
        """Log message if verbose is enabled"""
        if self.verbose:
            print(f"{color}{message}{Style.RESET_ALL}")
    
    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from API response"""
        response = response.strip()
        
        # Remove markdown code blocks
        if response.startswith("```json"):
            response = response[7:]
        elif response.startswith("```"):
            response = response[3:]
        
        if response.endswith("```"):
            response = response[:-3]
        
        response = response.strip()
        
        # Find JSON object or array boundaries
        if response.startswith('['):
            # Find the last valid closing bracket
            depth = 0
            last_valid = -1
            for i, char in enumerate(response):
                if char == '[':
                    depth += 1
                elif char == ']':
                    depth -= 1
                    if depth == 0:
                        last_valid = i
                        break
            if last_valid > 0:
                response = response[:last_valid + 1]
        elif response.startswith('{'):
            # Find the last valid closing brace
            depth = 0
            last_valid = -1
            for i, char in enumerate(response):
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        last_valid = i
                        break
            if last_valid > 0:
                response = response[:last_valid + 1]
        
        return response
    
    def _call_groq(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096
    ) -> str:
        """Call Groq API with fallback to multiple models on rate limit"""
        if not self.groq_api_key:
            return "Error: Groq API key not provided"
            
        models_to_try = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-1b-preview",
            "llama-3.2-3b-preview",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]
        
        last_error = "Unknown error"
        
        for model in models_to_try:
            for attempt in range(2): # 2 attempts per model
                try:
                    self._log(f"🤖 Sending to Groq ({model}, try {attempt+1})...", Fore.CYAN)
                    response = requests.post(
                        GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {self.groq_api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": model,
                            "messages": [{"role": "user", "content": prompt}],
                            "temperature": temperature,
                            "max_tokens": max_tokens
                        },
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                        else:
                            last_error = "No response generated from Groq"
                            continue
                    elif response.status_code == 429:
                        wait_time = (attempt + 1) * 4 # Increased backoff
                        self._log(f"⚠️ Groq Rate Limit (429) on {model}. Waiting {wait_time}s...", Fore.YELLOW)
                        time.sleep(wait_time)
                        last_error = f"Rate limited on {model}"
                        continue
                    else:
                        self._log(f"❌ Groq API error ({response.status_code}) on {model}", Fore.RED)
                        last_error = f"Error {response.status_code}: {response.text}"
                        continue
                        
                except Exception as e:
                    self._log(f"⚠️ Request error on {model}: {str(e)}", Fore.YELLOW)
                    last_error = str(e)
                    time.sleep(1)
                    continue
        
        
        return f"Error: All Groq models failed. Last error: {last_error}"

    def _call_ai(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> str:
        """
        Unified Provider Pool: Prioritizes Groq models (per user request) 
        and only uses Gemini as a last resort.
        """
        last_error = "No providers available"
        
        # --- PHASE 1: GROQ POOL (Primary) ---
        if self.groq_api_key:
            self._log("🧪 Attempting Groq Pool (Primary)...", Fore.CYAN)
            groq_response = self._call_groq(prompt, temperature, min(max_tokens, 4096))
            
            # If Groq actually returned a result (didn't return an error string)
            if not groq_response.startswith("Error:"):
                return groq_response
            else:
                last_error = groq_response

        # --- PHASE 2: GEMINI POOL (Last Resort) ---
        if self.api_key_manager or getattr(self, 'gemini_api_key', None):
            self._log("🧪 Falling back to Gemini Pool (Last Resort)...", Fore.CYAN)
            
            # Prepare Gemini Models to try
            gemini_models = ["gemini-2.0-flash", "gemini-1.5-flash"]
            
            # Get list of keys to cycle
            keys = self.api_key_manager.get_key_list() if self.api_key_manager else [self.gemini_api_key]
            
            for model_name in gemini_models:
                for idx, key in enumerate(keys):
                    for attempt in range(2): # 2 attempts per key
                        try:
                            self._log(f"  Attempting {model_name} with Key #{idx+1} (try {attempt+1})...", Fore.BLUE)
                            response = requests.post(
                                f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={key}",
                                headers={"Content-Type": "application/json"},
                                json={
                                    "contents": [{"parts": [{"text": prompt}]}],
                                    "generationConfig": {
                                        "temperature": temperature,
                                        "topK": 40,
                                        "topP": 0.95,
                                        "maxOutputTokens": max_tokens,
                                    }
                                },
                                timeout=60
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                if "candidates" in data and len(data["candidates"]) > 0:
                                    return data["candidates"][0]["content"]["parts"][0]["text"]
                                else:
                                    last_error = f"Gemini {model_name} returned no candidates"
                            elif response.status_code == 429:
                                wait_time = (attempt + 1) * 3
                                self._log(f"  ⚠️ Rate limit (429) on Gemini {model_name}. Waiting {wait_time}s...", Fore.YELLOW)
                                time.sleep(wait_time)
                            else:
                                last_error = f"Gemini {response.status_code}: {response.text}"
                                
                        except Exception as e:
                            self._log(f"  ⚠️ Gemini exception: {str(e)}", Fore.YELLOW)
                            last_error = str(e)
                            time.sleep(1)
                
        return f"Error: All providers in the Unified Pool exhausted. Last error: {last_error}"

    def generate_bulk(
        self,
        content: str,
        topic: str,
        num_cards: int = 15,
        difficulty: str = "medium"
    ) -> List[Flashcard]:
        """Generate flashcards in a single bulk request to avoid rate limits."""
        self._log(f"🚀 Generating {num_cards} flashcards in bulk for: {topic}", Fore.CYAN)
        
        prompt = f"""Generate {num_cards} high-quality flashcards for the SPECIFIC topic: "{topic}"
        
        CRITICAL REQUIREMENT: Every single flashcard MUST be directly related to "{topic}". 
        Avoid broad generalities about the subject (e.g. if the topic is "{topic}", do not generate basic cards about general functions unless they specifically illustrate a property of {topic}).
        
        Context from study material:
        {content[:100000]}
        
        Target Difficulty: {difficulty}
        
        Instructions:
        1. Mix of Q&A, definitions, and application problems.
        2. Ensure cards are detailed, technical, and study-optimized.
        3. If the context doesn't contain enough information for {num_cards} cards on "{topic}", use your internal expertise as a tutor to fulfill the request for this SPECIFIC topic.
        4. **Use LaTeX math syntax** (e.g., $x^2$ or $\\frac{{a}}{{b}}$) for any mathematical formulas or scientific notation.
        5. Respond ONLY with a valid JSON array of objects.
        
        Format:
        [
          {{
            "front": "Specific question or term",
            "back": "Detailed answer with context and examples",
            "explanation": "Brief explanation of why this matters",
            "type": "qa" or "definition",
            "difficulty": "easy", "medium", or "hard",
            "tags": ["topic1", "topic2"]
          }}
        ]
        """
        
        try:
            response = self._call_ai(prompt, temperature=0.7)
            response = self._clean_json_response(response)
            
            raw_cards = json.loads(response)
            flashcards = []
            
            for card_data in raw_cards:
                if isinstance(card_data, dict) and 'front' in card_data and 'back' in card_data:
                    flashcards.append(Flashcard(
                        front=card_data.get('front', '')[:500],
                        back=card_data.get('back', '')[:1000],
                        card_type=card_data.get('type', 'qa'),
                        difficulty=card_data.get('difficulty', difficulty),
                        explanation=card_data.get('explanation', '')[:500],
                        tags=card_data.get('tags', [topic])[:5]
                    ))
            
            return flashcards
        except Exception as e:
            self._log(f"❌ Bulk generation failed: {e}", Fore.RED)
            return []

    def _quality_check(self, flashcards: List[Flashcard]) -> List[Flashcard]:
        """Quality check and filtering for bulk generated cards."""
        valid_cards = []
        seen_fronts = set()
        
        for card in flashcards:
            if not card.front or not card.back: continue
            if len(card.front) < 5 or len(card.back) < 5: continue
            
            front_lower = card.front.lower().strip()
            if front_lower in seen_fronts: continue
            
            seen_fronts.add(front_lower)
            valid_cards.append(card)
        
        return valid_cards

    def generate(
        self,
        content: str,
        title: str = "Generated Flashcards",
        difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed",
        card_count: Literal["auto", "few", "normal", "many"] = "auto",
        custom_count: Optional[int] = None
    ) -> FlashcardSet:
        """Generate flashcards using the bulk approach for stability."""
        self._log(f"\n{'='*80}", Fore.CYAN)
        self._log(f"🎴 Generating Flashcards (Bulk Mode): {title}", Fore.CYAN)
        self._log(f"  Content size: {len(content):,} characters", Fore.CYAN)
        self._log(f"{'='*80}", Fore.CYAN)
        
        start_time = time.time()
        
        # Determine card count
        if custom_count:
            num_cards = custom_count
        elif card_count == "few":
            num_cards = 10
        elif card_count == "many":
            num_cards = 30
        else:
            num_cards = 15 # Healthy default for bulk
            
        # Bulk generation (Avoids multiple RPM hits)
        flashcards = self.generate_bulk(content, title, num_cards, difficulty if difficulty != "mixed" else "medium")
        
        # Quality check
        flashcards = self._quality_check(flashcards)
        
        elapsed_time = time.time() - start_time
        
        flashcard_set = FlashcardSet(
            title=title,
            cards=flashcards,
            metadata={
                'content_size': len(content),
                'total_cards': len(flashcards),
                'mode': 'bulk_optimized',
                'processing_time_seconds': elapsed_time
            }
        )
        
        self._log(f"\n{'='*80}", Fore.GREEN)
        self._log(f"✅ Flashcard generation completed in {elapsed_time:.2f} seconds", Fore.GREEN)
        self._log(f"📊 Total Cards: {len(flashcards)}", Fore.GREEN)
        self._log(f"{'='*80}\n", Fore.GREEN)
        
        return flashcard_set
    
    def save_flashcards(
        self,
        flashcard_set: FlashcardSet,
        filepath: str,
        format: Literal["json", "markdown", "csv"] = "json"
    ):
        """Save flashcards to file"""
        try:
            if format == "json":
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(flashcard_set.to_dict(), f, indent=2, ensure_ascii=False)
            
            elif format == "markdown":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(flashcard_set.to_markdown())
            
            elif format == "csv":
                import csv
                with open(filepath, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Front', 'Back', 'Type', 'Difficulty', 'Explanation', 'Tags'])
                    for card in flashcard_set.cards:
                        writer.writerow([
                            card.front,
                            card.back,
                            card.card_type,
                            card.difficulty,
                            card.explanation,
                            ', '.join(card.tags)
                        ])
            
            self._log(f"✓ Flashcards saved to {filepath}", Fore.GREEN)
            
        except Exception as e:
            self._log(f"❌ Error saving flashcards: {str(e)}", Fore.RED)