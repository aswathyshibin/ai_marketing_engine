import os
from scripts.talking_face_client import TalkingFaceClient
import requests

def test_auth():
    client = TalkingFaceClient()
    print(f"Testing D-ID Auth with headers: {client.headers}")
    
    # Try to get credits or simple user info
    try:
        response = requests.get("https://api.d-id.com/credits", headers=client.headers)
        if response.status_code == 200:
            print("Successfully authenticated with D-ID!")
            print("Credits Info:", response.json())
        else:
            print(f"Auth Failed. Status: {response.status_code}")
            print("Response:", response.text)
    except Exception as e:
        print(f"Error during auth test: {e}")

if __name__ == "__main__":
    test_auth()
