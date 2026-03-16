import asyncio
import os
from scripts.video_generator import VideoGenerator

async def test_short_audio():
    vg = VideoGenerator()
    data = {
        "Course": "Test Course",
        "video_script": {
            "dialogue": "Hi" # Very short audio to test muxing issues
        }
    }
    
    print("Testing create_reel with short audio...")
    try:
        output = await vg.create_reel(data, "test_short_reel")
        print("Success! Output:", output)
    except Exception as e:
        import traceback
        print("Exception caught:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_short_audio())
