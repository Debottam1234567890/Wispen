import os
import json
from typing import List, Dict
import requests
from PIL import Image
import io
import time

# Import the external API key manager
from api_key_manager import APIKeyManager, call_gemini_with_retry

class SlideshowGenerator:
    """
    Backend system for generating AI-narrated slideshows with consistent visuals.
    Uses:
    - Gemini 2.0 Flash REST API for content generation (with key rotation)
    - Stable Diffusion (Hugging Face) for image generation
    - Murf.ai API for text-to-speech
    """
    
    def __init__(self, hf_api_key: str = None, murf_api_key: str = None):
        """
        Initialize the slideshow generator.
        
        Args:
            hf_api_key: Hugging Face API key (or set STABLE_DIFFUSION_API_KEY env var)
            murf_api_key: Murf.ai API key (or set MURF_API_KEY env var)
        """
        # Initialize API Key Manager for Gemini (reads GEMINI_API_KEY1, GEMINI_API_KEY2)
        self.api_key_manager = APIKeyManager(["GEMINI_API_KEY1", "GEMINI_API_KEY2"])
        
        self.hf_api_key = hf_api_key or os.environ.get("STABLE_DIFFUSION_API_KEY")
        self.murf_api_key = murf_api_key or os.environ.get("MURF_API_KEY")
        
        self.gemini_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.gemini_model = "gemini-2.0-flash-exp"
        self.visual_style = None
        self.base_visual_prompt = None
        
        print(f"✓ Initialized with {len(self.api_key_manager.get_key_list())} Gemini API keys")
        
    def _call_gemini(self, prompt: str, temperature: float = 0.7) -> str:
        """
        Call Gemini API with automatic retry using the API key manager.
        
        Args:
            prompt: The prompt to send
            temperature: Sampling temperature
            
        Returns:
            Generated text response
        """
        def api_call(api_key: str) -> str:
            """Inner function that performs the actual API call"""
            url = f"{self.gemini_url}/{self.gemini_model}:generateContent?key={api_key}"
            
            headers = {"Content-Type": "application/json"}
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 8192,
                }
            }
            
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
        
        # Use the external retry function with API key rotation
        return call_gemini_with_retry(
            api_call_func=api_call,
            api_key_manager=self.api_key_manager,
            verbose=True,
            max_retries=2
        )
        
    def generate_presentation(self, topic: str, num_slides: int = 5) -> Dict:
        """
        Generate complete presentation with narration and visual descriptions.
        
        Args:
            topic: The topic to create a presentation about
            num_slides: Number of slides to generate
            
        Returns:
            Dictionary containing slides with content, narration, and visual specs
        """
        print(f"Generating {num_slides}-slide presentation on: {topic}")
        
        # First, establish visual style and base prompt for consistency
        style_prompt = f"""For a presentation about {topic}, define:
1. Visual art style (e.g., "digital illustration", "minimalist vector art", "photorealistic", "isometric diagram")
2. Color palette (3-4 main colors as hex codes)
3. Common visual theme/elements that should appear in every slide
4. Base prompt template for Stable Diffusion

Return ONLY valid JSON:
{{
  "style": "art style description",
  "colors": ["#RRGGBB", "#RRGGBB", "#RRGGBB"],
  "common_theme": "theme that connects all visuals",
  "base_prompt": "base Stable Diffusion prompt with style keywords"
}}"""

        print("Step 1: Establishing visual style...")
        style_text = self._call_gemini(style_prompt, temperature=0.5)
        
        style_text = self._extract_json(style_text)
        style_json = json.loads(style_text)
        self.visual_style = style_json
        self.base_visual_prompt = style_json['base_prompt']
        
        print(f"✓ Visual style: {style_json['style']}")
        print(f"✓ Theme: {style_json['common_theme']}")
        print(f"✓ Base prompt: {self.base_visual_prompt}")
        
        # Generate slide content with consistent visuals
        content_prompt = f"""Create a {num_slides}-slide educational presentation about: {topic}

VISUAL CONSISTENCY REQUIREMENTS:
- Art Style: {style_json['style']}
- Color Palette: {', '.join(style_json['colors'])}
- Common Theme: {style_json['common_theme']}
- Base Visual Prompt: {self.base_visual_prompt}

For each slide, provide:
1. Title (max 8 words)
2. Key points (3-4 bullets, max 15 words each)
3. Narration (conversational, 3-4 sentences)
4. Specific image prompt (extends base prompt with slide-specific details)
5. How this visual connects to previous/next slide

CRITICAL: Each slide's image_prompt must:
- Start with the base prompt
- Add specific elements for THIS slide
- Maintain the same style/theme
- Show clear progression from previous slides

Return ONLY valid JSON:
{{
  "presentation_title": "{topic}",
  "slides": [
    {{
      "slide_number": 1,
      "title": "Slide Title",
      "points": ["Point 1", "Point 2", "Point 3"],
      "narration": "Natural narration text.",
      "image_prompt": "{self.base_visual_prompt}, [specific elements for this slide]",
      "visual_connection": "How this connects to other slides"
    }}
  ]
}}"""

        print("Step 2: Generating slide content...")
        content_text = self._call_gemini(content_prompt, temperature=0.7)
        
        content_text = self._extract_json(content_text)
        presentation_data = json.loads(content_text)
        presentation_data['visual_style'] = self.visual_style
        
        print(f"✓ Generated {len(presentation_data['slides'])} slides successfully")
        return presentation_data
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from markdown code blocks or plain text."""
        text = text.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start != -1 and end != 0:
            text = text[start:end]
            
        return text
    
    def generate_slide_image(self, slide_data: Dict, output_path: str = None) -> Image.Image:
        """
        Generate an image using Hugging Face Stable Diffusion API.
        
        Args:
            slide_data: Dictionary containing slide information with image_prompt
            output_path: Optional path to save the image
            
        Returns:
            PIL Image object
        """
        if not self.hf_api_key:
            print("⚠ No Hugging Face API key provided, skipping image generation")
            return None
            
        print(f"Generating image for slide {slide_data['slide_number']}: {slide_data['title']}")
        
        # Use Hugging Face Inference API - try multiple active Stable Diffusion models
        models = [
            "runwayml/stable-diffusion-v1-5",
            "stabilityai/stable-diffusion-2-1",
            "CompVis/stable-diffusion-v1-4"
        ]
        
        # Enhance prompt with quality boosters
        enhanced_prompt = f"{slide_data['image_prompt']}, high quality, detailed, professional, clear, educational, 4k"
        
        headers = {
            "Authorization": f"Bearer {self.hf_api_key}"
        }
        
        # Try each model until one works
        for model in models:
            try:
                url = f"https://api-inference.huggingface.co/models/{model}"
                
                payload = {
                    "inputs": enhanced_prompt,
                    "options": {"wait_for_model": True}
                }
                
                response = requests.post(url, headers=headers, json=payload)
                
                # Handle model loading delay
                if response.status_code == 503:
                    print(f"  Model {model} is loading, waiting 20 seconds...")
                    time.sleep(20)
                    response = requests.post(url, headers=headers, json=payload)
                
                response.raise_for_status()
                
                # Response is the image bytes directly
                img = Image.open(io.BytesIO(response.content))
                
                if output_path:
                    img.save(output_path)
                    print(f"✓ Saved image to: {output_path} (using {model})")
                
                return img
                
            except Exception as e:
                print(f"  ⚠ {model} failed: {str(e)[:50]}, trying next model...")
                continue
        
        print(f"⚠ All image generation models failed")
        print(f"  Prompt was: {enhanced_prompt[:100]}...")
        return None
    
    def generate_audio_narration(self, narration_text: str, output_path: str, voice: str = "en-US-matthew"):
        """
        Generate audio narration using Murf.ai API.
        
        Args:
            narration_text: The narration text to convert to speech
            output_path: Path to save the audio file (.mp3)
            voice: Voice ID to use
        """
        if not self.murf_api_key:
            print("⚠ No Murf API key provided, skipping audio generation")
            return
            
        print(f"Generating audio: {narration_text[:50]}...")
        
        url = "https://api.murf.ai/v1/speech/generate"
        
        headers = {
            "api-key": self.murf_api_key,
            "Content-Type": "application/json"
        }
        
        # Map simple voice names to Murf voice IDs
        voice_map = {
            "matthew": "en-US-matthew",
            "natalie": "en-US-natalie",
            "wayne": "en-US-wayne",
            "marcus": "en-US-marcus"
        }
        
        voice_id = voice_map.get(voice.lower(), "en-US-matthew")
        
        payload = {
            "voiceId": voice_id,
            "style": "Conversational",
            "text": narration_text,
            "rate": 0,
            "pitch": 0,
            "sampleRate": 48000,
            "format": "MP3",
            "channelType": "STEREO",
            "pronunciationDictionary": {},
            "encodeAsBase64": False
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Download the audio file from the URL provided
            if 'audioFile' in result:
                audio_url = result['audioFile']
                audio_response = requests.get(audio_url)
                audio_response.raise_for_status()
                
                with open(output_path, 'wb') as f:
                    f.write(audio_response.content)
                
                print(f"✓ Saved audio to: {output_path}")
            else:
                print(f"⚠ No audio file in response")
                
        except Exception as e:
            print(f"⚠ Audio generation failed: {e}")
            print("  Note: Check Murf API key and quota")
    
    def export_presentation(self, presentation_data: Dict, output_dir: str = "presentation_output", 
                          generate_images: bool = True, generate_audio: bool = True):
        """
        Export complete presentation with images and audio files.
        
        Args:
            presentation_data: Full presentation data dictionary
            output_dir: Directory to save all output files
            generate_images: Whether to generate images with Stable Diffusion
            generate_audio: Whether to generate audio with Murf.ai
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Save presentation metadata
        metadata_path = os.path.join(output_dir, "presentation_metadata.json")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(presentation_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved metadata to: {metadata_path}")
        
        # Generate images and audio for each slide
        for slide in presentation_data['slides']:
            slide_num = slide['slide_number']
            
            # Generate and save image
            if generate_images:
                img_path = os.path.join(output_dir, f"slide_{slide_num:02d}.png")
                self.generate_slide_image(slide, img_path)
                time.sleep(1)  # Rate limiting for Stability AI
            
            # Generate audio narration
            if generate_audio:
                audio_path = os.path.join(output_dir, f"narration_{slide_num:02d}.mp3")
                self.generate_audio_narration(slide['narration'], audio_path)
                time.sleep(0.5)  # Rate limiting
        
        print(f"\n✓ Presentation exported to: {output_dir}")
        print(f"  - {len(presentation_data['slides'])} slides")
        if generate_images:
            print(f"  - {len(presentation_data['slides'])} images (Stable Diffusion)")
        if generate_audio:
            print(f"  - {len(presentation_data['slides'])} audio files (Murf.ai)")
        
        # Create a simple HTML viewer
        self._create_html_viewer(presentation_data, output_dir)
    
    def _create_html_viewer(self, presentation_data: Dict, output_dir: str):
        """Create a simple HTML file to view the presentation."""
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>{presentation_data['presentation_title']}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .slide {{
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin: 20px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .slide h2 {{
            color: #333;
            border-bottom: 3px solid {presentation_data['visual_style']['colors'][0]};
            padding-bottom: 10px;
        }}
        .slide img {{
            width: 100%;
            max-width: 800px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .points {{
            list-style-type: none;
            padding: 0;
        }}
        .points li {{
            padding: 10px;
            margin: 10px 0;
            background: #f5f5f5;
            border-left: 4px solid {presentation_data['visual_style']['colors'][0]};
            border-radius: 4px;
        }}
        .narration {{
            background: #e8f4f8;
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
        }}
        audio {{
            width: 100%;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <h1 style="color: white; text-align: center;">{presentation_data['presentation_title']}</h1>
    <p style="color: white; text-align: center;">Visual Style: {presentation_data['visual_style']['style']}</p>
"""
        
        for slide in presentation_data['slides']:
            slide_num = slide['slide_number']
            html_content += f"""
    <div class="slide">
        <h2>Slide {slide_num}: {slide['title']}</h2>
        <img src="slide_{slide_num:02d}.png" alt="Slide {slide_num}" onerror="this.style.display='none'">
        <ul class="points">
"""
            for point in slide['points']:
                html_content += f"            <li>{point}</li>\n"
            
            html_content += f"""        </ul>
        <div class="narration">
            <strong>Narration:</strong><br>
            {slide['narration']}
        </div>
        <audio controls>
            <source src="narration_{slide_num:02d}.mp3" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
    </div>
"""
        
        html_content += """
</body>
</html>"""
        
        html_path = os.path.join(output_dir, "presentation.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"✓ Created HTML viewer: {html_path}")


# Example usage
if __name__ == "__main__":
    # Initialize generator with API keys
    generator = SlideshowGenerator(
        hf_api_key=os.environ.get("STABLE_DIFFUSION_API_KEY"),
        murf_api_key=os.environ.get("MURF_API_KEY")
    )
    
    # Generate presentation
    topic = "Photosynthesis"
    presentation = generator.generate_presentation(topic, num_slides=5)
    
    # Export everything
    generator.export_presentation(
        presentation, 
        output_dir=f"output_{topic.lower()}",
        generate_images=True,  # Set to False if no Hugging Face API key
        generate_audio=True    # Set to False if no Murf API key
    )
    
    print("\n" + "="*60)
    print("PRESENTATION SUMMARY")
    print("="*60)
    print(f"Title: {presentation['presentation_title']}")
    print(f"Style: {presentation['visual_style']['style']}")
    print(f"Theme: {presentation['visual_style']['common_theme']}")
    print(f"Colors: {', '.join(presentation['visual_style']['colors'])}")
    print(f"\nSlides:")
    for slide in presentation['slides']:
        print(f"  {slide['slide_number']}. {slide['title']}")
    print(f"\nOpen presentation.html in your browser to view!")