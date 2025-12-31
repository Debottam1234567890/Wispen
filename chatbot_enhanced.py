import os
import io
import json
import requests
from datetime import datetime
import time
from urllib.parse import quote, urlparse
from pathlib import Path
import base64
import mimetypes
from typing import List, Dict, Optional, Tuple, Generator
import hashlib
from collections import defaultdict
import re
import uuid
from web_search_client import WebSearchClient
import asyncio
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
    print("⚠️  edge_tts not installed. Run: pip install edge-tts")

import threading # Added for background extraction

class BookshelfRAG:
    """
    RAG engine for user's bookshelf items.
    """
    
    # Simple static dicts for caching
    _text_cache = {}
    _extraction_status = {} # item_id -> 'running' | 'completed' | 'failed'

    @staticmethod
    def extract_text(file_bytes: bytes, file_type: str, start_page: int = 0, max_pages: int = None) -> str:
        """Extract text from file bytes with pagination."""
        try:
            if file_type == 'pdf' or file_type == 'application/pdf':
                if not DOCUMENT_PROCESSING_AVAILABLE:
                    return "[PDF processing not available]"
                
                try:
                    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
                    total_pages = len(reader.pages)
                    text = ""
                    
                    end_page = total_pages
                    if max_pages:
                        end_page = min(start_page + max_pages, total_pages)
                    
                    print(f"DEBUG: Extracting PDF pages {start_page} to {end_page} (Total: {total_pages})")
                    
                    for i in range(start_page, end_page):
                        page = reader.pages[i]
                        extracted = page.extract_text()
                        if extracted:
                            text += extracted + "\n"
                        # No print needed for background usually, unless verbose
                            
                    return text
                except Exception as pdf_err:
                    print(f"PDF Error: {pdf_err}")
                    return ""
                
            else:
                # Text files don't support pagination easily in this simple impl
                # Just return full text
                try:
                    return file_bytes.decode('utf-8')
                except UnicodeDecodeError:
                    return file_bytes.decode('latin-1', errors='ignore')
                
        except Exception as e:
            print(f"Extraction Error: {e}")
            return ""

    @staticmethod
    def _background_extract_worker(item_id: str, file_bytes: bytes, file_type: str, start_page: int):
        """Worker to extract remaining pages in background."""
        print(f"DEBUG: Starting background extraction for {item_id} from page {start_page}")
        try:
            # Extract EVERYTHING remaining
            remaining_text = BookshelfRAG.extract_text(file_bytes, file_type, start_page=start_page)
            
            # Update cache safely
            if item_id in BookshelfRAG._text_cache:
                BookshelfRAG._text_cache[item_id] += "\n" + remaining_text
            else:
                BookshelfRAG._text_cache[item_id] = remaining_text
                
            BookshelfRAG._extraction_status[item_id] = 'completed'
            print(f"DEBUG: Background extraction completed for {item_id}. Total cache size: {len(BookshelfRAG._text_cache[item_id])} chars")
            
        except Exception as e:
            print(f"DEBUG: Background extraction failed: {e}")
            BookshelfRAG._extraction_status[item_id] = 'failed'

    @staticmethod
    def search(bookshelf_items: List[Dict], query: str, top_k: int = 20, user_id: str = None, opensearch_client=None) -> List[Dict]:
        """
        Search bookshelf items for relevant chunks.
        Uses OpenSearch if available, falls back to legacy/simple text matching.
        """
        print(f"DEBUG: RAG Search called with query: '{query}'")
        
        # 1. Try OpenSearch First
        # Use injected client (preferred) or global fallback
        client = opensearch_client if opensearch_client else ws_manager
        
        if OPENSEARCH_AVAILABLE and client and user_id:
            try:
                print(f"DEBUG: Delegating to OpenSearch for user {user_id}")
                results = client.search(query, user_id, top_k=top_k)
                
                # Return OpenSearch results directly
                # No more fragile chapter detection
                if results:
                    return results
                else:
                    print("DEBUG: OpenSearch returned no results, falling back to legacy.")
            except Exception as e:
                print(f"OpenSearch Search Error: {e}")

        # Fallback to legacy logic if OpenSearch fails or returned nothing (e.g. not indexed yet)
        if not query or not bookshelf_items:
            return []

        # Remove the previous incomplete block if it exists
        
        # ... (Legacy logic below)


        query_terms = set(query.lower().split())
        relevant_chunks = []
        
        chunk_size = 800
        overlap = 150

        for item in bookshelf_items:
            item_id = item.get('id') or item.get('storageUrl')
            if not item_id: continue

            # Check Status
            status = BookshelfRAG._extraction_status.get(item_id)
            
            # Check Text Cache
            text = BookshelfRAG._text_cache.get(item_id, "")
            
            # Hybrid Extraction Logic
            if not text and status != 'running':
                # Need to download and start process
                print(f"DEBUG: No text for {item.get('title')}, starting Hybrid Extraction...")
                
                file_bytes = None
                # Download logic (reused)
                if item.get('content'):
                     try: file_bytes = base64.b64decode(item['content'])
                     except: pass
                elif item.get('storageUrl'):
                    try:
                        resp = requests.get(item['storageUrl'], timeout=10)
                        if resp.status_code == 200: file_bytes = resp.content
                    except: pass
                
                if file_bytes:
                    # 1. Immediate Extraction (First 50 pages)
                    initial_limit = 50
                    initial_text = BookshelfRAG.extract_text(file_bytes, item.get('fileType', ''), max_pages=initial_limit)
                    
                    # Update Cache immediately
                    BookshelfRAG._text_cache[item_id] = initial_text
                    text = initial_text # Use this for current search
                    
                    # 2. Background Extraction (Rest of book)
                    # Only for PDF basically
                    file_type = item.get('fileType', item.get('type', ''))
                    if 'pdf' in file_type.lower() or 'pdf' in str(item.get('title')).lower():
                        BookshelfRAG._extraction_status[item_id] = 'running'
                        thread = threading.Thread(
                            target=BookshelfRAG._background_extract_worker,
                            args=(item_id, file_bytes, file_type, initial_limit)
                        )
                        thread.daemon = True
                        thread.start()
            
            # Determine if we should warn user about partial results
            # access global status inside loop?
            
            if not text:
                continue

            # Search Logic (Standard)
            for i in range(0, len(text), chunk_size - overlap):
                chunk = text[i:i + chunk_size]
                if len(chunk) < 50: continue
                
                score = 0
                chunk_lower = chunk.lower()
                for term in query_terms:
                    if term in chunk_lower: score += 1
                
                if score > 0:
                    note = ""
                    if BookshelfRAG._extraction_status.get(item_id) == 'running':
                        note = " [Note: Still reading rest of book...]"
                        
                    relevant_chunks.append({
                        'score': score,
                        'content': chunk + note,
                        'source': item.get('title', 'Unknown Source'),
                        'page': 'N/A'
                    })
        
        print(f"DEBUG: Found {len(relevant_chunks)} relevant chunks before sorting.")

        # Sort by score desc
        relevant_chunks.sort(key=lambda x: x['score'], reverse=True)
        return relevant_chunks[:top_k]


try:
    from processer_for_upload import (
        EnhancedFileProcessor, RAGDocumentProcessor, 
        EmbeddingCache, HybridEmbedding, WebSearchIntegration
    )
    RAG_PROCESSOR_AVAILABLE = True
except ImportError:
    RAG_PROCESSOR_AVAILABLE = False
    print("⚠️  RAG processor not available. Run: pip install sentence-transformers tavily-python")

# Try to import OpenSearch Manager
try:
    from backend.opensearch_client import ws_manager
    OPENSEARCH_AVAILABLE = True
except ImportError:
    # If running from root, maybe it's just opensearch_client if path messed up, 
    # but likely backend.opensearch_client
    try:
        from opensearch_client import ws_manager
        OPENSEARCH_AVAILABLE = True
    except:
        OPENSEARCH_AVAILABLE = False
        print("⚠️  OpenSearch client not available.")

# Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("⚠️  Firebase Admin SDK not installed. Run: pip install firebase-admin")

# PDF and document processing
try:
    import PyPDF2
    from PIL import Image
    import pytesseract
    DOCUMENT_PROCESSING_AVAILABLE = True
except ImportError:
    DOCUMENT_PROCESSING_AVAILABLE = False
    print("⚠️  Document processing libraries not available. Run: pip install PyPDF2 pillow pytesseract")

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FIREBASE_CREDENTIALS_PATH = "/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json"
STABLE_DIFFUSION_API_KEY = os.getenv("STABLE_DIFFUSION_API_KEY", "")
STABLE_DIFFUSION_API_URL = "https://api.stability.ai/v1/generate/ultra"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

# Groq Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

MURF_API_KEY = os.getenv("MURF_API_KEY", "")

class GeminiChat:
    """Gemini Chat Integration (Google Generative AI)"""
    
    @staticmethod
    def chat(user_message: str, history: List[Dict] = [], model: str = "gemini-2.0-flash") -> str:
        """
        Send a message to Gemini API.
        """
        if not GEMINI_API_KEY:
            return "Error: No Gemini API key configured. Please set GEMINI_API_KEY in .env"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        
        # Prepare contents
        contents = []
        
        # Add conversation history
        for msg in history[-15:]:
            role = msg.get("role", "user")
            if role == "ai": role = "model"
            elif role == "assistant": role = "model"
            contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
            
        contents.append({"role": "user", "parts": [{"text": user_message}]})
        
        try:
            response = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "contents": contents,
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 4096,
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    return data["candidates"][0]["content"]["parts"][0]["text"]
                return "Gemini returned no response."
            else:
                print(f"Gemini API Error {response.status_code}: {response.text}")
                return f"Gemini API Error: {response.status_code}"

        except Exception as e:
            print(f"Gemini Request Error: {e}")
            return f"Gemini Request Error: {str(e)}"



class GroqChat:
    """Groq Chat Integration (Llama 3)"""
    
    @staticmethod
    def chat(user_message: str, history: List[Dict] = [], model: Optional[str] = None, json_mode: bool = False) -> str:
        """
        Send a message to Groq with fallback to smaller model on rate limit.
        """
        if not GROQ_API_KEY:
            return "Error: No Groq API key configured. Please set GROQ_API_KEY in .env"

        models_to_try = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-1b-preview",
            "llama-3.2-3b-preview",
            "mixtral-8x7b-32768",
            "gemma2-9b-it"
        ]

        system_instruction = GroqChat._get_system_instruction()
        
        # Prepare messages
        messages = [{"role": "system", "content": system_instruction}]
        
        # Add conversation history (Limit to last 15 to save tokens)
        for msg in history[-15:]:
            role = msg.get("role", "user")
            if role == "ai": role = "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_message})
        
        models_list = models_to_try
        if model:
            models_list = [model] + [m for m in models_to_try if m != model]

        for current_model in models_list:
            for attempt in range(2): # Double attempt per model
                try:
                    # print(f"{Colors.CYAN}🤖 Sending to Groq ({current_model}, try {attempt+1})...{Colors.END}")
                    payload = {
                        "model": current_model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1024
                    }
                    if json_mode:
                        payload["response_format"] = {"type": "json_object"}

                    response = requests.post(
                        GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json=payload,
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if "choices" in data and len(data["choices"]) > 0:
                            return data["choices"][0]["message"]["content"]
                    elif response.status_code == 429:
                        wait = (attempt + 1) * 4
                        print(f"{Colors.YELLOW}⚠️ Groq Rate Limit (429) on {current_model}. Waiting {wait}s...{Colors.END}")
                        time.sleep(wait)
                        continue # Retry same model or move on
                    
                    # If other error, print and return
                    if response.status_code != 200:
                         print(f"Error {response.status_code}: {response.text}")
                         break # Move to next model

                except Exception as e:
                    print(f"{Colors.YELLOW}⚠️ Request error on {model}: {e}{Colors.END}")
                    time.sleep(1)
                    continue

        return "I'm sorry, I'm currently experiencing high traffic. Please try again in a moment."

    @staticmethod
    def chat_stream(user_message: str, history: List[Dict] = []) -> Generator[str, None, None]:
        """
        Stream message from Groq with fallback to smaller model on rate limit.
        """
        if not GROQ_API_KEY:
            yield "Error: No Groq API key configured."
            return

        models_to_try = [
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "mixtral-8x7b-32768",
            "llama-3.1-8b-instant",
            "llama3-70b-8192",
            "llama3-8b-8192",
            "gemma-7b-it"
        ]

        system_instruction = GroqChat._get_system_instruction()
        
        # Prepare messages
        messages = [{"role": "system", "content": system_instruction}]
        
        # Add conversation history (Limit to last 15 to save tokens)
        for msg in history[-15:]:
            role = msg.get("role", "user")
            if role == "ai": role = "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_message})

        # Retry logic with backoff
        import time
        import random

        for attempt in range(3): # Try up to 3 times total sequence
            for current_model in models_to_try:
                try:
                    response = requests.post(
                        GROQ_API_URL,
                        headers={
                            "Authorization": f"Bearer {GROQ_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": current_model,
                            "messages": messages,
                            "temperature": 0.7,
                            "max_tokens": 1024,
                            "stream": True
                        },
                        timeout=30,
                        stream=True
                    )

                    if response.status_code == 200:
                        success = False
                        for line in response.iter_lines():
                            if line:
                                line = line.decode('utf-8')
                                if line.startswith('data: '):
                                    json_str = line[6:]
                                    if json_str.strip() == '[DONE]':
                                        break
                                    try:
                                        chunk = json.loads(json_str)
                                        if "choices" in chunk and len(chunk["choices"]) > 0:
                                            delta = chunk["choices"][0].get("delta", {})
                                            content = delta.get("content", "")
                                            if content:
                                                success = True
                                                yield content
                                    except json.JSONDecodeError:
                                        pass
                        if success:
                            return # Successfully streamed, exit function
                    
                    elif response.status_code == 429:
                        print(f"{Colors.YELLOW}⚠️ Groq Rate Limit (429) on {current_model}. Switching...{Colors.END}")
                        continue # Try next model immediately
                    elif response.status_code == 503:
                        print(f"{Colors.YELLOW}⚠️ Groq Service Unavailable (503). Retrying...{Colors.END}")
                        time.sleep(1 + random.random()) # Short backoff
                        continue
                    else:
                        print(f"{Colors.RED}❌ Groq Error {response.status_code}: {response.text}{Colors.END}")
                        # Don't yield error to user immediately, try next model/attempt
                        continue

                except Exception as e:
                    print(f"{Colors.YELLOW}⚠️ Request error on {model}: {e}{Colors.END}")
                    continue
            
            # If we exhausted models in this attempt, wait a bit before full retry?
            # Or just give up? 
            # Let's add a small sleep before retrying the whole model list again
            time.sleep(2 + random.random())

        # Final fallback if all attempts fail
        yield "I'm having a little trouble connecting to my brain right now due to high traffic. Please try asking again in a few seconds!"

    @staticmethod
    def _get_system_instruction():
        try:
            kb_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'knowledge_base.txt')
            with open(kb_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return "You are Wispen, an advanced AI tutor."


    @staticmethod
    def generate_speech(text: str) -> Optional[bytes]:
        """Generates speech using Groq API (PlayAI model) - NOTE: This requires terms acceptance."""
        if not GROQ_API_KEY:
            print(f"{Colors.RED}❌ No Groq API key for TTS{Colors.END}")
            return None

        url = "https://api.groq.com/openai/v1/audio/speech"
        try:
            response = requests.post(
                url, 
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json"
                }, 
                json={
                    "model": "playai-tts", 
                    "voice": "Fritz-PlayAI",
                    "input": text,
                    "response_format": "mp3"
                }, 
                timeout=30
            )
            
            if response.status_code == 200:
                return response.content
            else:
                # print(f"{Colors.YELLOW}⚠️ Groq TTS failed ({response.status_code}): {response.text}{Colors.END}")
                return None
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Groq TTS error: {e}{Colors.END}")
            return None



