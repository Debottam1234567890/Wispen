import os
import time
import json
import asyncio
import requests
import re
import base64
from typing import List, Dict, Tuple
from io import BytesIO
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# Import your existing utilities
from chatbot_enhanced import GroqChat
from firebase_admin import firestore, storage

# Determine public videos path - MUST be within backend folder for Render deployment
PUBLIC_VIDEOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'videos')
os.makedirs(PUBLIC_VIDEOS_DIR, exist_ok=True)

class VideoGeneratorService:
    """
    Service to generate educational MP4 videos sequentially and reliably.
    Integrates LLM for script generation + Pollinations for images + EdgeTTS for audio.
    """
    
    def __init__(self, db_client=None):
        self.db = db_client if db_client else firestore.client()

    def generate_script(self, topic: str) -> List[Dict]:
        """Use LLM to generate a 5-scene educational script."""
        print(f"  🧠 Generating script for: {topic}")
        
        prompt = f"""
        Create a 5-scene educational video script about: "{topic}".
        Output ONLY valid JSON object with a "scenes" key containing an array.
        
        JSON Structure (MUST be an object with "scenes" key):
        {{
            "scenes": [
                {{
                    "title": "Scene 1 Title",
                    "narration": "Detailed educational narration for this scene (2-3 sentences explaining the concept clearly).",
                    "image_prompt": "highly detailed educational illustration of [specific aspect], [visual details], clear scientific diagram",
                    "overlay_text": "SHORT LABEL (1-5 words)",
                    "overlay_position": "top"
                }},
                ...
            ]
        }}
        
        Rules:
        1. "image_prompt" must be very descriptive and visual but concise. NO TEXT in images.
        2. "overlay_text" must be very short (1-5 words) to label the scene.
        3. "narration" should be engaging, educational, and 2-3 sentences long.
        4. Generate exactly 5 scenes that build upon each other to tell a complete educational story.
        5. Return ONLY the JSON object with "scenes" key, nothing else.
        """
        
        fallback_script = [
            {
                "title": topic,
                "narration": f"Welcome. Today we are learning about {topic}.",
                "image_prompt": f"educational illustration of {topic}, scientific, clear, no text",
                "overlay_text": topic.upper()[:15],
                "overlay_position": "center"
            }
        ]
        
        try:
            # Use direct API call for custom params (max_tokens)
            groq_key = os.getenv("GROQ_API_KEY")
            if not groq_key:
                print("  ❌ No Groq API key found")
                return fallback_script

            print(f"  🤖 Sending to Groq (llama-3.1-8b-instant)...")
            
            payload = {
                "model": "llama-3.1-8b-instant", # Cheaper & Faster
                "messages": [
                    {"role": "system", "content": "You are a helpful educational video scriptwriter. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 8192, # Increased to ensure full 10-scene generation
                "response_format": {"type": "json_object"}
            }

            response_raw = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=30
            )

            if response_raw.status_code == 200:
                data = response_raw.json()
                response = data["choices"][0]["message"]["content"]
            else:
                print(f"  ❌ Groq API Error {response_raw.status_code}: {response_raw.text}")
                return fallback_script
            
            print(f"  📝 Raw LLM response type: {type(response)}")
            print(f"  📝 Raw LLM response preview: {str(response)[:200]}...")
            
            # Clean response if needed (remove markdown)
            if isinstance(response, str):
                response = re.sub(r'```json\s*', '', response)
                response = re.sub(r'```\s*', '', response)
                response = response.strip()
                script = json.loads(response)
            else:
                script = response
            
            print(f"  📝 Parsed script type: {type(script)}")
            
            # Validate - must be a list
            if isinstance(script, dict):
                # Sometimes LLM returns {"scenes": [...]} - extract the list
                if 'scenes' in script:
                    script = script['scenes']
                elif 'script' in script:
                    script = script['script']
                else:
                    # Take first value that's a list
                    for v in script.values():
                        if isinstance(v, list):
                            script = v
                            break
            
            if not isinstance(script, list):
                print(f"  ❌ Script is not a list: {type(script)}")
                return fallback_script
                
            if len(script) == 0:
                print(f"  ❌ Script is empty")
                return fallback_script
            
            # Validate each scene has required keys
            for i, scene in enumerate(script):
                if not isinstance(scene, dict):
                    print(f"  ❌ Scene {i} is not a dict: {type(scene)}")
                    return fallback_script
                if 'narration' not in scene or 'image_prompt' not in scene:
                    print(f"  ⚠️ Scene {i} missing keys, adding defaults")
                    scene.setdefault('narration', f"This is scene {i+1} about {topic}.")
                    scene.setdefault('image_prompt', f"educational illustration of {topic}, scene {i+1}")
                    scene.setdefault('overlay_text', f"Scene {i+1}")
                    scene.setdefault('overlay_position', 'top')
            
            
            print(f"  ✅ Script validated: {len(script)} scenes")
            
            # Ensure we have 10 scenes
            if len(script) < 10:
                print(f"  ⚠️ WARNING: Only {len(script)} scenes generated (expected 10)")
                print(f"  ⚠️ This may be due to token limits or LLM response truncation")
            
            return script
            
        except Exception as e:
            print(f"  ❌ Script generation failed: {e}")
            import traceback
            traceback.print_exc()
            return fallback_script

    def _generate_image_pollinations(self, prompt: str, output_path: str) -> bool:
        """Generate image using Pollinations.ai unified API with Flux model & Turbo fallback."""
        import urllib.parse
        import time
        
        api_key = os.getenv("POLLINATIONS_API_KEY")
        if api_key:
            api_key = api_key.strip().strip('"').strip("'")
            
        max_retries = 3 # Reduced retries per model to speed up fallback
        models = ["flux", "turbo"] # Try Flux first, then Turbo
        
        # Clean prompt: remove common LLM filler
        clean_prompt = prompt.replace("absolutely no text, no letters, no words, no writing", "").strip()
        clean_prompt = clean_prompt.rstrip('.').rstrip(',').strip()
        # STRICT NO TEXT INSTRUCTION
        enhanced_prompt = f"{clean_prompt}, colorful educational illustration, friendly style, vibrant colors, absolutely no text no letters no words no writing no labels no numbers no captions"
        encoded_prompt = urllib.parse.quote(enhanced_prompt)

        for model in models:
            print(f"    Trying Pollinations model: {model}...")
            for attempt in range(max_retries):
                try:
                    url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model={model}&nologo=true&seed={int(time.time() + attempt)}"
                    
                    headers = {}
                    if api_key:
                        headers["Authorization"] = f"Bearer {api_key}"
                    
                    response = requests.get(url, headers=headers, timeout=60)
                    
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                        img.save(output_path, quality=95)
                        print(f"    ✓ Saved ({model}): {output_path}")
                        return True
                    else:
                        print(f"    ⚠ HTTP {response.status_code} ({model}) at attempt {attempt+1}")
                        # If flux is down, don't waste all retries, move to turbo
                        if model == "flux" and "No active flux servers available" in response.text:
                            print("    ⚠ Flux servers down. Switching to Turbo fallback...")
                            break
                        
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"    ⚠ Error on {model} attempt {attempt+1}: {e}")
                    time.sleep(2)
        
        return False

    def _generate_image_stability(self, prompt: str, output_path: str) -> bool:
        """Generate image using Stability AI as a reliable high-tier fallback."""
        api_key = os.getenv("STABILITY_API_KEY")
        if not api_key:
            return False
            
        print("    Trying Stability AI fallback...")
        try:
            # Clean prompt for Stability with STRICT no-text instruction
            clean_prompt = prompt.replace("absolutely no text, no letters, no words, no writing", "").strip()
            
            response = requests.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "text_prompts": [
                        {"text": f"{clean_prompt}, colorful educational illustration, digital art, vibrant, no text no letters no words no labels", "weight": 1.0},
                        {"text": "text, labels, words, letters, numbers, captions, titles, watermarks, signature, blurry", "weight": -1.0}
                    ],
                    "cfg_scale": 7,
                    "height": 1024,
                    "width": 1024,
                    "samples": 1,
                    "steps": 30,
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                for i, image in enumerate(data["artifacts"]):
                    image_data = base64.b64decode(image["base64"])
                    img = Image.open(BytesIO(image_data))
                    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                    img.save(output_path, quality=95)
                    print(f"    ✓ Saved (Stability AI): {output_path}")
                    return True
            else:
                print(f"    ⚠ Stability AI Error: {response.text[:200]}")
        except Exception as e:
            print(f"    ⚠ Stability AI Exception: {e}")
        
        return False

    def _generate_image_infip(self, prompt: str, output_path: str) -> bool:
        """Generate image using Infip AI with nano-banana model at 1024x1024."""
        api_key = os.getenv("VIDEO_API_KEY")
        if not api_key:
            print("    ❌ No VIDEO_API_KEY found")
            return False
            
        print("    Trying Infip AI (nano-banana)...")
        try:
            url = "https://api.infip.pro/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Clean prompt and add STRICT no-text instruction
            clean_prompt = prompt.replace("absolutely no text, no letters, no words, no writing", "").strip()
            
            payload = {
                "model": "nano-banana",
                "prompt": f"{clean_prompt}, colorful educational illustration, digital art, vibrant, absolutely no text no letters no words no writing no labels no numbers no captions",
                "n": 1,
                "size": "1024x1024",
                "response_format": "url"
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=90)
            
            if response.status_code == 200:
                data = response.json()
                image_url = data["data"][0]["url"]
            elif response.status_code == 202:
                # Async mode - polling required
                task_data = response.json()
                poll_url = task_data.get("poll_url")
                print(f"    ⏳ Generation pending, polling {poll_url}...")
                
                # Poll for up to 90 seconds
                for p in range(18):
                    time.sleep(5)
                    poll_response = requests.get(poll_url, headers=headers, timeout=30)
                    if poll_response.status_code == 200:
                        p_data = poll_response.json()
                        # When completed, the 'status' field is often removed and 'data' is returned
                        if "data" in p_data and len(p_data["data"]) > 0:
                            image_url = p_data["data"][0].get("url")
                            if image_url:
                                print(f"    ✓ Infip generation complete!")
                                break
                        elif p_data.get("status") in ["processing", "pending"]:
                            print(f"    ... still processing ({p+1}/18)")
                        elif p_data.get("status") == "completed":
                            image_url = p_data.get("image_url") or p_data.get("data", [{}])[0].get("url")
                            if image_url:
                                break
                        elif p_data.get("status") == "failed":
                            print(f"    ❌ Infip task failed: {p_data.get('message')}")
                            return False
                    else:
                         print(f"    ⚠ Poll failed with status {poll_response.status_code}")
                else:
                    print("    ❌ Polling timed out")
                    return False
            else:
                print(f"    ⚠ Infip AI Error {response.status_code}: {response.text[:200]}")
                return False
                
            if 'image_url' in locals() and image_url:
                # Download the image
                img_response = requests.get(image_url, timeout=60)
                if img_response.status_code == 200:
                    img = Image.open(BytesIO(img_response.content))
                    # Resize to standard 1280x720 for video
                    img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                    img.save(output_path, quality=95)
                    print(f"    ✓ Saved (Infip AI): {output_path}")
                    return True
                else:
                    print(f"    ⚠ Failed to download image from Infip URL: {img_response.status_code}")
        except Exception as e:
            print(f"    ⚠ Infip AI Exception: {e}")
            
        return False




    def _add_text_overlay(self, image_path: str, text: str, position: str = "top"):
        """Add clean, correct text overlay to an image using PIL (from photosynthesis_video_generator.py)."""
        try:
            img = Image.open(image_path)
            draw = ImageDraw.Draw(img)
            
            # Try to load a nice font, fall back to default
            try:
                # macOS system fonts - try larger size
                font_paths = [
                    "/System/Library/Fonts/Helvetica.ttc",
                    "/System/Library/Fonts/SFNSDisplay.ttf",
                    "/Library/Fonts/Arial.ttf"
                ]
                font = None
                for fp in font_paths:
                    if os.path.exists(fp):
                        font = ImageFont.truetype(fp, 52)  # Larger font
                        break
                if not font:
                    font = ImageFont.load_default()
            except:
                font = ImageFont.load_default()
            
            # Calculate text position
            width, height = img.size
            
            # Get text bounding box
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # Position based on setting
            if position == "top":
                x = (width - text_width) // 2
                y = 25
            elif position == "center":
                x = (width - text_width) // 2
                y = (height - text_height) // 2
            elif position == "bottom":
                x = (width - text_width) // 2
                y = height - text_height - 25
            else:
                x = (width - text_width) // 2
                y = 25
            
            # Draw semi-transparent background for readability
            padding = 18
            bg_bbox = (x - padding, y - padding, x + text_width + padding, y + text_height + padding)
            
            # Create overlay for semi-transparent background
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rounded_rectangle(bg_bbox, radius=12, fill=(0, 0, 0, 200))
            
            # Convert original to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Paste overlay
            img = Image.alpha_composite(img, overlay)
            
            # Draw text
            draw = ImageDraw.Draw(img)
            draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
            
            # Save back
            img = img.convert('RGB')
            img.save(image_path, quality=95)
            
        except Exception as e:
            print(f"    ⚠️ Overlay failed: {e}")

    def _create_placeholder_image(self, title: str, output_path: str):
        """Create a styled placeholder image if generation fails (from photosynthesis_video_generator.py)."""
        try:
            img = Image.new('RGB', (1280, 720), color=(20, 60, 40))
            draw = ImageDraw.Draw(img)
            draw.text((640, 360), title, fill='white', anchor='mm')
            img.save(output_path)
            print(f"    ⚠ Created placeholder: {output_path}")
        except Exception as e:
            print(f"    ❌ Placeholder failed: {e}")

    async def _generate_audio(self, text: str, output_path: str) -> float:
        """Generate audio using EdgeTTS and return duration."""
        try:
            import edge_tts
            from mutagen.mp3 import MP3
            
            voice = "en-US-ChristopherNeural"
            communicate = edge_tts.Communicate(text, voice, rate="-2%")
            await communicate.save(output_path)
            
            audio = MP3(output_path)
            return audio.info.length
        except Exception as e:
            print(f"    ⚠️ Audio failed: {e}")
            return 3.0 # Default duration

    def combine_video(self, scenes_data: List[Dict], audio_path: str, output_path: str):
        """Combine images and audio into video using MoviePy."""
        try:
            from moviepy import ImageClip, concatenate_videoclips, AudioFileClip
            
            clips = []
            for scene in scenes_data:
                img_path = scene['image_path']
                duration = scene['duration']
                clip = ImageClip(img_path).with_duration(duration)
                clips.append(clip)
            
            final_video = concatenate_videoclips(clips, method="compose")
            
            if os.path.exists(audio_path):
                audio = AudioFileClip(audio_path)
                final_video = final_video.with_audio(audio)
            
            final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
            return True
        except Exception as e:
            print(f"  ❌ Rendering failed: {e}")
            return False

    def generate_video_background_task(self, topic: str, user_id: str, session_id: str = None):
        """Main entry point for background task."""
        video_id = str(int(time.time()))
        temp_dir = os.path.join(PUBLIC_VIDEOS_DIR, f"temp_{video_id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        final_filename = f"video_{video_id}.mp4"
        final_video_path = os.path.join(PUBLIC_VIDEOS_DIR, final_filename)
        # Use absolute URL as requested by user for reliability
        # Use Render URL if available, else localhost
        render_url = os.getenv('RENDER_EXTERNAL_URL')
        if render_url:
            public_url = f"{render_url}/videos/{final_filename}"
        else:
            public_url = f"http://localhost:5000/videos/{final_filename}" 
        
        full_audio_path = os.path.join(temp_dir, "full_audio.mp3")
        
        print(f"🎬 Starting Video Generation Job: {topic} (ID: {video_id}, Session: {session_id})")
        
        try:
             # 1. Update Firestore: Processing
            video_data = {
                'title': topic,
                'status': 'generating',
                'createdAt': datetime.now().isoformat(),
                'type': 'video_mp4',
                'sessionId': session_id
            }
            
            # Determine collection
            if session_id:
                print(f"DEBUG: Writing to users/{user_id}/sessions/{session_id}/videos", flush=True)
                col_ref = self.db.collection('users').document(user_id).collection('sessions').document(session_id).collection('videos')
            else:
                print(f"DEBUG: Writing to users/{user_id}/videos", flush=True)
                col_ref = self.db.collection('users').document(user_id).collection('videos')
                
            doc_ref = col_ref.add(video_data)[1]
            print(f"DEBUG: Created doc {doc_ref.id} in Firestore", flush=True)
            
            # 2. Generate Script
            try:
                scenes = self.generate_script(topic)
            except Exception as e:
                print(f"❌ Script generation CRASHED: {e}", flush=True)
                raise e
            
            # 3. Generate Assets Sequentially
            combined_audio = b""
            processed_scenes = []
            
            for i, scene in enumerate(scenes):
                print(f"  Processing Scene {i+1}/{len(scenes)}...")
                
                # Image Generation Loop (Smart Fallback)
                img_path = os.path.join(temp_dir, f"scene_{i}.png")
                
                # 1. Try Infip AI (Primary)
                success = self._generate_image_infip(scene['image_prompt'], img_path)
                
                # 2. Try Pollinations Fallback (Flux -> Turbo)
                if not success:
                    success = self._generate_image_pollinations(scene['image_prompt'], img_path)
                
                # 3. Try Stability AI Fallback
                if not success:
                    success = self._generate_image_stability(scene['image_prompt'], img_path)
                
                # 3. Create Placeholder as last resort
                if not success:
                    self._create_placeholder_image(scene.get('title', topic), img_path)
                
                self._add_text_overlay(img_path, scene.get('overlay_text', ''), scene.get('overlay_position', 'top'))
                
                # Audio
                scene_audio_path = os.path.join(temp_dir, f"audio_{i}.mp3")
                asyncio.run(self._generate_audio(scene['narration'], scene_audio_path))
                
                # Read audio bytes for combining
                with open(scene_audio_path, 'rb') as f:
                    combined_audio += f.read()
                
                # Get duration
                from mutagen.mp3 import MP3
                try:
                    duration = MP3(scene_audio_path).info.length
                except:
                    duration = 3.0
                
                processed_scenes.append({
                    'image_path': img_path,
                    'duration': duration
                })
            
            # Save full audio (simplified concatenation)
            with open(full_audio_path, 'wb') as f:
                f.write(combined_audio)
                
            # 4. Render Video
            print("  🎥 Rendering final video...")
            self.combine_video(processed_scenes, full_audio_path, final_video_path)
            
            # 5. Upload to Firebase Storage for persistent URL
            print("  ☁️ Uploading to Firebase Storage...")
            try:
                bucket = storage.bucket()
                blob = bucket.blob(f"videos/{user_id}/{final_filename}")
                blob.upload_from_filename(final_video_path, content_type='video/mp4')
                blob.make_public()
                public_url = blob.public_url
                print(f"  ✅ Uploaded to Firebase Storage: {public_url}")
            except Exception as upload_err:
                print(f"  ⚠️ Firebase upload failed, using local URL: {upload_err}")
                # Fallback to Render URL if upload fails
                render_url = os.getenv('RENDER_EXTERNAL_URL')
                if render_url:
                    public_url = f"{render_url}/videos/{final_filename}"
                else:
                    public_url = f"http://localhost:5000/videos/{final_filename}"
            
            # 6. Cleanup Temp
            import shutil
            shutil.rmtree(temp_dir)
            # Also remove local video file since it's now in Firebase
            if os.path.exists(final_video_path):
                os.remove(final_video_path)
            
            # 7. Update Firestore: Complete
            if doc_ref:
                doc_ref.update({
                    'status': 'completed',
                    'videoUrl': public_url, # Firebase Storage URL
                    'steps': scenes, # Save the script/steps for UI
                    'duration': sum(s['duration'] for s in processed_scenes),
                    'completedAt': datetime.now().isoformat()
                })
                print(f"✅ Video pipeline complete! URL: {public_url}")
                print(f"   Generated {len(processed_scenes)} scenes, Total Duration: {sum(s['duration'] for s in processed_scenes):.2f}s")
            else:
                 print("⚠️ Could not find firestore doc to update.")

        except Exception as e:
            print(f"❌ Video Generation Job Failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Attempt to update status to failed
            if 'doc_ref' in locals() and doc_ref:
                 doc_ref.update({'status': 'failed', 'error': str(e)})

    def assemble_video_from_urls(self, scenes: List[Dict], image_urls: List[str], 
                                  user_id: str, session_id: str = None):
        """
        Assemble a video from pre-generated image URLs (from frontend Puter generation).
        This allows the frontend to use Puter's free AI and backend just stitches images.
        
        Args:
            scenes: List of scene dicts with 'narration' key
            image_urls: List of Firebase Storage URLs for each scene
            user_id: User ID
            session_id: Optional session ID
        """
        video_id = str(int(time.time()))
        temp_dir = os.path.join(PUBLIC_VIDEOS_DIR, f"temp_{video_id}")
        os.makedirs(temp_dir, exist_ok=True)
        
        final_filename = f"video_{video_id}.mp4"
        final_video_path = os.path.join(PUBLIC_VIDEOS_DIR, final_filename)
        render_url = os.getenv('RENDER_EXTERNAL_URL')
        if render_url:
            public_url = f"{render_url}/videos/{final_filename}"
        else:
            public_url = f"http://localhost:5000/videos/{final_filename}"
        full_audio_path = os.path.join(temp_dir, "full_audio.mp3")
        
        print(f"🎬 Starting Video Assembly Job (ID: {video_id}, Session: {session_id})")
        print(f"   Using {len(image_urls)} pre-generated images from frontend")
        
        try:
            # Create Firestore document
            doc_ref = None
            if session_id:
                col_ref = self.db.collection('users').document(user_id).collection('sessions').document(session_id).collection('videos')
            else:
                col_ref = self.db.collection('users').document(user_id).collection('videos')
            
            doc_ref = col_ref.document(str(video_id))
            doc_ref.set({
                'status': 'assembling',
                'topic': scenes[0].get('title', 'Video') if scenes else 'Video',
                'createdAt': datetime.now().isoformat(),
                'sceneCount': len(scenes)
            })
            
            processed_scenes = []
            combined_audio = b''
            
            for i, scene in enumerate(scenes):
                print(f"  Processing Scene {i+1}/{len(scenes)}...")
                
                # Download image from URL
                img_path = os.path.join(temp_dir, f"scene_{i}.png")
                if i < len(image_urls) and image_urls[i]:
                    try:
                        response = requests.get(image_urls[i], timeout=30)
                        if response.status_code == 200:
                            img = Image.open(BytesIO(response.content))
                            img = img.resize((1280, 720), Image.Resampling.LANCZOS)
                            img.save(img_path, quality=95)
                            print(f"    ✓ Downloaded image from Firebase")
                        else:
                            self._create_placeholder_image(img_path, scene.get('title', f'Scene {i+1}'))
                    except Exception as e:
                        print(f"    ⚠ Failed to download: {e}, using placeholder")
                        self._create_placeholder_image(img_path, scene.get('title', f'Scene {i+1}'))
                else:
                    self._create_placeholder_image(img_path, scene.get('title', f'Scene {i+1}'))
                
                # Generate audio
                narration = scene.get('narration', '')
                audio_path = os.path.join(temp_dir, f"scene_{i}.mp3")
                duration = asyncio.run(self._generate_audio(narration, audio_path))
                
                # Append audio
                if os.path.exists(audio_path):
                    with open(audio_path, 'rb') as f:
                        combined_audio += f.read()
                
                processed_scenes.append({
                    'image_path': img_path,
                    'duration': duration
                })
            
            # Save combined audio
            with open(full_audio_path, 'wb') as f:
                f.write(combined_audio)
            
            # Render video
            print("  🎥 Rendering final video...")
            self.combine_video(processed_scenes, full_audio_path, final_video_path)
            
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)
            
            # Update Firestore
            if doc_ref:
                doc_ref.update({
                    'status': 'completed',
                    'videoUrl': public_url,
                    'steps': scenes,
                    'duration': sum(s['duration'] for s in processed_scenes),
                    'completedAt': datetime.now().isoformat()
                })
                print(f"✅ Video assembly complete! URL: {public_url}")
            
            return {'success': True, 'videoUrl': public_url, 'videoId': video_id}
            
        except Exception as e:
            print(f"❌ Video Assembly Failed: {e}")
            import traceback
            traceback.print_exc()
            if 'doc_ref' in locals() and doc_ref:
                doc_ref.update({'status': 'failed', 'error': str(e)})
            return {'success': False, 'error': str(e)}

