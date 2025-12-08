#!/usr/bin/env python3
"""
Advanced Animated AI Educational Video Generator v5.0
- TRUE ANIMATIONS: Objects, particles, and characters actually MOVE
- Realistic visuals: No diagrams, only photorealistic scenes with action
- Dynamic overlays: Animated elements appear during narration
- Optimized for Kaggle with memory management
- Multi-layered animation system
"""

import os
import sys
import json
import requests
import torch
import gc
import numpy as np
from typing import List, Dict, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import subprocess
from pathlib import Path
import warnings
import time
from dataclasses import dataclass
import cv2
warnings.filterwarnings('ignore')

# =============================================================================
# CONFIGURATION
# =============================================================================

GEMINI_KEY = "AIzaSyAkGR1DE9k06NPVckqCkE5ewNo3W1wByDg"

# Use SD 1.5 for better Kaggle compatibility
SD_MODEL = "runwayml/stable-diffusion-v1-5"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Directories
OUTPUT_DIR = "output"
TEMP_DIR = "temp_generation"
VIDEO_CLIPS_DIR = "video_segments"
AUDIO_DIR = "audio_files"
ASSETS_DIR = "visual_assets"
ANIMATION_DIR = "animations"

# Video settings optimized for Kaggle
VIDEO_FPS = 24  # Reduced for performance
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
ANIMATION_DURATION = 0.8
MAX_PROMPT_LENGTH = 75

# Quality settings
IMAGE_QUALITY = 90
VIDEO_BITRATE = "5M"
AUDIO_BITRATE = "128k"

# =============================================================================
# DATA MODELS
# =============================================================================

@dataclass
class AnimationElement:
    """Represents an animated element in the scene."""
    element_type: str  # 'particle', 'arrow', 'glow', 'text', 'object'
    start_time: float
    end_time: float
    start_pos: Tuple[int, int]
    end_pos: Tuple[int, int]
    color: Tuple[int, int, int]
    size: int
    motion_type: str  # 'linear', 'wave', 'spiral', 'fade', 'grow'
    label: str = ""

@dataclass
class Scene:
    """Represents a single animated scene."""
    scene_number: int
    scene_type: str  # Always 'animated_realistic'
    duration: float
    narration: str
    visual_prompt: str
    key_concepts: List[str]
    camera_motion: str
    transition_type: str
    lighting: str
    mood: str
    animation_elements: List[AnimationElement]
    action_description: str  # What actually moves/happens
    
@dataclass
class VideoMetadata:
    """Metadata for the entire video."""
    title: str
    total_duration: float
    scene_count: int
    educational_level: str
    topic_category: str
    key_learnings: List[str]

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def setup_directories():
    """Create necessary directories."""
    for dir_path in [OUTPUT_DIR, TEMP_DIR, VIDEO_CLIPS_DIR, AUDIO_DIR, ASSETS_DIR, ANIMATION_DIR]:
        os.makedirs(dir_path, exist_ok=True)
        
