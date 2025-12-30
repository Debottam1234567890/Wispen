import os
import sys
import asyncio
import firebase_admin
from firebase_admin import credentials, firestore

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from backend.memory_engine import StudentMemoryEngine

async def test_personalization():
    # Initialize Firebase if not already
    if not firebase_admin._apps:
        cred = credentials.Certificate('/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    engine = StudentMemoryEngine(db)
    
    # Use the session ID from previous debugs
    session_id = 'v4IBB7bpIHGZbHH9VaxK'
    user_id = 'C72eYp1WpBUPF3Fiz0zWogT9w5P2' # Found from app.py logs
    
    print(f"--- Testing Personalization for User: {user_id} ---")
    
    try:
        # 1. Trigger profile update
        print("Triggereing profile update...")
        profile = engine.generate_updated_profile(user_id)
        
        if profile:
            print("\n--- Student Profile Generated ---")
            print(json.dumps(profile, indent=2))
        
        if profile_doc.exists:
            data = profile_doc.to_dict()
            print("\n--- Student Profile Found ---")
            print(f"Detailed Feedback: {data.get('detailed_feedback')[:200]}...")
            print(f"Strengths: {data.get('strengths', [])}")
            print(f"Weaknesses: {data.get('weaknesses', [])}")
            print(f"Interests: {data.get('interests', [])}")
        else:
            print("\n[!] Student profile document does not exist yet.")

    except Exception as e:
        print(f"\n[!] Error during personalization test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_personalization())
