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

messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
messages = messages_ref.stream()

total = 0
missing_timestamp = 0
for msg in messages:
    data = msg.to_dict()
    total += 1
    if 'timestamp' not in data:
        missing_timestamp += 1
        print(f"Doc {msg.id} is missing timestamp!")

print(f"Total: {total}, Missing Timestamp: {missing_timestamp}")
