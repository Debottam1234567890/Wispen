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
messages = messages_ref.order_by('timestamp').stream()

count = 0
for msg in messages:
    print(f"Message {count}: {msg.to_dict()}")
    count += 1

if count == 0:
    print("No messages found in subcollection.")
else:
    print(f"Found {count} messages.")