IMAGES_FOLDER = os.path.join(Path.home(), "LearnBot", "images")
class MurfTTS:
    """Murf.ai Text-to-Speech Integration"""
    
    @staticmethod
    def generate_speech(text: str) -> Optional[bytes]:
        """Generates speech using Murf.ai API"""
        url = "https://api.murf.ai/v1/speech/generate"
        
        if not MURF_API_KEY:
            print(f"{Colors.RED}❌ No Murf API key found{Colors.END}")
            # Try fallback to Groq? No, user explicitly requested Murf.
            return None

        headers = {
            "api-key": MURF_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        data = {
            "voiceId": "en-US-ryan", # Male, standard
            # "voiceId": "en-US-natalie", # Female, standard (alternative)
            "text": text,
            "format": "MP3",
            "channelType": "MONO",
            "encodeAsBase64": True
        }
        
        try:
            # print(f"Generate speech with Murf: {text[:20]}...")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                json_data = response.json()
                encoded_audio = json_data.get("encodedAudio")
                
                if encoded_audio:
                    return base64.b64decode(encoded_audio)
                elif "audioFile" in json_data:
                    # Fallback if base64 not returned (shouldn't happen with flag)
                    audio_url = json_data["audioFile"]
                    file_resp = requests.get(audio_url)
                    return file_resp.content
            else:
                print(f"{Colors.YELLOW}⚠️ Murf TTS failed ({response.status_code}): {response.text}{Colors.END}")
                return None
                
        except Exception as e:
            print(f"{Colors.RED}❌ Murf TTS error: {e}{Colors.END}")
            return None

os.makedirs(IMAGES_FOLDER, exist_ok=True)

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
    MAGENTA = '\033[95m'

class EdgeTTS:
    """Edge TTS Integration (Microsoft Edge Voice) - Free & High Quality"""
    
    @staticmethod
    def generate_speech(text: str, voice: str = "en-US-ChristopherNeural") -> Optional[bytes]:
        """Generates speech using edge-tts (async wrapper)"""
        if not EDGE_TTS_AVAILABLE:
            print(f"{Colors.RED}❌ EdgeTTS not available. Install it with: pip install edge-tts{Colors.END}")
            return None

        async def _run_tts():
            communicate = edge_tts.Communicate(text, voice)
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
            
        try:
            # Use asyncio.run to execute the async function
            return asyncio.run(_run_tts())
        except Exception as e:
            print(f"{Colors.RED}❌ EdgeTTS error: {e}{Colors.END}")
            return None

    @staticmethod
    def generate_speech_stream(text: str) -> Generator[bytes, None, None]:
        """Generates speech stream using edge-tts (sync wrapper for generator)"""
        if not EDGE_TTS_AVAILABLE:
            yield b""
            return

        voice = "en-US-ChristopherNeural" 
        
        # We need a way to bridge async stream to sync generator for Flask
        # This is tricky with asyncio.run. 
        # Simpler approach: gather larger chunks or use a queue.
        # But for simplicity and safety in Flask generic environment:
        # We will just use the run implementation but yield chunks if possible?
        # Actually, asyncio generators are async.
        # We might need to run the loop in a separate thread or use a bridge.
        
        # Alternative: Just run it and buffer? No, that defeats the purpose.
        # Let's keep it simple: The user wants "chatgpt speed". 
        # EdgeTTS is fast. The bottleneck is likely just the full generation wait.
        
        # Let's try to run a loop that pushes to a queue.
        import queue
        import threading
        
        q = queue.Queue()
        
        def _producer():
            async def _async_gen():
                communicate = edge_tts.Communicate(text, voice)
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        q.put(chunk["data"])
                q.put(None) # Signal done

            try:
                print(f"DEBUG: EdgeTTS starting for text: {text[:30]}...", flush=True)
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(_async_gen())
                loop.close()
                print(f"DEBUG: EdgeTTS completed for text: {text[:30]}...", flush=True)
            except Exception as e:
                print(f"TTS Stream Error: {e}", flush=True)
                q.put(None)


        t = threading.Thread(target=_producer)
        t.start()
        
        while True:
            chunk = q.get()
            if chunk is None:
                break
            yield chunk

class ImageGenerator:
    """AI Image Generation Integration"""
    
    @staticmethod
    def generate_image(prompt: str, filename: str, output_dir: str) -> Optional[str]:
        """
        Generates an AI image from a prompt using Pollinations.
        Returns the saved filename or None on failure.
        """
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            
        try:
            # Clean prompt for URL
            safe_prompt = quote(prompt)
            url = f"https://image.pollinations.ai/prompt/{safe_prompt}?width=800&height=450&nologo=true&seed={int(time.time())}"
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(response.content)
                return filename
            else:
                print(f"Image API error: {response.status_code}")
        except Exception as e:
            print(f"Image generation failed: {e}")
            
        return None



def research(query: str, max_results: int = 5):
    """Perform AI-synthesized web research with Tavily API"""
    if not TAVILY_API_KEY:
        print(f"{Colors.YELLOW}⚠️ Tavily API key not configured. Skipping web research.{Colors.END}")
        return None
    
    try:
        print(f"{Colors.CYAN}🔍 Researching: {query}...{Colors.END}\n")
        
        search_client = WebSearchClient(api_key=TAVILY_API_KEY)
        raw_results = search_client.search(query, max_results=max_results)
        
        if not raw_results or raw_results.get('results') is None:
            print(f"{Colors.YELLOW}⚠️ No search results found{Colors.END}\n")
            return None
        
        save_path = f"{query.replace(' ', '_')}_research.json"
        try:
            with open(save_path, 'w') as f:
                json.dump(raw_results, f, indent=2)
            print(f"{Colors.YELLOW}💾 Research data saved to {save_path}{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Could not save research: {str(e)}{Colors.END}\n")
        
        search_client.process_results(raw_results)
        
        answer = raw_results.get('answer', '')
        sources = raw_results.get('results', [])[:max_results]
        follow_ups = raw_results.get('follow_up_questions', [])
        
        return {
            "query": query,
            "response": answer if answer and answer.strip() else "Research completed",
            "sources": sources,
            "follow_up_questions": follow_ups,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"{Colors.RED}❌ Research error: {str(e)}{Colors.END}\n")
    
    return None


class FileProcessor:
    """Process multiple file types including images, PDFs, documents"""
    
    @staticmethod
    def process_file(filepath: str) -> Dict:
        """
        Process any file type and extract content
        
        Returns:
            Dict with 'content', 'type', 'metadata'
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        file_ext = Path(filepath).suffix.lower()
        mime_type, _ = mimetypes.guess_type(filepath)
        
        print(f"{Colors.CYAN}📁 Processing file: {filepath} ({file_ext}){Colors.END}")
        
        # PDF files
        if file_ext == '.pdf':
            return FileProcessor._process_pdf(filepath)
        
        # Image files
        elif file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
            return FileProcessor._process_image(filepath)
        
        # Text files
        elif file_ext in ['.txt', '.md', '.csv', '.json', '.xml']:
            return FileProcessor._process_text(filepath)
        
        # Binary/other files
        else:
            return FileProcessor._process_binary(filepath)
    
    @staticmethod
    def _process_pdf(filepath: str) -> Dict:
        """Extract text from PDF"""
        if not DOCUMENT_PROCESSING_AVAILABLE:
            return {
                "content": f"[PDF file: {filepath} - Install PyPDF2 to extract text]",
                "type": "pdf",
                "metadata": {"filename": filepath}
            }
        
        try:
            with open(filepath, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                
                return {
                    "content": text,
                    "type": "pdf",
                    "metadata": {
                        "filename": filepath,
                        "pages": len(pdf_reader.pages),
                        "size_bytes": os.path.getsize(filepath)
                    }
                }
        except Exception as e:
            return {
                "content": f"[Error reading PDF: {str(e)}]",
                "type": "pdf",
                "metadata": {"filename": filepath, "error": str(e)}
            }
    
    @staticmethod
    def _process_image(filepath: str) -> Dict:
        """Process image - convert to base64 for Gemini API"""
        try:
            with open(filepath, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')
            
            mime_type, _ = mimetypes.guess_type(filepath)
            
            return {
                "content": image_data,
                "type": "image",
                "mime_type": mime_type or "image/jpeg",
                "metadata": {
                    "filename": filepath,
                    "size_bytes": os.path.getsize(filepath)
                }
            }
        except Exception as e:
            return {
                "content": f"[Error reading image: {str(e)}]",
                "type": "image",
                "metadata": {"filename": filepath, "error": str(e)}
            }
    
    @staticmethod
    def _process_text(filepath: str) -> Dict:
        """Extract text from text files"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "content": content,
                "type": "text",
                "metadata": {
                    "filename": filepath,
                    "size_bytes": os.path.getsize(filepath),
                    "lines": len(content.split('\n'))
                }
            }
        except Exception as e:
            return {
                "content": f"[Error reading file: {str(e)}]",
                "type": "text",
                "metadata": {"filename": filepath, "error": str(e)}
            }
    
    @staticmethod
    def _process_binary(filepath: str) -> Dict:
        """Handle binary files"""
        try:
            with open(filepath, 'rb') as f:
                data = base64.b64encode(f.read()).decode('utf-8')
            
            mime_type, _ = mimetypes.guess_type(filepath)
            
            return {
                "content": data,
                "type": "binary",
                "mime_type": mime_type or "application/octet-stream",
                "metadata": {
                    "filename": filepath,
                    "size_bytes": os.path.getsize(filepath)
                }
            }
        except Exception as e:
            return {
                "content": f"[Error reading file: {str(e)}]",
                "type": "binary",
                "metadata": {"filename": filepath, "error": str(e)}
            }


