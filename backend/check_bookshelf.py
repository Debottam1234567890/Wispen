
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json
import base64
from dotenv import load_dotenv

load_dotenv()

# Setup Firebase exactly like app.py
firebase_creds_b64 = os.getenv('FIREBASE_CREDENTIALS_BASE64')
cred = None

if firebase_creds_b64:
    try:
        cred_dict = json.loads(base64.b64decode(firebase_creds_b64))
        cred = credentials.Certificate(cred_dict)
    except Exception as e:
        print(f"Error loading creds from env: {e}")

if not cred:
    possible_paths = [
        "/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json",
        "serviceAccountKey.json",
        "../serviceAccountKey.json"
    ]
    for p in possible_paths:
        if os.path.exists(p):
            cred = credentials.Certificate(p)
            break

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

def check_all_bookshelves():
    print(f"🔍 Searching ALL bookshelves (including sessions)...")
    
    users_ref = db.collection('users')
    users = users_ref.list_documents()
    
    for user_doc in users:
        uid = user_doc.id
        
        # 1. Check Global Bookshelf
        bookshelf_ref = user_doc.collection('bookshelf')
        docs = bookshelf_ref.stream()
        for doc in docs:
            data = doc.to_dict()
            print(f"\n[GLOBAL] User: {uid}")
            print(f"ID: {doc.id}")
            print(f"Title: {data.get('title')}")
            print(f"URL: {data.get('url')}")
            
        # 2. Check Session Bookshelves
        sessions_ref = user_doc.collection('sessions')
        sessions = sessions_ref.list_documents()
        for session_doc in sessions:
            sid = session_doc.id
            sess_bookshelf_ref = session_doc.collection('bookshelf')
            docs = sess_bookshelf_ref.stream()
            for doc in docs:
                data = doc.to_dict()
                print(f"\n[SESSION: {sid}] User: {uid}")
                print(f"ID: {doc.id}")
                for k, v in data.items():
                    print(f"  {k}: {v}")

def check_user_sessions():
    uid = "bP4LovmoafQjPFjE9vNj5yR03jf2"
    print(f"🔍 Searching ALL sessions for user: {uid}")
    
    user_doc = db.collection('users').document(uid)
    sessions_ref = user_doc.collection('sessions')
    sessions = sessions_ref.list_documents()
    
    for session_doc in sessions:
        sid = session_doc.id
        print(f"  Session: {sid}")
        sess_bookshelf_ref = session_doc.collection('bookshelf')
        docs = sess_bookshelf_ref.stream()
        for doc in docs:
            data = doc.to_dict()
            print(f"    [BOOK] Title: {data.get('title')}, URL: {data.get('storageUrl') or data.get('url')}")




if __name__ == "__main__":
    check_user_sessions()
