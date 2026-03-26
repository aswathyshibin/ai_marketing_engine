import os
import requests
import time
import json
import base64
from dotenv import load_dotenv

load_dotenv()

class TalkingFaceClient:
    """
    Client for Talking Head APIs (D-ID, HeyGen, or Replicate).
    Currently implemented for D-ID.
    """
    def __init__(self, api_key=None, provider="d-id"):
        self.provider = provider
        self.api_key = api_key or os.getenv("DID_API_KEY")
        
        if self.provider == "d-id":
            self.base_url = "https://api.d-id.com"
            # D-ID Basic Auth: requires base64(email:key) or base64(key)
            # If the user provided email:key, we encode the whole thing.
            auth_str = self.api_key
            if ":" in auth_str:
                auth_bytes = auth_str.encode('ascii')
                base64_bytes = base64.b64encode(auth_bytes)
                auth_str = base64_bytes.decode('ascii')
            
            self.headers = {
                "Authorization": f"Basic {auth_str}",
                "Content-Type": "application/json",
                "accept": "application/json"
            }
        elif self.provider == "heygen":
            self.base_url = "https://api.heygen.com/v1"
            self.headers = {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            }

    def create_talk(self, source_url: str, script_text: str, voice_id: str = "en-US-AndrewNeural"):
        """
        Creates a 'talk' (animated video) from a photo and text.
        """
        if not self.api_key:
            raise ValueError(f"API Key for {self.provider} not found.")

        if self.provider == "d-id":
            payload = {
                "source_url": source_url,
                "script": {
                    "type": "text",
                    "input": script_text,
                    "provider": {
                        "type": "microsoft",
                        "voice_id": voice_id
                    }
                },
                "config": {
                    "fluent": True,
                    "pad_audio": 0.0,
                    "stitch": True
                }
            }
            response = requests.post(f"{self.base_url}/talks", json=payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        
        # Placeholder for HeyGen or others
        return None

    def get_talk_status(self, talk_id: str):
        """
        Polls for the completion of the talk.
        """
        if self.provider == "d-id":
            response = requests.get(f"{self.base_url}/talks/{talk_id}", headers=self.headers)
            response.raise_for_status()
            return response.json()
        return None

    def wait_for_completion(self, talk_id: str, interval: int = 5, timeout: int = 300):
        """
        Waits until the video is ready.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            status = self.get_talk_status(talk_id)
            if status.get("status") == "done":
                return status.get("result_url")
            elif status.get("status") == "error":
                raise Exception(f"Talking Head generation failed: {status.get('error')}")
            
            print(f"Status: {status.get('status')}... waiting {interval}s")
            time.sleep(interval)
        
        raise TimeoutError("Talking Head generation timed out.")

if __name__ == "__main__":
    # Quick test harness (mocking or requires real key)
    client = TalkingFaceClient()
    print("TalkingFaceClient initialized.")
