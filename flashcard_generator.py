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

from colorama import Fore, Style, init
from api_key_manager import APIKeyManager, call_gemini_with_retry

# Initialize colorama
init(autoreset=True)

# Gemini API Configuration
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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
        api_key_manager: Optional[APIKeyManager] = None,
        model_name: str = "gemini-2.0-flash",
        verbose: bool = True
    ):
        """Initialize the Flashcard Generator"""
        self.model_name = model_name
        self.verbose = verbose
        
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
                    raise ValueError(
                        "Gemini API key required. Set GEMINI_API_KEY1 and GEMINI_API_KEY2 "
                        "in environment or pass gemini_api_key"
                    )
        
        key_count = len(self.api_key_manager.get_key_list()) if self.api_key_manager else 1
        self._log(
            f"✓ Flashcard Generator initialized with {model_name} "
            f"({key_count} API key(s))",
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
    
    def _call_gemini(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 8192
    ) -> str:
        """Call Gemini API with automatic retry"""
        if self.api_key_manager:
            def api_call(api_key: str) -> str:
                response = requests.post(
                    f"{GEMINI_API_URL}?key={api_key}",
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
                
                response.raise_for_status()
                data = response.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    return "Error: No response generated from Gemini"
            
            return call_gemini_with_retry(
                api_call,
                self.api_key_manager,
                verbose=self.verbose,
                max_retries=2
            )
        else:
            try:
                response = requests.post(
                    f"{GEMINI_API_URL}?key={self.gemini_api_key}",
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
                
                response.raise_for_status()
                data = response.json()
                
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                else:
                    return "Error: No response generated from Gemini"
                
            except Exception as e:
                self._log(f"❌ Gemini API error: {str(e)}", Fore.RED)
                return f"Error: {str(e)}"
    
    def _chunk_content(self, content: str, max_size: int) -> List[str]:
        """Split large content into manageable chunks"""
        if len(content) <= max_size:
            return [content]
        
        chunks = []
        
        # Try to split by paragraphs first
        paragraphs = content.split('\n\n')
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= max_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If chunks are still too large, split by sentences
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= max_size:
                final_chunks.append(chunk)
            else:
                # Force split at max_size
                for i in range(0, len(chunk), max_size):
                    final_chunks.append(chunk[i:i + max_size])
        
        return final_chunks
    
    def _analyze_content(self, content: str) -> Dict[str, Any]:
        """Analyze content to determine optimal flashcard strategy"""
        self._log("\n🔍 Step 1: Analyzing content...", Fore.CYAN)
        
        # Use first chunk for analysis if content is large
        sample = content[:MAX_CONTENT_SIZE] if len(content) > MAX_CONTENT_SIZE else content
        self._log(f"  Analyzing sample: {len(sample)} characters", Fore.BLUE)
        
        analysis_prompt = f"""Analyze this content sample and provide a JSON response with:
1. content_type: "textbook", "lecture_notes", "research_paper", "article", etc.
2. complexity_level: "beginner", "intermediate", "advanced"
3. key_topics: List of 3-7 main topics covered
4. estimated_concepts: Approximate number of key concepts
5. recommended_card_count: Optimal number of flashcards (10-100)
6. difficulty_distribution: {{"easy": 30, "medium": 50, "hard": 20}}
7. recommended_card_types: ["qa", "definition", "cloze"]

Content sample (first ~200KB):
{sample}

IMPORTANT: Respond with ONLY valid JSON. No explanations, no markdown. Just the JSON object."""
        
        response = self._call_gemini(analysis_prompt, temperature=0.3)
        
        try:
            response = self._clean_json_response(response)
            analysis = json.loads(response)
            
            self._log(f"✓ Content Type: {analysis.get('content_type', 'unknown')}", Fore.GREEN)
            self._log(f"✓ Complexity: {analysis.get('complexity_level', 'unknown')}", Fore.GREEN)
            self._log(f"✓ Key Topics: {len(analysis.get('key_topics', []))}", Fore.GREEN)
            self._log(f"✓ Recommended Cards: {analysis.get('recommended_card_count', 0)}", Fore.GREEN)
            
            return analysis
        except json.JSONDecodeError as e:
            self._log(f"⚠️ JSON parsing error: {e}", Fore.YELLOW)
            self._log(f"  Response preview: {response[:200]}...", Fore.YELLOW)
            
            # Return safe defaults
            return {
                'content_type': 'textbook',
                'complexity_level': 'intermediate',
                'key_topics': ['Chapter Content'],
                'estimated_concepts': 40,
                'recommended_card_count': 40,
                'difficulty_distribution': {'easy': 30, 'medium': 50, 'hard': 20},
                'recommended_card_types': ['qa', 'definition']
            }
    
    def _extract_concepts_from_chunk(
        self,
        chunk: str,
        chunk_index: int,
        total_chunks: int,
        cards_per_chunk: int
    ) -> List[Dict]:
        """Extract concepts from a single chunk"""
        self._log(f"  Processing chunk {chunk_index + 1}/{total_chunks} ({len(chunk)} chars)", Fore.BLUE)
        
        extraction_prompt = f"""Extract exactly {cards_per_chunk} key concepts from this content for flashcard generation.

Content:
{chunk}

For each concept, provide a JSON object with:
- concept: The main concept/term
- definition: Brief definition
- importance: "high", "medium", "low"
- suggested_card_type: "qa", "definition", or "cloze"
- suggested_difficulty: "easy", "medium", or "hard"

IMPORTANT: 
1. Return ONLY a JSON array of concepts
2. No markdown formatting, no code blocks
3. Ensure all strings are properly quoted
4. Each concept object must be complete

Example format:
[
  {{"concept": "Term 1", "definition": "Def 1", "importance": "high", "suggested_card_type": "definition", "suggested_difficulty": "easy"}},
  {{"concept": "Term 2", "definition": "Def 2", "importance": "medium", "suggested_card_type": "qa", "suggested_difficulty": "medium"}}
]"""
        
        for attempt in range(3):  # Try up to 3 times
            try:
                response = self._call_gemini(extraction_prompt, temperature=0.5, max_tokens=8192)
                response = self._clean_json_response(response)
                
                concepts = json.loads(response)
                
                # Handle nested structure
                if isinstance(concepts, dict) and 'concepts' in concepts:
                    concepts = concepts['concepts']
                
                if not isinstance(concepts, list):
                    raise ValueError("Response is not a list")
                
                # Validate concepts
                valid_concepts = []
                for c in concepts:
                    if isinstance(c, dict) and 'concept' in c and 'definition' in c:
                        valid_concepts.append(c)
                
                if valid_concepts:
                    self._log(f"    ✓ Extracted {len(valid_concepts)} concepts", Fore.GREEN)
                    return valid_concepts
                
            except (json.JSONDecodeError, ValueError) as e:
                self._log(f"    ⚠️ Attempt {attempt + 1} failed: {str(e)[:100]}", Fore.YELLOW)
                if attempt < 2:
                    time.sleep(1)  # Brief pause before retry
                continue
        
        self._log(f"    ❌ Failed to extract concepts from chunk {chunk_index + 1}", Fore.RED)
        return []
    
    def _extract_concepts(self, content: str, analysis: Dict) -> List[Dict]:
        """Extract key concepts from content with chunking support"""
        self._log("\n📚 Step 2: Extracting key concepts...", Fore.CYAN)
        
        recommended_count = analysis.get('recommended_card_count', 40)
        
        # Split content into chunks if too large
        chunks = self._chunk_content(content, MAX_EXTRACTION_SIZE)
        self._log(f"  Split into {len(chunks)} chunks for processing", Fore.BLUE)
        
        # Calculate cards per chunk
        cards_per_chunk = max(5, recommended_count // len(chunks))
        
        all_concepts = []
        
        for i, chunk in enumerate(chunks):
            chunk_concepts = self._extract_concepts_from_chunk(
                chunk, i, len(chunks), cards_per_chunk
            )
            all_concepts.extend(chunk_concepts)
            
            # Limit to recommended count
            if len(all_concepts) >= recommended_count:
                all_concepts = all_concepts[:recommended_count]
                break
        
        self._log(f"✓ Total extracted: {len(all_concepts)} concepts", Fore.GREEN)
        return all_concepts
    
    def _generate_flashcards_from_concepts(
        self,
        concepts: List[Dict],
        analysis: Dict,
        difficulty_preference: str = "mixed"
    ) -> List[Flashcard]:
        """Generate flashcards from extracted concepts"""
        self._log("\n🎴 Step 3: Generating flashcards...", Fore.CYAN)
        
        flashcards = []
        
        # Determine difficulty distribution
        if difficulty_preference == "mixed":
            dist = analysis.get('difficulty_distribution', {'easy': 30, 'medium': 50, 'hard': 20})
        else:
            dist = {difficulty_preference: 100}
        
        for i, concept in enumerate(concepts, 1):
            # Determine difficulty
            if i <= len(concepts) * (dist.get('easy', 30) / 100):
                difficulty = 'easy'
            elif i <= len(concepts) * ((dist.get('easy', 30) + dist.get('medium', 50)) / 100):
                difficulty = 'medium'
            else:
                difficulty = 'hard'
            
            if 'suggested_difficulty' in concept:
                difficulty = concept['suggested_difficulty']
            
            card_type = concept.get('suggested_card_type', 'qa')
            
            card_prompt = f"""Generate a {difficulty} difficulty {card_type} flashcard:

Concept: {concept.get('concept', '')}
Definition: {concept.get('definition', '')}

Return JSON:
{{"front": "question or term", "back": "answer or definition", "explanation": "why this matters", "tags": ["tag1", "tag2"]}}

IMPORTANT: Return ONLY the JSON object, no markdown, no extra text."""
            
            for attempt in range(2):
                try:
                    response = self._call_gemini(card_prompt, temperature=0.7)
                    response = self._clean_json_response(response)
                    card_data = json.loads(response)
                    
                    flashcard = Flashcard(
                        front=card_data.get('front', '')[:500],  # Limit length
                        back=card_data.get('back', '')[:1000],
                        card_type=card_type,
                        difficulty=difficulty,
                        explanation=card_data.get('explanation', '')[:500],
                        tags=card_data.get('tags', [concept.get('concept', 'General')])[:5],
                        confidence_score=0.85
                    )
                    
                    # Validate minimum content
                    if len(flashcard.front) >= 10 and len(flashcard.back) >= 10:
                        flashcards.append(flashcard)
                        break
                    
                except (json.JSONDecodeError, Exception) as e:
                    if attempt == 0:
                        time.sleep(0.5)
                    continue
            
            if (i % 10 == 0) or (i == len(concepts)):
                self._log(f"  Generated {len(flashcards)}/{i} cards...", Fore.BLUE)
        
        self._log(f"✓ Successfully generated {len(flashcards)} flashcards", Fore.GREEN)
        return flashcards
    
    def _quality_check(self, flashcards: List[Flashcard]) -> List[Flashcard]:
        """Quality check and filtering"""
        self._log("\n✅ Step 4: Quality checking flashcards...", Fore.CYAN)
        
        valid_cards = []
        seen_fronts = set()
        
        for card in flashcards:
            # Check basic validity
            if not card.front or not card.back:
                continue
            
            # Check minimum length
            if len(card.front) < 10 or len(card.back) < 10:
                continue
            
            # Check for duplicates (case-insensitive)
            front_lower = card.front.lower().strip()
            if front_lower in seen_fronts:
                continue
            
            seen_fronts.add(front_lower)
            valid_cards.append(card)
        
        removed = len(flashcards) - len(valid_cards)
        if removed > 0:
            self._log(f"⚠️ Removed {removed} invalid/duplicate cards", Fore.YELLOW)
        
        self._log(f"✓ {len(valid_cards)} valid cards remaining", Fore.GREEN)
        return valid_cards
    
    def generate(
        self,
        content: str,
        title: str = "Generated Flashcards",
        difficulty: Literal["easy", "medium", "hard", "mixed"] = "mixed",
        card_count: Literal["auto", "few", "normal", "many"] = "auto",
        custom_count: Optional[int] = None
    ) -> FlashcardSet:
        """Generate flashcards with large content support"""
        self._log(f"\n{'='*80}", Fore.CYAN)
        self._log(f"🎴 Generating Flashcards: {title}", Fore.CYAN)
        self._log(f"  Content size: {len(content):,} characters", Fore.CYAN)
        self._log(f"{'='*80}", Fore.CYAN)
        
        start_time = time.time()
        
        # Step 1: Analyze content
        analysis = self._analyze_content(content)
        
        # Adjust count
        if custom_count:
            analysis['recommended_card_count'] = custom_count
        elif card_count == "few":
            analysis['recommended_card_count'] = max(10, analysis['recommended_card_count'] // 2)
        elif card_count == "many":
            analysis['recommended_card_count'] = min(100, analysis['recommended_card_count'] * 2)
        
        # Step 2: Extract concepts
        concepts = self._extract_concepts(content, analysis)
        
        if not concepts:
            self._log("❌ No concepts extracted", Fore.RED)
            return FlashcardSet(title=title, cards=[], metadata={'error': 'No concepts found'})
        
        # Step 3: Generate flashcards
        flashcards = self._generate_flashcards_from_concepts(concepts, analysis, difficulty)
        
        # Step 4: Quality check
        flashcards = self._quality_check(flashcards)
        
        elapsed_time = time.time() - start_time
        
        flashcard_set = FlashcardSet(
            title=title,
            cards=flashcards,
            metadata={
                'content_analysis': analysis,
                'content_size': len(content),
                'chunks_processed': len(self._chunk_content(content, MAX_EXTRACTION_SIZE)),
                'total_cards': len(flashcards),
                'difficulty_counts': {
                    'easy': len([c for c in flashcards if c.difficulty == 'easy']),
                    'medium': len([c for c in flashcards if c.difficulty == 'medium']),
                    'hard': len([c for c in flashcards if c.difficulty == 'hard'])
                },
                'card_type_counts': {
                    'qa': len([c for c in flashcards if c.card_type == 'qa']),
                    'definition': len([c for c in flashcards if c.card_type == 'definition']),
                    'cloze': len([c for c in flashcards if c.card_type == 'cloze'])
                },
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