def clear_memory():
    """Aggressive memory cleanup for Kaggle."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()
        
def print_header(text: str, style: str = "main"):
    """Print styled headers."""
    if style == "main":
        print("\n" + "="*80)
        print(f"  {text}")
        print("="*80 + "\n")
    elif style == "sub":
        print("\n" + "-"*80)
        print(f"  {text}")
        print("-"*80 + "\n")
    elif style == "phase":
        print("\n" + "█"*80)
        print(f"  {text}")
        print("█"*80 + "\n")

# =============================================================================
# ANIMATION GENERATOR
# =============================================================================

class AnimationGenerator:
    """
    Creates TRUE animations with moving elements.
    No static diagrams - everything has realistic motion.
    """
    
    def __init__(self):
        self.fps = VIDEO_FPS
        
    def create_particle_animation(self, width: int, height: int, duration: float,
                                   particle_type: str, direction: str) -> List[np.ndarray]:
        """
        Create particle animations (water drops, energy, light, etc.)
        """
        frames = []
        total_frames = int(duration * self.fps)
        
        # Particle settings based on type
        particle_configs = {
            'water': {'count': 50, 'size': (3, 8), 'color': (100, 180, 255), 'gravity': True},
            'energy': {'count': 30, 'size': (4, 10), 'color': (255, 255, 100), 'gravity': False},
            'light': {'count': 40, 'size': (2, 6), 'color': (255, 240, 200), 'gravity': False},
            'co2': {'count': 35, 'size': (3, 7), 'color': (150, 150, 150), 'gravity': False},
            'oxygen': {'count': 35, 'size': (3, 7), 'color': (150, 255, 150), 'gravity': False}
        }
        
        config = particle_configs.get(particle_type, particle_configs['water'])
        
        # Initialize particles
        particles = []
        for _ in range(config['count']):
            if direction == 'down':
                x, y = np.random.randint(0, width), 0
                vx, vy = np.random.uniform(-1, 1), np.random.uniform(2, 5)
            elif direction == 'up':
                x, y = np.random.randint(0, width), height
                vx, vy = np.random.uniform(-1, 1), np.random.uniform(-5, -2)
            elif direction == 'right':
                x, y = 0, np.random.randint(0, height)
                vx, vy = np.random.uniform(2, 5), np.random.uniform(-1, 1)
            elif direction == 'left':
                x, y = width, np.random.randint(0, height)
                vx, vy = np.random.uniform(-5, -2), np.random.uniform(-1, 1)
            else:  # random
                x = np.random.randint(0, width)
                y = np.random.randint(0, height)
                angle = np.random.uniform(0, 2*np.pi)
                speed = np.random.uniform(2, 4)
                vx, vy = speed * np.cos(angle), speed * np.sin(angle)
                
            size = np.random.randint(config['size'][0], config['size'][1])
            particles.append({
                'x': float(x), 'y': float(y),
                'vx': float(vx), 'vy': float(vy),
                'size': size,
                'life': np.random.randint(total_frames // 2, total_frames),
                'age': 0
            })
        
        # Generate frames
        for frame_num in range(total_frames):
            # Create transparent frame
            frame = np.zeros((height, width, 4), dtype=np.uint8)
            
            for particle in particles:
                if particle['age'] < particle['life']:
                    # Update position
                    particle['x'] += particle['vx']
                    particle['y'] += particle['vy']
                    
                    # Apply gravity if needed
                    if config['gravity']:
                        particle['vy'] += 0.2
                    
                    # Wrap around or respawn
                    if particle['x'] < 0 or particle['x'] >= width or \
                       particle['y'] < 0 or particle['y'] >= height:
                        if direction == 'down':
                            particle['x'] = float(np.random.randint(0, width))
                            particle['y'] = 0
                        elif direction == 'up':
                            particle['x'] = float(np.random.randint(0, width))
                            particle['y'] = float(height)
                        else:
                            particle['x'] = float(np.random.randint(0, width))
                            particle['y'] = float(np.random.randint(0, height))
                    
                    # Calculate alpha based on life
                    alpha = int(255 * (1 - particle['age'] / particle['life']))
                    
                    # Draw particle with glow
                    x, y = int(particle['x']), int(particle['y'])
                    if 0 <= x < width and 0 <= y < height:
                        # Main particle
                        cv2.circle(frame, (x, y), particle['size'], 
                                  (*config['color'], alpha), -1)
                        # Glow effect
                        cv2.circle(frame, (x, y), particle['size'] + 3, 
                                  (*config['color'], alpha // 2), 1)
                    
                    particle['age'] += 1
            
            frames.append(frame)
        
        return frames
    
    def create_growing_animation(self, width: int, height: int, duration: float,
                                 object_type: str) -> List[np.ndarray]:
        """
        Create growing/transforming animations (plants growing, cells dividing, etc.)
        """
        frames = []
        total_frames = int(duration * self.fps)
        
        for frame_num in range(total_frames):
            frame = np.zeros((height, width, 4), dtype=np.uint8)
            progress = frame_num / total_frames
            
            if object_type == 'plant':
                # Draw growing plant
                stem_height = int(height * 0.6 * progress)
                stem_x = width // 2
                
                # Stem
                cv2.line(frame, (stem_x, height), (stem_x, height - stem_height),
                        (50, 200, 50, 255), 8)
                
                # Leaves (appear progressively)
                if progress > 0.3:
                    leaf_size = int(40 * (progress - 0.3) / 0.7)
                    # Left leaf
                    cv2.ellipse(frame, (stem_x - 30, height - stem_height + 50),
                               (leaf_size, leaf_size // 2), 45, 0, 360,
                               (100, 255, 100, 255), -1)
                    # Right leaf
                    cv2.ellipse(frame, (stem_x + 30, height - stem_height + 50),
                               (leaf_size, leaf_size // 2), 135, 0, 360,
                               (100, 255, 100, 255), -1)
                
                # Flower (appears at end)
                if progress > 0.7:
                    flower_size = int(30 * (progress - 0.7) / 0.3)
                    cv2.circle(frame, (stem_x, height - stem_height),
                             flower_size, (255, 200, 100, 255), -1)
            
            elif object_type == 'cell':
                # Draw growing/dividing cell
                radius = int(100 + 50 * progress)
                center = (width // 2, height // 2)
                
                # Cell membrane
                cv2.circle(frame, center, radius, (150, 200, 255, 200), 5)
                
                # Nucleus
                nucleus_radius = int(radius * 0.3)
                cv2.circle(frame, center, nucleus_radius, (200, 150, 255, 255), -1)
                
                # Organelles (appear and multiply)
                for i in range(int(5 * progress)):
                    angle = i * 2 * np.pi / 5
                    org_x = int(center[0] + radius * 0.5 * np.cos(angle))
                    org_y = int(center[1] + radius * 0.5 * np.sin(angle))
                    cv2.circle(frame, (org_x, org_y), 15, (100, 255, 100, 255), -1)
            
            frames.append(frame)
        
        return frames
    
    def create_flow_animation(self, width: int, height: int, duration: float,
                             flow_type: str, path: str) -> List[np.ndarray]:
        """
        Create flowing animations (blood, water in plants, electricity, etc.)
        """
        frames = []
        total_frames = int(duration * self.fps)
        
        # Define path
        if path == 'vertical':
            path_points = [(width // 2, int(y)) for y in np.linspace(height, 0, 50)]
        elif path == 'horizontal':
            path_points = [(int(x), height // 2) for x in np.linspace(0, width, 50)]
        elif path == 'curved':
            t = np.linspace(0, 2*np.pi, 50)
            path_points = [(int(width // 4 + width // 2 * (1 + 0.5*np.sin(ti))),
                          int(height // 4 + height // 2 * (1 + 0.5*np.cos(ti))))
                         for ti in t]
        else:  # tree/branching
            path_points = [(width // 2, height)]
            for i in range(1, 50):
                y = height - int(i * height / 50)
                x = width // 2 + int(30 * np.sin(i * 0.2))
                path_points.append((x, y))
        
        # Color based on type
        colors = {
            'water': (100, 180, 255),
            'blood': (255, 100, 100),
            'energy': (255, 255, 100),
            'signal': (255, 150, 255)
        }
        color = colors.get(flow_type, (255, 255, 255))
        
        for frame_num in range(total_frames):
            frame = np.zeros((height, width, 4), dtype=np.uint8)
            
            # Draw path faintly
            for i in range(len(path_points) - 1):
                cv2.line(frame, path_points[i], path_points[i+1], (*color, 50), 3)
            
            # Animated particles flowing along path
            num_particles = 15
            for p in range(num_particles):
                phase = (frame_num + p * total_frames // num_particles) % total_frames
                progress = phase / total_frames
                
                point_idx = int(progress * (len(path_points) - 1))
                if point_idx < len(path_points):
                    pos = path_points[point_idx]
                    
                    # Particle with trail
                    cv2.circle(frame, pos, 8, (*color, 255), -1)
                    cv2.circle(frame, pos, 12, (*color, 128), 2)
                    
                    # Trail
                    for trail in range(1, 4):
                        trail_idx = max(0, point_idx - trail * 2)
                        trail_pos = path_points[trail_idx]
                        alpha = int(255 * (1 - trail * 0.25))
                        cv2.circle(frame, trail_pos, 6 - trail, (*color, alpha), -1)
            
            frames.append(frame)
        
        return frames
    
    def create_text_animation(self, width: int, height: int, duration: float,
                            text: str, position: str = 'bottom') -> List[np.ndarray]:
        """
        Create animated text that appears during narration.
        """
        frames = []
        total_frames = int(duration * self.fps)
        
        # Font settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 3
        
        # Get text size
        (text_width, text_height), _ = cv2.getTextSize(text, font, font_scale, thickness)
        
        # Position
        if position == 'bottom':
            text_x = (width - text_width) // 2
            text_y = height - 100
        elif position == 'top':
            text_x = (width - text_width) // 2
            text_y = 100
        else:  # center
            text_x = (width - text_width) // 2
            text_y = height // 2
        
        for frame_num in range(total_frames):
            frame = np.zeros((height, width, 4), dtype=np.uint8)
            
            # Fade in effect
            alpha = min(255, int(255 * frame_num / (total_frames * 0.2)))
            
            # Draw text background
            padding = 20
            cv2.rectangle(frame,
                        (text_x - padding, text_y - text_height - padding),
                        (text_x + text_width + padding, text_y + padding),
                        (0, 0, 0, alpha // 2), -1)
            
            # Draw text with outline
            cv2.putText(frame, text, (text_x, text_y), font, font_scale,
                       (0, 0, 0, alpha), thickness + 2, cv2.LINE_AA)
            cv2.putText(frame, text, (text_x, text_y), font, font_scale,
                       (255, 255, 255, alpha), thickness, cv2.LINE_AA)
            
            frames.append(frame)
        
        return frames
    
    def overlay_animation_on_video(self, base_video: str, animation_frames: List[np.ndarray],
                                   output_path: str):
        """
        Overlay animation frames on base video.
        """
        # Read base video
        cap = cv2.VideoCapture(base_video)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Get animation frame (loop if necessary)
            if frame_idx < len(animation_frames):
                anim_frame = animation_frames[frame_idx]
            else:
                anim_frame = animation_frames[-1]
            
            # Resize animation to match video
            if anim_frame.shape[:2] != (height, width):
                anim_frame = cv2.resize(anim_frame, (width, height))
            
            # Blend animation with video (alpha compositing)
            alpha = anim_frame[:, :, 3] / 255.0
            for c in range(3):
                frame[:, :, c] = (alpha * anim_frame[:, :, c] + 
                                 (1 - alpha) * frame[:, :, c]).astype(np.uint8)
            
            out.write(frame)
            frame_idx += 1
        
        cap.release()
        out.release()

# =============================================================================
# AGENT: DIRECTOR
# =============================================================================

class DirectorAgent:
    """
    AI Director: Plans animated realistic scenes.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        
    def call_gemini(self, prompt: str, temperature: float = 0.7) -> str:
        """Make API call to Gemini."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={self.api_key}"
        
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192,
            }
        }
        
        try:
            response = requests.post(url, json=body, timeout=120)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"⚠ Gemini API error: {e}")
            raise
            
    def create_master_plan(self, topic: str) -> Tuple[VideoMetadata, List[Scene]]:
        """
        Create comprehensive animated video plan.
        """
        
        prompt = f"""You are an expert animator and educational video director. Create an ANIMATED educational video plan about: {topic}

