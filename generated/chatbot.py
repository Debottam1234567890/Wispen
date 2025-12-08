import os
import json
import requests
from datetime import datetime
import time

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # Get from https://tavily.com
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"

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

class WebSearchEngine:
    """Handles web search using Tavily API"""
    
    def __init__(self, api_key=None):
        self.api_key = api_key or TAVILY_API_KEY
        self.tavily_url = "https://api.tavily.com/search"
    
    def search(self, query, max_results=5):
        """Perform web search and return results"""
        if not self.api_key:
            return None, "Tavily API key not set. Get one from https://tavily.com"
        
        try:
            payload = {
                "api_key": self.api_key,
                "query": query,
                "search_depth": "advanced",  # Deep research mode
                "include_answer": True,
                "include_raw_content": False,
                "max_results": max_results,
                "include_domains": [],
                "exclude_domains": []
            }
            
            response = requests.post(self.tavily_url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Format search results
            results = []
            if "results" in data:
                for idx, result in enumerate(data["results"][:max_results], 1):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0)
                    })
            
            answer = data.get("answer", "")
            
            return results, answer
            
        except requests.exceptions.RequestException as e:
            return None, f"Search error: {str(e)}"
        except Exception as e:
            return None, f"Error: {str(e)}"

class AITutor:
    def __init__(self, knowledge_base_path="knowledge.txt", web_search_enabled=True):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.api_key = GEMINI_API_KEY
        self.conversation_history = []
        self.knowledge_base = ""
        self.web_search_enabled = web_search_enabled
        self.search_engine = WebSearchEngine()
        self.last_search_results = []
        
        if knowledge_base_path:
            self.load_knowledge_base(knowledge_base_path)
        
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self):
        prompt = """You are an expert AI tutor with deep pedagogical knowledge. Your role is to:

1. **Teach Effectively**: Break down complex concepts into understandable parts
2. **Adapt to Learning Style**: Gauge the student's level and adjust explanations
3. **Encourage Critical Thinking**: Ask guiding questions rather than just giving answers
4. **Provide Examples**: Use real-world examples and analogies
5. **Be Patient and Supportive**: Create a safe learning environment
6. **Check Understanding**: Regularly verify comprehension before moving forward
7. **Use the Socratic Method**: Guide students to discover answers themselves

**Teaching Principles**:
- Start with what the student knows
- Build from simple to complex
- Use multiple explanation methods (visual, verbal, analogical)
- Encourage questions and curiosity
- Provide positive reinforcement
- Correct misconceptions gently

"""
        if self.knowledge_base:
            prompt += f"\n**Knowledge Base Available**: YES\n"
            prompt += f"Use the following knowledge base to answer questions accurately:\n\n{self.knowledge_base}\n\n"
        else:
            prompt += "\n**Knowledge Base**: Not loaded - Use your general knowledge\n\n"
        
        if self.web_search_enabled:
            prompt += "**Web Search**: ENABLED - When you need current information or want to verify facts, you can access web search results that will be provided to you.\n\n"
        
        prompt += "Always maintain an encouraging, patient, and enthusiastic teaching demeanor."
        
        return prompt
    
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
        """Determine if web search is needed for this query"""
        search_keywords = [
            "latest", "recent", "current", "today", "news", "2024", "2025",
            "what's new", "update", "happening now", "this year", "this month"
        ]
        
        user_lower = user_input.lower()
        return any(keyword in user_lower for keyword in search_keywords)
    
    def _perform_web_search(self, query):
        """Perform web search and format results"""
        print(f"{Colors.YELLOW}🔍 Searching the web for: {query}...{Colors.END}")
        
        results, answer = self.search_engine.search(query, max_results=5)
        
        if results is None:
            return f"\n[Web Search Error: {answer}]\n"
        
        self.last_search_results = results
        
        # Format search results for the AI
        search_context = "\n\n--- WEB SEARCH RESULTS ---\n"
        if answer:
            search_context += f"\nQuick Answer: {answer}\n\n"
        
        search_context += "Detailed Results:\n\n"
        for idx, result in enumerate(results, 1):
            search_context += f"{idx}. {result['title']}\n"
            search_context += f"   Source: {result['url']}\n"
            search_context += f"   Content: {result['content'][:500]}...\n\n"
        
        search_context += "--- END SEARCH RESULTS ---\n\n"
        
        print(f"{Colors.GREEN}✓ Found {len(results)} results{Colors.END}\n")
        
        return search_context
    
    def send_message(self, user_input):
        """Send a message to Gemini API and get response"""
        search_context = ""
        
        # Perform web search if enabled and needed
        if self.web_search_enabled and self._should_search(user_input):
            search_context = self._perform_web_search(user_input)
        
        # Add user message with search context to history
        message_with_context = user_input
        if search_context:
            message_with_context = search_context + "\nStudent Question: " + user_input
        
        self.conversation_history.append({
            "role": "user",
            "parts": [{"text": message_with_context}]
        })
        
        # Prepare request body
        request_body = {
            "contents": self.conversation_history,
            "systemInstruction": {
                "parts": [{"text": self.system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.7,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            }
        }
        
        try:
            # Make API request
            response = requests.post(
                f"{GEMINI_API_URL}?key={self.api_key}",
                headers={"Content-Type": "application/json"},
                json=request_body,
                timeout=30
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extract response
            if "candidates" in data and len(data["candidates"]) > 0:
                assistant_text = data["candidates"][0]["content"]["parts"][0]["text"]
                
                # Add assistant response to history (without search context)
                self.conversation_history.append({
                    "role": "model",
                    "parts": [{"text": assistant_text}]
                })
                
                # Add sources if search was performed
                if self.last_search_results:
                    assistant_text += "\n\n" + Colors.CYAN + "📚 Sources:" + Colors.END + "\n"
                    for idx, result in enumerate(self.last_search_results[:3], 1):
                        assistant_text += f"{idx}. {result['title']}\n   {result['url']}\n"
                    self.last_search_results = []
                
                return assistant_text
            else:
                return "Error: No response generated"
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return "Error: Rate limit exceeded. Please wait a moment and try again."
            return f"Error: HTTP {e.response.status_code} - {str(e)}"
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"
        except Exception as e:
            return f"Error: {str(e)}"
    
    def manual_search(self, query):
        """Manually trigger a web search"""
        if not self.web_search_enabled:
            return "Web search is disabled. Enable it with /web on"
        
        search_context = self._perform_web_search(query)
        return search_context
    
    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print(f"{Colors.YELLOW}Conversation history cleared.{Colors.END}\n")
    
    def export_chat(self, filename=None):
        """Export chat history to a file"""
        if not filename:
            filename = f"tutor_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"AI Tutor Session - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                for msg in self.conversation_history:
                    role = "STUDENT" if msg["role"] == "user" else "TUTOR"
                    text = msg["parts"][0]["text"]
                    f.write(f"{role}:\n{text}\n\n")
                    f.write("-" * 80 + "\n\n")
            
            print(f"{Colors.GREEN}✓ Chat exported to: {filename}{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.RED}✗ Error exporting chat: {str(e)}{Colors.END}\n")

def print_banner():
    """Print welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}                           AI TUTOR - CLI{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")
    print(f"{Colors.GREEN}Your personal AI learning assistant powered by Gemini + Web Search{Colors.END}\n")

def print_help():
    """Print help menu"""
    print(f"\n{Colors.BOLD}Available Commands:{Colors.END}")
    print(f"  {Colors.CYAN}/help{Colors.END}        - Show this help menu")
    print(f"  {Colors.CYAN}/clear{Colors.END}       - Clear conversation history")
    print(f"  {Colors.CYAN}/export{Colors.END}      - Export chat to a file")
    print(f"  {Colors.CYAN}/load <file>{Colors.END}  - Load a knowledge base file")
    print(f"  {Colors.CYAN}/search <query>{Colors.END} - Manually search the web")
    print(f"  {Colors.CYAN}/web on{Colors.END}      - Enable web search")
    print(f"  {Colors.CYAN}/web off{Colors.END}     - Disable web search")
    print(f"  {Colors.CYAN}/quit{Colors.END}        - Exit the tutor")
    print()

def main():
    """Main CLI loop"""
    print_banner()
    
    # Check for API keys
    if not GEMINI_API_KEY:
        print(f"{Colors.RED}✗ GEMINI_API_KEY environment variable not set!{Colors.END}")
        print(f"{Colors.YELLOW}Please set it using: export GEMINI_API_KEY='your-api-key'{Colors.END}\n")
        return
    
    if not TAVILY_API_KEY:
        print(f"{Colors.YELLOW}⚠ TAVILY_API_KEY not set. Web search will be disabled.{Colors.END}")
        print(f"{Colors.YELLOW}Get a free API key from: https://tavily.com{Colors.END}\n")
        web_search = False
    else:
        web_search = True
    
    # Initialize tutor
    print(f"{Colors.YELLOW}Initializing AI Tutor...{Colors.END}")
    tutor = AITutor(web_search_enabled=web_search)
    status = "ENABLED" if web_search else "DISABLED"
    print(f"{Colors.GREEN}✓ Tutor ready! Web search: {status}{Colors.END}\n")
    
    print_help()
    print(f"{Colors.BOLD}Start asking questions! (Type /help for commands){Colors.END}\n")
    print(f"{Colors.CYAN}💡 Tip: Use keywords like 'latest', 'recent', 'current' to trigger web search{Colors.END}\n")
    
    # Main loop
    while True:
        try:
            # Get user input
            user_input = input(f"{Colors.BOLD}{Colors.GREEN}You: {Colors.END}").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith('/'):
                cmd_parts = user_input.split(maxsplit=1)
                cmd = cmd_parts[0].lower()
                
                if cmd == '/quit' or cmd == '/exit':
                    print(f"\n{Colors.CYAN}Thanks for learning with me! Goodbye! 👋{Colors.END}\n")
                    break
                
                elif cmd == '/help':
                    print_help()
                
                elif cmd == '/clear':
                    tutor.clear_history()
                
                elif cmd == '/export':
                    tutor.export_chat()
                
                elif cmd == '/load':
                    if len(cmd_parts) < 2:
                        print(f"{Colors.RED}Usage: /load <filepath>{Colors.END}\n")
                    else:
                        tutor.load_knowledge_base(cmd_parts[1])
                
                elif cmd == '/search':
                    if len(cmd_parts) < 2:
                        print(f"{Colors.RED}Usage: /search <query>{Colors.END}\n")
                    else:
                        result = tutor.manual_search(cmd_parts[1])
                        print(result)
                
                elif cmd == '/web':
                    if len(cmd_parts) < 2:
                        status = "ENABLED" if tutor.web_search_enabled else "DISABLED"
                        print(f"{Colors.YELLOW}Web search is currently: {status}{Colors.END}\n")
                    else:
                        if cmd_parts[1].lower() == 'on':
                            if TAVILY_API_KEY:
                                tutor.web_search_enabled = True
                                print(f"{Colors.GREEN}✓ Web search enabled{Colors.END}\n")
                            else:
                                print(f"{Colors.RED}Cannot enable: TAVILY_API_KEY not set{Colors.END}\n")
                        elif cmd_parts[1].lower() == 'off':
                            tutor.web_search_enabled = False
                            print(f"{Colors.YELLOW}Web search disabled{Colors.END}\n")
                        else:
                            print(f"{Colors.RED}Usage: /web [on|off]{Colors.END}\n")
                
                else:
                    print(f"{Colors.RED}Unknown command. Type /help for available commands.{Colors.END}\n")
                
                continue
            
            # Send message to tutor
            print(f"\n{Colors.CYAN}Tutor is thinking...{Colors.END}\n")
            response = tutor.send_message(user_input)
            
            # Print response
            print(f"{Colors.BOLD}{Colors.BLUE}Tutor:{Colors.END} {response}\n")
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}Thanks for learning with me! Goodbye! 👋{Colors.END}\n")
            break
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.END}\n")

if __name__ == "__main__":
    main()