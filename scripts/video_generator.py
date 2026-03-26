import os
import asyncio
import edge_tts
import multiprocessing
import requests
from moviepy import ColorClip, AudioFileClip, CompositeVideoClip, ImageClip, VideoFileClip
from moviepy.video.fx import CrossFadeIn
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import random
import uuid

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
        pass # Removed background box to allow text to float cleanly on video
    
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
        self.pexels_api_key = os.getenv("PEXELS_API_KEY")

    async def generate_speech(self, text: str, filename: str):
        """Generates speech using edge-tts with professional pacing."""
        output_path = os.path.join(self.temp_dir, filename)
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        await communicate.save(output_path)
        return output_path

    async def _fetch_pexels_videos(self, keywords: str, count: int = 3):
        """Fetches vertical videos from Pexels based on keywords."""
        if not self.pexels_api_key:
            return []
        
        url = f"https://api.pexels.com/videos/search?query={keywords}&per_page={count}&orientation=portrait&size=medium"
        headers = {"Authorization": self.pexels_api_key}
        
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.get(url, headers=headers, timeout=10))
            if response.status_code == 200:
                data = response.json()
                video_urls = []
                for v in data.get("videos", []):
                    # Get the link to the mp4 file (usually the first video_file)
                    video_files = v.get("video_files", [])
                    if video_files:
                        # Prefer HD if available
                        hd_files = [f for f in video_files if f.get("quality") == "hd"]
                        video_urls.append(hd_files[0]["link"] if hd_files else video_files[0]["link"])
                return video_urls
        except Exception as e:
            print(f"ERROR: Pexels fetch failed: {e}")
        return []

    async def create_reel(self, data: dict, filename: str, bg_image_paths: list = None, logo_path: str = None, fast_mode: bool = True, theme: str = "TECH"):
        """Creates a professional 9:16 reel with a sequence of videos/images and text overlays."""
        
        scenes = data.get("video_script", {}).get("scenes", [])
        if not scenes:
            full_text = "Unlock your potential with Acadeno."
        else:
            full_text = " ".join([s["text"] for s in scenes])
            
        print(f"DEBUG: Generating speech for {len(full_text)} chars...")
        audio_path = await self.generate_speech(full_text, f"{filename}.mp3")
        
        # --- TURBO OPTIMIZATION: Parallel Downloads ---
        bg_video_paths = []
        if self.pexels_api_key and scenes:
            all_keywords = ", ".join([s.get("keyword", "technology") for s in scenes])
            video_urls = await self._fetch_pexels_videos(all_keywords, count=len(scenes))
            
            async def download_one_video(url, index):
                try:
                    v_path = os.path.join(self.temp_dir, f"video_{uuid.uuid4().hex[:8]}_{index}.mp4")
                    loop = asyncio.get_event_loop()
                    res = await loop.run_in_executor(None, lambda: requests.get(url, stream=True, timeout=15))
                    if res.status_code == 200:
                        with open(v_path, "wb") as f:
                            for chunk in res.iter_content(chunk_size=16384):
                                f.write(chunk)
                        if os.path.exists(v_path) and os.path.getsize(v_path) > 10000:
                            return v_path
                except Exception as e:
                    print(f"DEBUG: Download failed for {url}: {e}")
                return None

            if video_urls:
                print(f"DEBUG: Downloading {len(video_urls)} Pexels videos in parallel...")
                tasks = [download_one_video(url, i) for i, url in enumerate(video_urls)]
                results = await asyncio.gather(*tasks)
                bg_video_paths = [r for r in results if r]
                print(f"DEBUG: Downloaded {len(bg_video_paths)} videos successfully.")

        # Heavy MoviePy logic in thread
        loop = asyncio.get_running_loop()
        output_path = await loop.run_in_executor(
            None, 
            self._render_video, 
            data, filename, bg_image_paths, bg_video_paths, logo_path, audio_path, fast_mode, theme
        )
        
        # Cleanup temp videos
        for v_path in bg_video_paths:
            try:
                if os.path.exists(v_path): os.remove(v_path)
            except: pass
            
        return output_path

    def _render_video(self, data, filename, bg_image_paths, bg_video_paths, logo_path, audio_path, fast_mode, theme):
        """Heavy blocking MoviePy rendering logic with multi-core support."""
        audio = AudioFileClip(audio_path)
        duration = audio.duration
        
        # Theme Definitions
        themes = {
            "TECH": {
                "accent": (0, 242, 254), # Cyan
                "bg_fallback": (15, 23, 42), # Dark Navy
                "course_color": "#00f2fe",
                "headline_bg": (0, 0, 0, 160)
            },
            "CORPORATE": {
                "accent": (59, 130, 246), # Blue
                "bg_fallback": (31, 41, 55), # Gray 800
                "course_color": "#3b82f6",
                "headline_bg": (17, 24, 39, 180)
            },
            "CREATIVE": {
                "accent": (236, 72, 153), # Pink
                "bg_fallback": (88, 28, 135), # Purple
                "course_color": "#ec4899",
                "headline_bg": (0, 0, 0, 140)
            }
        }
        style = themes.get(theme.upper(), themes["TECH"])
        
        target_size = (540, 960) if fast_mode else (720, 1280)
        target_fps = 15 if fast_mode else 24
        
        # 1. Background Sequence
        bg_clips = []
        scenes = data.get("video_script", {}).get("scenes", [])
        num_scenes = len(scenes) if scenes else 1
        clip_dur = duration / num_scenes
        
        # Use videos if available, otherwise images
        source_paths = bg_video_paths if bg_video_paths else bg_image_paths
        
        if source_paths:
            for i, s_path in enumerate(source_paths):
                try:
                    start_time = i * clip_dur
                    actual_dur = clip_dur + (0.5 if i < len(source_paths) - 1 else 0)
                    
                    if s_path.endswith(".mp4"):
                        clip = VideoFileClip(s_path).without_audio().with_duration(actual_dur).with_start(start_time)
                        # Resize and center crop - optimize for speed
                        if clip.w != target_size[0] or clip.h != target_size[1]:
                            aspect_ratio = target_size[0] / target_size[1]
                            if clip.w/clip.h > aspect_ratio:
                                clip = clip.resized(height=target_size[1])
                            else:
                                clip = clip.resized(width=target_size[0])
                            clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=target_size[0], height=target_size[1])
                    else:
                        img = Image.open(s_path).convert("RGB")
                        bg_arr = np.array(img)
                        clip = ImageClip(bg_arr).with_duration(actual_dur).with_start(start_time)
                        img.close()
                        clip = clip.resized(height=target_size[1]) if clip.w/clip.h > target_size[0]/target_size[1] else clip.resized(width=target_size[0])
                        clip = clip.cropped(x_center=clip.w/2, y_center=clip.h/2, width=target_size[0], height=target_size[1])
                    
                    if i > 0 and not fast_mode:
                        clip = clip.with_effects([CrossFadeIn(0.4)])
                    bg_clips.append(clip)
                except Exception as e:
                    print(f"Error processing asset {s_path}: {e}")

            bg = CompositeVideoClip(bg_clips, size=target_size).with_duration(duration) if bg_clips else ColorClip(size=target_size, color=style["bg_fallback"]).with_duration(duration)
        else:
            bg = ColorClip(size=target_size, color=style["bg_fallback"]).with_duration(duration)

        layers = [bg]
        
        # Cinematic Grade
        vignette = ColorClip(size=target_size, color=(0, 0, 0)).with_opacity(0.3).with_duration(duration)
        layers.append(vignette)

        if logo_path and os.path.exists(logo_path):
            logo_w = 120 if fast_mode else 160
            logo = ImageClip(logo_path).with_duration(duration).resized(width=logo_w)
            logo = logo.with_position(('center', 60 if fast_mode else 80)).with_start(0.5)
            layers.append(logo)

        # 2. Text Overlays
        title_text = data.get("Course", data.get("course_name", "Featured Course"))
        headline = data.get("poster_headline", "Master This Skill")
        
        font_paths = [
            os.path.join("assets", "fonts", "Inter-Bold.ttf"),
            "C:\\Windows\\Fonts\\arialbd.ttf"
        ]
        font_path = next((p for p in font_paths if os.path.exists(p)), None)
        
        # Brand Accent Line (Removed per user request)

        # Headline
        h_size = 45 if fast_mode else 65
        h_y = 330 if fast_mode else 380
        headline_arr = create_text_image(text=headline.upper(), width=target_size[0]-100, font_path=font_path, font_size=h_size, color="white", bg_color=style["headline_bg"])
        headline_clip = ImageClip(headline_arr).with_duration(duration).with_position(('center', h_y)).with_start(1)
        
        # Course Name
        c_size = 30 if fast_mode else 40
        c_y = 880 if fast_mode else 1150
        course_arr = create_text_image(text=title_text, width=target_size[0]-100, font_path=font_path, font_size=c_size, color=style["course_color"], bg_color=(0, 0, 0, 180))
        course_clip = ImageClip(course_arr).with_duration(duration).with_position(('center', c_y)).with_start(1.2)
        
        layers.extend([headline_clip, course_clip])

        # 4. Final Composition & Rendering
        video = CompositeVideoClip(layers, size=target_size).with_audio(audio)
        output_path = os.path.join(self.output_dir, f"{filename}.mp4")
        
        thread_count = multiprocessing.cpu_count()
        video.write_videofile(
            output_path, 
            fps=target_fps, 
            codec="libx264", 
            audio_codec="aac", 
            preset="ultrafast",
            threads=thread_count,
            logger=None
        )
        
        try:
            audio.close()
            video.close()
        except: pass
            
        return output_path

if __name__ == "__main__":
    vg = VideoGenerator()
    test_data = {
        "Course": "AI Integrated Flutter Development",
        "video_script": {
            "scenes": [
                {"text": "Build the future of mobile apps.", "keyword": "mobile developer"},
                {"text": "Learn how to integrate AI into Flutter.", "keyword": "artificial intelligence"},
                {"text": "Join Acadeno Technologies today.", "keyword": "technology business"}
            ]
        }
    }
    asyncio.run(vg.create_reel(test_data, "theme_test_reel", theme="TECH"))