CRITICAL REQUIREMENTS:
1. Generate 8-12 scenes with TRUE REALISTIC ANIMATIONS (no diagrams!)
2. Each scene MUST have:
   - Photorealistic base visual (actual objects, not diagrams)
   - Specific animations described (what moves, how it moves)
   - 6-10 seconds duration
3. Visual prompts must be PHOTOREALISTIC descriptions under 75 words
4. Include specific animation types for each scene
5. Describe ACTUAL MOVEMENT that will happen

ANIMATION TYPES:
- particles: flowing water, energy, light, CO2, oxygen (specify direction: up/down/right/left)
- growing: plants growing, cells dividing, crystals forming
- flowing: water in stems, blood in veins, signals in nerves (specify path: vertical/horizontal/curved/tree)
- text: key concepts appearing during narration

EXCELLENT SCENE EXAMPLES:

Scene 1 (Photosynthesis):
{{
  "visual_prompt": "Extreme close-up of green leaf surface with visible water droplets, morning dew, macro photography, natural sunlight, photorealistic, 8K detail",
  "action_description": "Water droplets flow DOWN into leaf pores, becoming smaller as they enter",
  "animation_elements": [
    {{"type": "particles", "detail": "water droplets flowing down into stomata", "direction": "down", "timing": "0-5s"}},
    {{"type": "text", "detail": "WATER ABSORPTION", "timing": "2-6s", "position": "bottom"}}
  ]
}}