class FirestoreManager:
    """Manage Firestore operations for user data and session management"""
    
    def __init__(self, credentials_path: str = FIREBASE_CREDENTIALS_PATH):
        if not FIREBASE_AVAILABLE:
            raise ImportError("Firebase Admin SDK not available")
        
        # Initialize Firebase
        if not firebase_admin._apps:
            cred = credentials.Certificate(credentials_path)
            firebase_admin.initialize_app(cred)
        
        self.db = firestore.client()
        print(f"{Colors.GREEN}✓ Firestore connected{Colors.END}")
    
    def save_user_profile(self, user_id: str, profile_data: Dict):
        """Save or update user profile"""
        doc_ref = self.db.collection('users').document(user_id)
        doc_ref.set(profile_data, merge=True)
        print(f"{Colors.GREEN}✓ Profile saved for user: {user_id}{Colors.END}")
    
    def get_user_profile(self, user_id: str) -> Optional[Dict]:
        """Retrieve user profile"""
        doc_ref = self.db.collection('users').document(user_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else None
    
    def save_session(self, user_id: str, session_data: Dict, session_summary: str):
        """Save a learning session with AI-generated summary"""
        session_ref = self.db.collection('users').document(user_id).collection('sessions')
        session_doc = session_ref.document()
        
        session_data['summary'] = session_summary
        session_data['session_id'] = session_doc.id
        session_data['created_at'] = firestore.SERVER_TIMESTAMP
        
        session_doc.set(session_data)
        print(f"{Colors.GREEN}✓ Session saved: {session_doc.id}{Colors.END}")
        return session_doc.id
    
    def save_quiz_result(self, user_id: str, quiz_data: Dict):
        """Save quiz results"""
        quiz_ref = self.db.collection('users').document(user_id).collection('quizzes')
        quiz_doc = quiz_ref.document()
        
        quiz_data['quiz_id'] = quiz_doc.id
        quiz_data['timestamp'] = firestore.SERVER_TIMESTAMP
        
        quiz_doc.set(quiz_data)
        
        # Update user stats
        user_ref = self.db.collection('users').document(user_id)
        user_ref.update({
            'total_quizzes': firestore.Increment(1),
            'total_quiz_score': firestore.Increment(quiz_data.get('score', 0)),
            'last_quiz_date': firestore.SERVER_TIMESTAMP
        })
        
        print(f"{Colors.GREEN}✓ Quiz result saved{Colors.END}")
        return quiz_doc.id
    
    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve recent sessions"""
        sessions_ref = self.db.collection('users').document(user_id).collection('sessions')
        sessions = sessions_ref.order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [s.to_dict() for s in sessions]
    
    def get_user_quizzes(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Retrieve recent quizzes"""
        quizzes_ref = self.db.collection('users').document(user_id).collection('quizzes')
        quizzes = quizzes_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [q.to_dict() for q in quizzes]
    
    def update_learning_insights(self, user_id: str, insights: Dict):
        """Update personalized learning insights"""
        user_ref = self.db.collection('users').document(user_id)
        user_ref.update({
            'learning_insights': insights,
            'insights_updated_at': firestore.SERVER_TIMESTAMP
        })


class PersonalizationEngine:
    """Advanced AI-powered personalization engine using Gemini for deep content analysis"""
    
    def __init__(self, firestore_manager: Optional[FirestoreManager] = None):
        self.fs_manager = firestore_manager
        self.learning_patterns = defaultdict(list)
    
    def analyze_learning_patterns(self, user_data: Dict, chat_content: str = "") -> Dict:
        """
        Analyze user's learning patterns using Gemini AI and chat history.
        Goes beyond scores to understand actual learning behavior and comprehension.
        """
        try:
            if chat_content and len(chat_content) > 100:
                return self._analyze_with_gemini(user_data, chat_content)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ AI analysis fallback: {str(e)}{Colors.END}")
        
        return self._fallback_analysis(user_data)
    
    def _analyze_with_gemini(self, user_data: Dict, chat_content: str) -> Dict:
        """Use Gemini to deeply analyze chat content and learning patterns"""
        analysis_prompt = f"""Analyze this student's learning patterns based on their conversation and performance data.

STUDENT PROFILE:
- Total Sessions: {user_data.get('total_sessions', 0)}
- Interactions: {user_data.get('interaction_count', 0)}
- Quizzes Completed: {user_data.get('total_quizzes', 0)}
- Average Score: {user_data.get('average_quiz_score', 0):.1f}%
- Learning Style: {user_data.get('learning_style', 'balanced')}
- Difficulty Level: {user_data.get('difficulty_preference', 'intermediate')}

RECENT LEARNING CONVERSATION:
{chat_content[:2000]}

Based on this data, provide a JSON analysis with:
{{
  "learning_pace": "fast/moderate/steady" (based on question depth and complexity growth),
  "comprehension_level": "novice/intermediate/advanced" (from conversation quality),
  "learning_style_actual": "visual/verbal/kinesthetic/balanced" (from chat patterns),
  "strong_areas": ["topic1", "topic2"] (topics they handle well),
  "weak_areas": ["topic1", "topic2"] (topics causing confusion),
  "engagement_score": 0-100 (from interaction quality),
  "recommended_difficulty": "beginner/intermediate/advanced",
  "optimal_session_time": "20-30/30-45/45-60 minutes",
  "cognitive_patterns": "explanation of key learning patterns",
  "personalized_insights": "2-3 specific insights about their learning",
  "recommended_next_topics": ["topic1", "topic2", "topic3"],
  "learning_strengths": ["strength1", "strength2"],
  "areas_for_development": ["area1", "area2"]
}}

Focus on patterns visible in their questions, explanations, and responses - not just scores."""
        
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": analysis_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.6,
                        "maxOutputTokens": 1024,
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        insights = json.loads(json_match.group(0))
                        insights['engagement_score'] = float(insights.get('engagement_score', 50))
                        return insights
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Gemini analysis error: {str(e)}{Colors.END}")
        
        return self._fallback_analysis(user_data)
    
    def _fallback_analysis(self, user_data: Dict) -> Dict:
        """Fallback analysis using traditional metrics"""
        return {
            "learning_pace": self._calculate_learning_pace(user_data),
            "comprehension_level": self._estimate_comprehension(user_data),
            "learning_style_actual": user_data.get('learning_style', 'balanced'),
            "strong_areas": self._identify_strong_subjects(user_data),
            "weak_areas": self._identify_improvement_areas(user_data),
            "engagement_score": self._calculate_engagement_score(user_data),
            "recommended_difficulty": self._recommend_difficulty(user_data),
            "optimal_session_time": self._calculate_optimal_session_time(user_data),
            "cognitive_patterns": "Pattern analysis based on quiz performance and interaction metrics",
            "personalized_insights": ["Based on available metrics", "Deeper insights from chat analysis coming soon"],
            "recommended_next_topics": [],
            "learning_strengths": self._identify_strong_subjects(user_data),
            "areas_for_development": self._identify_improvement_areas(user_data)
        }
    
    def _calculate_learning_pace(self, user_data: Dict) -> str:
        """Determine if user learns fast, medium, or slow"""
        sessions = user_data.get('total_sessions', 0)
        topics_learned = len(user_data.get('topics_learned', []))
        
        if sessions == 0:
            return "unknown"
        
        pace_ratio = topics_learned / sessions
        
        if pace_ratio > 2:
            return "fast"
        elif pace_ratio > 1:
            return "moderate"
        else:
            return "steady"
    
    def _estimate_comprehension(self, user_data: Dict) -> str:
        """Estimate comprehension level from quiz scores"""
        avg_score = user_data.get('average_quiz_score', 50)
        
        if avg_score > 85:
            return "advanced"
        elif avg_score > 70:
            return "intermediate"
        elif avg_score > 50:
            return "foundational"
        else:
            return "novice"
    
    def _identify_strong_subjects(self, user_data: Dict) -> List[str]:
        """Identify subjects where user excels"""
        quiz_scores = user_data.get('quiz_scores', {})
        strong_subjects = [subj.replace('_', ' ').title() for subj, score in quiz_scores.items() if score > 80]
        return strong_subjects[:5] if strong_subjects else ["Building expertise"]
    
    def _identify_improvement_areas(self, user_data: Dict) -> List[str]:
        """Identify subjects needing improvement"""
        quiz_scores = user_data.get('quiz_scores', {})
        weak_subjects = [subj.replace('_', ' ').title() for subj, score in quiz_scores.items() if score < 60]
        return weak_subjects[:5] if weak_subjects else ["Areas to explore"]
    
    def _calculate_optimal_session_time(self, user_data: Dict) -> str:
        """Calculate optimal learning session duration"""
        engagement = user_data.get('engagement_score', 50)
        
        if engagement > 80:
            return "45-60 minutes"
        elif engagement > 60:
            return "30-45 minutes"
        else:
            return "20-30 minutes"
    
    def _calculate_engagement_score(self, user_data: Dict) -> float:
        """Calculate overall engagement score (0-100)"""
        factors = {
            'interaction_count': user_data.get('interaction_count', 0) * 0.3,
            'sessions': user_data.get('total_sessions', 0) * 2,
            'quizzes': user_data.get('total_quizzes', 0) * 5,
            'topics': len(user_data.get('topics_learned', [])) * 3
        }
        
        score = sum(factors.values())
        return min(score, 100)
    
    def _recommend_difficulty(self, user_data: Dict) -> str:
        """Recommend difficulty level based on performance"""
        avg_quiz_score = user_data.get('average_quiz_score', 50)
        
        if avg_quiz_score > 85:
            return "advanced"
        elif avg_quiz_score > 70:
            return "intermediate"
        else:
            return "beginner"


class VisualRepresentationGenerator:
    """Generate visual representations using Stable Diffusion"""
    
    def generate_visual_prompt(self, topic: str, learning_style: str = "educational") -> str:
        """Generate sophisticated prompt for Stable Diffusion"""
        prompt = f"""Create a professional, educational diagram about {topic}.
        
Requirements:
- Clear, labeled components
- Use educational color schemes
- Include key concepts with annotations
- Make it suitable for learning and teaching
- Professional illustration style
- Learning style: {learning_style}

Style: Clean, organized, with clear visual hierarchy suitable for {learning_style} learners."""
        return prompt
    
    def generate_visual(self, topic: str, learning_style: str = "educational") -> Optional[str]:
        """Generate visual representation for topic"""
        if not STABLE_DIFFUSION_API_KEY:
            print(f"{Colors.YELLOW}⚠️ Stable Diffusion API not configured. Skipping visual generation.{Colors.END}")
            return None
        
        try:
            print(f"{Colors.MAGENTA}🎨 Generating visual representation for: {topic}{Colors.END}")
            
            visual_prompt = self.generate_visual_prompt(topic, learning_style)
            
            response = requests.post(
                STABLE_DIFFUSION_API_URL,
                headers={"Authorization": f"Bearer {STABLE_DIFFUSION_API_KEY}"},
                json={
                    "prompt": visual_prompt,
                    "output_format": "png",
                    "aspect_ratio": "16:9"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                image_filename = f"visual_{topic.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                image_path = os.path.join(IMAGES_FOLDER, image_filename)
                
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"{Colors.GREEN}✓ Visual saved: {image_path}{Colors.END}")
                return image_path
            else:
                print(f"{Colors.YELLOW}⚠️ Visual generation failed: {response.status_code}{Colors.END}")
                return None
        
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error generating visual: {str(e)}{Colors.END}")
            return None


class FlashcardGenerator:
    """Generate NotebookLM-style flashcards with rich content and auto-determined count"""
    
    def __init__(self, gemini_tutor):
        self.tutor = gemini_tutor
    
    def generate_flashcards(self, topic: str, num_cards: int = None) -> Dict:
        """Generate NotebookLM-style flashcards with comprehensive content coverage"""
        if num_cards is None:
            complexity = TopicComplexityAnalyzer.analyze_complexity(topic)
            num_cards = complexity.get('recommended_flashcards', 25)
        
        print(f"{Colors.MAGENTA}📇 Generating {num_cards} NotebookLM-style flashcards for: {topic}{Colors.END}")
        
        flashcard_prompt = f"""Create {num_cards} NotebookLM-style flashcards for comprehensive mastery of: {topic}

These should be high-quality, study-optimized cards with deep content. Include:

1. Definition & Concept cards (explain core concepts with examples)
2. Application cards (real-world usage, case studies)
3. Comparison cards (how this relates to similar concepts)
4. Deeper Understanding cards (nuances, edge cases, deeper implications)
5. Problem-Solving cards (practice questions with solution paths)

Each card should:
- Have a clear, thought-provoking front (question or concept)
- Include detailed, comprehensive back (explanation, examples, context)
- Build progressively in difficulty
- Include memory aids and mnemonics where helpful
- Reference related concepts

Format as JSON:
{{
  "topic": "{topic}",
  "total_cards": {num_cards},
  "card_categories": {{"definitions": 5, "applications": 5, "comparisons": 3, "deep_understanding": 4, "practice": 3}},
  "flashcards": [
    {{
      "id": 1,
      "category": "definition",
      "difficulty": "beginner/intermediate/advanced",
      "front": "Clear question or concept prompt",
      "back": "Detailed answer with examples, context, and connections",
      "memory_aid": "helpful mnemonic or memory technique",
      "related_concepts": ["concept1", "concept2"]
    }}
  ],
  "learning_notes": "Tips for using these flashcards effectively"
}}

Make the content rich, detailed, and suitable for deep learning and long-term retention."""
        
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": flashcard_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 8000,
                    }
                },
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                    if not json_match:
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    
                    if json_match:
                        flashcard_data = json.loads(json_match.group(1) if '```' in ai_response else json_match.group(0))
                        actual_count = len(flashcard_data.get('flashcards', []))
                        print(f"{Colors.GREEN}✓ Generated {actual_count} flashcards with rich content{Colors.END}")
                        return flashcard_data
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error generating flashcards: {str(e)}{Colors.END}")
        
        return None


class MindMapGenerator:
    """Generate detailed, content-rich NotebookLM-style mind maps with auto-determined depth"""
    
    def __init__(self, gemini_tutor):
        self.tutor = gemini_tutor
    
    def generate_mindmap(self, topic: str, depth: int = None) -> Dict:
        """Generate comprehensive mind map with actual content and deep structure"""
        if depth is None:
            complexity = TopicComplexityAnalyzer.analyze_complexity(topic)
            depth = complexity.get('recommended_mindmap_depth', 4)
            num_branches = complexity.get('recommended_mindmap_branches', 12)
        else:
            num_branches = max(8, min(20, 5 + depth))
        
        print(f"{Colors.MAGENTA}🧠 Generating deep mind map for: {topic} (Depth: {depth}, Branches: {num_branches}){Colors.END}")
        
        mindmap_prompt = f"""Create a comprehensive, content-rich mind map for: {topic}

Requirements:
- Depth: {depth} levels of hierarchical detail
- Breadth: {num_branches} main branches with rich sub-branches
- Content: Actual concepts, definitions, examples - NOT just single words
- Structure: Logical hierarchy showing relationships and dependencies
- Density: High information density with meaningful connections

Format as JSON:
{{
  "topic": "{topic}",
  "depth": {depth},
  "overview": "2-3 sentence overview of the topic and its structure",
  "central_concept": "Core definition or essence of the topic",
  "branches": [
    {{
      "id": 1,
      "main": "Main branch title with 1-2 descriptive words",
      "description": "What this branch covers and its importance",
      "sub_branches": [
        {{
          "title": "Sub-branch name",
          "content": "Detailed explanation, example, or context (2-3 sentences)",
          "key_points": ["point1", "point2", "point3"],
          "children": [
            {{
              "title": "Deep sub-topic",
              "content": "Specific details, formulas, or implementation details"
            }}
          ]
        }}
      ],
      "applications": ["Real-world application 1", "Real-world application 2"],
      "importance": "Why this branch matters in the overall topic"
    }}
  ],
  "cross_connections": [
    {{
      "from": "Branch A concept",
      "to": "Branch B concept",
      "relationship": "How they relate or influence each other"
    }}
  ],
  "key_insights": ["Important insight 1", "Important insight 2", "Important insight 3"],
  "learning_pathway": "Recommended order to learn the branches for maximum understanding"
}}

Create a true mind map with RICH CONTENT:
- Include actual definitions, explanations, and examples
- Show how concepts connect and interact
- Provide real-world applications and use cases
- Demonstrate depth at each level
- Make it suitable for NotebookLM-quality learning materials"""
        
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": mindmap_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.8,
                        "maxOutputTokens": 8000,
                    }
                },
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    json_match = re.search(r'```json\s*(.*?)\s*```', ai_response, re.DOTALL)
                    if not json_match:
                        json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    
                    if json_match:
                        mindmap_data = json.loads(json_match.group(1) if '```' in ai_response else json_match.group(0))
                        self._display_mindmap(mindmap_data)
                        return mindmap_data
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error generating mind map: {str(e)}{Colors.END}")
        
        return None
    
    def _display_mindmap(self, mindmap_data: Dict):
        """Display mind map in terminal"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.MAGENTA}🧠 MIND MAP: {mindmap_data.get('topic', 'Topic')}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")
        
        branches = mindmap_data.get('branches', [])
        for idx, branch in enumerate(branches):
            is_last = idx == len(branches) - 1
            prefix = "└─ " if is_last else "├─ "
            continuation = "   " if is_last else "│  "
            
            main = branch.get('main', 'Main') if isinstance(branch, dict) else str(branch)
            print(f"{Colors.BOLD}{Colors.GREEN}{prefix}{main}{Colors.END}")
            
            sub_branches = branch.get('sub_branches', []) if isinstance(branch, dict) else []
            for sub_idx, sub in enumerate(sub_branches):
                is_last_sub = sub_idx == len(sub_branches) - 1
                sub_prefix = "└─ " if is_last_sub else "├─ "
                sub_continuation = "   " if is_last_sub else "│  "
                print(f"{Colors.CYAN}{continuation}{sub_prefix}{sub}{Colors.END}")
            
            details = branch.get('details', '') if isinstance(branch, dict) else ''
            if details:
                print(f"{Colors.YELLOW}{continuation}└─ 📝 {details}{Colors.END}")
            print()


class QuizGenerator:
    """Generate and manage quizzes"""
    
    def __init__(self, gemini_tutor):
        self.tutor = gemini_tutor
    
    def generate_quiz(self, topic: str, difficulty: str = "intermediate", num_questions: int = 5) -> Dict:
        """Generate a quiz on given topic"""
        print(f"{Colors.MAGENTA}📝 Generating quiz on: {topic} ({difficulty}){Colors.END}")
        
        quiz_prompt = f"""Generate a quiz on the topic: {topic}
