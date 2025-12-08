#!/usr/bin/env python3
"""
Generate an educational animation video from an explanation.
- Uses Gemini Flash API for scene generation (requires GEMINI_API_KEY).
- Generates images for each scene using Stable Diffusion (diffusers library).
- Adds motion to images and creates a video using MoviePy.
- Optimized for CPU and MPS (Metal Performance Shaders) on macOS.
"""

import os
import sys
import json
import requests
import torch
import torch.multiprocessing as mp
from typing import List, Dict

# --- Configuration ---
mp.set_start_method("spawn", force=True)  # Fix for macOS multiprocessing
torch.set_num_threads(1)  # Limit PyTorch threads
USE_GEMINI = bool(os.environ.get("GEMINI_API_KEY"))
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")
SD_MODEL = "runwayml/stable-diffusion-v1-5"  # Stable Diffusion model
DEVICE = "cpu"  # Use MPS if available, otherwise CPU
HF_TOKEN = os.environ.get("HF_TOKEN")  # Optional Hugging Face token for API fallback

def request_gemini_storyboard(explanation: str) -> List[Dict]:
    """
    Use Gemini Flash API to generate a storyboard with scenes.
    """
    if not GEMINI_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Please export it as an environment variable.")
    
    instruction = f"""
    You are a helpful assistant. Convert the following explanation into 3 simple scenes for an educational animation.
    Each scene should include:
      - title: A short title for the scene.
      - description: A one-sentence description of what visually happens.
      - prompt: A very short, explicit Stable Diffusion prompt to generate an illustration for the scene.
      - duration_sec: Suggested duration for the scene in seconds.
    Explanation:
    \"\"\"{explanation}\"\"\"
    Return the result as a JSON array of 3 objects.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    headers = {"Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": instruction}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1024,
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        # Debug the raw response
        print("Raw API Response:")
        print(json.dumps(data, indent=2))
        
        if "candidates" in data and len(data["candidates"]) > 0:
            # Extract the text content
            text_out = data["candidates"][0]["content"]["parts"][0]["text"]
            
            # Extract JSON from the code block
            if text_out.startswith("```") and text_out.endswith("```"):
                text_out = text_out.strip("```").strip("json").strip()
            
            # Parse the JSON array
            return json.loads(text_out)
        else:
            print("No candidates returned from Gemini API.")
            sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"HTTPError: {e}")
        print("Check your GEMINI_API_KEY and ensure it is valid.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Failed to parse the response from Gemini API: {e}")
        sys.exit(1)

def generate_images_local_diffusers(scenes: List[Dict], out_dir="frames") -> List[str]:
    """
    Generate images locally using Stable Diffusion.
    """
    from diffusers import StableDiffusionPipeline

    os.makedirs(out_dir, exist_ok=True)
    print("Initializing Stable Diffusion pipeline...")
    pipe = StableDiffusionPipeline.from_pretrained(SD_MODEL, torch_dtype=torch.float32)
    pipe = pipe.to(DEVICE)
    print("Pipeline initialized successfully.")

    image_paths = []
    for i, scene in enumerate(scenes):
        prompt = scene["prompt"]
        print(f"Generating image for scene {i+1}: {prompt[:120]}...")
        try:
            image = pipe(prompt, guidance_scale=7.5, num_inference_steps=20).images[0]
            filename = os.path.join(out_dir, f"scene_{i+1:02d}.png")
            image.save(filename)
            image_paths.append(filename)
        except Exception as e:
            print(f"Error generating image for scene {i+1}: {e}")
            sys.exit(1)
    return image_paths

def create_video_from_images(image_paths: List[str], scenes: List[Dict], out_file="final_video.mp4"):
    """
    Create a video from images with motion effects using MoviePy.
    """
    from moviepy.editor import ImageClip, concatenate_videoclips
    clips = []
    for img_path, scene in zip(image_paths, scenes):
        duration = max(3, min(10, int(scene.get("duration_sec", 5))))
        clip = ImageClip(img_path).set_duration(duration).resize(lambda t: 1.0 + 0.02 * t)
        clips.append(clip)
    final_video = concatenate_videoclips(clips, method="compose")
    final_video.write_videofile(out_file, fps=24, codec="libx264", audio=False)
    print(f"Video saved as {out_file}")

def main():
    print("Enter an explanation (or press Enter for default):")
    explanation = input().strip() or (
        "Photosynthesis is the process by which green plants use sunlight to make food. "
        "They take in carbon dioxide and water; inside the leaf's chloroplasts, light energy "
        "converts them into glucose and oxygen."
    )
    print("Generating storyboard...")
    if USE_GEMINI:
        scenes = request_gemini_storyboard(explanation)
    else:
        print("GEMINI_API_KEY not found. Exiting.")
        return

    print("Generating images...")
    image_paths = generate_images_local_diffusers(scenes)

    print("Creating video...")
    create_video_from_images(image_paths, scenes)

if __name__ == "__main__":
    main()