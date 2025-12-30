import os
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load .env
load_dotenv('.env')

def test_pollinations_gen():
    api_key = os.getenv("POLLINATIONS_API_KEY")
    if api_key and (api_key.startswith('"') or api_key.startswith("'")):
        api_key = api_key[1:-1]
    
    prompt = "a cat riding a skateboard in Times Square, digital art, cartoonic style"
    import urllib.parse
    encoded_prompt = urllib.parse.quote(prompt)
    
    # Exact URL from user's curl
    url = f"https://gen.pollinations.ai/image/{encoded_prompt}?model=flux"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
        print(f"Using API Key: {api_key[:10]}...")
    
    print(f"Requesting: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=60)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content))
            img.save("backend_test_pollinations.png")
            print("✅ Successfully saved backend_test_pollinations.png")
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_pollinations_gen()
