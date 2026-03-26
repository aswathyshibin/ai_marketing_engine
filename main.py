import os
# Force unified path to ensure consistency regardless of dashoard settings
if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/playwright-browsers"
    print(f"DEBUG: Forced Browser Path: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")

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
from scripts.talking_face_client import TalkingFaceClient

load_dotenv(override=True)

class PosterRequest(BaseModel):
    course: str
    audience: str
    tone: str
    topic: str = None
    cta: str = None
    language: str = "english"
    avatar_url: str = None
    theme: str = "TECH" # TECH, CORPORATE, CREATIVE

app = FastAPI(title="Acadeno AI Marketing Engine - v3")

@app.get("/debug-env")
async def debug_env():
    import os
    browser_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "Not Set")
    path_exists = os.path.exists(browser_path)
    contents = os.listdir(browser_path) if path_exists else []
    
    # Check for fonts
    font_path = os.path.join("assets", "fonts", "Inter-Bold.ttf")
    font_exists = os.path.exists(font_path)
    
    # Check writable directories
    writable = {}
    for d in ["output", "output/posters", "output/reels", "output/temp"]:
        writable[d] = os.access(d, os.W_OK) if os.path.exists(d) else "Not Found"

    return {
        "status": "ready",
        "version": "v3.2",
        "PLAYWRIGHT_BROWSERS_PATH": browser_path,
        "browser_path_exists": path_exists,
        "browser_contents_count": len(contents),
        "font_bold_exists": font_exists,
        "writable_dirs": writable,
        "railway_env": bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID")),
        "env_vars": {k: v for k, v in os.environ.items() if any(x in k for x in ["PORT", "RAILWAY", "PLAYWRIGHT"])}
    }

# Setup directories
print(f"DEBUG: Railway Environment detected: {bool(os.environ.get('RAILWAY_ENVIRONMENT'))}")
print(f"DEBUG: Browser Path: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH')}")
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