Scene 2 (Photosynthesis):
{{
  "visual_prompt": "Transparent view of plant stem cross-section, realistic botanical microscopy, xylem vessels visible, cellular detail, scientific photography quality",
  "action_description": "Water flows UPWARD through xylem vessels with visible movement",
  "animation_elements": [
    {{"type": "flowing", "detail": "water moving up through xylem", "path": "vertical", "timing": "0-7s"}},
    {{"type": "text", "detail": "XYLEM TRANSPORT", "timing": "2-7s", "position": "bottom"}}
  ]
}}

Scene 3 (Photosynthesis):
{{
  "visual_prompt": "Interior of plant cell with visible chloroplasts, realistic electron microscopy style, green organelles, thylakoid membranes, biological accuracy, high detail",
  "action_description": "Light energy particles stream IN from above, chloroplasts glow as they absorb energy",
  "animation_elements": [
    {{"type": "particles", "detail": "light energy flowing in", "direction": "down", "timing": "0-6s"}},
    {{"type": "particles", "detail": "oxygen being released", "direction": "up", "timing": "3-8s"}},
    {{"type": "text", "detail": "LIGHT REACTIONS", "timing": "2-8s", "position": "bottom"}}
  ]
}}

BAD EXAMPLES:
✗ "diagram of photosynthesis with labels"
✗ "simple illustration showing stages"
✗ Any static image without described movement

Return ONLY valid JSON:
{{
  "metadata": {{
    "title": "Engaging title",
    "educational_level": "intermediate",
    "topic_category": "biology",
    "key_learnings": ["learning1", "learning2", "learning3"]
  }},
  "scenes": [
    {{
      "scene_number": 1,
      "scene_type": "animated_realistic",
      "duration": 8.0,
      "narration": "Clear narration describing what viewer sees AND what's moving",
      "visual_prompt": "Photorealistic description under 75 words",
      "action_description": "Detailed description of what moves/happens in this scene",
      "key_concepts": ["concept1", "concept2"],
      "camera_motion": "zoom_in",
      "transition_type": "fade",
      "lighting": "natural",
      "mood": "scientific",
      "animation_elements": [
        {{
          "animation_type": "particles",
          "detail": "what particles and their behavior",
          "direction": "down/up/left/right/random",
          "particle_type": "water/energy/light/co2/oxygen",
          "start_time": 0.0,
          "end_time": 5.0
        }},
        {{
          "animation_type": "text",
          "detail": "KEY CONCEPT TEXT",
          "position": "bottom/top/center",
          "start_time": 2.0,
          "end_time": 8.0
        }}
      ]
    }}
  ]
}}

