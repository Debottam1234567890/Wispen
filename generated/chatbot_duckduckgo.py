import os
import json
import requests
from datetime import datetime
import time
from urllib.parse import quote
from pathlib import Path

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

# Memory file path
MEMORY_FILE = "tutor_memory.json"

# Colors for CLI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class WebSearch:
    """Enhanced web search using DuckDuckGo and SerpAPI fallback"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def search(self, query, max_results=5):
        """Perform comprehensive web search"""
        try:
            # Clean and optimize search query
            search_query = self._optimize_query(query)
            print(f"{Colors.YELLOW}🔍 Optimized search: {search_query}{Colors.END}")
            
            # Try DuckDuckGo Instant Answer API
            results = self._duckduckgo_search(search_query, max_results)
            
            if results and len(results) > 0:
                return results, f"Found {len(results)} relevant sources"
            
            # Fallback message
            return [{
                "title": f"Web search for: {query}",
                "url": f"https://duckduckgo.com/?q={quote(query)}",
                "content": f"Search the web for more information about '{query}'. The query has been optimized for better results.",
                "score": 0.5
            }], "Limited results found - try more specific keywords"
            
        except Exception as e:
            return None, f"Search error: {str(e)}"
    
    def _optimize_query(self, query):
        """Optimize search query for better results"""
        # Remove filler words
        filler_words = ['the', 'a', 'an', 'could', 'please', 'can', 'you', 'give', 'me', 'tell', 'about']
        words = query.lower().split()
        optimized = [w for w in words if w not in filler_words]
        
        # Join and clean
        optimized_query = ' '.join(optimized)
        
        # Add quotes for exact phrases if NCERT/book related
        if 'ncert' in query.lower() or 'class' in query.lower():
            # Extract class and subject
            optimized_query = f"NCERT {optimized_query}"
        
        return optimized_query[:200]  # Limit length
    
    def _duckduckgo_search(self, query, max_results):
        """Search using DuckDuckGo API"""
        try:
            url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Get abstract
            abstract = data.get('Abstract', '')
            abstract_url = data.get('AbstractURL', '')
            abstract_source = data.get('AbstractSource', '')
            
            if abstract:
                results.append({
                    "title": abstract_source or "Overview",
                    "url": abstract_url,
                    "content": abstract,
                    "score": 1.0
                })
            
            # Get related topics
            related = data.get('RelatedTopics', [])
            for item in related[:max_results]:
                if isinstance(item, dict):
                    if 'Text' in item:
                        results.append({
                            "title": item.get('Text', '')[:100],
                            "url": item.get('FirstURL', ''),
                            "content": item.get('Text', ''),
                            "score": 0.8
                        })
                    elif 'Topics' in item:
                        # Nested topics
                        for subtopic in item['Topics'][:2]:
                            if 'Text' in subtopic:
                                results.append({
                                    "title": subtopic.get('Text', '')[:100],
                                    "url": subtopic.get('FirstURL', ''),
                                    "content": subtopic.get('Text', ''),
                                    "score": 0.7
                                })
            
            return results[:max_results]
            
        except Exception as e:
            print(f"{Colors.RED}DuckDuckGo search failed: {str(e)}{Colors.END}")
            return []

class StudentMemory:
    """Manages student profile and learning progress"""
    
    def __init__(self, memory_file=MEMORY_FILE):
        self.memory_file = memory_file
        self.memory = self._load_memory()
    
    def _load_memory(self):
        """Load memory from file"""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        # Default memory structure
        return {
            "student_name": None,
            "grade_level": None,
            "subjects_of_interest": [],
            "difficulty_preference": "intermediate",
            "learning_style": "balanced",  # visual, verbal, balanced
            "topics_learned": [],
            "strengths": [],
            "areas_for_improvement": [],
            "last_session": None,
            "total_sessions": 0,
            "quiz_scores": {},
            "interaction_count": 0
        }
    
    def save_memory(self):
        """Save memory to file"""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
        except Exception as e:
            print(f"{Colors.RED}Failed to save memory: {str(e)}{Colors.END}")
    
    def update_profile(self, key, value):
        """Update student profile"""
        if key in self.memory:
            self.memory[key] = value
            self.save_memory()
    
    def add_topic_learned(self, topic):
        """Add a topic to learned list"""
        if topic not in self.memory["topics_learned"]:
            self.memory["topics_learned"].append(topic)
            self.save_memory()
    
    def get_personalized_prompt(self):
        """Generate personalized context for AI"""
        context = ""
        
        if self.memory["student_name"]:
            context += f"Student Name: {self.memory['student_name']}\n"
        
        if self.memory["grade_level"]:
            context += f"Grade Level: {self.memory['grade_level']}\n"
        
        if self.memory["difficulty_preference"]:
            context += f"Preferred Difficulty: {self.memory['difficulty_preference']}\n"
        
        if self.memory["learning_style"]:
            context += f"Learning Style: {self.memory['learning_style']}\n"
        
        if self.memory["topics_learned"]:
            context += f"Previously Learned: {', '.join(self.memory['topics_learned'][-5:])}\n"
        
        if self.memory["areas_for_improvement"]:
            context += f"Areas to Focus: {', '.join(self.memory['areas_for_improvement'])}\n"
        
        return context

class AITutor:
    def __init__(self, knowledge_base_path=None, web_search_enabled=True):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.api_key = GEMINI_API_KEY
        self.conversation_history = []
        self.knowledge_base = ""
        self.web_search_enabled = web_search_enabled
        self.search_engine = WebSearch()
        self.memory = StudentMemory()
        self.last_search_results = []
        self.current_subject = "General"
        
        if knowledge_base_path:
            self.load_knowledge_base(knowledge_base_path)
        
        self.system_prompt = self._create_system_prompt()
        
        # Update session info
        self.memory.memory["total_sessions"] += 1
        self.memory.memory["last_session"] = datetime.now().isoformat()
        self.memory.save_memory()
    
    def _create_system_prompt(self):
        prompt = """You are an expert AI tutor for ALL ACADEMIC SUBJECTS. You are a world-class educator who is HELPFUL and ENGAGING, not frustrating.

