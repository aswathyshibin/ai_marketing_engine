import os
# Unified Playwright path for Railway
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
    if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/playwright-browsers"

from fastapi import FastAPI, Request, BackgroundTasks, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import json
import uuid
import random
import requests
from dotenv import load_dotenv
from scripts.scheduler import MarketingScheduler
from scripts.shotstack_client import ShotstackClient

load_dotenv(override=True)

class PosterRequest(BaseModel):
    course: str
    audience: str
    tone: str
    topic: str = None
    cta: str = None

app = FastAPI(title="Acadeno AI Marketing Engine")

# Setup directories
os.makedirs("output/posters", exist_ok=True)
os.makedirs("output/reels", exist_ok=True)
os.makedirs("assets", exist_ok=True)

# Mount static files for generated assets and branding
app.mount("/output", StaticFiles(directory="output"), name="output")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

templates = Jinja2Templates(directory="templates")

scheduler = MarketingScheduler()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    courses = scheduler.engine.load_courses()
    posters = os.listdir("output/posters")
    reels = os.listdir("output/reels")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "courses": courses,
        "posters": posters,
        "reels": reels,
        "stats": {
            "total_courses": len(courses),
            "total_posters": len(posters),
            "total_reels": len(reels)
        }
    })

@app.get("/debug-env")
async def debug_env():
    import subprocess
    browser_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "Not Set")
    path_exists = os.path.exists(browser_path) if browser_path != "Not Set" else False
    
    contents = []
    if path_exists:
        try:
            contents = os.listdir(browser_path)
        except Exception as e:
            contents = [f"Error listing: {str(e)}"]

    return {
        "PLAYWRIGHT_BROWSERS_PATH": browser_path,
        "exists": path_exists,
        "contents": contents,
        "cwd": os.getcwd(),
        "whoami": subprocess.check_output(["whoami"]).decode().strip(),
        "env_vars": {k: v for k, v in os.environ.items() if "KEY" not in k and "TOKEN" not in k and "SECRET" not in k}
    }

@app.post("/generate-manual-poster")
async def generate_manual_poster(request: PosterRequest):
    try:
        # 1. Generate High-Impact Content (Instagram Square Optimized)
        prompt = f"Generate a ultra-short, magnetic professional headline (MAX 4 WORDS) for a course named '{request.course}'. Targeted at {request.audience}."
        
        chat_completion = scheduler.engine.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an elite marketing copywriter. Return ONLY a 4-word headline. No punctuation at end."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
        )
        raw_headline = chat_completion.choices[0].message.content.strip().strip('"')
        
        # Generate a short professional insight (max 12 words)
        insight_prompt = f"Write a single, high-impact professional power-statement (MAX 12 WORDS) about the career value of '{request.course}'. Tone: Executive."
        insight_completion = scheduler.engine.client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an elite marketing copywriter. Return ONLY one extremely short sentence."},
                {"role": "user", "content": insight_prompt}
            ],
            model="llama-3.3-70b-versatile",
        )
        description = insight_completion.choices[0].message.content.strip().strip('"')

        # NLP Refinement with word limits
        headline = scheduler.engine.refine_text(raw_headline, "ultra short headline", max_words=4)
        description = scheduler.engine.refine_text(description, "concise power statement", max_words=12)

        # 2. Prepare data for poster generator
        logo_png = os.path.join("assets", "logos", "acadeno_logo.png")
        logo_jpeg = os.path.join("assets", "logos", "acadeno_logo.jpeg")
        logo_path = logo_png if os.path.exists(logo_png) else logo_jpeg
        
        logo_base64 = ""
        if os.path.exists(logo_path):
            import base64
            mime_type = "image/png" if logo_path.endswith(".png") else "image/jpeg"
            with open(logo_path, "rb") as image_file:
                logo_base64 = f"data:{mime_type};base64,{base64.b64encode(image_file.read()).decode()}"

        # Select a beautiful background image (High-authority Unsplash collections)
        bg_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1080&q=80" # Default Deep Tech
        course_lower = request.course.lower()
        if "flutter" in course_lower or "mobile" in course_lower:
            bg_url = "https://images.unsplash.com/photo-1512941937669-90a1b58e729c?auto=format&fit=crop&w=1080&q=80"
        elif "ai" in course_lower or "intelligence" in course_lower:
            bg_url = "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1080&q=80"
        elif "marketing" in course_lower or "business" in course_lower:
            bg_url = "https://images.unsplash.com/photo-1460925895917-afdab827c52f?auto=format&fit=crop&w=1080&q=80"

        data = {
            "course_name": request.course, # Explicit course name
            "Topic": description,
            "Target Audience": request.audience,
            "CTA": request.cta if request.cta else "Join Now",
            "poster_headline": headline,
            "logo_data": logo_base64,
            "bg_url": bg_url
        }

        # 3. Generate Poster
        filename = f"manual_{uuid.uuid4().hex[:8]}.png"
        await scheduler.poster_gen.generate_poster(data, filename)

        return {"success": True, "filename": filename, "headline": headline}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/generate-manual-reel")
