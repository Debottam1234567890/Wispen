import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_infip():
    api_key = os.getenv("VIDEO_API_KEY")
    if not api_key:
        print("❌ VIDEO_API_KEY not found in .env")
        return

    print(f"Using API Key: {api_key}")
    url = "https://api.infip.pro/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "nano-banana",
        "prompt": "A beautiful sunset over mountains, educational style",
        "n": 1,
        "size": "1024x1024",
        "response_format": "url"
    }

    import time
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            image_url = data["data"][0]["url"]
            print(f"✅ Success! Image URL: {image_url}")
        elif response.status_code == 202:
            task_data = response.json()
            poll_url = task_data.get("poll_url")
            print(f"⏳ Generation pending, polling {poll_url}...")
            
            # Poll for up to 90 seconds
            for p in range(18):
                time.sleep(5)
                poll_response = requests.get(poll_url, headers=headers, timeout=30)
                if poll_response.status_code == 200:
                    p_data = poll_response.json()
                    print(f"DEBUG: {p_data}")
                    if "data" in p_data and len(p_data["data"]) > 0:
                        image_url = p_data["data"][0].get("url")
                        print(f"✅ Success! Image URL: {image_url}")
                        break
                    elif p_data.get("status") in ["processing", "pending"]:
                        print(f"... still processing ({p+1}/18)")
                    elif p_data.get("status") == "completed":
                        image_url = p_data.get("image_url") or p_data.get("data", [{}])[0].get("url")
                        print(f"✅ Success! Image URL: {image_url}")
                        break
                    elif p_data.get("status") == "failed":
                        print(f"❌ Failed: {p_data.get('message')}")
                        break
                else:
                    print(f"⚠ Poll status: {poll_response.status_code}")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_infip()