🎓 **CORE TEACHING PHILOSOPHY:**

**BE REASONABLE - NOT PURELY SOCRATIC:**
- If student says "I don't know" or "no" → EXPLAIN DIRECTLY with clear information
- If student shows some knowledge → Guide with questions to deepen understanding
- If student asks for help solving something → Work through it together
- NEVER go in circles - 2 questions maximum, then provide the answer with context

**Golden Rule:**
- ONE initial question to assess knowledge is fine
- If they don't know → TEACH them immediately with interesting facts and context
- If they know something → Build on it with guided questions
- If they're stuck → Help them, don't interrogate them

**Adaptive Difficulty:**
- Beginner (says "no", "I don't know") → Full, engaging explanation with examples
- Intermediate (partial knowledge) → Quick explanation + deeper questions
- Advanced (confident) → Challenge with extensions and applications

**Personalized Learning:**
"""
        # Add student context
        student_context = self.memory.get_personalized_prompt()
        if student_context:
            prompt += f"\n**STUDENT PROFILE:**\n{student_context}\n"
        
        prompt += """
**TEACHING APPROACH BY SITUATION:**

1. **Student Says "I Don't Know" / "No" / "Nothing":**
   ❌ DON'T: Ask more questions
   ✅ DO: Give a clear, engaging explanation immediately
   
   Example:
   Student: "Who built the Taj Mahal?"
   You: "The Taj Mahal was built by Emperor Shah Jahan in 1632-1653. Here's the beautiful story behind it: Shah Jahan built it as a memorial for his beloved wife, Mumtaz Mahal, who died during childbirth. It took 20,000 workers and 22 years to complete. It's made of white marble and is considered one of the most beautiful buildings in the world. The name 'Taj Mahal' means 'Crown of Palaces'."

2. **Student Shows Partial Knowledge:**
   - Acknowledge what they know
   - Fill in gaps
   - Ask ONE follow-up question to deepen
   
   Example:
   Student: "I know Taj Mahal is in India"
   You: "Exactly! It's in Agra, India. Now let me tell you the fascinating story... [explanation]. What do you think motivated Shah Jahan to build something so grand?"

