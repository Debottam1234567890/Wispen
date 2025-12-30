import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore

def debug_firestore():
    print("🚀 Debugging Firestore Data...")
    
    if not firebase_admin._apps:
        cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'wispen-f4a94.firebasestorage.app' 
        })
    
    db = firestore.client()
    
    print("Listing ALL collections in root...")
    cols = db.collections()
    for col in cols:
        print(f" - Collection: {col.id}")
        
    print("\nChecking 'users' collection...")
    users = list(db.collection('users').stream())
    print(f"Found {len(users)} users.")
    
    for user in users:
        print(f"\nUser: {user.id}")
        bookshelf = list(db.collection('users').document(user.id).collection('bookshelf').stream())
        print(f" - Bookshelf Items: {len(bookshelf)}")
        for item in bookshelf:
            data = item.to_dict()
            print(f"   * {item.id}: {data.get('title', 'No Title')} (Type: {data.get('fileType')})")
            if data.get('content'):
                print(f"     - Content Len: {len(data['content'])}")
            if data.get('storageUrl'):
                print(f"     - Storage URL: {data['storageUrl'][:50]}...")

if __name__ == "__main__":
    debug_firestore()
