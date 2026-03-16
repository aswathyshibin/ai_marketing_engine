import os
import asyncio
import edge_tts
from moviepy import ColorClip, AudioFileClip, CompositeVideoClip, ImageClip
from moviepy.video.fx import CrossFadeIn
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random

def create_text_image(text, width=1080, height=None, font_path=None, font_size=80, color="white", bg_color=None, padding=None):
    """Creates a premium Glassmorphism-style text image."""
    try:
        font = ImageFont.truetype(font_path, font_size) if font_path and os.path.exists(font_path) else ImageFont.load_default()
    except Exception as e:
        font = ImageFont.load_default()

    dummy_img = Image.new('RGBA', (width, 1))
    draw = ImageDraw.Draw(dummy_img)

    side_padding = 80
    max_w = width - side_padding * 2
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        test_line = " ".join(current_line)
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) > max_w and len(current_line) > 1:
            current_line.pop()
            lines.append(" ".join(current_line))
            current_line = [word]
    if current_line:
        lines.append(" ".join(current_line))
        
    wrapped_text = "\n".join(lines)
    bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    img_w = width
    box_padding_v = 60
    box_padding_h = 80
    img_h = height if height else text_h + box_padding_v * 2
    
    img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if bg_color:
        box_w = text_w + box_padding_h * 2
        box_h = text_h + box_padding_v * 2
        box_x0 = (img_w - box_w) / 2
        box_y0 = (img_h - box_h) / 2
        box_x1 = box_x0 + box_w
        box_y1 = box_y0 + box_h
        
        # Glass effect base: semi-transparent with slight white tint
        base_fill = (255, 255, 255, 30) if "black" in str(bg_color).lower() or bg_color[3] > 0 else (255,255,255,20)
        # Use provided bg_color but ensure it's "glassy"
        r, g, b, a = bg_color if len(bg_color) == 4 else (*bg_color, 180)
        glass_fill = (r, g, b, min(a, 160)) 
        
        # Draw box with rounded corners and subtle border
        draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=35, fill=glass_fill)
        # Subtle glass border
        draw.rounded_rectangle([box_x0, box_y0, box_x1, box_y1], radius=35, outline=(255, 255, 255, 60), width=2)
    
    x = (img_w - text_w) / 2
    y = (img_h - text_h) / 2 - bbox[1]
    
    # Premium text shadow
    draw.multiline_text((x + 3, y + 3), wrapped_text, font=font, fill=(0, 0, 0, 150), align="center")
    draw.multiline_text((x, y), wrapped_text, font=font, fill=color, align="center")
    
    return np.array(img)