Difficulty: {difficulty}
Number of questions: {num_questions}

Create {num_questions} multiple-choice questions. For each question:
1. Write a clear question
2. Provide 4 options (A, B, C, D)
3. Indicate the correct answer
4. Provide a brief explanation

Format your response as JSON:
{{
  "quiz_title": "...",
  "topic": "{topic}",
  "difficulty": "{difficulty}",
  "questions": [
    {{
      "question": "...",
      "options": {{"A": "...", "B": "...", "C": "...", "D": "..."}},
      "correct_answer": "A",
      "explanation": "..."
    }}
  ]
}}"""
        
        response = self.tutor.send_message(quiz_prompt, skip_history=True)
        
        # Parse JSON from response
        try:
            # Extract JSON from markdown if present
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                quiz_data = json.loads(json_match.group(1))
            else:
                quiz_data = json.loads(response)
            
            return quiz_data
        except Exception as e:
            print(f"{Colors.RED}Error parsing quiz: {str(e)}{Colors.END}")
            return None
    
    def administer_quiz(self, quiz_data: Dict) -> Dict:
        """Administer quiz and track results"""
        if not quiz_data:
            return None
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}📝 QUIZ: {quiz_data.get('quiz_title', 'Quiz')}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
        
        questions = quiz_data.get('questions', [])
        score = 0
        total = len(questions)
        start_time = time.time()
        answers = []
        
        for idx, q in enumerate(questions, 1):
            print(f"{Colors.YELLOW}Question {idx}/{total}:{Colors.END}")
            print(f"{Colors.BOLD}{q['question']}{Colors.END}\n")
            
            options = q['options']
            for key, value in options.items():
                print(f"  {key}. {value}")
            
            print()
            user_answer = input(f"{Colors.GREEN}Your answer (A/B/C/D): {Colors.END}").strip().upper()
            
            correct = user_answer == q['correct_answer']
            if correct:
                score += 1
                print(f"{Colors.GREEN}✓ Correct!{Colors.END}\n")
            else:
                print(f"{Colors.RED}✗ Incorrect. Correct answer: {q['correct_answer']}{Colors.END}")
                print(f"{Colors.CYAN}Explanation: {q['explanation']}{Colors.END}\n")
            
            answers.append({
                "question": q['question'],
                "user_answer": user_answer,
                "correct_answer": q['correct_answer'],
                "is_correct": correct
            })
            
            print(f"{Colors.CYAN}{'─'*80}{Colors.END}\n")
        
        end_time = time.time()
        duration = end_time - start_time
        
        percentage = (score / total) * 100
        
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}📊 QUIZ RESULTS{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
        print(f"Score: {score}/{total} ({percentage:.1f}%)")
        print(f"Time taken: {duration:.1f} seconds")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.END}\n")
        
        return {
            "topic": quiz_data.get('topic'),
            "difficulty": quiz_data.get('difficulty'),
            "score": score,
            "total_questions": total,
            "percentage": percentage,
            "duration_seconds": duration,
            "answers": answers,
            "timestamp": datetime.now().isoformat()
        }


class TopicComplexityAnalyzer:
    """Advanced topic complexity analyzer with semantic understanding"""
    
    @staticmethod
    def analyze_complexity(topic: str) -> Dict:
        """Analyze topic complexity with sophisticated metrics and recommendations"""
        try:
            prompt = f"""Perform an advanced complexity analysis of this topic: "{topic}"

Analyze across multiple dimensions:

1. **Conceptual Depth**: How many levels of abstraction exist?
2. **Breadth**: How many subtopics and branches exist?
3. **Prerequisites**: What foundational knowledge is needed?
4. **Interdisciplinary Connections**: How many other fields does it touch?
5. **Real-world Applications**: Complexity of practical implementations?
6. **Mathematical/Technical Rigor**: Level of formalism required?

Respond with JSON:
{{
  "complexity_score": 1-10 (overall complexity),
  "recommended_mindmap_depth": 3-6 (for comprehensive coverage),
  "recommended_mindmap_branches": 8-20 (number of main branches),
  "recommended_flashcards": 20-50 (comprehensive coverage),
  "recommended_quiz_questions": 10-20 (for thorough assessment),
  "estimated_learning_time_hours": number (to master topic),
  "cognitive_complexity": "novice/intermediate/advanced",
  "topic_dependencies": ["prerequisite1", "prerequisite2"],
  "key_subtopics": ["subtopic1", "subtopic2", "subtopic3", "subtopic4", "subtopic5"],
  "complexity_reasoning": "detailed explanation of complexity factors",
  "recommended_approach": "detailed learning pathway recommendation"
}}

Complexity Guide:
1-2: Basic definitions
3-4: Foundational understanding
5-6: Moderate depth and breadth
7-8: Significant depth, multiple interconnections
9-10: Highly advanced, extensive prerequisites, deep mastery required"""
            
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.6,
                        "maxOutputTokens": 1024,
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    ai_response = data["candidates"][0]["content"]["parts"][0]["text"]
                    json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                    if json_match:
                        complexity_data = json.loads(json_match.group(0))
                        complexity_data['mindmap_branches'] = complexity_data.get('recommended_mindmap_branches', 12)
                        print(f"{Colors.YELLOW}🔍 Complexity Analysis:{Colors.END}")
                        print(f"   Complexity Level: {complexity_data.get('complexity_score', 5)}/10")
                        print(f"   Cognitive Level: {complexity_data.get('cognitive_complexity', 'intermediate').title()}")
                        print(f"   Estimated Learning Time: {complexity_data.get('estimated_learning_time_hours', 'varies')} hours")
                        print(f"   {complexity_data.get('complexity_reasoning', '')}\n")
                        return complexity_data
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Complexity analysis failed: {str(e)}{Colors.END}")
        
        return {
            "complexity_score": 5,
            "recommended_mindmap_depth": 4,
            "recommended_mindmap_branches": 12,
            "recommended_flashcards": 25,
            "recommended_quiz_questions": 10,
            "estimated_learning_time_hours": 2,
            "cognitive_complexity": "intermediate",
            "topic_dependencies": [],
            "key_subtopics": ["Core Concept", "Application", "Examples", "Practice"],
            "complexity_reasoning": "Moderate complexity - balanced depth and breadth",
            "recommended_approach": "Start with fundamentals, progress to applications"
        }


class SourceManager:
    """Manage learning sources"""
    
    def __init__(self):
        self.sources = []
        self.sources_file = os.path.join(IMAGES_FOLDER, "sources.json")
        self.load_sources()
    
    def load_sources(self):
        """Load sources from file"""
        try:
            if os.path.exists(self.sources_file):
                with open(self.sources_file, 'r') as f:
                    self.sources = json.load(f)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error loading sources: {str(e)}{Colors.END}")
            self.sources = []
    
    def add_source(self, source_data: Dict):
        """Add source to collection"""
        source_entry = {
            "id": str(uuid.uuid4()),
            "title": source_data.get('title', 'Untitled'),
            "url": source_data.get('url', ''),
            "content": source_data.get('content', ''),
            "topic": source_data.get('topic', 'General'),
            "added_date": datetime.now().isoformat(),
            "type": source_data.get('type', 'research')
        }
        self.sources.append(source_entry)
        self.save_sources()
        return source_entry["id"]
    
    def save_sources(self):
        """Save sources to file"""
        try:
            with open(self.sources_file, 'w') as f:
                json.dump(self.sources, f, indent=2)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error saving sources: {str(e)}{Colors.END}")
    
    def get_sources_by_topic(self, topic: str) -> List[Dict]:
        """Get sources for a topic"""
        return [s for s in self.sources if s.get('topic', '').lower() == topic.lower()]
    
    def display_sources(self, topic: str = None):
        """Display sources in formatted way"""
        if topic:
            sources = self.get_sources_by_topic(topic)
        else:
            sources = self.sources
        
        if not sources:
            print(f"{Colors.YELLOW}No sources found{Colors.END}\n")
            return
        
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}📚 YOUR LEARNING SOURCES{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*70}{Colors.END}\n")
        
        for idx, source in enumerate(sources, 1):
            print(f"{Colors.YELLOW}[{idx}] {source.get('title', 'Untitled')}{Colors.END}")
            print(f"    Topic: {source.get('topic', 'General')}")
            if source.get('url'):
                print(f"    URL: {source.get('url', '')}")
            print(f"    Added: {source.get('added_date', '')}")
            print()


class ReportGenerator:
    """Generate comprehensive learning reports"""
    
    def __init__(self, tutor):
        self.tutor = tutor
    
    def generate_session_report(self) -> str:
        """Generate comprehensive session report"""
        print(f"{Colors.MAGENTA}📋 Generating personalized learning report...{Colors.END}")
        
        profile = self.tutor.user_profile
        chat_content = self.tutor._get_conversation_text() if self.tutor.conversation_history else ""
        insights = self.tutor.personalization.analyze_learning_patterns(profile, chat_content)
        
        report_prompt = f"""Generate a comprehensive learning report for this student session:

STUDENT PROFILE:
- Name: {profile.get('student_name', 'Student')}
- Grade: {profile.get('grade_level', 'Not specified')}
- Total Sessions: {profile.get('total_sessions', 0)}
- Average Quiz Score: {profile.get('average_quiz_score', 0):.1f}%

AI-ANALYZED LEARNING INSIGHTS:
- Learning Pace: {insights.get('learning_pace', 'unknown')}
- Comprehension Level: {insights.get('comprehension_level', 'intermediate')}
- Learning Style: {insights.get('learning_style_actual', 'balanced')}
- Engagement Score: {insights.get('engagement_score', 0):.1f}/100
- Strong Areas: {', '.join(insights.get('strong_areas', insights.get('strong_subjects', ['Developing'])))}
- Areas for Development: {', '.join(insights.get('weak_areas', insights.get('improvement_areas', ['Under assessment'])))}
- Cognitive Patterns: {insights.get('cognitive_patterns', 'Analysis in progress')}

CONVERSATION ANALYSIS:
{chat_content[:2500]}

Generate a professional, personalized report that includes:
1. Session Overview
2. Key Learnings
3. Progress Assessment
4. Strengths Demonstrated
5. Areas for Improvement
6. Personalized Recommendations
7. Next Steps

Make it encouraging and actionable."""
        
        try:
            response = requests.post(
                f"{GEMINI_API_URL}?key={GEMINI_API_KEY}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": report_prompt}]}],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 2048,
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if "candidates" in data and len(data["candidates"]) > 0:
                    report = data["candidates"][0]["content"]["parts"][0]["text"]
                    return report
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error generating report: {str(e)}{Colors.END}")
        
        return self._generate_fallback_report(profile, insights)
    
    def _generate_fallback_report(self, profile: Dict, insights: Dict) -> str:
        """Generate basic fallback report"""
        report = f"""
📊 LEARNING SESSION REPORT
{'='*50}

Student: {profile.get('student_name', 'Student')}
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

PERFORMANCE SUMMARY:
• Current Average Score: {profile.get('average_quiz_score', 0):.1f}%
• Total Sessions: {profile.get('total_sessions', 0)}
• Engagement Level: {insights.get('engagement_score', 0):.1f}/100

STRENGTHS:
{chr(10).join([f"• {s}" for s in insights.get('strong_subjects', ['Continue building on current topics'])])}

FOCUS AREAS:
{chr(10).join([f"• {a}" for a in insights.get('improvement_areas', ['Review fundamentals'])])}

RECOMMENDATIONS:
• Practice regular spaced repetition
• Focus on areas marked for improvement
• Continue engaging with challenging material
• Maintain consistent learning schedule

