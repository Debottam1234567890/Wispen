import os
import requests
import io
import base64
from typing import Optional
from PIL import Image

class StableDiffusionGenerator:
    """
    Handles image generation using Stability AI API (prioritized) or Hugging Face.
    """
    
    def __init__(self, api_key: str = None):
        # Prioritize Stability AI Key
        self.stability_key = os.environ.get("STABILITY_API_KEY")
        self.hf_key = api_key or os.environ.get("STABLE_DIFFUSION_API_KEY")
        
        # Stability AI Endpoint (SDXL 1.0)
        self.stability_engine_id = "stable-diffusion-xl-1024-v1-0"
        self.stability_api_host = "https://api.stability.ai"

    def generate_image(self, prompt: str, output_path: str) -> Optional[str]:
        """
        Generate high quality image. 
        Tries Stability AI (SDXL) first, then Pollinations (Flux).
        """
        # 1. Try Stability AI (Premium/High-res)
        if self.stability_key:
            res = self._generate_with_stability(prompt, output_path)
            if res: return res

        # 2. Try Pollinations (Flux - reliable, free, good at following prompts)
        print("⚠ Stability failed or key missing, falling back to Pollinations (Flux)...")
        return self._generate_with_pollinations(prompt, output_path)

    def _generate_with_pollinations(self, prompt: str, output_path: str) -> Optional[str]:
        """Fallback generator using Pollinations API (Flux)."""
        import urllib.parse
        from io import BytesIO
        try:
            # Flux is great at complex prompts and handles "no text" well
            enhanced_prompt = f"{prompt}, high quality scientific illustration, detailed 4k"
            encoded_prompt = urllib.parse.quote(enhanced_prompt)
            url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={int(os.getpid())}"
            
            response = requests.get(url, timeout=60)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                image.save(output_path)
                print(f"✓ Saved Pollinations (Flux) image to {output_path}")
                return os.path.basename(output_path)
        except Exception as e:
            print(f"❌ Pollinations Fallback failed: {e}")
        return None

    def _generate_with_stability(self, prompt: str, output_path: str) -> Optional[str]:
        print(f"🎨 Generating with Stability AI (SDXL): {prompt[:50]}...")
        
        enhanced_prompt = f"{prompt}, cartoonic educational style, detailed, clear lines, vibrant colors, 4k, high quality, illustration"
        
        url = f"{self.stability_api_host}/v1/generation/{self.stability_engine_id}/text-to-image"
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.stability_key}"
        }
        
        payload = {
            "text_prompts": [
                {"text": enhanced_prompt, "weight": 1}
            ],
            "cfg_scale": 7,
            "height": 1024,
            "width": 1024,
            "samples": 1,
            "steps": 20, # User requested 20 steps
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                error_detail = "Unknown error"
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text
                print(f"❌ Stability API Error {response.status_code}: {error_detail}")
                return None

            data = response.json()
            
            # Stability returns base64 string
            for i, image_data in enumerate(data["artifacts"]):
                if image_data["finishReason"] == "CONTENT_FILTERED":
                    print("⚠ Generation blocked by content filter.")
                    return None
                    
                b64_str = image_data["base64"]
                image_bytes = base64.b64decode(b64_str)
                image = Image.open(io.BytesIO(image_bytes))
                
                # Resize if needed (optional, keeping 1024 for quality then resizing for web if app expects smaller?)
                # App likely expects 16:9, SDXL is native 1024x1024 typically square or 1152x896.
                # Let's resize/crop to 16:9 800x450 to match app's expectation or keep high res.
                # For now, saving as is. 
                
                # Ensure directory exists
                directory = os.path.dirname(output_path)
                if directory:
                    os.makedirs(directory, exist_ok=True)
                
                image.save(output_path)
                print(f"✓ Saved Stability image to {output_path}")
                return os.path.basename(output_path)
                
        except Exception as e:
            print(f"❌ Stability Generation Exception: {e}")
            return None
        
        return None
