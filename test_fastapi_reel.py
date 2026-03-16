import asyncio
import os
import sys

# Add the project directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scripts.video_generator import VideoGenerator

async def test_fastapi_context():
    vg = VideoGenerator()
    data = {
        "Course": "Test Course",
        "video_script": {"dialogue": "Testing dialogue inside an async function."}
    }
    
    print("Testing create_reel inside an async context (simulating FastAPI)...")
    try:
        import requests
        bg_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1080&q=80"
        bg_path = "output/temp/test_bg.jpg"
        response = requests.get(bg_url)
        with open(bg_path, "wb") as f:
            f.write(response.content)

        # This simulates main.py calling create_reel synchronously from inside an async endpoint
        output = await vg.create_reel(data, "test_fastapi_reel", bg_image_path=bg_path)
        print("Success! Output:", output)
    except Exception as e:
        import traceback
        print("Exception caught:")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_fastapi_context())