Next Learning Goals:
→ Complete recommended study materials
→ Track progress on focus areas
→ Celebrate milestones and achievements
"""
        return report
    
    def save_report(self, report: str, user_id: str) -> str:
        """Save report to file"""
        try:
            report_filename = f"report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report_path = os.path.join(IMAGES_FOLDER, report_filename)
            
            with open(report_path, 'w') as f:
                f.write(report)
            
            return report_path
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error saving report: {str(e)}{Colors.END}")
            return None
    
    def display_report(self, report: str):
        """Display report in formatted way"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*75}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}📊 PERSONALIZED LEARNING REPORT{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*75}{Colors.END}\n")
        print(report)
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*75}{Colors.END}\n")


class AdvancedAITutor:
    """Advanced AI Tutor with all enhanced features"""
    
    def __init__(self, user_id: str, knowledge_base_path: Optional[str] = None, enable_web_search: bool = False):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        self.api_key = GEMINI_API_KEY
        self.user_id = user_id
        self.conversation_history = []
        self.knowledge_base = ""
        self.uploaded_files = []
        self.current_subject = "General"
        self.enable_web_search = enable_web_search
        
        # Initialize managers
        try:
            self.fs_manager = FirestoreManager()
            self.firestore_enabled = True
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️  Firestore not available: {str(e)}{Colors.END}")
            self.firestore_enabled = False
            self.fs_manager = None
        
        self.deep_research = None
        self.file_processor = FileProcessor()
        
        self.rag_processor = None
        if RAG_PROCESSOR_AVAILABLE:
            tavily_key = os.getenv("TAVILY_API_KEY", "")
            try:
                self.rag_processor = EnhancedFileProcessor(
                    tavily_api_key=tavily_key if enable_web_search else None,
                    use_semantic=True
                )
                print(f"{Colors.GREEN}✓ Enhanced RAG processor initialized{Colors.END}")
            except Exception as e:
                print(f"{Colors.YELLOW}⚠️  RAG processor initialization failed: {str(e)}{Colors.END}")
        
        self.personalization = PersonalizationEngine(self.fs_manager)
        self.quiz_gen = QuizGenerator(self)
        self.visual_gen = VisualRepresentationGenerator()
        self.flashcard_gen = FlashcardGenerator(self)
        self.mindmap_gen = MindMapGenerator(self)
        self.complexity_analyzer = TopicComplexityAnalyzer()
        self.source_manager = SourceManager()
        self.report_gen = ReportGenerator(self)
        
        # Load or create user profile
        self.user_profile = self._load_user_profile()
        
        # Create system prompt
        self.system_prompt = self._create_system_prompt()
        
        if knowledge_base_path:
            self.load_knowledge_base(knowledge_base_path)
        
        print(f"{Colors.GREEN}✓ Advanced AI Tutor initialized for user: {user_id}{Colors.END}\n")
    
    def _load_user_profile(self) -> Dict:
        """Load user profile from Firestore or create new"""
        if self.firestore_enabled:
            profile = self.fs_manager.get_user_profile(self.user_id)
            if profile:
                print(f"{Colors.GREEN}✓ Profile loaded from Firestore{Colors.END}")
                return profile
        
        # Default profile
        return {
            "user_id": self.user_id,
            "student_name": None,
            "grade_level": None,
            "subjects_of_interest": [],
            "difficulty_preference": "intermediate",
            "learning_style": "balanced",
            "topics_learned": [],
            "strengths": [],
            "areas_for_improvement": [],
            "total_sessions": 0,
            "total_quizzes": 0,
            "quiz_scores": {},
            "interaction_count": 0,
            "average_quiz_score": 0,
            "engagement_score": 0,
            "last_session": None,
            "created_at": datetime.now().isoformat()
        }
    
    def _create_system_prompt(self) -> str:
        """Create sophisticated AI tutor system prompt with advanced pedagogical approach"""
        chat_content = self._get_conversation_text() if self.conversation_history else ""
        insights = self.personalization.analyze_learning_patterns(self.user_profile, chat_content)
        user_data_context = self._get_comprehensive_user_data()

        prompt = f"""You are an advanced AI tutor employing evidence-based teaching methodologies and personalized learning strategies.

**STUDENT PROFILE & CONTEXT:**
User ID: {self.user_id}
Name: {self.user_profile.get('student_name', 'Student')}
Grade Level: {self.user_profile.get('grade_level', 'Not specified')}
Learning Style: {self.user_profile.get('learning_style', 'balanced')}
Preferred Difficulty: {self.user_profile.get('difficulty_preference', 'intermediate')}
Current Focus: {self.current_subject}

**LEARNING ANALYTICS:**
Sessions: {self.user_profile.get('total_sessions', 0)} | Interactions: {self.user_profile.get('interaction_count', 0)} | Quizzes: {self.user_profile.get('total_quizzes', 0)}
Performance: {self.user_profile.get('average_quiz_score', 0):.1f}% | Engagement: {insights.get('engagement_score', 0):.1f}/100
Pace: {insights.get('learning_pace', 'unknown')} | Recommended Level: {insights.get('recommended_difficulty', 'intermediate')}

**PEDAGOGICAL INSIGHTS:**
Strengths: {', '.join(insights.get('strong_subjects', ['Developing'])) if insights.get('strong_subjects') else 'Developing'}
Focus Areas: {', '.join(insights.get('improvement_areas', ['Under assessment'])) if insights.get('improvement_areas') else 'Under assessment'}
Learning History: {user_data_context}

**CORE TEACHING METHODOLOGY:**

1. **Socratic Method**: Guide discovery through thoughtful questioning
   - Ask leading questions to help students develop understanding
   - Build upon existing knowledge to construct new concepts
   - Encourage critical thinking and analytical reasoning

2. **Scaffolding & Progressive Complexity**:
   - Start with foundational concepts
   - Build complexity gradually based on mastery
   - Provide support that fades as competence increases
   - Reference previously mastered topics

3. **Multimodal Learning**:
   - Adapt to student's learning style (visual, verbal, kinesthetic, balanced)
   - Use analogies, examples, and real-world applications
   - Create conceptual bridges between topics
   - Offer multiple perspectives on complex ideas

4. **Formative Assessment**:
   - Check understanding frequently through questions
   - Provide immediate, constructive feedback
   - Identify misconceptions early
   - Adjust pacing based on demonstrated mastery

5. **Metacognitive Development**:
   - Help students understand their learning process
   - Teach self-assessment techniques
   - Encourage reflection on learning strategies
   - Build independent problem-solving skills

6. **Personalized Recommendations**:
   - Suggest next topics based on learning profile
   - Identify prerequisite knowledge gaps
   - Recommend varied learning formats (text, visuals, problems, discussions)
   - Celebrate progress and milestones

**RESPONSE CHARACTERISTICS:**

- **Clarity**: Explain concepts simply but not simplistically
- **Engagement**: Use questions, examples, and interactive elements
- **Relevance**: Connect to student's interests and prior knowledge
- **Encouragement**: Maintain positive, growth-oriented tone
- **Structure**: Organize responses logically with clear sections
- **Depth Adjustment**: Adapt explanation depth to current understanding level

**SPECIAL HANDLING:**

Visual Representations: If student requests diagrams, charts, or visual explanations, offer to generate visual aids.
Complex Topics: Break into smaller, digestible components with progressive complexity.
Misconceptions: Address gently while redirecting to correct understanding.
Motivation: Recognize effort, celebrate progress, frame challenges as growth opportunities.

**AVAILABLE FEATURES TO SUGGEST:**
- Mind maps for conceptual organization
- Flashcards for spaced repetition learning
- Quizzes for formative assessment
- Visual representations for complex topics
- Deep research for comprehensive understanding

Your goal is to be a transformative educational partner that combines personalized learning science with adaptive teaching to maximize student growth and understanding."""
        return prompt

    def _get_comprehensive_user_data(self) -> str:
        """Fetch and format comprehensive user data from Firestore"""
        if not self.firestore_enabled:
            return "No Firestore data available - running in offline mode."

        try:
            context_parts = []

            # Recent sessions
            recent_sessions = self.fs_manager.get_user_sessions(self.user_id, limit=5)
            if recent_sessions:
                context_parts.append("**RECENT SESSIONS:**")
                for i, session in enumerate(recent_sessions, 1):
                    summary = session.get('summary', 'No summary available')
                    # Truncate summary for prompt
                    if len(summary) > 200:
                        summary = summary[:200] + "..."
                    context_parts.append(f"Session {i}: {summary}")
                context_parts.append("")

            # Recent quiz results
            recent_quizzes = self.fs_manager.get_user_quizzes(self.user_id, limit=10)
            if recent_quizzes:
                context_parts.append("**RECENT QUIZ PERFORMANCE:**")
                for quiz in recent_quizzes:
                    topic = quiz.get('topic', 'Unknown')
                    score = quiz.get('percentage', 0)
                    context_parts.append(f"• {topic}: {score:.1f}%")
                context_parts.append("")

            # Quiz scores by subject
            quiz_scores = self.user_profile.get('quiz_scores', {})
            if quiz_scores:
                context_parts.append("**SUBJECT PERFORMANCE:**")
                for subject, score in sorted(quiz_scores.items()):
                    context_parts.append(f"• {subject.replace('_', ' ').title()}: {score:.1f}%")
                context_parts.append("")

            # Learning patterns and insights
            insights = self.personalization.analyze_learning_patterns(self.user_profile)
            context_parts.append("**LEARNING PATTERNS:**")
            context_parts.append(f"• Engagement Level: {insights.get('engagement_score', 0):.1f}/100")
            context_parts.append(f"• Learning Pace: {insights.get('learning_pace', 'unknown')}")
            context_parts.append(f"• Preferred Style: {self.user_profile.get('learning_style', 'balanced')}")
            context_parts.append(f"• Recommended Difficulty: {insights.get('recommended_difficulty', 'intermediate')}")
            context_parts.append("")

            # Topics learned
            topics_learned = self.user_profile.get('topics_learned', [])
            if topics_learned:
                context_parts.append("**TOPICS MASTERED:**")
                # Group topics by recency
                recent_topics = topics_learned[-10:]
                context_parts.append(f"{', '.join(recent_topics)}")
                context_parts.append("")

            # Strengths and areas for improvement
            strengths = self.user_profile.get('strengths', [])
            improvements = self.user_profile.get('areas_for_improvement', [])
            if strengths or improvements:
                context_parts.append("**STRENGTHS & IMPROVEMENT AREAS:**")
                if strengths:
                    context_parts.append(f"Strengths: {', '.join(strengths)}")
                if improvements:
                    context_parts.append(f"Areas to focus: {', '.join(improvements)}")
                context_parts.append("")

            return "\n".join(context_parts)

        except Exception as e:
            return f"Error retrieving user data: {str(e)}"

    def upload_file(self, filepath: str) -> bool:
        """Upload and process any file type with RAG indexing"""
        try:
            # First, do basic file processing
            processed = self.file_processor.process_file(filepath)
            self.uploaded_files.append(processed)
            
            print(f"{Colors.GREEN}✓ File uploaded: {filepath}{Colors.END}")
            print(f"  Type: {processed['type']}")
            print(f"  Metadata: {processed['metadata']}\n")
            
            # If RAG processor available, index for intelligent search
            if self.rag_processor and processed['type'] in ['text', 'pdf']:
                try:
                    print(f"{Colors.CYAN}📚 Indexing with RAG for intelligent search...{Colors.END}")
                    rag_result = self.rag_processor.process_file(filepath)
                    if rag_result.get('status') == 'success':
                        print(f"{Colors.GREEN}✓ RAG indexing complete: {rag_result['summary']['total_chunks']} chunks{Colors.END}")
                        print(f"{Colors.CYAN}💡 You can now ask questions about this document!{Colors.END}\n")
                    else:
                        print(f"{Colors.YELLOW}⚠️ RAG indexing skipped{Colors.END}\n")
                except Exception as e:
                    print(f"{Colors.YELLOW}⚠️ RAG indexing failed: {str(e)}{Colors.END}\n")
            
            return True
        except Exception as e:
            print(f"{Colors.RED}✗ Error uploading file: {str(e)}{Colors.END}\n")
            return False
    
    def query_uploaded_documents(self, user_question: str) -> Optional[str]:
        """Query uploaded documents using RAG"""
        if not self.rag_processor:
            return None
        
        try:
            result = self.rag_processor.query_documents(
                user_question, 
                include_web=False,  # Only search uploaded docs
                use_hybrid=True      # Use semantic + keyword search
            )
            
            if result['found'] and result['local_context']:
                context = f"\n=== CONTEXT FROM YOUR UPLOADED DOCUMENTS ===\n"
                context += result['local_context']
                context += "\n=== END CONTEXT ===\n\n"
                return context
            
            return None
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Document query error: {str(e)}{Colors.END}")
            return None
    def send_message(self, user_input: str, skip_history: bool = False, 
                deep_research: bool = False, research_depth: int = 3) -> str:
        """Send message with optional deep research"""
        
        self.user_profile['interaction_count'] += 1
        
        # Conduct deep research if requested
        research_context = ""
        research_results = None
        if deep_research:
            research_results = research(user_input)
            research_context = self._format_research_context(research_results)
        
        # Automatically search uploaded documents if RAG is available
        doc_context = ""
        if self.rag_processor and not skip_history:
            doc_context = self.query_uploaded_documents(user_input) or ""
            if doc_context:
                print(f"{Colors.CYAN}📄 Found relevant content in uploaded documents{Colors.END}")
        
        # Prepare message parts
        message_parts = []
        
        # Add research context
        if research_context:
            message_parts.append(research_context)
        
        # Add RAG document context (intelligent search)
        if doc_context:
            message_parts.append(doc_context)
        
        # Add file context (for images and other non-text files)
        if self.uploaded_files:
            message_parts.append(self._format_file_context())
        
        # Add user question
        message_parts.append(f"Student Question: {user_input}")
            
        message_with_context = "\n\n".join(message_parts)
        
        # Build Gemini API request
        contents = []
        
        # Add conversation history (keep last 20 messages)
        if not skip_history:
            contents.extend(self.conversation_history[-20:])
        
        # Add current message with any uploaded images
        current_content = {"role": "user", "parts": []}
        
        # Add text
        current_content["parts"].append({"text": message_with_context})
        
        # Add images if any
        for file_data in self.uploaded_files:
            if file_data['type'] == 'image':
                current_content["parts"].append({
                    "inline_data": {
                        "mime_type": file_data.get('mime_type', 'image/jpeg'),
                        "data": file_data['content']
                    }
                })
        
        contents.append(current_content)
        
        # Prepare API request
        request_body = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": self.system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.8,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 8192,
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
                
                # Add to history
                if not skip_history:
                    self.conversation_history.append({
                        "role": "user",
                        "parts": [{"text": user_input}]
                    })
                    self.conversation_history.append({
                        "role": "model",
                        "parts": [{"text": assistant_text}]
                    })
                
                # Clear uploaded files after processing
                self.uploaded_files = []
                
                return assistant_text
            else:
                return "Error: No response generated"
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                return "⚠️ Rate limit exceeded. Please wait 60 seconds and try again."
            return f"❌ HTTP Error {e.response.status_code}: {str(e)}"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    
    def _import_research_sources(self, research_results: Dict, topic: str):
        """Import research sources to collection"""
        try:
            count = 0
            for result in research_results.get('results', [])[:5]:
                self.source_manager.add_source({
                    'title': result.get('title', 'Untitled'),
                    'url': result.get('url', ''),
                    'content': result.get('content', '')[:1000],
                    'topic': topic,
                    'type': 'research'
                })
                count += 1
            
            print(f"{Colors.GREEN}✓ Added {count} sources to your collection{Colors.END}\n")
        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Error importing sources: {str(e)}{Colors.END}")
    
    def _format_research_results(self, research: Dict) -> str:
        """Format deep research results for context"""
        context = "=== DEEP RESEARCH RESULTS ===\n"
        context += f"Original Query: {research['original_query']}\n"
        context += f"Research Depth: {research['research_depth']}\n"
        context += f"Total Sources: {research['total_sources']}\n\n"
        
        for idx, result in enumerate(research['results'][:10], 1):
            context += f"[Source {idx}]\n"
            context += f"Title: {result['title']}\n"
            context += f"Relevance: {result.get('relevance_score', 0):.2f}\n"
            if result.get('url'):
                context += f"URL: {result['url']}\n"
            context += f"Content: {result['content'][:500]}...\n"
            if result.get('full_content'):
                context += f"Extended Content Available: Yes\n"
            context += "\n"
        
        context += "=== END RESEARCH RESULTS ===\n"
        context += "Synthesize information from multiple sources to provide a comprehensive answer.\n"
        
        return context
    
    def _format_file_context(self) -> str:
        """Format uploaded files context"""
        context = "=== UPLOADED FILES ===\n"
        
        for idx, file_data in enumerate(self.uploaded_files, 1):
            context += f"\n[File {idx}]\n"
            context += f"Type: {file_data['type']}\n"
            context += f"Metadata: {file_data['metadata']}\n"
            
            if file_data['type'] in ['text', 'pdf']:
                context += f"Content:\n{file_data['content'][:2000]}...\n"
            elif file_data['type'] == 'image':
                context += "Image data attached inline\n"
            else:
                context += "Binary file attached\n"
        
        context += "\n=== END FILES ===\n"
        return context
    
    def save_session(self):
        """Save current session to Firestore with AI-generated summary"""
        if not self.firestore_enabled or len(self.conversation_history) == 0:
            return
        
        print(f"{Colors.CYAN}💾 Generating session summary...{Colors.END}")
        
        # Generate summary using Gemini
        summary_prompt = f"""Analyze this learning session and provide a concise summary in the following format:

Session Date: {datetime.now().strftime('%Y-%m-%d')}
Duration: {len(self.conversation_history)} exchanges

Topics Covered: [List main topics discussed]
Key Concepts Learned: [List 3-5 key concepts]
Student Progress: [Brief assessment of understanding]
Strengths Demonstrated: [List 2-3 strengths]
Areas for Improvement: [List 2-3 areas]
Recommended Next Steps: [2-3 suggestions]

Conversation:
{self._get_conversation_text()[:3000]}

Provide the summary in natural language, organized clearly."""
        
        summary = self.send_message(summary_prompt, skip_history=True)
        
        session_data = {
            "user_id": self.user_id,
            "subject": self.current_subject,
            "message_count": len(self.conversation_history),
            "interaction_count": self.user_profile['interaction_count'],
            "topics_discussed": self._extract_topics(),
            "full_conversation": self._get_conversation_text(),
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
        session_id = self.fs_manager.save_session(self.user_id, session_data, summary)
        
        # Update user profile
        self.user_profile['total_sessions'] += 1
        self.user_profile['last_session'] = datetime.now().isoformat()
        self._save_user_profile()
        
        print(f"{Colors.GREEN}✓ Session saved: {session_id}{Colors.END}\n")
    
    def _get_conversation_text(self) -> str:
        """Get full conversation as text"""
        text = ""
        for msg in self.conversation_history:
            role = "STUDENT" if msg["role"] == "user" else "TUTOR"
            content = msg["parts"][0]["text"]
            text += f"{role}: {content}\n\n"
        return text
    
    def _extract_topics(self) -> List[str]:
        """Extract discussed topics from conversation"""
        # Simplified topic extraction
        topics = set()
        conversation = self._get_conversation_text().lower()
        
        # Common academic topics
        topic_keywords = [
            'photosynthesis', 'algebra', 'calculus', 'physics', 'chemistry',
            'biology', 'history', 'geography', 'literature', 'grammar',
            'programming', 'mathematics', 'science', 'python', 'java',
            'newton', 'einstein', 'shakespeare', 'equation', 'theorem'
        ]
        
        for keyword in topic_keywords:
            if keyword in conversation:
                topics.add(keyword.title())
        
        return list(topics)[:10]
    
    def _save_user_profile(self):
        """Save user profile to Firestore with comprehensive insights"""
        if self.firestore_enabled:
            chat_content = self._get_conversation_text() if self.conversation_history else ""
            insights = self.personalization.analyze_learning_patterns(self.user_profile, chat_content)
            self.user_profile['learning_insights'] = insights
            self.user_profile['last_updated'] = datetime.now().isoformat()
            
            self.fs_manager.save_user_profile(self.user_id, self.user_profile)
    
    def load_knowledge_base(self, filepath: str):
        """Load knowledge base from file"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                self.knowledge_base = f.read()
            print(f"{Colors.GREEN}✓ Knowledge base loaded: {filepath}{Colors.END}\n")
            self.system_prompt = self._create_system_prompt()
        except Exception as e:
            print(f"{Colors.RED}✗ Error loading knowledge base: {str(e)}{Colors.END}\n")
    
    def generate_quiz(self, topic: str, difficulty: str = None, num_questions: int = 5):
        """Generate and administer quiz"""
        if difficulty is None:
            difficulty = self.user_profile.get('difficulty_preference', 'intermediate')
        
        quiz_data = self.quiz_gen.generate_quiz(topic, difficulty, num_questions)
        
        if quiz_data:
            results = self.quiz_gen.administer_quiz(quiz_data)
            
            if results and self.firestore_enabled:
                self.fs_manager.save_quiz_result(self.user_id, results)
                
                self.user_profile['total_quizzes'] += 1
                topic_key = topic.lower().replace(' ', '_')
                self.user_profile['quiz_scores'][topic_key] = results['percentage']
                
                scores = list(self.user_profile['quiz_scores'].values())
                self.user_profile['average_quiz_score'] = sum(scores) / len(scores) if scores else 0
                
                self._save_user_profile()
                self.system_prompt = self._create_system_prompt()
            
            return results
        
        return None
    
    def generate_flashcards(self, topic: str, num_cards: int = None):
        """Generate NotebookLM-style flashcards with auto-decided count"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
        flashcard_data = self.flashcard_gen.generate_flashcards(topic, num_cards)
        
        if flashcard_data:
            print(f"\n{Colors.BOLD}{Colors.GREEN}📇 FLASHCARDS: {topic}{Colors.END}\n")
            
            for idx, card in enumerate(flashcard_data.get('flashcards', []), 1):
                print(f"{Colors.CYAN}Card {idx}/{len(flashcard_data.get('flashcards', []))}:{Colors.END}")
                front = card.get('front', '')
                back = card.get('back', '')
                memory_aid = card.get('memory_aid', '')
                difficulty = card.get('difficulty', 'intermediate')
                
                print(f"{Colors.YELLOW}[{difficulty.upper()}]{Colors.END} {Colors.BOLD}{front}{Colors.END}")
                print(f"{Colors.CYAN}→ {back}{Colors.END}")
                if memory_aid:
                    print(f"{Colors.GREEN}💡 Memory Aid: {memory_aid}{Colors.END}")
                print()
            
            if flashcard_data.get('learning_notes'):
                print(f"{Colors.MAGENTA}📝 Learning Notes: {flashcard_data.get('learning_notes')}{Colors.END}\n")
            
            print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")
            return flashcard_data
        
        return None
    
    def generate_mindmap(self, topic: str, depth: int = None):
        """Generate content-rich mind map with auto-decided depth and density"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
        mindmap_data = self.mindmap_gen.generate_mindmap(topic, depth)
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")
        return mindmap_data
    
    def generate_visual(self, topic: str):
        """Generate visual representation for a topic"""
        learning_style = self.user_profile.get('learning_style', 'educational')
        image_path = self.visual_gen.generate_visual(topic, learning_style)
        
        if image_path:
            print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
            print(f"{Colors.GREEN}✓ Visual representation saved!{Colors.END}")
            print(f"{Colors.CYAN}Location: {image_path}{Colors.END}")
            print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")
        
        return image_path
    
    def generate_report(self) -> str:
        """Generate and display comprehensive learning report"""
        if len(self.conversation_history) == 0:
            print(f"{Colors.YELLOW}⚠️ No conversation yet. Generate a report after learning!{Colors.END}\n")
            return None
        
        report = self.report_gen.generate_session_report()
        self.report_gen.display_report(report)
        
        save_choice = input(f"{Colors.GREEN}Save report to file? (y/n): {Colors.END}").strip().lower()
        if save_choice == 'y':
            report_path = self.report_gen.save_report(report, self.user_id)
            if report_path:
                print(f"{Colors.GREEN}✓ Report saved: {report_path}{Colors.END}\n")
        
        return report
    
    def show_sources(self, topic: str = None):
        """Display learning sources"""
        self.source_manager.display_sources(topic)
    
    def set_study_style(self):
        """Set preferred study style (NotebookLM-inspired)"""
        print(f"\n{Colors.BOLD}{Colors.CYAN}🎓 Study Style Preferences{Colors.END}\n")
        print("Choose your preferred study approach:")
        print("1. Deep Learner     - Comprehensive topics, more details")
        print("2. Quick Learner    - Concise summaries, key points")
        print("3. Visual Learner   - Diagrams, mind maps, visuals")
        print("4. Interactive      - Quizzes, flashcards, engagement")
        print("5. Balanced         - Mix of all approaches")
        
        choice = input(f"\n{Colors.GREEN}Select (1-5): {Colors.END}").strip()
        
        style_map = {
            "1": "deep",
            "2": "quick",
            "3": "visual",
            "4": "interactive",
            "5": "balanced"
        }
        
        if choice in style_map:
            self.user_profile['study_style'] = style_map[choice]
            self._save_user_profile()
            print(f"{Colors.GREEN}✓ Study style set to: {style_map[choice].title()}{Colors.END}\n")
        else:
            print(f"{Colors.RED}Invalid choice{Colors.END}\n")
    
    def show_dashboard(self):
        """Display professional learning dashboard with comprehensive analytics"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*85}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{' '*20}📊 LEARNING ANALYTICS DASHBOARD 📊{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'═'*85}{Colors.END}\n")

        profile = self.user_profile
        chat_content = self._get_conversation_text() if self.conversation_history else ""
        insights = self.personalization.analyze_learning_patterns(profile, chat_content)

        # Student Profile Section
        print(f"{Colors.BOLD}{Colors.GREEN}👤 STUDENT PROFILE:{Colors.END}")
        print(f"  {Colors.CYAN}Name:{Colors.END} {profile.get('student_name', 'Not configured')}")
        print(f"  {Colors.CYAN}Grade Level:{Colors.END} {profile.get('grade_level', 'Not specified')}")
        print(f"  {Colors.CYAN}Learning Style:{Colors.END} {profile.get('learning_style', 'balanced').title()}")
        print(f"  {Colors.CYAN}Preferred Difficulty:{Colors.END} {profile.get('difficulty_preference', 'intermediate').title()}")
        print()

        # Learning Statistics Section
        print(f"{Colors.BOLD}{Colors.MAGENTA}📈 LEARNING STATISTICS:{Colors.END}")
        stats = [
            ("Total Sessions", profile.get('total_sessions', 0)),
            ("Total Interactions", profile.get('interaction_count', 0)),
            ("Total Quizzes", profile.get('total_quizzes', 0)),
            ("Average Quiz Score", f"{profile.get('average_quiz_score', 0):.1f}%"),
            ("Engagement Score", f"{insights.get('engagement_score', 0):.1f}/100")
        ]
        for label, value in stats:
            print(f"  {Colors.YELLOW}●{Colors.END} {label}: {Colors.BOLD}{value}{Colors.END}")
        print()

        # Learning Insights Section
        print(f"{Colors.BOLD}{Colors.BLUE}🎯 LEARNING INSIGHTS:{Colors.END}")
        insights_data = [
            ("Learning Pace", insights.get('learning_pace', 'unknown').title()),
            ("Comprehension Level", insights.get('comprehension_level', 'intermediate').title()),
            ("Learning Style", insights.get('learning_style_actual', 'balanced').title()),
            ("Recommended Difficulty", insights.get('recommended_difficulty', 'intermediate').title()),
            ("Optimal Session Time", insights.get('optimal_session_time', '20-30 minutes')),
            ("Engagement Level", self._get_engagement_level(insights.get('engagement_score', 0)))
        ]
        for label, value in insights_data:
            print(f"  {Colors.CYAN}▸{Colors.END} {label}: {Colors.BOLD}{value}{Colors.END}")
        print()

        # Cognitive Patterns
        if insights.get('cognitive_patterns'):
            print(f"{Colors.BOLD}{Colors.MAGENTA}🧠 COGNITIVE PATTERNS:{Colors.END}")
            print(f"  {insights.get('cognitive_patterns', 'Pattern analysis in progress')}")
            print()

        # Performance Breakdown
        strong = insights.get('strong_areas') or insights.get('strong_subjects', [])
        if strong:
            print(f"{Colors.BOLD}{Colors.GREEN}✅ STRONG AREAS:{Colors.END}")
            for subj in strong[:5]:
                print(f"  {Colors.GREEN}✓{Colors.END} {subj}")
            print()

        improve = insights.get('weak_areas') or insights.get('improvement_areas', [])
        if improve:
            print(f"{Colors.BOLD}{Colors.YELLOW}🎯 AREAS FOR DEVELOPMENT:{Colors.END}")
            for area in improve[:5]:
                print(f"  {Colors.YELLOW}•{Colors.END} {area}")
            print()

        # Personalized Insights
        insights_list = insights.get('personalized_insights', [])
        if insights_list and isinstance(insights_list, list):
            print(f"{Colors.BOLD}{Colors.CYAN}💡 KEY INSIGHTS:{Colors.END}")
            for insight in insights_list[:3]:
                print(f"  {Colors.CYAN}→{Colors.END} {insight}")
            print()

        # Recent Topics
        topics = profile.get('topics_learned', [])
        if topics:
            print(f"{Colors.BOLD}{Colors.CYAN}📚 RECENT TOPICS LEARNED ({len(topics)} total):{Colors.END}")
            recent_topics = topics[-8:]  # Show last 8 topics
            for i, topic in enumerate(recent_topics, 1):
                print(f"  {Colors.CYAN}{i}.{Colors.END} {topic}")
            print()

        # Progress Visualization
        self._show_progress_visualization(profile, insights)

        print(f"{Colors.BOLD}{Colors.BLUE}{'═'*85}{Colors.END}\n")

    def _get_engagement_level(self, score: float) -> str:
        """Convert engagement score to descriptive level"""
        if score >= 80:
            return f"{Colors.GREEN}Highly Engaged{Colors.END}"
        elif score >= 60:
            return f"{Colors.CYAN}Moderately Engaged{Colors.END}"
        elif score >= 40:
            return f"{Colors.YELLOW}Needs Improvement{Colors.END}"
        else:
            return f"{Colors.RED}Low Engagement{Colors.END}"

    def _show_progress_visualization(self, profile: Dict, insights: Dict):
        """Show visual progress indicators"""
        print(f"{Colors.BOLD}{Colors.MAGENTA}📊 PROGRESS VISUALIZATION:{Colors.END}")

        # Quiz Performance Bar
        avg_score = profile.get('average_quiz_score', 0)
        bar_length = 20
        filled = int((avg_score / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"  Quiz Performance: [{Colors.GREEN}{bar}{Colors.END}] {avg_score:.1f}%")

        # Engagement Bar
        eng_score = insights.get('engagement_score', 0)
        filled = int((eng_score / 100) * bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        color = Colors.GREEN if eng_score >= 70 else Colors.YELLOW if eng_score >= 50 else Colors.RED
        print(f"  Engagement Level: [{color}{bar}{Colors.END}] {eng_score:.1f}%")

        # Sessions Progress
        sessions = profile.get('total_sessions', 0)
        session_goal = 10  # Example goal
        filled = min(int((sessions / session_goal) * bar_length), bar_length)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"  Session Progress: [{Colors.BLUE}{bar}{Colors.END}] {sessions}/{session_goal} sessions")
        print()
    
    def generate_learning_recommendations(self) -> str:
        """Generate personalized learning recommendations using AI"""
        try:
            # Gather comprehensive user data
            user_data = self._get_comprehensive_user_data()

            prompt = f"""Based on this student's comprehensive learning profile, generate 5-7 personalized learning recommendations.

STUDENT PROFILE SUMMARY:
{user_data}

Generate recommendations that are:
1. Specific and actionable
2. Based on their learning patterns and performance
3. Aligned with their interests and goals
4. Progressive (building on current knowledge)
5. Varied in format (videos, projects, readings, etc.)

Format as a structured list with:
- **Topic/Area**: Brief description
- **Why Recommended**: Connection to their profile
- **Suggested Activity**: Specific learning action
- **Estimated Time**: Time commitment
- **Difficulty Level**: Based on their preferences

Focus on their strengths, address weaknesses, and suggest next steps in their learning journey."""

            # Use HuggingFaceChat instead of Gemini
            recommendations = HuggingFaceChat.chat(prompt)
            if recommendations and not recommendations.startswith("Error:"):
                return recommendations
            else:
                print(f"{Colors.YELLOW}⚠️ AI recommendations failed: {recommendations}{Colors.END}")
                return self._generate_fallback_recommendations()

        except Exception as e:
            print(f"{Colors.YELLOW}⚠️ Could not generate AI recommendations: {str(e)}{Colors.END}")

        # Fallback recommendations
        return self._generate_fallback_recommendations()

    def _generate_fallback_recommendations(self) -> str:
        """Generate basic recommendations when AI fails"""
        profile = self.user_profile
        insights = self.personalization.analyze_learning_patterns(profile)

        recommendations = "**PERSONALIZED LEARNING RECOMMENDATIONS**\n\n"

        # Based on quiz performance
        avg_score = profile.get('average_quiz_score', 0)
        if avg_score < 70:
            recommendations += "• **Focus on Fundamentals**: Review basic concepts in challenging subjects\n"
        elif avg_score > 85:
            recommendations += "• **Advance to Complex Topics**: Ready for advanced material and projects\n"

        # Based on engagement
        eng_score = insights.get('engagement_score', 0)
        if eng_score < 50:
            recommendations += "• **Increase Engagement**: Try interactive projects and real-world applications\n"

        # Based on learning style
        style = profile.get('learning_style', 'balanced')
        if style == 'visual':
            recommendations += "• **Visual Learning**: Explore diagrams, videos, and interactive simulations\n"
        elif style == 'verbal':
            recommendations += "• **Verbal Learning**: Focus on discussions, writing, and explanations\n"

        # Subject-specific
        interests = profile.get('subjects_of_interest', [])
        if interests:
            recommendations += f"• **Deepen Interests**: Explore advanced topics in {', '.join(interests[:2])}\n"

        return recommendations

    def show_recommendations(self):
        """Display personalized learning recommendations"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*75}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{' '*15}🎯 PERSONALIZED LEARNING RECOMMENDATIONS{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'═'*75}{Colors.END}\n")

        print(f"{Colors.MAGENTA}🤖 Generating AI-powered recommendations...{Colors.END}\n")

        recommendations = self.generate_learning_recommendations()

        print(f"{Colors.BOLD}{Colors.GREEN}📚 YOUR LEARNING PATHWAY:{Colors.END}\n")
        print(recommendations)
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*75}{Colors.END}\n")

    def clear_history(self):
        """Clear conversation history"""
        self.conversation_history = []
        print(f"{Colors.YELLOW}Conversation history cleared.{Colors.END}\n")


def print_banner():
    """Print professional welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*95}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{' '*10}🎓 ADVANCED AI TUTOR - PROFESSIONAL LEARNING SYSTEM 🎓{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═'*95}{Colors.END}\n")

    print(f"{Colors.BOLD}{Colors.GREEN}🚀 CORE FEATURES:{Colors.END}")
    print(f"  {Colors.CYAN}●{Colors.END} Advanced AI Tutor with Socratic Method & Evidence-Based Pedagogy")
    print(f"  {Colors.CYAN}●{Colors.END} Deep Research with Auto-Approved Educational Resources")
    print(f"  {Colors.CYAN}●{Colors.END} Multi-Format File Processing & RAG-Powered Search")
    print(f"  {Colors.CYAN}●{Colors.END} Cloud Data Persistence with Firestore Analytics")
    print()

    print(f"{Colors.BOLD}{Colors.YELLOW}📚 NOTEBOOKLM-INSPIRED STUDY TOOLS:{Colors.END}")
    print(f"  {Colors.CYAN}●{Colors.END} Adaptive Quiz Generation with Smart Difficulty Scaling")
    print(f"  {Colors.CYAN}●{Colors.END} AI-Generated Flashcards (Auto-count, Rich Content)")
    print(f"  {Colors.CYAN}●{Colors.END} Deep Content Mind Maps (Auto-depth, Multiple Branches)")
    print(f"  {Colors.CYAN}●{Colors.END} Visual Representations powered by Stable Diffusion")
    print()

    print(f"{Colors.BOLD}{Colors.MAGENTA}💡 INTELLIGENT PERSONALIZATION:{Colors.END}")
    print(f"  {Colors.YELLOW}•{Colors.END} Gemini-Powered Learning Pattern Analysis")
    print(f"  {Colors.YELLOW}•{Colors.END} Chat Content-Based Comprehension Assessment")
    print(f"  {Colors.YELLOW}•{Colors.END} Advanced Topic Complexity Analysis")
    print(f"  {Colors.YELLOW}•{Colors.END} Comprehensive Learning Analytics Dashboard")
    print(f"  {Colors.YELLOW}•{Colors.END} AI-Generated Personalized Recommendations")
    print()

    print(f"{Colors.BOLD}{Colors.BLUE}⚡ POWERED BY:{Colors.END} {Colors.CYAN}Google Gemini 2.0 Flash (Core AI) + Optional Stable Diffusion{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═'*95}{Colors.END}\n")


def print_help():
    """Print professional help menu"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'═'*90}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.CYAN}{' '*20}📚 COMMAND REFERENCE 📚{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═'*90}{Colors.END}\n")

    print(f"{Colors.BOLD}{Colors.GREEN}🎯 LEARNING MANAGEMENT:{Colors.END}")
    print(f"  {Colors.CYAN}/profile{Colors.END}                 - Configure personalized learning profile")
    print(f"  {Colors.CYAN}/dashboard{Colors.END}               - View comprehensive learning analytics")
    print(f"  {Colors.CYAN}/recommendations{Colors.END}         - Get AI-powered learning recommendations")
    print(f"  {Colors.CYAN}/subject <name>{Colors.END}          - Set current learning focus area")
    print(f"  {Colors.CYAN}/style{Colors.END}                   - Set study style preferences")
    print()

    print(f"{Colors.BOLD}{Colors.MAGENTA}📁 CONTENT & RESEARCH:{Colors.END}")
    print(f"  {Colors.CYAN}/upload <file>{Colors.END}           - Process documents, images, or PDFs")
    print(f"  {Colors.CYAN}/search <query>{Colors.END}          - Search your uploaded documents intelligently")
    print(f"  {Colors.CYAN}/research <query>{Colors.END}        - AI-powered deep research with source import")
    print(f"  {Colors.CYAN}/load <file>{Colors.END}             - Import external knowledge base")
    print(f"  {Colors.CYAN}/sources [topic]{Colors.END}         - View your learning sources collection")
    print()

    print(f"{Colors.BOLD}{Colors.YELLOW}📚 STUDY TOOLS (NotebookLM-inspired):{Colors.END}")
    print(f"  {Colors.CYAN}/quiz <topic>{Colors.END}            - Generate adaptive quizzes")
    print(f"  {Colors.CYAN}/flashcards <topic>{Colors.END}      - Create NotebookLM-style flashcards (AI-decided count)")
    print(f"  {Colors.CYAN}/mindmap <topic>{Colors.END}         - Generate rich content mind maps (AI-decided depth)")
    print(f"  {Colors.CYAN}/visual <topic>{Colors.END}          - Generate visual representations")
    print()

    print(f"{Colors.BOLD}{Colors.BLUE}📊 REPORTING & ANALYTICS:{Colors.END}")
    print(f"  {Colors.CYAN}/report{Colors.END}                  - Generate personalized learning report")
    print()

    print(f"{Colors.BOLD}{Colors.CYAN}💾 SESSION MANAGEMENT:{Colors.END}")
    print(f"  {Colors.CYAN}/save{Colors.END}                    - Persist session with AI summary")
    print(f"  {Colors.CYAN}/clear{Colors.END}                   - Reset conversation context")
    print()

    print(f"{Colors.BOLD}{Colors.GREEN}🔧 SYSTEM CONTROLS:{Colors.END}")
    print(f"  {Colors.CYAN}/help{Colors.END}                    - Display this command reference")
    print(f"  {Colors.CYAN}/quit{Colors.END}                    - Exit learning session")
    print()

    print(f"{Colors.BOLD}{Colors.MAGENTA}💡 TIP:{Colors.END} {Colors.CYAN}Ask questions naturally or use commands for specific functions{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'═'*90}{Colors.END}\n")


def setup_profile(tutor: AdvancedAITutor):
    """Interactive profile setup"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}👋 Let's personalize your learning experience!{Colors.END}\n")
    
    name = input(f"{Colors.GREEN}What's your name? {Colors.END}").strip()
    if name:
        tutor.user_profile['student_name'] = name
        print(f"\n{Colors.CYAN}Nice to meet you, {name}! 😊{Colors.END}\n")
    
    grade = input(f"{Colors.GREEN}What grade/class are you in? (e.g., 7, 10, College) {Colors.END}").strip()
    if grade:
        tutor.user_profile['grade_level'] = grade
    
    print(f"\n{Colors.YELLOW}Learning Style:{Colors.END}")
    print("1. Visual (diagrams, examples, images)")
    print("2. Verbal (detailed text explanations)")
    print("3. Balanced (mix of both)")
    style_choice = input(f"{Colors.GREEN}Choose (1-3): {Colors.END}").strip()
    style_map = {"1": "visual", "2": "verbal", "3": "balanced"}
    if style_choice in style_map:
        tutor.user_profile['learning_style'] = style_map[style_choice]
    
    print(f"\n{Colors.YELLOW}Preferred Difficulty:{Colors.END}")
    print("1. Beginner")
    print("2. Intermediate")
    print("3. Advanced")
    diff_choice = input(f"{Colors.GREEN}Choose (1-3): {Colors.END}").strip()
    diff_map = {"1": "beginner", "2": "intermediate", "3": "advanced"}
    if diff_choice in diff_map:
        tutor.user_profile['difficulty_preference'] = diff_map[diff_choice]
    
    subjects = input(f"\n{Colors.GREEN}What subjects are you interested in? (comma-separated): {Colors.END}").strip()
    if subjects:
        tutor.user_profile['subjects_of_interest'] = [s.strip() for s in subjects.split(',')]
    
    print(f"\n{Colors.GREEN}✓ Profile configured! Saving to Firestore...{Colors.END}")
    tutor._save_user_profile()
    
    # Recreate system prompt with new profile
    tutor.system_prompt = tutor._create_system_prompt()
    print(f"{Colors.GREEN}✓ Personalization engine updated!{Colors.END}\n")


