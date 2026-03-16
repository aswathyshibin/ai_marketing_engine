import os
import requests
import json
import time

class ShotstackClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("SHOTSTACK_API_KEY")
        self.api_url = "https://api.shotstack.io/v1/render"
        self.headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key
        }

    def render_reel(self, scenes, voice="Matthew"):
        """
        renders a reel using Shotstack Cloud API and built-in TTS.
        scenes: list of dicts with {"image_url": str, "text": str, "duration": float}
        """
        if not self.api_key:
            raise ValueError("SHOTSTACK_API_KEY not found in environment.")

        timeline = {
            "background": "#000000",
            "tracks": []
        }

        # Track 1: Text Overlays
        text_clips = []
        # Track 2: Images
        image_clips = []
        # Track 3: Audio (TTS)
        audio_clips = []
        
        current_start = 0
        for scene in scenes:
            dur = scene.get("duration", 3.0)
            
            # Image Clip
            img_clip = {
                "asset": {
                    "type": "image",
                    "src": scene["image_url"]
                },
                "start": current_start,
                "length": dur,
                "transition": {
                    "in": "fade",
                    "out": "fade"
                },
                "effect": "zoomIn"
            }
            image_clips.append(img_clip)

            # Text Clip
            if scene.get("text"):
                text_clip = {
                    "asset": {
                        "type": "html",
                        "html": f'<p data-html-type="text" style="color: #ffffff; font-family: Arial; font-size: 40px; text-align: center; background-color: rgba(0,0,0,0.5); padding: 10px;">{scene["text"]}</p>',
                        "css": "p { font-weight: bold; border-radius: 10px; }"
                    },
                    "start": current_start + 0.2,
                    "length": dur - 0.2,
                    "position": "center",
                    "transition": {
                        "in": "slideUp",
                        "out": "fade"
                    }
                }
                text_clips.append(text_clip)
                
                # TTS Audio Clip
                audio_clip = {
                    "asset": {
                        "type": "audio",
                        "src": "shotstack-voice", # Internal provider
                        "text": scene["text"],
                        "voice": voice
                    },
                    "start": current_start,
                    "length": dur
                }
                audio_clips.append(audio_clip)
            
            current_start += dur

        timeline["tracks"].append({"clips": text_clips})
        timeline["tracks"].append({"clips": image_clips})
        timeline["tracks"].append({"clips": audio_clips})

        payload = {
            "timeline": timeline,
            "output": {
                "format": "mp4",
                "resolution": "hd"
            }
        }

        response = requests.post(self.api_url, headers=self.headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()

    def get_status(self, render_id):
        url = f"{self.api_url}/{render_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def wait_for_render(self, render_id, interval=2, timeout=60):
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_status(render_id)
            if status["response"]["status"] == "done":
                return status["response"]["url"]
            elif status["response"]["status"] == "failed":
                raise Exception(f"Shotstack render failed: {status['response'].get('error')}")
            time.sleep(interval)
        raise TimeoutError("Shotstack render timed out.")