class VideoGenerator:
    def __init__(self):
        self.output_dir = os.path.join("output", "reels")
        self.temp_dir = os.path.join("output", "temp")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        # High-status authoritative professional voice
        self.voice = "en-US-AndrewNeural"
        self.rate = "+15%" # Energetic reels pace

    async def generate_speech(self, text: str, filename: str):
        """Generates speech using edge-tts with professional pacing."""
        output_path = os.path.join(self.temp_dir, filename)
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(output_path)
        return output_path

    async def create_reel(self, data: dict, filename: str, bg_image_paths: list = None, logo_path: str = None):
        """Creates a professional 9:16 reel with a sequence of images and text overlays."""
        
        scenes = data.get("video_script", {}).get("scenes", [])
        if not scenes:
            full_text = "Unlock your potential with Acadeno."
        else:
            full_text = " ".join([s["text"] for s in scenes])
            
        audio_path = await self.generate_speech(full_text, f"{filename}.mp3")
        
        # Move heavy MoviePy logic to a thread to prevent blocking the event loop
        loop = asyncio.get_running_loop()
        output_path = await loop.run_in_executor(
            None, 
            self._render_video, 
            data, filename, bg_image_paths, logo_path, audio_path
        )
        return output_path

    def _render_video(self, data, filename, bg_image_paths, logo_path, audio_path):
        """Heavy blocking MoviePy rendering logic."""
        audio = AudioFileClip(audio_path)
        duration = max(15, audio.duration)
        
        # Turbo Local Optimization: Reduced Resolution (720x1280) and FPS (18)
        # 1. Dynamic Background Sequence
        bg_clips = []
        target_size = (720, 1280)
        
        if bg_image_paths and len(bg_image_paths) > 0:
            num_images = len(bg_image_paths)
            clip_dur = duration / num_images
            
            for i, img_path in enumerate(bg_image_paths):
                try:
                    if os.path.exists(img_path):
                        img = Image.open(img_path).convert("RGB")
                        bg_arr = np.array(img)
                        clip = ImageClip(bg_arr).with_duration(clip_dur + 0.5).with_start(i * clip_dur)
                        img.close()
                        
                        w, h = clip.size
                        aspect_ratio = 720 / 1280
                        if w/h > aspect_ratio:
                            new_h = 1280
                            new_w = int(w * (1280 / h))
                        else:
                            new_w = 720
                            new_h = int(h * (720 / w))
                        
                        clip = clip.resized(width=new_w) if w/h > aspect_ratio else clip.resized(height=new_h)
                        clip = clip.cropped(x_center=new_w/2, y_center=new_h/2, width=720, height=1280)
                        
                        if i > 0:
                            clip = clip.with_effects([CrossFadeIn(0.5)])
                            
                        zoom_dir = random.choice([1, -1])
                        def dynamic_transform(t):
                            if zoom_dir > 0:
                                scale = 1 + 0.2 * (t / clip_dur)
                            else:
                                scale = 1.2 - 0.2 * (t / clip_dur)
                            return scale

                        clip = clip.resized(dynamic_transform)
                        bg_clips.append(clip)
                except Exception as e:
                    print(f"Error processing image {img_path}: {e}")
            
            if not bg_clips:
                bg = ColorClip(size=target_size, color=(15, 23, 42)).with_duration(duration)
            else:
                bg = CompositeVideoClip(bg_clips, size=target_size).with_duration(duration)
        else:
            bg = ColorClip(size=target_size, color=(15, 23, 42)).with_duration(duration)
            bg_clips = [bg]

        # 1.5 Cinematic Overlays
        dust_overlay = ColorClip(size=target_size, color=(255, 255, 255)).with_opacity(0.04).with_duration(duration)
        
        # Human Touch: Subtle Warm Color Grade
        warm_grade = ColorClip(size=target_size, color=(255, 150, 50)).with_opacity(0.03).with_duration(duration)
        
        layers = [bg, dust_overlay, warm_grade]
        
        # Add Vignette for focus
        vignette_img = Image.new('RGBA', target_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(vignette_img)
        # Simple radial gradient as vignette
        for i in range(1, 1281, 20):
            alpha = int(180 * (i / 1280))
            draw.ellipse([720/2 - i, 1280/2 - i, 720/2 + i, 1280/2 + i], outline=(0, 0, 0, alpha), width=20)
        vignette_arr = np.array(vignette_img)
        vignette = ImageClip(vignette_arr).with_duration(duration)
        layers.append(vignette)

        if logo_path and os.path.exists(logo_path):
            logo = ImageClip(logo_path).with_duration(duration).resized(width=160)
            logo = logo.with_position(('center', 80)).with_start(0.5).with_effects([CrossFadeIn(0.5)])
            layers.append(logo)

        # Humanized Layout: Variable Text Positions
        title_text = data.get("Course", data.get("course_name", "Featured Course"))
        headline = data.get("poster_headline", "Master This Skill")
        font_path = "C:\\Windows\\Fonts\\arialbd.ttf"  # Arial Bold
        
        # Brand Accent Line (Top)
        accent_color = (0, 242, 254) # Cyan-ish brand color
        accent = ColorClip(size=(450, 6), color=accent_color).with_duration(duration).with_position(('center', 320)).with_start(1).with_effects([CrossFadeIn(0.5)])
        layers.append(accent)

        # Headline (Top-Mid)
        headline_arr = create_text_image(
            text=headline.upper(), 
            width=680, 
            font_path=font_path, 
            font_size=65, 
            color="white",
            bg_color=(0, 0, 0, 160) # Semi-transparent black box
        )
        headline_clip = ImageClip(headline_arr).with_duration(duration).with_position(('center', 380)).with_start(1).with_effects([CrossFadeIn(0.5)])
        
        # Course Name (Lower-Mid)
        course_arr = create_text_image(
            text=title_text, 
            width=680, 
            font_path=font_path, 
            font_size=50, 
            color="#00f2fe", # Brand primary color
            bg_color=(0, 0, 0, 180)
        )
        # Randomize course name position (top vs bottom) for variety
        pos_y = random.choice([950, 1050])
        course_clip = ImageClip(course_arr).with_duration(duration).with_position(('center', pos_y)).with_start(1.5).with_effects([CrossFadeIn(0.5)])
        
        # Footer Gradient Overlay
        footer_gradient = ColorClip(size=(720, 280), color=(0, 0, 0)).with_opacity(0.7).with_duration(duration).with_position(('center', 'bottom'))
        layers.extend([footer_gradient, headline_clip, course_clip])

        # Progress bar (common in human-generated reels)
        progress_bar_bg = ColorClip(size=(720, 8), color=(255, 255, 255)).with_opacity(0.2).with_duration(duration).with_position(('center', 'bottom'))
        
        def make_progress_bar(t):
            bar_w = int(720 * (t / duration))
            if bar_w < 1: bar_w = 1
            return ColorClip(size=(bar_w, 8), color=accent_color)
            
        progress_bar = ImageClip(np.zeros((8, 720, 3))).with_duration(duration).with_position(('left', 'bottom'))
        # Custom progress bar using a simple animation function
        progress_bar = ColorClip(size=(1, 8), color=accent_color).with_duration(duration)
        # MoviePy 2 doesn't easily support dynamic resizing with lambda for ColorClip in this way, 
        # so we'll just omit it or use a static glow for now to keep it stable.
        layers.append(progress_bar_bg) # Add the static background for the progress bar
        # layers.append(progress_bar) # If dynamic progress bar is implemented, add it here

        # 4. Final Composition
        video = CompositeVideoClip(layers, size=target_size)
        video = video.with_audio(audio)
        
        output_filename = f"{filename}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        print(f"DEBUG: Starting Turbo Rendering for {output_filename} (speed first)")
        video.write_videofile(output_path, fps=18, codec="libx264", audio_codec="aac", preset="ultrafast")
        print(f"DEBUG: Finished Turbo Rendering for {output_filename}")
        
        # Clean up moviepy resources to prevent avcodec errors on subsequent runs
        try:
            audio.close()
            video.close()
            for layer in layers:
                layer.close()
        except:
            pass
            
        return output_path

if __name__ == "__main__":
    # Test Data
    test_data = {
        "Course": "AI Integrated Flutter Development",
        "video_script": {
            "scenes": [
                {"text": "Build the future of mobile apps.", "keyword": "mobile development"},
                {"text": "Learn how to integrate AI into Flutter.", "keyword": "artificial intelligence"},
                {"text": "Join Acadeno Technologies today.", "keyword": "technology"}
            ]
        }
    }
    
    vg = VideoGenerator()
    asyncio.run(vg.create_reel(test_data, "test_reel_threaded"))
