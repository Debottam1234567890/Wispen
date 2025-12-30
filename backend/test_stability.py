import os
import requests
import dotenv
import base64

dotenv.load_dotenv()
STABILITY_KEY = os.getenv("STABILITY_API_KEY")

def test_stability():
    print("Testing Stability AI API...")
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    
    body = {
        "steps": 30,
        "width": 1024,
        "height": 1024,
        "seed": 0,
        "cfg_scale": 5,
        "samples": 1,
        "text_prompts": [
            {"text": "A futuristic city with flying cars", "weight": 1}
        ],
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_KEY}",
    }

    response = requests.post(url, headers=headers, json=body)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
    else:
        data = response.json()
        for i, image in enumerate(data["artifacts"]):
            with open(f'test_stability_{i}.png', "wb") as f:
                f.write(base64.b64decode(image["base64"]))
        print("Success! Saved test_stability_0.png")

if __name__ == "__main__":
    test_stability()