3. **Student Asks "Why are you asking questions?" or seems frustrated:**
   - IMMEDIATELY provide the answer
   - Apologize for confusion
   - Give rich context
   
   Example:
   "You're right - let me just tell you! [Full explanation with interesting details]"

4. **Student Wants to Solve Problems (Math, Science):**
   - Work through it TOGETHER step-by-step
   - Show the process, explain WHY
   - Let them try steps when ready
   
   Example:
   Student: "Solve x² + 5x + 6 = 0"
   You: "Great! Let's solve this together. This is a quadratic equation, and we can factor it. We need two numbers that multiply to 6 and add to 5. Those numbers are 2 and 3. So we get (x+2)(x+3)=0. Therefore x=-2 or x=-3. Want to try a similar one?"

**RESPONSE STYLE:**
- Be conversational and friendly
- Make learning interesting with stories, facts, connections
- Use proper markdown formatting
- Keep explanations clear but engaging
- End with "Want to learn more about this?" or "Any questions?"

**NEVER:**
- Ask more than 2 questions without giving information
- Use "Before I tell you..." repeatedly
- Say "Let me ask you first..." to frustrated students
- Keep probing when student clearly doesn't know

**RESPONSE FORMAT (MARKDOWN):**

Use proper markdown formatting:

# Main Topic
## Subtopic
### Key Point

**Bold** for emphasis
*Italic* for terms
`code` for technical terms
- Bullet points for lists
1. Numbered lists for steps

> Blockquotes for important notes

```language
Code blocks when needed
```

Mathematical equations: Use clear notation like x² or (x + y) / z

**SCAFFOLDING TECHNIQUE:**
1. Ask what they already know about the topic
2. Pose guiding questions before explaining
3. Let them attempt problems first
4. Provide hints progressively (mild → stronger)
5. Only give full solution if they're truly stuck
6. Always end with a comprehension check question

**EXAMPLES:**

✅ GOOD (Helpful Teaching):
Student: "What is photosynthesis?"
Tutor: "Photosynthesis is how plants make their own food! Here's how it works: Plants take in carbon dioxide from the air, water from the soil, and energy from sunlight. They use these to create glucose (sugar) for energy and release oxygen as a byproduct. That's why we need plants - they give us oxygen to breathe! Think of it like a plant's kitchen where sunlight is the stove. Have you seen how plants grow toward windows? That's them seeking sunlight for photosynthesis!"

✅ GOOD (Problem Solving):
Student: "Help me solve x² + 5x + 6 = 0"
Tutor: "Absolutely! Let's solve this quadratic equation together. 

We can factor this. We need two numbers that:
- Multiply to give 6 (the last term)
- Add to give 5 (the middle coefficient)

Those numbers are 2 and 3 because 2 × 3 = 6 and 2 + 3 = 5.

So: x² + 5x + 6 = (x + 2)(x + 3) = 0

This means either (x + 2) = 0 OR (x + 3) = 0
Therefore: x = -2 or x = -3

Let's verify: If x = -2: (-2)² + 5(-2) + 6 = 4 - 10 + 6 = 0 ✓

Make sense? Want to try another one?"

❌ BAD (Frustrating):
Student: "I don't know anything about photosynthesis"
Tutor: "Before I explain, what do you think plants need to survive? Where do you think they get energy? Have you noticed..." [Too many questions!]

❌ BAD (Problem Solving):
Student: "Solve x² + 5x + 6 = 0"
Tutor: "Can you tell me what you know about factoring? What two numbers multiply to 6?" [Just work through it together!]

**WEB SEARCH CONTEXT:**
When web search results are provided, synthesize information naturally into your explanation. Cite sources when using specific facts.
"""
        
        if self.knowledge_base:
            prompt += f"\n**KNOWLEDGE BASE AVAILABLE:**\nYou have access to reference material. Use it to verify accuracy and provide detailed explanations when needed.\n"
        
        if self.web_search_enabled:
            prompt += "\n**WEB SEARCH:** Enabled for current information.\n"
        
        prompt += f"\n**CURRENT SUBJECT FOCUS:** {self.current_subject}\n"
        
        prompt += """
**INTERACTION GUIDELINES:**
- Be warm, encouraging, and patient
- Celebrate small wins and progress
- Use emojis sparingly for engagement
- Ask follow-up questions to check understanding
- Adapt your teaching style based on student responses
- Remember context from earlier in conversation
- If student is frustrated, simplify and encourage