async def generate_manual_reel(request: PosterRequest):
    try:
        # 1. Generate Viral Script and Headline
        bundle = scheduler.engine.generate_marketing_bundle({
            "Course": request.course,
            "Topic": request.topic if request.topic else request.course,
            "Target Audience": request.audience,
            "CTA": request.cta if request.cta else "Join Now"
        })
        
        # 2. Collect Background Assets (URLs or Paths)
        scenes = bundle.get("video_script", {}).get("scenes", [])
        bg_paths = []
        shotstack_scenes = []
        shotstack_key = os.getenv("SHOTSTACK_API_KEY")
        
        from urllib.parse import quote
        
        for i, scene in enumerate(scenes):
            raw_keyword = scene.get("keyword", "technology")
            keyword = raw_keyword.split(',')[0].strip().replace(' ', '+')
            
            # High-res hardcoded library for Acadeno topics (reliable CDNs)
            library = {
                "flutter": [
                    "https://images.unsplash.com/photo-1512941937669-90a1b58e729c?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1551650975-87deedd944c3?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1517694712202-14dd9538aa97?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1555066931-4365d14bab8c?auto=format&fit=crop&w=1080&q=80"
                ],
                "ai": [
                    "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1593508512255-86ab42a8e620?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1620712943543-bcc4628c6757?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=1080&q=80"
                ],
                "code": [
                    "https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1587620962725-abab7fe55159?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1550439062-609e1531270e?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1516116216624-53e697fedbea?auto=format&fit=crop&w=1080&q=80"
                ],
                "business": [
                    "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&w=1080&q=80",
                    "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1080&q=80"
                ]
            }

            bg_url = f"https://loremflickr.com/1080/1920/{keyword}"
            category = "code"
            if "flutter" in keyword.lower() or "mobile" in keyword.lower(): category = "flutter"
            elif "ai" in keyword.lower() or "intelligence" in keyword.lower(): category = "ai"
            if category in library:
                bg_url = random.choice(library[category])
            
            # If using Shotstack, we just need the URL
            if shotstack_key:
                shotstack_scenes.append({
                    "image_url": bg_url,
                    "text": scenes[i].get("text", ""),
                    "duration": 3.0
                })
                continue

            # Otherwise, download locally for MoviePy
            try:
                bg_path = os.path.join("output", "temp", f"bg_{uuid.uuid4().hex[:8]}_{i}.jpg")
                response = requests.get(bg_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True)
                if response.status_code == 200:
                    with open(bg_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    if os.path.exists(bg_path) and os.path.getsize(bg_path) > 5000:
                        bg_paths.append(bg_path)
                        continue
                # Fallback for local
                res = requests.get("https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1080&q=80", stream=True)
                with open(bg_path, "wb") as f: f.write(res.content)
                bg_paths.append(bg_path)
            except Exception as e:
                print(f"ERROR: Image download failed for keyword {keyword} for local rendering: {e}")
                # Use a rock-solid tech fallback for local rendering if all else fails
                bg_path = os.path.join("output", "temp", f"bg_fallback_{uuid.uuid4().hex[:8]}_{i}.jpg")
                fallback_url = "https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1080&q=80"
                res = requests.get(fallback_url, stream=True, timeout=10)
                with open(bg_path, "wb") as f:
                    f.write(res.content)
                bg_paths.append(bg_path)


        # 4. Generate Reel
        filename = f"manual_reel_{uuid.uuid4().hex[:8]}"
        
        # --- CLOUD RENDERING (SHOTSTACK) ---
        if shotstack_key:
            print(f"DEBUG: Using Shotstack Cloud Rendering for {filename}")
            client = ShotstackClient(shotstack_key)
            render_resp = client.render_reel(shotstack_scenes)
            render_id = render_resp["response"]["id"]
            # For 2-second experience, we return the render info immediately
            return {
                "success": True, 
                "cloud": True,
                "render_id": render_id,
                "message": "Video is being rendered in the cloud! It will be ready in ~15 seconds.",
                "filename": f"{filename}.mp4" # Placeholder
            }

        # --- LOCAL RENDERING (FALLBACK) ---
        data = {
            "Course": request.course,
            "poster_headline": bundle.get("poster_headline", "Master This Skill"),
            "video_script": bundle.get("video_script", {"scenes": []})
        }
        
        # Get Logo Path
        logo_png = os.path.join("assets", "logos", "acadeno_logo.png")
        logo_jpeg = os.path.join("assets", "logos", "acadeno_logo.jpeg")
        logo_path = logo_png if os.path.exists(logo_png) else logo_jpeg
        if not os.path.exists(logo_path):
            logo_path = None

        output_path = await scheduler.video_gen.create_reel(data, filename, bg_image_paths=bg_paths, logo_path=logo_path)
        
        # Clean up temp backgrounds
        for path in bg_paths:
            try:
                if os.path.exists(path): os.remove(path)
            except: pass

        return {"success": True, "filename": f"{filename}.mp4", "headline": data["poster_headline"]}
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/generate-all")
async def generate_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(scheduler.run_pipeline)
    return {"message": "Generation pipeline started in background."}

@app.get("/check-reel-status/{render_id}")
async def check_reel_status(render_id: str):
    try:
        shotstack_key = os.getenv("SHOTSTACK_API_KEY")
        if not shotstack_key:
            return JSONResponse(status_code=400, content={"success": False, "error": "Shotstack key not configured"})
        
        client = ShotstackClient(shotstack_key)
        status = client.get_status(render_id)
        
        resp = status.get("response", {})
        state = resp.get("status")
        video_url = resp.get("url")
        
        return {
            "success": True,
            "status": state,
            "url": video_url,
            "render_id": render_id
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("ACADENO MARKETING ENGINE STARTED")
    print("Access your dashboard at: http://localhost:8000")
    print("="*50 + "\n")
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
