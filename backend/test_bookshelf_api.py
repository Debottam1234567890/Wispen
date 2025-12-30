import requests
import sys
import os

# You need to get a valid Firebase ID token
# For testing, you can grab one from the browser's network tab

token_input = input("Paste your Firebase ID token (from browser dev tools -> Network -> any request -> Authorization header):\n").strip()

if not token_input:
    print("No token provided. Exiting.")
    sys.exit(1)

# Remove "Bearer " prefix if present
token = token_input.replace("Bearer ", "")

try:
    response = requests.get(
        "http://localhost:5000/bookshelf",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Got {len(data)} bookshelf items:")
        for item in data:
            print(f"\n📚 {item.get('title', 'Untitled')}")
            print(f"   ID: {item.get('id')}")
            print(f"   Type: {item.get('fileType')}")
            print(f"   Storage URL: {item.get('storageUrl', 'N/A')[:100]}...")
            if 'content' in item:
                print(f"   Has embedded content: {len(item.get('content', ''))} bytes")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"❌ Request failed: {e}")
