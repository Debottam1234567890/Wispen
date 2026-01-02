import os
import sys
import time
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Service
from video_generation_service import VideoGeneratorService
from dotenv import load_dotenv

# Load Env
load_dotenv()

# INJECT KEYS FOR TESTING
# ENV KEYS REQUIRED FOR PRODUCTION/LOCAL TEST WITHOUT HARDCODING
# os.environ["GEMINI_API_KEY"] = os.getenv("GEMINI_API_KEY")
# os.environ["GROQ_API_KEY"] = os.getenv("GROQ_API_KEY")
# os.environ["VIDEO_API_KEY"] = os.getenv("VIDEO_API_KEY") 
# os.environ["POLLINATIONS_API_KEY"] = os.getenv("POLLINATIONS_API_KEY")
# os.environ["STABLE_DIFFUSION_API_KEY"] = os.getenv("STABLE_DIFFUSION_API_KEY")


def setup_firebase():
    # Try to find local key
    possible_keys = [
        "wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json",
        "/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json",
        "serviceAccountKey.json"
    ]
    
    cred = None
    for k in possible_keys:
        if os.path.exists(k):
            print(f"Found credential: {k}")
            cred = credentials.Certificate(k)
            break
            
    if not cred:
        print("❌ No credential file found. Trying default google auth...")
        cred = credentials.ApplicationDefault()

    try:
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'wispen-f4a94.firebasestorage.app'
        })
        print("✅ Firebase Initialized")
    except ValueError:
        print("⚠️ Firebase already initialized")

def test_generation():
    setup_firebase()
    db = firestore.client()
    
    service = VideoGeneratorService(db)
    
    # Real User/Session form logs
    USER_ID = "D1DPjzy7dwXuDcmIjJOJ0mUYUvL2"
    SESSION_ID = "vFlCW1NwqD8QXuF9AbmE" 
    TOPIC = "Test Video Generation Local"
    
    print(f"🚀 Starting Test for User: {USER_ID}, Session: {SESSION_ID}")
    
    # Run synchronously for test
    service.generate_video_background_task(TOPIC, USER_ID, SESSION_ID)

if __name__ == "__main__":
    test_generation()