@app.post("/generate-manual-poster")
async def generate_manual_poster(request: PosterRequest):
    try:
        # 1. Generate High-Impact Content (Instagram Square Optimized)
        lang_instruction = f" The content MUST be in {request.language}." if request.language != "english" else ""
        malayalam_instruction = " Use ONLY natural, conversational 'Manglish' style (English technical terms written in Malayalam script). EXAMPLE: Instead of 'ബൃഹത്തായ ഡാറ്റ വിശ്ലേഷണം', use 'ഡാറ്റ അനലിറ്റിക്സ് മാസ്റ്ററി'. Keep words like 'AI', 'Course', 'Career', 'Success' in English sounds but write them in Malayalam script. Avoid 'pure' formal Malayalam. Stay in Malayalam script." if request.language == "malayalam" else ""
        
        prompt = f"Generate a ultra-short, magnetic professional headline (MAX 4 WORDS) for a course named '{request.course}'. Targeted at {request.audience}.{lang_instruction}{malayalam_instruction}"
        
        chat_completion = scheduler.engine.client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are an elite marketing copywriter. Return ONLY {request.language} text. Return ONLY a 4-word headline. No punctuation at end."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
        )
        raw_headline = chat_completion.choices[0].message.content.strip().strip('"')
        
        # Generate a short professional insight (max 12 words)
        insight_prompt = f"Write a single, high-impact professional power-statement (MAX 12 WORDS) about the career value of '{request.course}'. Tone: Executive.{lang_instruction}{malayalam_instruction}"
        insight_completion = scheduler.engine.client.chat.completions.create(
            messages=[
                {"role": "system", "content": f"You are an elite marketing copywriter. Return ONLY {request.language} text. Return ONLY one extremely short sentence."},
                {"role": "user", "content": insight_prompt}
            ],
            model="llama-3.3-70b-versatile",
        )
        description = insight_completion.choices[0].message.content.strip().strip('"')

        # NLP Refinement with word limits
        headline = scheduler.engine.refine_text(raw_headline, "ultra short headline", max_words=4, language=request.language)
        description = scheduler.engine.refine_text(description, "concise power statement", max_words=12, language=request.language)

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

        # 1.5 Generate AI Image Prompt via Groq and fetch via Pollinations
        import urllib.parse
        image_prompt_request = f"Write a highly descriptive, vivid, 25-word image generation prompt for a professional, cinematic, ultra-realistic background image for a marketing poster about '{request.course}'. Theme: {request.theme}. No text, no words in the image. Return ONLY the prompt text, nothing else."
        image_prompt_completion = scheduler.engine.client.chat.completions.create(
            messages=[{"role": "user", "content": image_prompt_request}],
            model="llama-3.1-8b-instant",
        )
        generated_image_prompt = image_prompt_completion.choices[0].message.content.strip()
        print(f"DEBUG: Generated AI Image Prompt: {generated_image_prompt}")

        # Build dynamic background URL using Pollinations Free API
        encoded_prompt = urllib.parse.quote(generated_image_prompt)
        bg_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1080&height=1080&nologo=true&enhance=true"
        
        print(f"DEBUG: Selected Final AI Image URL: {bg_url}")

        # Translate CTA if needed
        cta = request.cta if request.cta else "Join Now"
        if request.language == "malayalam":
            cta_completion = scheduler.engine.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": "You are an elite marketing copywriter. Return ONLY the natural, conversational 'Manglish' style (English words in Malayalam script if needed) translation of the given CTA (MAX 2 WORDS)."},
                    {"role": "user", "content": f"Translate this CTA to Malayalam: {cta}"}
                ],
                model="llama-3.3-70b-versatile",
            )
            cta = cta_completion.choices[0].message.content.strip().strip('"')

        data = {
            "course_name": request.course, # Explicit course name
            "Topic": description,
            "Target Audience": request.audience,
            "CTA": cta,
            "poster_headline": headline,
            "logo_data": logo_base64,
            "bg_url": bg_url,
            "language": request.language
        }

        # 3. Generate Poster
        filename = f"manual_{uuid.uuid4().hex[:8]}.png"
        await scheduler.poster_gen.generate_poster(data, filename)

        return {"success": True, "filename": filename, "headline": headline}
    except Exception as e:
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/generate-manual-reel")
async def generate_manual_reel(request: PosterRequest, background_tasks: BackgroundTasks):
    try:
        # 1. Generate Viral Script and Headline
        bundle = scheduler.engine.generate_marketing_bundle({
            "Course": request.course,
            "Topic": request.topic if request.topic else request.course,
            "Target Audience": request.audience,
            "CTA": request.cta if request.cta else "Join Now"
        }, language="english")
        
        # 2. Collect Background Assets (URLs or Paths)
        scenes = bundle.get("video_script", {}).get("scenes", [])
        bg_paths = []
        shotstack_scenes = []
        shotstack_key = os.getenv("SHOTSTACK_API_KEY")
        
        async def download_image(i, bg_url):
            try:
                keyword = scenes[i].get("keyword", "technology").split(',')[0].strip().replace(' ', '+')
                bg_path = os.path.join("output", "temp", f"bg_{uuid.uuid4().hex[:8]}_{i}.jpg")
                
                # Use a session or direct request (requests is blocking, but we run in a thread or use a faster way)
                # For minimal changes, we'll keep requests but wrap it. 
                # Better: use httpx if available, but let's stick to what's there but parallelized.
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(None, lambda: requests.get(bg_url, stream=True, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15, allow_redirects=True))
                
                if response.status_code == 200:
                    with open(bg_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    if os.path.exists(bg_path) and os.path.getsize(bg_path) > 5000:
                        return bg_path
                
                # Fallback
                res = await loop.run_in_executor(None, lambda: requests.get("https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1080&q=80", stream=True))
                with open(bg_path, "wb") as f: f.write(res.content)
                return bg_path
            except Exception as e:
                print(f"ERROR: Image download failed for scene {i}: {e}")
                return None

        # Prepare download tasks (ONLY if Pexels key is NOT set, or as a manual fallback)
        download_tasks = []
        pexels_key = os.getenv("PEXELS_API_KEY")

        if not pexels_key:
            for i, scene in enumerate(scenes):
                raw_keyword = scene.get("keyword", "technology")
                keyword = raw_keyword.split(',')[0].strip().replace(' ', '+')
                
                # High-res hardcoded library for Acadeno topics
                library = {
                    "flutter": [
                        "https://images.unsplash.com/photo-1512941937669-90a1b58e729c?auto=format&fit=crop&w=1080&q=80",
                        "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1080&q=80",
                        "https://images.unsplash.com/photo-1551650975-87deedd944c3?auto=format&fit=crop&w=1080&q=80"
                    ],
                    "ai": [
                        "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=1080&q=80",
                        "https://images.unsplash.com/photo-1593508512255-86ab42a8e620?auto=format&fit=crop&w=1080&q=80"
                    ],
                    "code": [
                        "https://images.unsplash.com/photo-1542831371-29b0f74f9713?auto=format&fit=crop&w=1080&q=80",
                        "https://images.unsplash.com/photo-1498050108023-c5249f4df085?auto=format&fit=crop&w=1080&q=80"
                    ]
                }

                bg_url = f"https://loremflickr.com/1080/1920/{keyword}"
                category = "code"
                if "flutter" in keyword.lower() or "mobile" in keyword.lower(): category = "flutter"
                elif "ai" in keyword.lower() or "intelligence" in keyword.lower(): category = "ai"
                
                if category in library:
                    bg_url = random.choice(library[category])
                
                if not shotstack_key:
                    download_tasks.append(download_image(i, bg_url))
                else:
                    shotstack_scenes.append({
                        "image_url": bg_url,
                        "text": scenes[i].get("text", ""),
                        "duration": 3.0
                    })

            # Execute downloads in parallel
            if download_tasks:
                results = await asyncio.gather(*download_tasks)
                bg_paths = [path for path in results if path]
        else:
            print("DEBUG: Pexels key found, skipping redundant image downloads in main.py")


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

        # 4. Generate Reel in Background
        job_id = f"reel_{uuid.uuid4().hex[:8]}"
        filename = f"{job_id}.mp4"
        
        # We store the status in a simple dict for this session (since it's a small app)
        if not hasattr(app, "jobs"): app.jobs = {}
        app.jobs[job_id] = {"status": "processing", "filename": filename}

        async def run_rendering():
            try:
                # Local Background Path
                local_bg_paths = bg_paths if 'bg_paths' in locals() else []
                logo_png = os.path.join("assets", "logos", "acadeno_logo.png")
                logo_jpeg = os.path.join("assets", "logos", "acadeno_logo.jpeg")
                logo_path = logo_png if os.path.exists(logo_png) else logo_jpeg
                if not os.path.exists(logo_path): logo_path = None

                data = {
                    "Course": request.course,
                    "poster_headline": bundle.get("poster_headline", "Master This Skill"),
                    "video_script": bundle.get("video_script", {"scenes": []})
                }

                await scheduler.video_gen.create_reel(data, job_id, bg_image_paths=local_bg_paths, logo_path=logo_path, theme=request.theme)
                app.jobs[job_id]["status"] = "done"
                
                # Cleanup temp backgrounds
                for path in local_bg_paths:
                    try: 
                        if os.path.exists(path): os.remove(path)
                    except: pass
            except Exception as e:
                print(f"ERROR in Background Reel Gen: {e}")
                app.jobs[job_id]["status"] = "failed"
                app.jobs[job_id]["error"] = str(e)

        background_tasks.add_task(run_rendering)

        return {
            "success": True, 
            "job_id": job_id, 
            "message": "Generation started! Instant feedback provided.",
            "status": "processing"
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/generate-talking-reel")
async def generate_talking_reel(request: PosterRequest):
    """
    Generate a talking head reel using a photo and AI script.
    """
    try:
        # 1. Generate Voice Script
        bundle = scheduler.engine.generate_marketing_bundle({
            "Course": request.course,
            "Topic": request.topic if request.topic else request.course,
            "Target Audience": request.audience,
            "CTA": request.cta if request.cta else "Join Now"
        }, language=request.language)
        
        script_text = bundle.get("video_script", {}).get("scenes", [{}])[0].get("text", "Unlock your potential with Acadeno.")
        # Join all scene text for a full script if multiple scenes
        scenes = bundle.get("video_script", {}).get("scenes", [])
        if len(scenes) > 1:
            script_text = " ".join([s["text"] for s in scenes])

        # 2. Talking Head Generation (D-ID)
        source_url = request.avatar_url
        if not source_url:
            return JSONResponse(status_code=400, content={"success": False, "error": "Please provide an 'avatar_url'. D-ID requires a public link to your photo."})
        
        client = TalkingFaceClient()
        print(f"DEBUG: Starting Talking Head generation for: {script_text[:50]}...")
        
        talk_resp = client.create_talk(source_url, script_text)
        talk_id = talk_resp.get("id")
        
        return {
            "success": True, 
            "status": "created",
            "talk_id": talk_id,
            "message": "AI Avatar is being generated! This usually takes 30-60 seconds."
        }
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return JSONResponse(status_code=500, content={"success": False, "error": str(e)})

@app.post("/generate-all")
async def generate_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(scheduler.run_pipeline)
    return {"message": "Generation pipeline started in background."}

@app.get("/check-job-status/{job_id}")
async def check_job_status(job_id: str):
    if not hasattr(app, "jobs") or job_id not in app.jobs:
        return JSONResponse(status_code=404, content={"success": False, "error": "Job not found"})
    
    return {
        "success": True,
        "job_id": job_id,
        "status": app.jobs[job_id]["status"],
        "filename": app.jobs[job_id].get("filename"),
        "error": app.jobs[job_id].get("error")
    }

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

@app.get("/check-talking-head-status/{talk_id}")
async def check_talking_head_status(talk_id: str):
    try:
        client = TalkingFaceClient()
        status_resp = client.get_talk_status(talk_id)
        
        state = status_resp.get("status")
        video_url = status_resp.get("result_url")
        
        if state == "done" and video_url:
            # Optionally download locally in background
            filename = f"talking_reel_{talk_id[:8]}.mp4"
            output_path = os.path.join("output", "reels", filename)
            if not os.path.exists(output_path):
                # We do it synchronously here for simplicity, but in a real app, use BackgroundTasks
                v_res = requests.get(video_url, stream=True)
                with open(output_path, "wb") as f:
                    for chunk in v_res.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            return {
                "success": True,
                "status": "done",
                "url": video_url,
                "filename": filename
            }
            
        return {
            "success": True,
            "status": state,
            "talk_id": talk_id
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
