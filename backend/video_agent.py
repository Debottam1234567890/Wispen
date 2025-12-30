from chatbot_enhanced import GroqChat, GeminiChat, BookshelfRAG, EdgeTTS, research, ImageGenerator
from firebase_admin import firestore
import uuid
import os
import json
import re
from typing import List, Dict, Any, Optional
from mutagen.mp3 import MP3
from stable_diffusion import StableDiffusionGenerator

# Initialize SD Generator
sd_generator = StableDiffusionGenerator()

class VideoAgent:
    """
    Agent responsible for generating structured JSON scene definitions for 
    low-compute educational animations.
    """

    def __init__(self):
        # Base paths for media
        self.public_audio_path = "audio/videos"
        self.public_image_path = "images/videos"
        
        self.audio_base_path = os.path.join(os.getcwd(), "wispen-ai-tutor", "public", self.public_audio_path)
        self.image_base_path = os.path.join(os.getcwd(), "wispen-ai-tutor", "public", self.public_image_path)
        
        self.public_audio_url_base = f"/{self.public_audio_path}"
        self.public_image_url_base = f"/{self.public_image_path}"
        
        # Ensure directories exist
        os.makedirs(self.audio_base_path, exist_ok=True)
        os.makedirs(self.image_base_path, exist_ok=True)
        
        # Syncing voices
        self.voices = {
            "Host A": "en-US-ChristopherNeural", # Male
            "Host B": "en-US-JennyNeural"        # Female
        }

    def _clean_json(self, text: str) -> str:
        """Robustly extract and clean JSON from LLM response."""
        if not text: return "{}"
        
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find the first { and last }
        match_obj = re.search(r'(\{.*\})', text, re.DOTALL)
        if not match_obj:
            return text.strip()
            
        cleaned = match_obj.group(0)
        
        # Minor fixes for common JSON errors
        cleaned = re.sub(r',\s*\}', '}', cleaned)
        cleaned = re.sub(r',\s*\]', ']', cleaned)
        cleaned = re.sub(r'//.*', '', cleaned)
        
        return cleaned.strip()

    def get_knowledge_context(self, topic: str, user_id: str, session_id: Optional[str] = None) -> str:
        """Fetch context from various sources, falling back to scientific web research if needed."""
        context_parts = []
        
        # 1. Try Bookshelf Search
        try:
            items = []
            # Access global db if available, otherwise skip
            import app
            if hasattr(app, 'db') and app.db:
                docs = app.db.collection('users').document(user_id).collection('bookshelf').stream()
                items = [doc.to_dict() for doc in docs]
            
            if items:
                relevant = BookshelfRAG.search(items, topic, top_k=5)
                if relevant:
                    context_parts.append("### FROM BOOKSHELF / NOTES:")
                    for r in relevant:
                        content = r.get('content', 'No content available')
                        source = r.get('source', 'Unknown source')
                        context_parts.append(f"- {content} (Source: {source})")
        except Exception as e:
            print(f"VideoAgent: Error fetching bookshelf: {e}")

        # 2. Try Deep Research if context is thin
        if len(context_parts) < 2 or any(k in topic.lower() for k in ["quantum", "science", "biology", "physics"]):
            try:
                print(f"DEBUG: VideoAgent triggering deep research for: {topic}")
                research_data = research(f"Scientific explanation of {topic}", max_results=3)
                if research_data:
                    context_parts.append("\n### FROM SCIENTIFIC WEB RESEARCH:")
                    context_parts.append(research_data.get('response', ''))
                    for source in research_data.get('sources', []):
                        snippet = source.get('snippet', 'No snippet available')
                        url = source.get('url', 'No URL available')
                        context_parts.append(f"- {snippet} (Ref: {url})")
            except Exception as e:
                print(f"VideoAgent: Research error: {e}")

        return "\n".join(context_parts) if context_parts else "No specific context found. Use your general scientific knowledge."

    def generate_scene(self, topic: str, user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates a visually stunning scientific animation JSON using Llama 3.
        Includes single-track continuous narration and Stable Diffusion images.
        """
        context = self.get_knowledge_context(topic, user_id, session_id)
        scene_id = str(uuid.uuid4())[:8]

        prompt = f"""You are a world-class Scientific Illustrator and Motion Graphics Designer. 
        Create a CLEAN, SCIENTIFIC 2D animation JSON for: "{topic}" in a PODCAST format.
        
        Using the provided context:
        {context}
        
        ### DESIGN & PODCAST STYLE:
        - **Format**: 9-10 Frames exactly.
        - **Visual Style**: Cartoonic educational detailed, clean lines, vibrant colors, clear diagrams.
        - **Camera Movement**: Describe simulated camera movement (pan/zoom) in the 'imagePrompt'.
        - **Podcast Duo**: Alternate between "Host A" (Expert) and "Host B" (Curious).
        
        ### JSON SCHEMA (STRICT):
        {{
          "title": "Clear Topic Title",
          "background": "#0f172a",
          "steps": [
            {{
              "narration": "Host A: Welcome everyone. Today we are exploring {topic}.",
              "speaker": "Host A",
              "imagePrompt": "Cartoonic educational illustration of {topic}, wide angle view, detailed laboratory setting",
              "cameraMovement": "Slow pan right",
              "layers": [
                {{"type": "text", "content": "{topic.upper()}", "x": 320, "y": 50, "font": "bold 32px 'Outfit'", "color": "#ffffff"}},
                {{"type": "particles", "source": {{"x": 100, "y": 180}}, "target": {{"x": 540, "y": 180}}, "count": 15, "color": "#3b82f6"}}
              ]
            }}
          ]
        }}

        ### RULES:
        1. **Frames**: MUST generate exactly 9 or 10 steps.
        2. **Narration**: MUST start with "Host A:" or "Host B:". Flow seamlessly from one to next.
        3. **Images**: Provide hyper-detailed scientific `imagePrompt` (50+ words). Always include: "absolutely no text, no letters, no words, no writing".
        4. **Valid JSON**: Produce ONLY the JSON object.
        """
        
        try:
            # Using a cheap & fast Llama model as requested
            response_text = GroqChat.chat(prompt, model="llama-3.1-8b-instant", json_mode=True)
            cleaned_json = self._clean_json(response_text)
            scene_data = json.loads(cleaned_json)

            full_audio_bytes = b""
            current_time_ms = 0
            
            # Process each step
            steps = scene_data.get('steps', [])
            
            print(f"VideoAgent: Processing {len(steps)} steps for media generation...")
            
            for i, step in enumerate(steps):
                narration = step.get('narration', '')
                speaker = step.get('speaker', 'Host A')
                img_prompt = step.get('imagePrompt')
                
                # --- 1. Audio Generation & Stitching ---
                voice = self.voices.get(speaker, self.voices["Host A"])
                clean_text = re.sub(r'^(Host A|Host B):\s*', '', narration)
                
                step_audio_bytes = EdgeTTS.generate_speech(clean_text, voice=voice)
                
                step_duration_ms = 0
                if step_audio_bytes:
                    # Append strictly to full audio
                    full_audio_bytes += step_audio_bytes
                    
                    # Calculate duration
                    try:
                        # Create temporary file to measure duration
                        temp_path = os.path.join(self.audio_base_path, f"temp_{scene_id}_{i}.mp3")
                        with open(temp_path, "wb") as f:
                            f.write(step_audio_bytes)
                        
                        audio_info = MP3(temp_path)
                        step_duration_ms = int(audio_info.info.length * 1000)
                        
                        # Cleanup temp
                        os.remove(temp_path)
                    except Exception as e:
                        print(f"Duration calc error: {e}, defaulting to 3000ms")
                        step_duration_ms = 3000
                else:
                    step_duration_ms = 3000 # Default if TTS fails
                
                # Set step timing
                step['start'] = current_time_ms
                step['end'] = current_time_ms + step_duration_ms
                current_time_ms += step_duration_ms
                
                # --- 2. Image Generation (Stable Diffusion) ---
                if img_prompt:
                    img_filename = f"{scene_id}_img_{i}_{int(current_time_ms)}.jpg"
                    img_path = os.path.join(self.image_base_path, img_filename)
                    
                    # Try SD first, fallback to Pollinations (ImageGenerator) if fails/no key
                    generated_file = sd_generator.generate_image(img_prompt, img_path)
                    
                    if not generated_file:
                        # Fallback
                        print(f"VideoAgent: Falling back to standard generator for step {i}")
                        generated_file = ImageGenerator.generate_image(img_prompt, img_filename, self.image_base_path)
                    
                    if generated_file:
                        # Add image as background layer
                        step['layers'].insert(0, {
                            "type": "image",
                            "url": f"{self.public_image_url_base}/{os.path.basename(generated_file)}",
                            "x": 320, "y": 180, "width": 640, "height": 360, "opacity": 1.0
                        })

            # Save Full Audio
            full_audio_filename = f"{scene_id}_full_narration.mp3"
            full_audio_path = os.path.join(self.audio_base_path, full_audio_filename)
            with open(full_audio_path, "wb") as f:
                f.write(full_audio_bytes)
            
            # Finalize Scene Data
            scene_data['topic'] = topic
            scene_data['scene_id'] = scene_id
            scene_data['audioUrl'] = f"{self.public_audio_url_base}/{full_audio_filename}"
            scene_data['duration'] = current_time_ms
            
            return scene_data
            
        except Exception as e:
            print(f"VideoAgent Critical Error: {e}")
            return {
                "title": topic, "duration": 5000, "steps": [{
                    "start": 0, "end": 5000, "narration": f"Error creating video: {e}",
                    "layers": [{"type": "text", "content": "Error Encountered", "x": 320, "y": 180}]
                }]
            }

video_agent = VideoAgent()
