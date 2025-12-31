
import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize Firebase
# Initialize Firebase Admin SDK
import json
import base64

firebase_creds_b64 = os.getenv('FIREBASE_CREDENTIALS_BASE64')
cred = None

if firebase_creds_b64:
    try:
        print("Keys found in env, decoding...")
        cred_dict = json.loads(base64.b64decode(firebase_creds_b64))
        cred = credentials.Certificate(cred_dict)
    except Exception as e:
        print(f"Error loading creds from env: {e}")

if not cred:
    # Local Fallback
    possible_paths = [
        "/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json",
        "serviceAccountKey.json",
        "../serviceAccountKey.json"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            print(f"Found credentials at {p}")
            cred = credentials.Certificate(p)
            break

try:
    if not firebase_admin._apps:
        if cred:
            firebase_admin.initialize_app(cred)
        else:
             # Try default
            firebase_admin.initialize_app()
            
    db = firestore.client()
    print("✅ Firebase initialized")
except Exception as e:
    print(f"❌ Firebase init failed: {e}")
    exit(1)

def check_videos():
    # We know the user UID from previous logs
    uid = "bP4LovmoafQjPFjE9vNj5yR03jf2"
    session_id = "UCKWgqoCT8FKbTNt5V3x" # The one currently active
    
    print(f"\n🔍 Checking videos for user: {uid}")
    print(f"📂 Session: {session_id}")

    # 1. Check Session Videos
    print("\n--- Session Videos Collection ---")
    try:
        videos_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('videos')
        docs = videos_ref.stream()
        found = False
        for doc in docs:
            found = True
            data = doc.to_dict()
            print(f"\nID: {doc.id}")
            print(f"Title: {data.get('title')}")
            print(f"Status: {data.get('status')}")
            print(f"Created: {data.get('createdAt')}")
            print(f"URL: {data.get('videoUrl')}")
            if data.get('status') == 'generating':
                print("⚠️  STUCK IN GENERATING - DELETING...")
                try:
                    doc.reference.delete()
                    print(f"🗑️ Deleted {doc.id}")
                except Exception as del_err:
                    print(f"Failed to delete: {del_err}")
    except Exception as e:
        print(f"Error checking session videos: {e}")

    # 2. Check Root Videos (Legacy/Fallback)
    print("\n--- Root Videos Collection ---")
    try:
        videos_ref = db.collection('users').document(uid).collection('videos')
        docs = videos_ref.stream()
        for doc in docs:
            data = doc.to_dict()
            print(f"\nID: {doc.id}")
            print(f"Title: {data.get('title')}")
            print(f"Status: {data.get('status')}")
            print(f"Created: {data.get('createdAt')}")
    except Exception as e:
        print(f"Error checking root videos: {e}")

if __name__ == "__main__":
    check_videos()
