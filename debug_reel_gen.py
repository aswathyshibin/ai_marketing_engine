import asyncio
import os
import sys
import uuid

# Add the project directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.video_generator import VideoGenerator
from scripts.content_engine import ContentEngine

async def test_reel_gen():
    vg = VideoGenerator()
    ce = ContentEngine()
    
    course = "AI tools for developers"
    print(f"Generating content for: {course}")
    
    # Simulate the manual generation flow
    try:
        bundle = ce.generate_marketing_bundle({
            "Course": course,
            "Topic": course,
            "Target Audience": "Devs",
            "CTA": "Join Now"
        })
        
        scenes = bundle.get("video_script", {}).get("scenes", [])
        print(f"Scenes generated: {len(scenes)}")
        
        import requests
        import time
        from urllib.parse import quote
        
        bg_paths = []
        for i, scene in enumerate(scenes):
            keyword = scene.get("keyword", "technology")
            # Using the same logic as in main.py
            bg_url = f"https://source.unsplash.com/featured/1080x1920?{quote(keyword)}"
            print(f"Downloading image {i+1} for keyword: {keyword}")
            
            try:
                bg_path = os.path.join("output", "temp", f"test_bg_{uuid.uuid4().hex[:8]}_{i}.jpg")
                response = requests.get(bg_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                if response.status_code == 200:
                    with open(bg_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    bg_paths.append(bg_path)
                    print(f"Downloaded to {bg_path}")
            except Exception as e:
                print(f"Failed to download image {i}: {e}")

        # Final reel generation
        filename = "debug_reel"
        data = {
            "Course": course,
            "poster_headline": bundle.get("poster_headline", "Master This Skill"),
            "video_script": bundle.get("video_script", {"scenes": []})
        }
        
        print("Starting video generation...")
        output_path = await vg.create_reel(data, filename, bg_image_paths=bg_paths)
        print(f"Success! Reel saved to: {output_path}")
        
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_reel_gen())