def main():
    """Main CLI loop with comprehensive error handling"""
    try:
        print_banner()
    except Exception as e:
        print(f"Warning: Could not display banner: {str(e)}")
        print("🎓 Advanced AI Tutor - Professional Learning System\n")

    # Check API key
    if not GEMINI_API_KEY:
        print(f"{Colors.RED}❌ CRITICAL ERROR: GEMINI_API_KEY environment variable not set!{Colors.END}")
        print(f"{Colors.YELLOW}🔧 SOLUTION: Set it with: export GEMINI_API_KEY='your-api-key'{Colors.END}")
        print(f"{Colors.CYAN}📖 Get your key from: https://makersuite.google.com/app/apikey{Colors.END}\n")
        return

    # Get user ID with validation
    try:
        user_id = input(f"{Colors.CYAN}👤 Enter your user ID (or press Enter for 'default_user'): {Colors.END}").strip()
        if not user_id:
            user_id = "default_user"
        elif not user_id.replace('_', '').replace('-', '').isalnum():
            print(f"{Colors.YELLOW}⚠️  User ID contains invalid characters. Using 'default_user' instead.{Colors.END}")
            user_id = "default_user"
    except (EOFError, KeyboardInterrupt):
        print(f"\n{Colors.CYAN}👋 Goodbye!{Colors.END}")
        return

    print(f"\n{Colors.YELLOW}🚀 Initializing Advanced AI Tutor for user: {user_id}{Colors.END}")

    # Initialize tutor with error handling
    tutor = None
    try:
        tutor = AdvancedAITutor(user_id=user_id)
        print(f"{Colors.GREEN}✅ Tutor initialized successfully!{Colors.END}")
    except ValueError as e:
        print(f"{Colors.RED}❌ Configuration Error: {str(e)}{Colors.END}")
        return
    except ImportError as e:
        print(f"{Colors.RED}❌ Missing Dependencies: {str(e)}{Colors.END}")
        return
    except Exception as e:
        print(f"{Colors.RED}❌ Initialization Failed: {str(e)}{Colors.END}")
        print(f"{Colors.YELLOW}💡 Try checking your internet connection and API key{Colors.END}")
        return

    print(f"{Colors.GREEN}🎯 Ready for learning session!{Colors.END}\n")

    # Profile setup for new users
    try:
        if not tutor.user_profile.get('student_name'):
            print(f"{Colors.MAGENTA}🌟 Welcome! Let's personalize your learning experience.{Colors.END}")
            setup = input(f"{Colors.CYAN}📝 Would you like to set up your learning profile? (y/n): {Colors.END}").strip().lower()
            if setup == 'y':
                setup_profile(tutor)
            else:
                print(f"{Colors.BLUE}ℹ️  You can set up your profile anytime with /profile{Colors.END}")
    except (EOFError, KeyboardInterrupt):
        print(f"\n{Colors.CYAN}👋 Session ended. Goodbye!{Colors.END}")
        return

    try:
        print_help()
        print(f"{Colors.BOLD}{Colors.GREEN}🚀 Start learning! Ask me anything or use commands!{Colors.END}\n")
    except Exception as e:
        print(f"Warning: Could not display help: {str(e)}")

    # Main interaction loop
    while True:
        try:
            user_input = input(f"{Colors.BOLD}{Colors.GREEN}You: {Colors.END}").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith('/'):
                try:
                    cmd_parts = user_input.split(maxsplit=1)
                    cmd = cmd_parts[0].lower()

                    if cmd in ['/quit', '/exit']:
                        # Save session before exiting
                        if tutor and len(tutor.conversation_history) > 0:
                            try:
                                save = input(f"\n{Colors.CYAN}💾 Save this session? (y/n): {Colors.END}").strip().lower()
                                if save == 'y':
                                    tutor.save_session()
                                    print(f"{Colors.GREEN}✅ Session saved successfully!{Colors.END}")
                            except (EOFError, KeyboardInterrupt):
                                print(f"\n{Colors.YELLOW}⚠️  Session not saved{Colors.END}")

                        print(f"\n{Colors.CYAN}🌟 Keep learning and stay curious! Goodbye!{Colors.END}\n")
                        break

                    elif cmd == '/help':
                        print_help()

                    elif cmd == '/profile':
                        setup_profile(tutor)

                    elif cmd == '/dashboard':
                        tutor.show_dashboard()

                    elif cmd == '/recommendations':
                        tutor.show_recommendations()

                    elif cmd == '/subject':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /subject <subject_name>{Colors.END}\n")
                        else:
                            subject = cmd_parts[1]
                            tutor.current_subject = subject
                            tutor.system_prompt = tutor._create_system_prompt()
                            print(f"{Colors.GREEN}✅ Subject focus set to: {subject}{Colors.END}\n")

                    elif cmd == '/upload':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /upload <filepath>{Colors.END}\n")
                        else:
                            filepath = cmd_parts[1]
                            if tutor.upload_file(filepath):
                                print(f"{Colors.GREEN}✅ File processed successfully!{Colors.END}")
                            else:
                                print(f"{Colors.RED}❌ File upload failed{Colors.END}")
                    elif cmd == '/search':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /search <query>{Colors.END}\n")
                        else:
                            query = cmd_parts[1]
                            try:
                                if not tutor.rag_processor:
                                    print(f"{Colors.YELLOW}⚠️ RAG processor not available{Colors.END}\n")
                                    continue
                                
                                print(f"{Colors.CYAN}🔍 Searching uploaded documents...{Colors.END}\n")
                                result = tutor.rag_processor.query_documents(
                                    query, 
                                    include_web=False, 
                                    use_hybrid=True
                                )
                                
                                if result['found']:
                                    print(f"{Colors.GREEN}✓ Found {result['total_results']} relevant sections{Colors.END}\n")
                                    print(f"{Colors.YELLOW}Sources:{Colors.END}")
                                    for source in result['local_sources']:
                                        print(f"  • {source}")
                                    print(f"\n{Colors.CYAN}Context:{Colors.END}")
                                    print(result['local_context'][:1000] + "...\n")
                                else:
                                    print(f"{Colors.YELLOW}⚠️ No relevant content found{Colors.END}\n")
                            except Exception as e:
                                print(f"{Colors.RED}❌ Search error: {str(e)}{Colors.END}\n")
                                
                    elif cmd == '/research':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /research <query>{Colors.END}\n")
                        else:
                            query = cmd_parts[1]
                            try:
                                print(f"\n{Colors.CYAN}🔬 Conducting AI-synthesized research...{Colors.END}\n")
                                research_result = research(query, max_results=5)
                                
                                if research_result:
                                    print(f"{Colors.CYAN}{'─' * 80}{Colors.END}\n")
                                else:
                                    print(f"{Colors.YELLOW}⚠️  Research returned no results{Colors.END}\n")
                            except (EOFError, KeyboardInterrupt):
                                print(f"\n{Colors.YELLOW}⚠️  Research cancelled{Colors.END}\n")

                    elif cmd == '/quiz':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /quiz <topic>{Colors.END}\n")
                        else:
                            topic = cmd_parts[1]
                            try:
                                num_input = input(f"{Colors.CYAN}📝 Number of questions (default 5): {Colors.END}").strip()
                                num_questions = int(num_input) if num_input.isdigit() else 5

                                print(f"{Colors.MAGENTA}🎯 Generating personalized quiz...{Colors.END}")
                                result = tutor.generate_quiz(topic, num_questions=num_questions)
                                if result:
                                    print(f"{Colors.GREEN}✅ Quiz completed! Check /dashboard for results.{Colors.END}")
                                else:
                                    print(f"{Colors.RED}❌ Quiz generation failed{Colors.END}")
                            except (ValueError, EOFError, KeyboardInterrupt):
                                print(f"\n{Colors.YELLOW}⚠️  Quiz cancelled{Colors.END}\n")
                    
                    elif cmd == '/flashcards':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /flashcards <topic>{Colors.END}\n")
                        else:
                            topic = cmd_parts[1]
                            try:
                                print(f"{Colors.MAGENTA}📇 Generating NotebookLM-style flashcards...{Colors.END}")
                                result = tutor.generate_flashcards(topic)
                                if result:
                                    print(f"{Colors.GREEN}✅ Flashcards generated successfully!{Colors.END}")
                                else:
                                    print(f"{Colors.RED}❌ Flashcard generation failed{Colors.END}")
                            except (ValueError, EOFError, KeyboardInterrupt):
                                print(f"\n{Colors.YELLOW}⚠️  Flashcard generation cancelled{Colors.END}\n")
                    
                    elif cmd == '/mindmap':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /mindmap <topic>{Colors.END}\n")
                        else:
                            topic = cmd_parts[1]
                            try:
                                print(f"{Colors.MAGENTA}🧠 Generating rich content mind map...{Colors.END}")
                                result = tutor.generate_mindmap(topic)
                                if result:
                                    print(f"{Colors.GREEN}✅ Mind map generated successfully!{Colors.END}")
                                else:
                                    print(f"{Colors.RED}❌ Mind map generation failed{Colors.END}")
                            except (ValueError, EOFError, KeyboardInterrupt):
                                print(f"\n{Colors.YELLOW}⚠️  Mind map generation cancelled{Colors.END}\n")
                    
                    elif cmd == '/visual':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /visual <topic>{Colors.END}\n")
                        else:
                            topic = cmd_parts[1]
                            try:
                                print(f"{Colors.MAGENTA}🎨 Generating visual representation...{Colors.END}")
                                result = tutor.generate_visual(topic)
                                if result:
                                    print(f"{Colors.GREEN}✅ Visual representation generated successfully!{Colors.END}")
                                else:
                                    print(f"{Colors.YELLOW}⚠️  Visual generation skipped (API not configured){Colors.END}")
                            except (EOFError, KeyboardInterrupt):
                                print(f"\n{Colors.YELLOW}⚠️  Visual generation cancelled{Colors.END}\n")

                    elif cmd == '/save':
                        try:
                            tutor.save_session()
                            print(f"{Colors.GREEN}✅ Session saved to cloud!{Colors.END}")
                        except Exception as e:
                            print(f"{Colors.RED}❌ Save failed: {str(e)}{Colors.END}")

                    elif cmd == '/load':
                        if len(cmd_parts) < 2:
                            print(f"{Colors.RED}❌ Usage: /load <filepath>{Colors.END}\n")
                        else:
                            try:
                                tutor.load_knowledge_base(cmd_parts[1])
                                print(f"{Colors.GREEN}✅ Knowledge base loaded!{Colors.END}")
                            except Exception as e:
                                print(f"{Colors.RED}❌ Load failed: {str(e)}{Colors.END}")

                    elif cmd == '/report':
                        try:
                            print(f"{Colors.MAGENTA}📊 Generating your personalized learning report...{Colors.END}")
                            tutor.generate_report()
                        except Exception as e:
                            print(f"{Colors.RED}❌ Report generation failed: {str(e)}{Colors.END}")
                    
                    elif cmd == '/sources':
                        try:
                            topic = cmd_parts[1] if len(cmd_parts) > 1 else None
                            tutor.show_sources(topic)
                        except Exception as e:
                            print(f"{Colors.RED}❌ Error displaying sources: {str(e)}{Colors.END}")
                    
                    elif cmd == '/style':
                        try:
                            tutor.set_study_style()
                        except Exception as e:
                            print(f"{Colors.RED}❌ Error setting study style: {str(e)}{Colors.END}")

                    elif cmd == '/clear':
                        tutor.clear_history()
                        print(f"{Colors.GREEN}✅ Conversation history cleared!{Colors.END}")

                    else:
                        print(f"{Colors.RED}❌ Unknown command: {cmd}{Colors.END}")
                        print(f"{Colors.CYAN}💡 Type /help for available commands{Colors.END}\n")

                except Exception as e:
                    print(f"{Colors.RED}❌ Command error: {str(e)}{Colors.END}\n")

                continue

            # Handle regular messages
            try:
                print(f"\n{Colors.CYAN}🤔 Processing your question...{Colors.END}\n")
                response = tutor.send_message(user_input)
                print(f"{Colors.BOLD}{Colors.BLUE}Tutor:{Colors.END}\n{response}\n")
                print(f"{Colors.CYAN}{'─' * 80}{Colors.END}\n")
            except Exception as e:
                print(f"{Colors.RED}❌ Response error: {str(e)}{Colors.END}")
                print(f"{Colors.YELLOW}💡 Try rephrasing your question or check your connection{Colors.END}\n")

        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}👋 Learning session interrupted. Goodbye!{Colors.END}\n")
            break
        except EOFError:
            print(f"\n\n{Colors.CYAN}👋 Input stream ended. Goodbye!{Colors.END}\n")
            break
        except Exception as e:
            print(f"{Colors.RED}❌ Unexpected error: {str(e)}{Colors.END}")
            print(f"{Colors.YELLOW}💡 If this persists, try restarting the application{Colors.END}\n")


if __name__ == "__main__":
    main()