Create the complete animated plan now:"""

        print_header("DIRECTOR: Creating Animated Plan", "phase")
        print("🎬 Planning realistic animations with actual movement...")
        sys.stdout.flush()
        
        response = self.call_gemini(prompt, temperature=0.8)
        
        # Extract JSON
        if "```json" in response:
            response = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()
            
        data = json.loads(response)
        
        # Parse metadata
        metadata = VideoMetadata(
            title=data['metadata']['title'],
            total_duration=sum(s['duration'] for s in data['scenes']),
            scene_count=len(data['scenes']),
            educational_level=data['metadata']['educational_level'],
            topic_category=data['metadata']['topic_category'],
            key_learnings=data['metadata']['key_learnings']
        )
        
        # Parse scenes with animations
        scenes = []
        for s_data in data['scenes']:
            # Parse animation elements
            anim_elements = []
            for anim in s_data.get('animation_elements', []):
                # Create proper animation element objects
                if anim['animation_type'] == 'particles':
                    element = AnimationElement(
                        element_type='particle',
                        start_time=anim.get('start_time', 0),
                        end_time=anim.get('end_time', s_data['duration']),
                        start_pos=(0, 0),  # Will be calculated
                        end_pos=(0, 0),
                        color=(255, 255, 255),
                        size=5,
                        motion_type=anim.get('direction', 'down'),
                        label=anim.get('particle_type', 'water')
                    )
                elif anim['animation_type'] == 'text':
                    element = AnimationElement(
                        element_type='text',
                        start_time=anim.get('start_time', 0),
                        end_time=anim.get('end_time', s_data['duration']),
                        start_pos=(0, 0),
                        end_pos=(0, 0),
                        color=(255, 255, 255),
                        size=0,
                        motion_type=anim.get('position', 'bottom'),
                        label=anim.get('detail', '')
                    )
                elif anim['animation_type'] == 'flowing':
                    element = AnimationElement(
                        element_type='flow',
                        start_time=anim.get('start_time', 0),
                        end_time=anim.get('end_time', s_data['duration']),
                        start_pos=(0, 0),
                        end_pos=(0, 0),
                        color=(255, 255, 255),
                        size=0,
                        motion_type=anim.get('path', 'vertical'),
                        label=anim.get('detail', '')
                    )
                elif anim['animation_type'] == 'growing':
                    element = AnimationElement(
                        element_type='growing',
                        start_time=anim.get('start_time', 0),
                        end_time=anim.get('end_time', s_data['duration']),
                        start_pos=(0, 0),
                        end_pos=(0, 0),
                        color=(255, 255, 255),
                        size=0,
                        motion_type='grow',
                        label=anim.get('object_type', 'plant')
                    )
                
                anim_elements.append(element)
            
            scene = Scene(
                scene_number=s_data['scene_number'],
                scene_type='animated_realistic',
                duration=s_data['duration'],
                narration=s_data['narration'],
                visual_prompt=s_data['visual_prompt'],
                key_concepts=s_data['key_concepts'],
                camera_motion=s_data['camera_motion'],
                transition_type=s_data['transition_type'],
                lighting=s_data['lighting'],
                mood=s_data['mood'],
                animation_elements=anim_elements,
                action_description=s_data.get('action_description', '')
            )
            scenes.append(scene)
        
        print(f"✓ Animated plan created!")
        print(f"  📹 Scenes: {metadata.scene_count} (all with animations)")
        print(f"  ⏱️  Duration: {metadata.total_duration:.1f}s")
        print(f"\n📋 Animation Breakdown:")
        
        for scene in scenes:
            print(f"\n  Scene {scene.scene_number}: {scene.key_concepts[0]}")
            print(f"    Action: {scene.action_description[:60]}...")
            print(f"    Animations: {len(scene.animation_elements)} elements")
            for elem in scene.animation_elements:
                print(f"      • {elem.element_type}: {elem.label}")
        
        return metadata, scenes

# =============================================================================
# VISUAL DIRECTOR WITH ANIMATION
# =============================================================================

class VisualDirectorAgent:
    """
    Visual Director: Creates photorealistic images and applies animations.
    """
    
    def __init__(self, device: str):
        self.device = device
        self.pipe = None
        self.animator = AnimationGenerator()
        
    def load_model(self):
        """Load SD model optimized for Kaggle."""
        if self.pipe is None:
            from diffusers import StableDiffusionPipeline, DPMSolverMultistepScheduler
            
            print_header("VISUAL DIRECTOR: Loading Model", "phase")
            print("📦 Loading Stable Diffusion (optimized for Kaggle)...")
            sys.stdout.flush()
            
            try:
                self.pipe = StableDiffusionPipeline.from_pretrained(
                    SD_MODEL,
                    torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                    safety_checker=None
                ).to(self.device)
                
                self.pipe.scheduler = DPMSolverMultistepScheduler.from_config(
                    self.pipe.scheduler.config
                )
                
                if self.device == "cuda":
                    self.pipe.enable_attention_slicing(1)
                    self.pipe.enable_vae_slicing()
                    
                print("✓ Model loaded successfully\n")
                clear_memory()
                
            except Exception as e:
                print(f"✗ Model load failed: {e}\n")
                self.pipe = None
    
    def enhance_prompt(self, prompt: str, scene: Scene) -> str:
        """Enhance prompt for photorealistic output."""
        enhanced = prompt.strip()
        enhanced += ", photorealistic, high detail, professional photography, 8K, sharp focus"
        enhanced += ", no text, no labels, no diagrams, natural lighting"
        
        if len(enhanced) > 300:
            enhanced = enhanced[:300].rsplit(',', 1)[0]
        
        return enhanced
    
    def generate_base_image(self, scene: Scene) -> Image.Image:
        """Generate photorealistic base image."""
        self.load_model()
        
        if self.pipe is None:
            return self.create_fallback_image(scene)
        
        prompt = self.enhance_prompt(scene.visual_prompt, scene)
        negative_prompt = "diagram, illustration, cartoon, text, labels, arrows, low quality, blurry"
        
        print(f"  🎨 Generating realistic image for Scene {scene.scene_number}")
        print(f"     Prompt: {prompt[:80]}...")
        sys.stdout.flush()
        
        try:
            with torch.no_grad():
                result = self.pipe(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    num_inference_steps=30,
                    guidance_scale=7.5,
                    width=VIDEO_WIDTH,
                    height=VIDEO_HEIGHT,
                    generator=torch.Generator(device=self.device).manual_seed(42 + scene.scene_number)
                )
            
            image = result.images[0]
            
            # Enhance
            image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
            enhancer = ImageEnhance.Color(image)
            image = enhancer.enhance(1.1)
            
            del result
            clear_memory()
            
            print(f"     ✓ Photorealistic image generated")
            return image
            
        except Exception as e:
            print(f"     ⚠ Generation error: {e}")
            return self.create_fallback_image(scene)
    
    def create_fallback_image(self, scene: Scene) -> Image.Image:
        """Create realistic fallback when model fails."""
        img = Image.new('RGB', (VIDEO_WIDTH, VIDEO_HEIGHT))
        draw = ImageDraw.Draw(img)
        
        # Natural gradient background
        for y in range(VIDEO_HEIGHT):
            progress = y / VIDEO_HEIGHT
            if 'plant' in scene.visual_prompt.lower() or 'leaf' in scene.visual_prompt.lower():
                r = int(100 + progress * 50)
                g = int(150 + progress * 50)
                b = int(100 + progress * 30)
            else:
                r = int(80 + progress * 80)
                g = int(120 + progress * 80)
                b = int(160 + progress * 60)
            draw.line([(0, y), (VIDEO_WIDTH, y)], fill=(r, g, b))
        
        # Add subtle texture
        pixels = img.load()
        for _ in range(1000):
            x, y = np.random.randint(0, VIDEO_WIDTH), np.random.randint(0, VIDEO_HEIGHT)
            r, g, b = pixels[x, y]
            noise = np.random.randint(-20, 20)
            pixels[x, y] = (max(0, min(255, r+noise)), 
                           max(0, min(255, g+noise)), 
                           max(0, min(255, b+noise)))
        
        return img
    
    def create_video_with_camera_motion(self, image: Image.Image, scene: Scene) -> str:
        """Create video with camera motion."""
        img_path = os.path.join(ASSETS_DIR, f"scene_{scene.scene_number:03d}.png")
        image.save(img_path, quality=IMAGE_QUALITY)
        
        base_video = os.path.join(VIDEO_CLIPS_DIR, f"scene_{scene.scene_number:03d}_base.mp4")
        
        duration = scene.duration
        fps = VIDEO_FPS
        total_frames = int(duration * fps)
        
        # Camera motion filters
        motion_filters = {
            'static': f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}",
            'zoom_in': f"zoompan=z='1.0+(0.2/({duration}))*(on/{fps})':d={total_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}",
            'zoom_out': f"zoompan=z='1.2-(0.2/({duration}))*(on/{fps})':d={total_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}",
            'pan_right': f"zoompan=z='1.0':x='iw*0.1*(on/{fps}/{duration})':d={total_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}",
            'pan_left': f"zoompan=z='1.0':x='iw*0.1*(1-on/{fps}/{duration})':d={total_frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={fps}"
        }
        
        filter_str = motion_filters.get(scene.camera_motion, motion_filters['static'])
        
        try:
            subprocess.run([
                'ffmpeg', '-y', '-loop', '1', '-i', img_path,
                '-vf', filter_str,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-t', str(duration),
                base_video
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
            
            print(f"     ✓ Base video with {scene.camera_motion}")
            return base_video
            
        except Exception as e:
            print(f"     ⚠ Camera motion failed: {e}")
            return None
    
    def add_animations_to_video(self, base_video: str, scene: Scene) -> str:
        """Add all animations to the video."""
        if not base_video or not os.path.exists(base_video):
            return base_video
        
        print(f"  🎬 Adding {len(scene.animation_elements)} animations...")
        
        current_video = base_video
        
        for i, anim_elem in enumerate(scene.animation_elements):
            print(f"     [{i+1}/{len(scene.animation_elements)}] {anim_elem.element_type}: {anim_elem.label}")
            
            # Generate animation frames
            duration = anim_elem.end_time - anim_elem.start_time
            
            if anim_elem.element_type == 'particle':
                anim_frames = self.animator.create_particle_animation(
                    VIDEO_WIDTH, VIDEO_HEIGHT, duration,
                    anim_elem.label, anim_elem.motion_type
                )
            elif anim_elem.element_type == 'flow':
                flow_type = anim_elem.label.split()[0] if anim_elem.label else 'water'
                anim_frames = self.animator.create_flow_animation(
                    VIDEO_WIDTH, VIDEO_HEIGHT, duration,
                    flow_type, anim_elem.motion_type
                )
            elif anim_elem.element_type == 'growing':
                anim_frames = self.animator.create_growing_animation(
                    VIDEO_WIDTH, VIDEO_HEIGHT, duration,
                    anim_elem.label
                )
            elif anim_elem.element_type == 'text':
                anim_frames = self.animator.create_text_animation(
                    VIDEO_WIDTH, VIDEO_HEIGHT, duration,
                    anim_elem.label, anim_elem.motion_type
                )
            else:
                continue
            
            # Overlay on video
            output_video = os.path.join(ANIMATION_DIR, 
                                       f"scene_{scene.scene_number:03d}_anim_{i}.mp4")
            
            try:
                self.animator.overlay_animation_on_video(current_video, anim_frames, output_video)
                current_video = output_video
                print(f"       ✓ Applied")
            except Exception as e:
                print(f"       ⚠ Failed: {e}")
        
        # Final output
        final_video = os.path.join(VIDEO_CLIPS_DIR, f"scene_{scene.scene_number:03d}_animated.mp4")
        
        if current_video != base_video:
            subprocess.run(['cp', current_video, final_video], check=True)
        else:
            subprocess.run(['cp', base_video, final_video], check=True)
        
        print(f"     ✓ All animations applied")
        
        return final_video
    
    def unload_model(self):
        """Free memory."""
        if self.pipe is not None:
            del self.pipe
            self.pipe = None
            clear_memory()

# =============================================================================
# NARRATION ENGINE
# =============================================================================

class NarrationEngine:
    """Professional narration with voice synthesis."""
    
    def __init__(self, audio_dir: str):
        self.audio_dir = audio_dir
        
    def generate_narration(self, scene: Scene) -> Optional[str]:
        """Generate narration audio."""
        from gtts import gTTS
        from pydub import AudioSegment
        from pydub.effects import normalize
        
        print(f"  🎙️  Scene {scene.scene_number}: Generating narration")
        sys.stdout.flush()
        
        audio_path = os.path.join(self.audio_dir, f"narration_{scene.scene_number:03d}.mp3")
        
        try:
            tts = gTTS(text=scene.narration, lang='en', slow=False)
            temp_path = audio_path.replace('.mp3', '_temp.mp3')
            tts.save(temp_path)
            
            # Process audio
            audio = AudioSegment.from_mp3(temp_path)
            
            # Lower pitch for deeper voice
            new_rate = int(audio.frame_rate * 0.9)
            audio = audio._spawn(audio.raw_data, overrides={'frame_rate': new_rate})
            audio = audio.set_frame_rate(audio.frame_rate)
            
            audio = normalize(audio)
            
            # Adjust to scene duration
            target_duration = scene.duration * 1000
            actual_duration = len(audio)
            
            if abs(actual_duration - target_duration) > 1000:
                speed_ratio = actual_duration / target_duration
                if 0.7 <= speed_ratio <= 1.4:
                    audio = audio._spawn(audio.raw_data, overrides={
                        "frame_rate": int(audio.frame_rate * speed_ratio)
                    }).set_frame_rate(audio.frame_rate)
            
            audio = audio.fade_in(200).fade_out(200)
            audio.export(audio_path, format="mp3", bitrate=AUDIO_BITRATE)
            
            os.remove(temp_path)
            
            print(f"     ✓ Narration generated ({len(audio)/1000:.1f}s)")
            return audio_path
            
        except Exception as e:
            print(f"     ✗ Narration failed: {e}")
            return None

# =============================================================================
# PRODUCTION COORDINATOR
# =============================================================================

class ProductionCoordinator:
    """Coordinates all production."""
    
    def __init__(self, api_key: str, device: str):
        self.director = DirectorAgent(api_key)
        self.visual_director = VisualDirectorAgent(device)
        self.narration = NarrationEngine(AUDIO_DIR)
    
    def produce_video(self, topic: str) -> str:
        """Execute production pipeline."""
        
        print_header("ADVANCED ANIMATED VIDEO GENERATOR v5.0", "main")
        print("🎬 Features:")
        print("  ✓ TRUE ANIMATIONS: Objects actually move")
        print("  ✓ Photorealistic visuals (no diagrams)")
        print("  ✓ Dynamic overlays during narration")
        print("  ✓ Optimized for Kaggle constraints")
        
        # Phase 1: Planning
        metadata, scenes = self.director.create_master_plan(topic)
        
        # Phase 2: Generate visuals with animations
        print_header("GENERATING ANIMATED SCENES", "phase")
        
        video_clips = []
        audio_clips = []
        
        for scene in scenes:
            print(f"\n{'='*80}")
            print(f"  SCENE {scene.scene_number}/{len(scenes)}: {scene.key_concepts[0]}")
            print(f"  Action: {scene.action_description}")
            print(f"{'='*80}")
            
            try:
                # 1. Generate base image
                base_image = self.visual_director.generate_base_image(scene)
                
                # 2. Create video with camera motion
                base_video = self.visual_director.create_video_with_camera_motion(base_image, scene)
                
                # 3. Add animations
                animated_video = self.visual_director.add_animations_to_video(base_video, scene)
                
                video_clips.append(animated_video)
                
                # 4. Generate narration
                audio_path = self.narration.generate_narration(scene)
                audio_clips.append(audio_path)
                
                # Cleanup
                del base_image
                clear_memory()
                
                print(f"\n  ✅ Scene {scene.scene_number} complete with animations")
                
            except Exception as e:
                print(f"\n  ⚠ Error: {e}")
                import traceback
                traceback.print_exc()
        
        # Unload models
        self.visual_director.unload_model()
        
        # Phase 3: Sync audio-video
        print_header("SYNCING AUDIO & VIDEO", "phase")
        
        synced_clips = []
        for i, (video, audio, scene) in enumerate(zip(video_clips, audio_clips, scenes)):
            print(f"  [{i+1}/{len(scenes)}] Scene {scene.scene_number}...", end=" ")
            
            if not video or not os.path.exists(video):
                print("⚠ video missing")
                continue
            
            output = os.path.join(TEMP_DIR, f"synced_{scene.scene_number:03d}.mp4")
            
            if audio and os.path.exists(audio):
                try:
                    subprocess.run([
                        'ffmpeg', '-y', '-i', video, '-i', audio,
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', AUDIO_BITRATE,
                        '-shortest', output
                    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=60)
                    print("✓")
                except:
                    subprocess.run(['cp', video, output], check=True)
                    print("⚠ audio sync failed")
            else:
                subprocess.run(['cp', video, output], check=True)
                print("⚠ no audio")
            
            synced_clips.append(output)
        
        # Phase 4: Final assembly
        print_header("FINAL ASSEMBLY", "phase")
        
        concat_file = os.path.join(TEMP_DIR, "concat_list.txt")
        with open(concat_file, 'w') as f:
            for clip in synced_clips:
                if os.path.exists(clip):
                    f.write(f"file '{os.path.abspath(clip)}'\n")
        
        output_path = os.path.join(OUTPUT_DIR, f"{metadata.title.replace(' ', '_')}_ANIMATED.mp4")
        
        print("📹 Rendering final video...")
        
        try:
            subprocess.run([
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', concat_file,
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', AUDIO_BITRATE,
                '-movflags', '+faststart',
                output_path
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=300)
            
            print("✓ Final video ready!\n")
            
        except Exception as e:
            print(f"✗ Assembly failed: {e}\n")
        
        # Final report
        print_header("PRODUCTION COMPLETE", "main")
        
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024*1024)
            print(f"✅ Animated educational video created!\n")
            print(f"📁 Output: {output_path}")
            print(f"📊 Size: {size_mb:.2f} MB")
            print(f"🎬 Scenes: {len(scenes)} with animations")
            print(f"⏱️  Duration: {metadata.total_duration:.1f}s")
            print(f"\n✨ Features:")
            print(f"  • Photorealistic visuals")
            print(f"  • Animated particles and flows")
            print(f"  • Text overlays during narration")
            print(f"  • Professional camera movements")
            print(f"\n🎉 Your animated educational video is ready!")
        
        return output_path

# =============================================================================
# MAIN
# =============================================================================

def main():
    """Main entry point."""
    
    print("="*80)
    print("  ADVANCED ANIMATED AI VIDEO GENERATOR v5.0")
    print("="*80)
    print("\n🎯 Revolutionary Features:")
    print("  ✓ TRUE ANIMATIONS with moving objects")
    print("  ✓ NO diagrams - only photorealistic scenes")
    print("  ✓ Particles flowing (water, energy, light)")
    print("  ✓ Text appearing during narration")
    print("  ✓ Optimized for Kaggle GPU")
    
    if DEVICE == "cuda":
        print(f"\n✓ GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("\n⚠ Running on CPU")
    
    setup_directories()
    
    print("\n" + "-"*80)
    print("Enter your topic for an ANIMATED educational video:")
    print("Example: 'How photosynthesis works with molecular details'")
    print("-"*80)
    
    topic = input("\n📝 Topic: ").strip()
    
    if not topic:
        topic = "How photosynthesis works: the complete process from water absorption to glucose production"
        print(f"\nUsing default: {topic}")
    
    print("\n🚀 Starting animated production...\n")
    
    try:
        coordinator = ProductionCoordinator(GEMINI_KEY, DEVICE)
        final_video = coordinator.produce_video(topic)
        
        return final_video
        
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        return None
        
    except Exception as e:
        print(f"\n✗ Production error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        clear_memory()

if __name__ == "__main__":
    main()