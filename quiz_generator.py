"""
AI-Powered Quiz Generator with MCQ Support
===========================================

Handles:
1. Dynamic MCQ generation (Question + 4 options + Correct Index + Explanation)
2. Source-based generation via context
3. Batch generation for performance
4. Robust error recovery

Dependencies:
    pip install requests colorama python-dotenv

Usage:
    from quiz_generator import QuizGenerator
    
    generator = QuizGenerator()
    quiz_set = generator.generate(content="...", topic="...", num_questions=10)
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
from api_key_manager import APIKeyManager

# Initialize colorama
init(autoreset=True)

# AI API Configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

@dataclass
class QuizQuestion:
    """Represents a single MCQ"""
    question: str
    options: List[str]
    correct: int  # 0-indexed index of correct option
    explanation: str
    difficulty: str = "medium"
    id: str = field(default_factory=lambda: f"q_{int(time.time() * 1000)}_{os.urandom(4).hex()}")

@dataclass
class QuizSet:
    """Represents a complete Quiz set"""
    title: str
    questions: List[QuizQuestion]
    metadata: Dict[str, Any]
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'questions': [
                {
                    'id': q.id,
                    'question': q.question,
                    'options': q.options,
                    'correct': q.correct,
                    'explanation': q.explanation,
                    'difficulty': q.difficulty
                }
                for q in self.questions
            ],
            'metadata': self.metadata,
            'generated_at': self.generated_at
        }

class QuizGenerator:
    """
    AI-Powered Quiz Generator
    """
    
    def __init__(
        self,
        gemini_api_key: Optional[str] = None,
        groq_api_key: Optional[str] = None,
        api_key_manager: Optional[APIKeyManager] = None,
        verbose: bool = True
    ):
        """Initialize the Quiz Generator"""
        self.verbose = verbose
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        
        if api_key_manager:
            self.api_key_manager = api_key_manager
        else:
            try:
                self.api_key_manager = APIKeyManager()
            except ValueError:
                self.api_key_manager = None
                self.gemini_api_key = gemini_api_key
        
        self._log("✓ Quiz Generator initialized", Fore.GREEN)
    
    def _log(self, message: str, color=Fore.YELLOW):
        """Log message if verbose is enabled"""
        if self.verbose:
            print(f"{color}{message}{Style.RESET_ALL}")

    def _clean_json_response(self, response: str) -> str:
        """Extract JSON from AI response, handling reasoning preamble and LaTeX blocks."""
        if not response:
            return "[]"
            
        # 1. Remove markdown code blocks if present
        if "```json" in response:
            parts = response.split("```json")
            if len(parts) > 1:
                response = parts[-1].split("```")[0]
        elif "```" in response:
            parts = response.split("```")
            if len(parts) > 1:
                response = parts[-1].split("```")[0]
            
        response = response.strip()
        
        # 2. Extract boundaries - Prioritize Arrays [ ] as they are the primary container for quizes
        start_arr = response.find('[')
        end_arr = response.rfind(']')
        
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            return response[start_arr:end_arr+1]
            
        # 3. Fallback to Objects { } if no array found
        start_obj = response.find('{')
        end_obj = response.rfind('}')
        
        if start_obj != -1 and end_obj != -1 and end_obj > start_obj:
            return response[start_obj:end_obj+1]
            
        return response

    def _fix_latex_escapes(self, s: str) -> str:
        """Fix unescaped LaTeX backslashes for JSON parsing while preserving JSON-required escapes."""
        import re
        # We need to turn \ into \\ for LaTeX, EXCEPT if it's already a \\ or a \"
        # Standard JSON escapes: \", \\, \/, \b, \f, \n, \r, \t, \uXXXX
        # But in AI-generated math, \f (frac), \t (text), \n (newline), \r (rho) are commands!
        # So we double-escape EVERYTHING that isn't already escaped or a quote.
        return re.sub(r'\\(?![\\"])', r'\\\\', s)

    def _call_ai(self, prompt: str) -> str:
        """Unified AI caller using FlashcardGenerator's style pool logic"""
        # (Simplified for now, can be expanded to full pool logic if needed)
        if not self.groq_api_key:
            return "Error: No Groq key"
            
        try:
            response = requests.post(
                GROQ_API_URL,
                headers={"Authorization": f"Bearer {self.groq_api_key}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 4096
                },
                timeout=30
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"]
            elif response.status_code == 429:
                self._log("⚠️ Rate limited (429). Retrying in 5s...", Fore.RED)
                time.sleep(5)
                return self._call_ai(prompt) # Simple retry
            return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            self._log(f"❌ AI Call Exception: {e}", Fore.RED)
            return f"Error: {str(e)}"

    def generate(
        self,
        content: str,
        topic: str,
        num_questions: int = 10,
        difficulty: str = "medium"
    ) -> QuizSet:
        """Generate a complete quiz set"""
        self._log(f"🚀 Generating {num_questions} questions for: {topic}", Fore.CYAN)
        
        # Handle dict vs string content for personalization
        if isinstance(content, dict):
            raw_text = content.get('content', '') + "\n" + content.get('rag_context', '')
            memory_profile = content.get('memory', {})
        else:
            raw_text = content
            memory_profile = {}

        prompt = rf"""You are an expert tutor. Generate {num_questions} high-quality Multiple Choice Questions (MCQs) for the topic: "{topic}".
        
        Context from study material:
        {raw_text[:100000]}
        
        Target Difficulty: {difficulty}
        
        [STUDENT MEMORY PROFILE]
        {json.dumps(memory_profile, indent=2) if memory_profile else 'No profile available yet.'}

        CRITICAL WORKFLOW (Follow strictly):
        1. REASONING: For each question, first solve it step-by-step. 
           - Personalize by focusing on identified Weaknesses or reinforcing Strengths.
           - Use the 'Detailed Progress Feedback' (if available) to inform the pedagogical approach, tone, and specific sub-topics to target.
        2. CORRECT ANSWER: Identify the final absolute correct answer.
        3. OPTIONS: Create 4 distinct options. 
           - IMPORTANT: You MUST place the correct answer as the FIRST option (index 0).
           - Place 3 plausible but incorrect distractors in the other 3 slots.
        
        JSON Requirements:
        - Output a valid JSON array of objects.
        - The "correct" field MUST be 0 (since the correct answer is the first option).
        - Use LaTeX math syntax (e.g., $x^2$) for ALL math expressions.
        - Ensure variety in question types.
        
        Format example:
        [
          {{
            "question": "If $f(x) = x^2$, what is $f'(x)$?",
            "options": ["$2x$", "$x$", "$x^2$", "$0$"],
            "correct": 0,
            "explanation": "To find the derivative of $x^n$, we use the power rule: $n \cdot x^{{n-1}}$. Thus, $f'(x) = 2 \cdot x^{{2-1}} = 2x$.",
            "difficulty": "{difficulty}"
          }}
        ]
        
        Begin by solving the questions step-by-step, then provide the JSON array below.
        """
        
        start_time = time.time()
        ai_response = self._call_ai(prompt)
        cleaned_response = self._clean_json_response(ai_response)
        
        # FIX: Escape LaTeX backslashes before JSON parsing
        escaped_response = self._fix_latex_escapes(cleaned_response)
        
        # Diagnostic logging
        self._log(f"📝 Raw AI Response length: {len(ai_response)} chars", Fore.YELLOW)
        
        try:
            raw_questions = json.loads(escaped_response)
            if isinstance(raw_questions, dict) and 'questions' in raw_questions:
                raw_questions = raw_questions['questions']
            
            if not isinstance(raw_questions, list):
                self._log(f"❌ JSON loaded but not a list: {type(raw_questions)}", Fore.RED)
                return QuizSet(topic, [], {"error": "JSON not a list"})
                
            questions = []
            import random
            for q_data in raw_questions:
                if isinstance(q_data, dict) and 'question' in q_data and 'options' in q_data:
                    orig_options = q_data.get('options', [])[:4]
                    orig_correct = int(q_data.get('correct', 0))
                    
                    # Ensure we have a valid correct index
                    if orig_correct >= len(orig_options):
                        orig_correct = 0
                        
                    correct_answer_str = orig_options[orig_correct]
                    
                    # Shuffle options
                    shuffled_options = list(orig_options)
                    random.shuffle(shuffled_options)
                    
                    # Find new correct index
                    new_correct = shuffled_options.index(correct_answer_str)
                    
                    questions.append(QuizQuestion(
                        question=q_data.get('question', ''),
                        options=shuffled_options,
                        correct=new_correct,
                        explanation=q_data.get('explanation', ''),
                        difficulty=q_data.get('difficulty', difficulty)
                    ))
            
            elapsed = time.time() - start_time
            self._log(f"✅ Successfully parsed {len(questions)} questions in {elapsed:.1f}s", Fore.GREEN)
            
            return QuizSet(
                title=topic,
                questions=questions,
                metadata={
                    "content_size": len(content),
                    "generator": "QuizGenerator v1",
                    "time_seconds": elapsed
                }
            )
            
        except Exception as e:
            self._log(f"❌ Quiz parsing failed: {e}", Fore.RED)
            self._log(f"🗑️ Cleaned Response Sample: {cleaned_response[:500]}...", Fore.RED)
            return QuizSet(topic, [], {"error": str(e)})
