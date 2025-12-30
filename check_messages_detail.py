import firebase_admin
from firebase_admin import credentials, firestore
import os

cred_path = "/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json"
if not firebase_admin._apps:
    cred = credentials.Certificate(cred_path)
    firebase_admin.initialize_app(cred)

db = firestore.client()

uid = "ecOkatnslATnBBS9tQFyKzgPx8t2"
session_id = "Eoy5xzOgYBHaQKx4orq7"

print(f"Checking messages for UID: {uid}, Session: {session_id}")

messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
messages = list(messages_ref.order_by('timestamp').stream())

print(f"Found {len(messages)} messages.")
if len(messages) > 0:
    for i in range(min(5, len(messages))):
        data = messages[i].to_dict()
        print(f"Message {i} ({messages[i].id}): Sender={data.get('sender')}, Type={data.get('type')}, Timestamp={data.get('timestamp')}")
    
    # Check last message too
    last_data = messages[-1].to_dict()
    print(f"Last Message ({messages[-1].id}): Sender={last_data.get('sender')}, Type={last_data.get('type')}, Timestamp={last_data.get('timestamp')}")
