import firebase_admin
from firebase_admin import credentials, firestore
import json
import os

# Initialize Firebase
cred = credentials.Certificate('/Users/sandeep/VSCODE/LearnBot/wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

uid = "bP4LovmoafQjPFjE9vNj5yR03jf2"    # Target session
session_id = 'W6hpRLkEFsaHXs60TCKC'
user_id = 'C72eYp1WpBUPF3Fiz0zWogT9w5P2' # Found from app.py logs

print(f"Checking messages for User: {user_id}, Session: {session_id}...")

messages_ref = db.collection('users').document(user_id).collection('sessions').document(session_id).collection('messages')
docs = messages_ref.stream()

count = 0
for doc in docs:
    count += 1
    data = doc.to_dict()
    ts = data.get('timestamp')
    print(f"ID: {doc.id} | Sender: {data.get('sender')} | TS Type: {type(ts)} | TS Value: {ts}")

if count == 0:
    print("Found 0 messages.")
    session_doc = db.collection('users').document(user_id).collection('sessions').document(session_id).get()
    if not session_doc.exists:
        print("Session document does NOT exist!")
    else:
        print("Session document exists but has no messages collection.")
        print(f"Session title: {session_doc.to_dict().get('title', 'No Title')}")
else:
    # If messages were found, we might still want to check the session document
    session_doc = db.collection('users').document(user_id).collection('sessions').document(session_id).get()
    if session_doc.exists:
        print(f"Session document exists: {session_doc.to_dict().get('title', 'No Title')}")
    else:
        print("Session document does NOT exist!")
