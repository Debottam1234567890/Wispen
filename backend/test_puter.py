import asyncio
import aiohttp
import json

async def test_manual_request():
    print("Testing Manual Puter API Request...")
    url = "https://api.puter.com/drivers/call"
    
    headers = {
        "Content-Type": "application/json",
        "Origin": "https://puter.com",
        "Referer": "https://puter.com/",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    payload = {
        "interface": "puter-image-generation",
        "driver": "gpt-image-1",
        "method": "generate",
        "args": {
            "prompt": "A futuristic city with flying cars, cartoon style"
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"Status: {response.status}")
                text = await response.text()
                print(f"Response: {text[:200]}...")
                
                if response.status == 200:
                    data = json.loads(text)
                    if "result" in data:
                        print("Success! Result:", data["result"])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_manual_request())