**CRITICAL RULES:**
- NEVER just give answers - guide to discovery
- ALWAYS assess understanding level first
- Format ALL responses in proper markdown
- End with a question to check comprehension
- Be conversational yet educational

Let's inspire a love of learning! 🌟
"""
        
        return prompt
    
    def set_subject(self, subject):
        """Set the current subject focus"""
        self.current_subject = subject
        self.system_prompt = self._create_system_prompt()
        print(f"{Colors.GREEN}✓ Subject set to: {subject}{Colors.END}\n")
    
    def load_knowledge_base(self, filepath):
        """Load knowledge base from a text file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.knowledge_base = f.read()
            print(f"{Colors.GREEN}✓ Knowledge base loaded: {filepath} ({len(self.knowledge_base)} characters){Colors.END}\n")
            self.system_prompt = self._create_system_prompt()
        except FileNotFoundError:
            print(f"{Colors.RED}✗ Knowledge base file not found: {filepath}{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.RED}✗ Error loading knowledge base: {str(e)}{Colors.END}\n")
    
    def _should_search(self, user_input):
        """Determine if web search is needed"""
        search_triggers = [
            "latest", "recent", "current", "today", "news", "2024", "2025",
            "what's new", "update", "developments", "this year", "this month",
            "ncert", "textbook", "curriculum", "syllabus", "book"
        ]
        
        user_lower = user_input.lower()
        return any(trigger in user_lower for trigger in search_triggers)
    
    def _perform_web_search(self, query):
        """Perform web search and format results"""
        results, message = self.search_engine.search(query, max_results=5)
        
        if results is None:
            return f"\n[Web Search Error: {message}]\n"
        
        self.last_search_results = results
        
        # Format search results
        search_context = "\n\n=== WEB SEARCH RESULTS ===\n"
        search_context += f"Query: {query}\n"
        search_context += f"Status: {message}\n\n"
        
        for idx, result in enumerate(results, 1):
            search_context += f"[Source {idx}]\n"
            search_context += f"Title: {result['title']}\n"
            if result['url']:
                search_context += f"URL: {result['url']}\n"
            search_context += f"Content: {result['content']}\n\n"
        
        search_context += "=== END SEARCH RESULTS ===\n\n"
        
        print(f"{Colors.GREEN}✓ {message}{Colors.END}\n")
        
        return search_context
    
    def send_message(self, user_input):
        """Send a message to Gemini API and get response"""
        # Update interaction count
        self.memory.memory["interaction_count"] += 1
        
        search_context = ""
        
        # Perform web search if enabled and needed
        if self.web_search_enabled and self._should_search(user_input):
            print(f"{Colors.YELLOW}🔍 Searching the web...{Colors.END}")
            search_context = self._perform_web_search(user_input)
        
        # Build message with context
        message_parts = []
        
        if search_context:
            message_parts.append(search_context)
        
        message_parts.append(f"Student Question: {user_input}")
        
        message_with_context = "\n".join(message_parts)
        
        # Add to conversation history
        self.conversation_history.append({
            "role": "user",
            "parts": [{"text": message_with_context}]
        })
        
        # Prepare request
        request_body = {
            "contents": self.conversation_history[-10:],  # Keep last 10 exchanges
            "systemInstruction": {
                "parts": [{"text": self.system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.8,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 4096,
            }
        }
        
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=request_body,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            if "candidates" in data and len(data["candidates"]) > 0:
                assistant_text = data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Add to history (clean version without search)
                self.conversation_history.append({
                    "role": "model",
                    "parts": [{"text": assistant_text}]
                })
                
                # Format markdown properly
                formatted_text = self._format_markdown(assistant_text)
                
                # Add sources if available
                if self.last_search_results:
                    formatted_text += "\n\n" + self._format_sources()
                    self.last_search_results = []
                
                # Update memory based on interaction
                self._update_memory(user_input, assistant_text)
                
                return formatted_text
            else:
                return "Error: No response generated"
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return "⚠️ Rate limit exceeded. Please wait 60 seconds and try again."
            return f"❌ HTTP Error {e.response.status_code}: {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _format_markdown(self, text):
        """Ensure proper markdown formatting"""
        # This is already handled by the terminal, just return clean text
        return text
    
    def _format_sources(self):
        """Format sources nicely"""
        sources = "\n" + "─" * 80 + "\n"
        sources += f"{Colors.CYAN}📚 Sources & References:{Colors.END}\n\n"
        
        for idx, result in enumerate(self.last_search_results[:3], 1):
            sources += f"{idx}. **{result['title'][:80]}**\n"
            if result['url']:
                sources += f"   🔗 {result['url']}\n"
            sources += "\n"
        
        return sources
    
    def _update_memory(self, user_input, assistant_text):
        """Update student memory based on interaction"""
        # Extract topics (basic NLP)
        keywords = ["photosynthesis", "newton", "pythagoras", "quadratic", "algebra", 
                    "calculus", "physics", "chemistry", "biology", "history"]
        
        for keyword in keywords:
            if keyword in user_input.lower() or keyword in assistant_text.lower():
                self.memory.add_topic_learned(keyword.title())
        
        # Save periodically
        if self.memory.memory["interaction_count"] % 5 == 0:
            self.memory.save_memory()
    
    def setup_profile(self):
        """Interactive profile setup"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}👋 Let's personalize your learning experience!{Colors.END}\n")
        
        name = input(f"{Colors.GREEN}What's your name? {Colors.END}").strip()
        if name:
            self.memory.update_profile("student_name", name)
            print(f"\n{Colors.CYAN}Nice to meet you, {name}! 😊{Colors.END}\n")
        
        grade = input(f"{Colors.GREEN}What grade/class are you in? (e.g., 7, 10, College) {Colors.END}").strip()
        if grade:
            self.memory.update_profile("grade_level", grade)
        
        print(f"\n{Colors.YELLOW}Learning Style:{Colors.END}")
        print("1. Visual (diagrams, examples)")
        print("2. Verbal (detailed explanations)")
        print("3. Balanced (mix of both)")
        
        style_choice = input(f"{Colors.GREEN}Choose (1-3): {Colors.END}").strip()
        style_map = {"1": "visual", "2": "verbal", "3": "balanced"}
        if style_choice in style_map:
            self.memory.update_profile("learning_style", style_map[style_choice])
        
        print(f"\n{Colors.GREEN}✓ Profile saved! I'll personalize our sessions based on your preferences.{Colors.END}\n")
        self.system_prompt = self._create_system_prompt()
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print(f"{Colors.YELLOW}Conversation history cleared.{Colors.END}\n")
    
    def export_chat(self, filename=None):
        """Export chat history"""
        if not filename:
            filename = f"tutor_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"AI Tutor Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Subject: {self.current_subject}\n")
                if self.memory.memory["student_name"]:
                    f.write(f"Student: {self.memory.memory['student_name']}\n")
                f.write("=" * 80 + "\n\n")
                
                for msg in self.conversation_history:
                    role = "STUDENT" if msg["role"] == "user" else "TUTOR"
                    text = msg["parts"][0]["text"]
                    # Clean web search context from exports
                    if "=== WEB SEARCH RESULTS ===" not in text:
                        f.write(f"{role}:\n{text}\n\n")
                        f.write("-" * 80 + "\n\n")
            
            print(f"{Colors.GREEN}✓ Chat exported to: {filename}{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.RED}✗ Error exporting chat: {str(e)}{Colors.END}\n")

def print_banner():
    """Print welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}                    🎓 AI TUTOR - PERSONALIZED LEARNING 🎓{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")
    print(f"{Colors.GREEN}Adaptive AI tutor for ALL subjects with personalized learning paths{Colors.END}")
    print(f"{Colors.CYAN}Powered by Gemini AI + Enhanced Web Search + Student Memory{Colors.END}\n")

def print_help():
    """Print help menu"""
    print(f"\n{Colors.BOLD}📖 Available Commands:{Colors.END}")
    print(f"  {Colors.CYAN}/help{Colors.END}           - Show this help menu")
    print(f"  {Colors.CYAN}/profile{Colors.END}        - Set up your learning profile")
    print(f"  {Colors.CYAN}/subject <name>{Colors.END} - Set current subject focus")
    print(f"  {Colors.CYAN}/clear{Colors.END}          - Clear conversation history")
    print(f"  {Colors.CYAN}/export{Colors.END}         - Export chat to a file")
    print(f"  {Colors.CYAN}/load <file>{Colors.END}    - Load a knowledge base file")
    print(f"  {Colors.CYAN}/memory{Colors.END}         - View your learning profile")
    print(f"  {Colors.CYAN}/web on/off{Colors.END}     - Toggle web search")
    print(f"  {Colors.CYAN}/quit{Colors.END}           - Exit the tutor")
    print()

def main():
    """Main CLI loop"""
    print_banner()
    
    if not GEMINI_API_KEY:
        print(f"{Colors.RED}✗ GEMINI_API_KEY environment variable not set!{Colors.END}")
        print(f"{Colors.YELLOW}Set it: export GEMINI_API_KEY='your-key'{Colors.END}\n")
        return
    
    print(f"{Colors.YELLOW}Initializing AI Tutor...{Colors.END}")
    tutor = AITutor(web_search_enabled=True)
    print(f"{Colors.GREEN}✓ Tutor ready! Web search: ENABLED{Colors.END}\n")
    
    # Check if first time user
    if not tutor.memory.memory["student_name"]:
        setup = input(f"{Colors.CYAN}Would you like to set up your learning profile? (y/n): {Colors.END}").strip().lower()
        if setup == 'y':
            tutor.setup_profile()
    
    print_help()
    print(f"{Colors.BOLD}🚀 Start learning! Ask me anything!{Colors.END}\n")
    
    while True:
        try:
            user_input = input(f"{Colors.BOLD}{Colors.GREEN}You: {Colors.END}").strip()
            
            if not user_input:
                continue
            
            if user_input.startswith('/'):
                cmd_parts = user_input.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                
                if cmd in ['/quit', '/exit']:
                    print(f"\n{Colors.CYAN}Keep learning and stay curious! 🌟 Goodbye!{Colors.END}\n")
                    break
                
                elif cmd == '/help':
                    print_help()
                
                elif cmd == '/profile':
                    tutor.setup_profile()
                
                elif cmd == '/memory':
                    print(f"\n{Colors.CYAN}📊 Your Learning Profile:{Colors.END}\n")
                    print(json.dumps(tutor.memory.memory, indent=2))
                    print()
                
                elif cmd == '/subject':
                    if len(cmd_parts) < 2:
                        print(f"{Colors.RED}Usage: /subject <subject_name>{Colors.END}\n")
                    else:
                        tutor.set_subject(cmd_parts[1])
                
                elif cmd == '/clear':
                    tutor.clear_history()
                
                elif cmd == '/export':
                    tutor.export_chat()
                
                elif cmd == '/load':
                    if len(cmd_parts) < 2:
                        print(f"{Colors.RED}Usage: /load <filepath>{Colors.END}\n")
                    else:
                        tutor.load_knowledge_base(cmd_parts[1])
                
                elif cmd == '/web':
                    if len(cmd_parts) < 2:
                        status = "ENABLED" if tutor.web_search_enabled else "DISABLED"
                        print(f"{Colors.YELLOW}Web search: {status}{Colors.END}\n")
                    else:
                        if cmd_parts[1].lower() == 'on':
                            tutor.web_search_enabled = True
                            print(f"{Colors.GREEN}✓ Web search enabled{Colors.END}\n")
                        elif cmd_parts[1].lower() == 'off':
                            tutor.web_search_enabled = False
                            print(f"{Colors.YELLOW}Web search disabled{Colors.END}\n")
                
                else:
                    print(f"{Colors.RED}Unknown command. Type /help{Colors.END}\n")
                
                continue
            
            print(f"\n{Colors.CYAN}🤔 Thinking...{Colors.END}\n")
            response = tutor.send_message(user_input)
            
            print(f"{Colors.BOLD}{Colors.BLUE}Tutor:{Colors.END}\n{response}\n")
            print(f"{Colors.CYAN}{'─' * 80}{Colors.END}\n")
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}Keep learning! Goodbye! 🌟{Colors.END}\n")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.END}\n")

if __name__ == "__main__":
    main()