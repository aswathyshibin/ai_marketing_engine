import os
import asyncio
import time
from typing import List, Dict
from scripts.content_engine import ContentEngine
from scripts.poster_generator import PosterGenerator
from scripts.video_generator import VideoGenerator

class MarketingScheduler:
    def __init__(self):
        self.engine = ContentEngine()
        self.poster_gen = PosterGenerator()
        self.video_gen = VideoGenerator()
        
    async def run_pipeline(self):
        """Main automation pipeline to generate weekly content."""
        courses = self.engine.load_courses()
        if not courses:
            print("No courses found in database.")
            return

        print(f"Starting pipeline for {len(courses)} courses...")
        
        for i, course in enumerate(courses):
            print(f"[{i+1}/{len(courses)}] Processing: {course['Course']}")
            
            try:
                # 1. Generate Content via AI
                bundle = self.engine.generate_marketing_bundle(course)
                course.update(bundle)
                
                # 2. Generate Poster
                poster_filename = f"poster_{i:03d}_{course['Course'].replace(' ', '_').lower()}.png"
                poster_path = await self.poster_gen.generate_poster(course, poster_filename)
                
                # 3. Generate Reel (every other course or specific logic)
                if i % 2 == 0:
                    reel_filename = f"reel_{i:03d}_{course['Course'].replace(' ', '_').lower()}"
                    await self.video_gen.create_reel(course, reel_filename, bg_image_path=poster_path)
                
                print(f"Successfully processed {course['Course']}")
                
            except Exception as e:
                print(f"Error processing {course['Course']}: {e}")

    def start_weekly_job(self):
        """Simulates a weekly cron job."""
        asyncio.run(self.run_pipeline())

if __name__ == "__main__":
    scheduler = MarketingScheduler()
    scheduler.start_weekly_job()
