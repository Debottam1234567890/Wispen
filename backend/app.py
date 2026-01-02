import os
import sys
import threading
from dotenv import load_dotenv

# Load environment variables from .env file BEFORE importing modules that need them
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context


import firebase_admin
from firebase_admin import credentials, auth, firestore, storage
from flask_cors import CORS
from datetime import datetime
import base64
import requests

# Ensure we can import from the parent directory
# Ensure we can import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import asyncio
try:
    from chatbot_enhanced import GroqChat, MurfTTS, EdgeTTS, BookshelfRAG
    from opensearch_client import OpenSearchManager
    # Add root to sys.path for importing generators
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root_path not in sys.path:
        sys.path.append(root_path)

    from flashcard_generator import FlashcardGenerator
    from quiz_generator import QuizGenerator
    from mindmap_agent import MindMapAgent
    from video_agent import video_agent
    from memory_engine import StudentMemoryEngine
except ImportError as e:
    # Fallback or silent fail if not found
    print(f"Warning: Could not import Chat modules: {e}")

try:
    from video_generation_service import VideoGeneratorService
    video_gen_service = None # Initialize later with db
except ImportError as e:
    print(f"Warning: Could not import VideoGeneratorService: {e}")

# Initialize OpenSearch
# Initialize OpenSearch
opensearch_manager = None
try:
    if os.getenv('OPENSEARCH_HOST'):
        opensearch_manager = OpenSearchManager()
        print("✅ Connected to OpenSearch")
    else:
        print("ℹ️ OPENSEARCH_HOST not set, skipping OpenSearch initialization")
except Exception as e:
    print(f"⚠️ OpenSearch connection failed (non-fatal): {e}")

# Explicit absolute path for static folder to avoid 404s
base_dir = os.path.dirname(os.path.abspath(__file__))
static_folder_path = os.path.join(os.path.dirname(base_dir), "wispen-ai-tutor", "dist")

app = Flask(__name__, static_folder=static_folder_path, static_url_path="/")
CORS(app)  # Enable CORS for frontend

# Configure Upload Folder
UPLOAD_FOLDER = os.path.join(base_dir, 'uploads')
print(f"DEBUG: UPLOAD_FOLDER is set to: {UPLOAD_FOLDER}", flush=True)
if not os.path.exists(UPLOAD_FOLDER):
    print(f"DEBUG: Creating {UPLOAD_FOLDER}", flush=True)
    os.makedirs(UPLOAD_FOLDER)


# Initialize Firebase Admin SDK
import json
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

if cred:
    try:
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'wispen-f4a94.firebasestorage.app'
        })
    except Exception as e:
        print(f"ERROR Initializing Firebase: {e}")
else:
    print("❌ CRITICAL: No Firebase Credentials found in ENV or Local paths")


# Initialize Firestore
db = firestore.client()
# Initialize Agents
mindmap_agent = MindMapAgent()
flashcard_generator = FlashcardGenerator()
quiz_generator = QuizGenerator()
memory_engine = StudentMemoryEngine(db)
# Initialize Storage Bucket
bucket = storage.bucket()

# Initialize Video Service with DB
if 'VideoGeneratorService' in globals():
    global video_gen_service
    try:
        video_gen_service = VideoGeneratorService(db)
        print("✅ VideoGeneratorService Initialized")
    except Exception as e:
        print(f"❌ VideoGeneratorService Init Failed: {e}")

@app.route('/')
def serve():
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    return app.send_static_file('index.html')

@app.route('/home', methods=['GET'])
def home():
    return jsonify({"message": "Welcome to the Wispen AI Tutor API!"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

def get_user_from_token():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    token = auth_header.split(' ')[1]
    try:
        decoded_token = auth.verify_id_token(token)
        print(f"DEBUG: Authenticated user: {decoded_token.get('uid')}")
        return decoded_token
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

@app.route('/auth/google', methods=['POST'])
def verify_google_token():
    try:
        data = request.json
        id_token = data.get('idToken')

        if not id_token:
            return jsonify({"error": "No ID token provided"}), 400

        # Verify the ID token
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
        email = decoded_token.get('email')
        name = decoded_token.get('name')
        
        return jsonify({
            "message": "Authentication successful",
            "user": {
                "uid": uid,
                "email": email,
                "name": name
            }
        }), 200

    except Exception as e:
        print(f"Auth error: {e}")
        return jsonify({"error": "Invalid token"}), 401
    
# --- CALENDAR ENDPOINTS ---
@app.route('/calendar', methods=['GET', 'POST'])
def handle_calendar():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    # Use 'calendar' collection
    col_ref = db.collection('users').document(uid).collection('calendar')

    if request.method == 'GET':
        try:
            docs = col_ref.stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            if not data.get('subject') or not data.get('date'):
                return jsonify({"error": "Missing required fields"}), 400
            
            update_time, doc_ref = col_ref.add(data)
            data['id'] = doc_ref.id
            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/calendar/<item_id>', methods=['DELETE', 'PATCH'])
def handle_single_calendar_item(item_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    doc_ref = db.collection('users').document(uid).collection('calendar').document(item_id)

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            return jsonify({"message": "Item deleted"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PATCH':
        try:
            data = request.json
            doc_ref.update(data)
            return jsonify({"message": "Item updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# --- JOURNAL ENDPOINTS ---
@app.route('/journal', methods=['GET', 'POST'])
def handle_journal():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    # Use 'journal' collection
    col_ref = db.collection('users').document(uid).collection('journal')

    if request.method == 'GET':
        try:
            docs = col_ref.stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            # Basic validation for journal
            if not data.get('subject') or not data.get('date'):
                return jsonify({"error": "Missing required fields"}), 400
            
            update_time, doc_ref = col_ref.add(data)
            data['id'] = doc_ref.id
            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/journal/<item_id>', methods=['DELETE', 'PATCH'])
def handle_single_journal_item(item_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    doc_ref = db.collection('users').document(uid).collection('journal').document(item_id)

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            return jsonify({"message": "Item deleted"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PATCH':
        try:
            data = request.json
            doc_ref.update(data)
            return jsonify({"message": "Item updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --- STATS ENDPOINTS ---
@app.route('/stats/heartbeat', methods=['POST'])
def heartbeat():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    stats_ref = db.collection('users').document(uid).collection('stats').document('daily')
    
    try:
        doc = stats_ref.get()
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        if doc.exists:
            data = doc.to_dict()
            last_date_str = data.get('last_activity_date', '')
            current_streak = data.get('streak', 1)
            time_spent = data.get('time_spent_today', 0)
            
            # Reset time if new day
            if last_date_str != today_str:
                time_spent = 0
                
                # Streak Logic
                last_date = datetime.strptime(last_date_str, '%Y-%m-%d') if last_date_str else None
                if last_date:
                    delta = (now - last_date).days
                    if delta == 1:
                        current_streak += 1
                    elif delta > 1:
                        current_streak = 1
                    # If delta == 0 (same day), do nothing to streak
            
            # Increment time (assuming ~1 min pulse)
            time_spent += 1
            
            stats_ref.set({
                'streak': current_streak,
                'time_spent_today': time_spent,
                'last_activity_date': today_str,
                'xp': data.get('xp', 0) + 1  # Bonus: 1 XP per minute
            }, merge=True)
            
            return jsonify({
                "streak": current_streak, 
                "time_spent_today": time_spent,
                "xp": data.get('xp', 0) + 1
            }), 200
        else:
            # Initialize stats
            initial_stats = {
                'streak': 1,
                'time_spent_today': 1,
                'last_activity_date': today_str,
                'xp': 10 # Initial XP bonus
            }
            stats_ref.set(initial_stats)
            return jsonify(initial_stats), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    stats_ref = db.collection('users').document(uid).collection('stats').document('daily')
    
    try:
        doc = stats_ref.get()
        if doc.exists:
            return jsonify(doc.to_dict()), 200
        else:
            return jsonify({"streak": 0, "time_spent_today": 0, "xp": 0}), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# --- STUDENT MEMORY ENDPOINTS ---
@app.route('/users/memory', methods=['GET', 'PATCH'])
def handle_user_memory():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    memory_ref = db.collection('users').document(uid).collection('memory').document('profile')
    
    if request.method == 'GET':
        try:
            doc = memory_ref.get()
            if doc.exists:
                return jsonify(doc.to_dict()), 200
            else:
                # Return default memory structure
                default_memory = {
                    "learning_style": "balanced",
                    "preferred_difficulty": "intermediate",
                    "strengths": [],
                    "weaknesses": [],
                    "personality_notes": "",
                    "last_updated": None
                }
                return jsonify(default_memory), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    elif request.method == 'PATCH':
        try:
            data = request.json
            # Add timestamp
            data['last_updated'] = datetime.now().isoformat()
            memory_ref.set(data, merge=True)
            return jsonify({"message": "Memory updated", **data}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --- SESSION ENDPOINTS ---
@app.route('/sessions', methods=['GET', 'POST'])
def handle_sessions():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    col_ref = db.collection('users').document(uid).collection('sessions')

    if request.method == 'GET':
        try:
            # Order by date desc
            docs = col_ref.order_by('date', direction=firestore.Query.DESCENDING).limit(5).stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            return jsonify(items), 200
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            if not data.get('subject'):
                return jsonify({"error": "Missing subject"}), 400
            
            data['date'] = datetime.now().isoformat() # Server-side timestamp for consistency
            if 'duration' not in data:
                data['duration'] = '0m'
            
            update_time, doc_ref = col_ref.add(data)
            data['id'] = doc_ref.id
            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/sessions/<session_id>', methods=['GET', 'DELETE', 'PATCH'])
def handle_session_item(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    doc_ref = db.collection('users').document(uid).collection('sessions').document(session_id)

    if request.method == 'GET':
        try:
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                data['id'] = doc.id
                return jsonify(data), 200
            else:
                return jsonify({"error": "Session not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            return jsonify({"message": "Session deleted"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PATCH':
        try:
            data = request.json
            doc_ref.update(data)
            return jsonify({"message": "Session updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --- BOOKSHELF ENDPOINTS ---
@app.route('/bookshelf', methods=['GET', 'POST'])
def handle_bookshelf():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    col_ref = db.collection('users').document(uid).collection('bookshelf')

    if request.method == 'GET':
        try:
            docs = list(col_ref.stream())
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            # Data can include: content (Base64), pages (actual count), stickyNotes [], highlights []
            update_time, doc_ref = col_ref.add(data)
            data['id'] = doc_ref.id
            
            # --- START OPENSEARCH INDEXING (BACKGROUND) ---
            if opensearch_manager:
                thread = threading.Thread(
                    target=background_index_task,
                    args=(uid, data, doc_ref.id, opensearch_manager)
                )
                thread.daemon = True
                thread.start()
                print(f"🚀 Started background indexing for {doc_ref.id}")
            # --- END OPENSEARCH INDEXING (BACKGROUND) ---

            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500


# --- UPLOAD PROXY ENDPOINT (LOCAL STORAGE) ---
@app.route('/upload', methods=['POST'])
def handle_upload():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    uid = user['uid']
    try:
        # Create a safe filename
        timestamp = int(datetime.now().timestamp() * 1000)
        # Sanitize filename (basic)
        safe_filename = "".join([c for c in file.filename if c.isalpha() or c.isdigit() or c in '._-']).strip()
        filename = f"{timestamp}_{safe_filename}"
        
        # User specific folder inside uploads (optional, but good for organization)
        # For simplicity, we'll put everything in uploads/, or create a subfolder
        # Let's keep it simple: all in uploads/
        
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        
        # Generate Local URL
        # Assuming backend is running on localhost:5000
        # You might want to make the base URL configurable or derived from request.host_url
        file_url = f"{request.host_url}uploads/{filename}"
        
        return jsonify({"url": file_url}), 200
    
    except Exception as e:
        print(f"Upload error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/uploads/<path:filename>')
def serve_upload(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/videos/<filename>')
def serve_video(filename):
    """Serve video files with proper MIME type for HTML5 playback."""
    videos_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'videos')
    os.makedirs(videos_dir, exist_ok=True)
    return send_from_directory(videos_dir, filename, mimetype='video/mp4')


@app.route('/bookshelf/<item_id>', methods=['DELETE', 'PATCH'])
def handle_bookshelf_item(item_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    doc_ref = db.collection('users').document(uid).collection('bookshelf').document(item_id)

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            
            # Remove from OpenSearch
            if opensearch_manager:
                opensearch_manager.delete_document(item_id)
                
            return jsonify({"message": "Deleted"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PATCH':
        try:
            data = request.json
            doc_ref.update(data)
            
            # --- START OPENSEARCH SYNC ---
            if opensearch_manager:
                try:
                    # Fetch current document to get full state
                    doc = doc_ref.get()
                    if doc.exists:
                        full_data = doc.to_dict()
                        # Update index with latest metadata (including highlights/notes)
                        # We want these to be searchable too
                        doc_body = {
                            "title": full_data.get('title', 'Untitled'),
                            "file_type": full_data.get('fileType', 'unknown'),
                            "storage_url": full_data.get('storageUrl', ''),
                            "user_id": uid,
                            "timestamp": datetime.now().isoformat(),
                            "sticky_notes": [n.get('content', '') for n in full_data.get('stickyNotes', [])],
                            "highlights": [h.get('text', '') for h in full_data.get('highlights', [])],
                            "explanations": [h.get('explanation', '') for h in full_data.get('highlights', [])]
                        }
                        # Note: We don't overwrite 'content' here to avoid re-extracting it unnecessarily
                        # opensearch_manager.update_document could be better if it exists, but index_document often handles upsert
                        opensearch_manager.index_document(item_id, doc_body)
                        print(f"✅ Synced document {item_id} annotations to OpenSearch")
                except Exception as sync_err:
                    print(f"❌ OpenSearch Sync error: {sync_err}")
            # --- END OPENSEARCH SYNC ---
            
            return jsonify({"message": "Updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --- SESSION SCOPED BOOKSHELF ENDPOINTS ---

@app.route('/sessions/<session_id>/bookshelf', methods=['GET', 'POST'])
def handle_session_bookshelf(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']

    # New collection path: users/{uid}/sessions/{session_id}/bookshelf
    col_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('bookshelf')

    if request.method == 'GET':
        try:
            docs = list(col_ref.stream())
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            update_time, doc_ref = col_ref.add(data)
            data['id'] = doc_ref.id
            
            # --- START OPENSEARCH INDEXING (BACKGROUND) ---
            if opensearch_manager:
                thread = threading.Thread(
                    target=background_index_task,
                    args=(uid, data, doc_ref.id, opensearch_manager)
                )
                thread.daemon = True
                thread.start()
                print(f"🚀 Started background indexing for {doc_ref.id} (Session: {session_id})")
            # --- END OPENSEARCH INDEXING (BACKGROUND) ---

            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/sessions/<session_id>/bookshelf/<item_id>', methods=['DELETE', 'PATCH'])
def handle_session_bookshelf_item(session_id, item_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    doc_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('bookshelf').document(item_id)

    if request.method == 'DELETE':
        try:
            doc_ref.delete()
            # Remove from OpenSearch (if indexed by item_id)
            if opensearch_manager:
                opensearch_manager.delete_document(item_id)
            return jsonify({"message": "Deleted"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'PATCH':
        try:
            data = request.json
            doc_ref.update(data)
            # Sync to OpenSearch
            if opensearch_manager:
                try:
                    # Fetch current document to get full state
                    doc = doc_ref.get()
                    if doc.exists:
                        full_data = doc.to_dict()
                        # Update index with latest metadata
                        doc_body = {
                            "title": full_data.get('title', 'Untitled'),
                            "file_type": full_data.get('fileType', 'unknown'),
                            "storage_url": full_data.get('storageUrl', ''),
                            "user_id": uid,
                            "timestamp": datetime.now().isoformat(),
                            "sticky_notes": [n.get('content', '') for n in full_data.get('stickyNotes', [])],
                            "highlights": [h.get('text', '') for h in full_data.get('highlights', [])],
                            "explanations": [h.get('explanation', '') for h in full_data.get('highlights', [])]
                        }
                        opensearch_manager.index_document(item_id, doc_body)
                        print(f"✅ Synced document {item_id} annotations to OpenSearch")
                except Exception as sync_err:
                    print(f"❌ OpenSearch Sync error: {sync_err}")

            return jsonify({"message": "Updated"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/explain', methods=['POST'])
def explain_text():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    try:
        data = request.json
        text_to_explain = data.get('text')
        book_title = data.get('bookTitle', 'this book')
        book_id = data.get('bookId')
        
        if not text_to_explain:
            return jsonify({"error": "No text provided"}), 400

        # --- GATHER CONTEXT VIA RAG ---
        context_str = ""
        if book_id:
            try:
                # Fetch only this book's metadata for focused RAG
                book_doc = db.collection('users').document(uid).collection('bookshelf').document(book_id).get()
                if book_doc.exists:
                    book_item = book_doc.to_dict()
                    book_item['id'] = book_doc.id
                    
                    # Search within this book specifically
                    rag_results = BookshelfRAG.search([book_item], text_to_explain, top_k=5, user_id=uid, opensearch_client=opensearch_manager)
                    
                    if rag_results:
                        context_str = "\n[Additional Context from Book]:\n"
                        for res in rag_results:
                            context_str += f"...{res['content']}...\n"
            except Exception as rag_err:
                print(f"RAG Explanation Error: {rag_err}")

        # --- REFINE PROMPT FOR ULTRA-CONCISENESS ---
        prompt = f"""
        You are Wispen, a friendly AI tutor. Explain the text below from "{book_title}" to a student.
        
        TEXT TO EXPLAIN: "{text_to_explain}"
        {context_str}
        
        INSTRUCTIONS:
        1. Be **ULTRA-CONCISE**. 1-3 short sentences MAX. Think "quick bite" or "flashcard" style.
        2. Use very simple language.
        3. Explain naturally. Do not cut off in the middle of a sentence.
        4. Focus on the core meaning.
        5. Use **LaTeX math syntax** (e.g., $x^2$ or $\frac{{a}}{{b}}$) for any mathematical formulas.
        6. Format using markdown (bolding for key terms).
        """
        
        try:
            explanation = GroqChat.chat(prompt)
        except Exception as groq_err:
            print(f"❌ Groq Error: {groq_err}")
            return jsonify({"error": f"AI Generation Failed: {str(groq_err)}"}), 500
        
        # Ensure it doesn't end abruptly
        explanation = explanation.strip()
        
        return jsonify({"explanation": explanation}), 200
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Explain Critical Error: {e}")
        print(error_trace)
        return jsonify({"error": str(e), "trace": error_trace}), 500

@app.route('/mindmap', methods=['POST'])
def generate_mindmap():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    prompt = data.get('prompt')
    session_id = data.get('sessionId')

    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400
    
    try:
        # Use sync agent methods
        result = mindmap_agent.generate_mindmap(prompt, user['uid'], session_id)
        
        # PERSISTENCE: Save to Firestore immediately
        if session_id:
             # Add timestamps
            result['timestamp'] = datetime.now().isoformat()
            result['title'] = prompt
            
            doc_ref = db.collection('users').document(user['uid']).collection('sessions').document(session_id).collection('mindmaps').add(result)
            result['id'] = doc_ref[1].id
            # Legacy global save (optional, or just return without ID if no session)
            pass

        return jsonify(result), 200

    except Exception as e:
        import traceback
        print(f"Mindmap Generation Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/generate_video_mp4', methods=['POST'])
def generate_video_mp4():
    """
    Endpoint to trigger background MP4 video generation.
    """
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    # user = {"uid": "test_debugger"}
    # user = {"uid": "test_video_user"}

    data = request.json
    prompt = data.get('prompt') or data.get('topic')
    session_id = data.get('sessionId')

    if not prompt:
        return jsonify({"error": "Prompt/Topic is required"}), 400

    if not video_gen_service:
        return jsonify({"error": "Video service not available"}), 503

    # Start background thread
    thread = threading.Thread(
        target=video_gen_service.generate_video_background_task,
        args=(prompt, user['uid'], session_id)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Video generation started", "status": "processing"}), 202

@app.route('/generate_video_script', methods=['POST'])
def generate_video_script():
    """
    Endpoint to generate video script only (no images).
    Used for frontend Puter-based image generation flow.
    
    Returns JSON with scenes array containing prompts for image generation.
    """
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    topic = data.get('topic') or data.get('prompt')

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    if not video_gen_service:
        return jsonify({"error": "Video service not available"}), 503

    try:
        # Generate script using LLM
        scenes = video_gen_service.generate_script(topic)
        return jsonify({
            "success": True,
            "topic": topic,
            "scenes": scenes
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/assemble_video', methods=['POST'])
def assemble_video():
    """
    Endpoint to assemble video from pre-generated images (from frontend Puter generation).
    This enables FREE UNLIMITED image generation via Puter.js in the browser.
    
    Expected JSON:
    {
        "scenes": [{"title": "...", "narration": "..."}],
        "imageUrls": ["https://firebase.../image1.png", ...],
        "sessionId": "optional_session_id"
    }
    """
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    scenes = data.get('scenes', [])
    image_urls = data.get('imageUrls', [])
    session_id = data.get('sessionId')

    if not scenes:
        return jsonify({"error": "Scenes are required"}), 400

    if not video_gen_service:
        return jsonify({"error": "Video service not available"}), 503

    # Start background thread for assembly
    thread = threading.Thread(
        target=video_gen_service.assemble_video_from_urls,
        args=(scenes, image_urls, user['uid'], session_id)
    )
    thread.daemon = True
    thread.start()

    return jsonify({"message": "Video assembly started", "status": "assembling"}), 202


@app.route('/mindmap/expand', methods=['POST'])
def expand_mindmap_node():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    node_id = data.get('nodeId')
    node_label = data.get('nodeLabel')
    session_id = data.get('sessionId')
    
    mindmap_id = data.get('mindmapId')

    if not node_id or not node_label:
        return jsonify({"error": "Node ID and Label are required"}), 400
    
    print(f"Backend: Mindmap expansion requested for node: {node_id}, Mindmap: {mindmap_id}, Session: {session_id}")
    try:
        children = mindmap_agent.expand_node(node_id, node_label, user['uid'], session_id)
        print(f"Backend: Agent generated {len(children) if children else 0} children")
        
        # PERSISTENCE: Update Firestore if valid mindmapId and sessionId are present
        if session_id and mindmap_id and children:
            doc_ref = db.collection('users').document(user['uid']).collection('sessions').document(session_id).collection('mindmaps').document(mindmap_id)
            
            doc = doc_ref.get()
            if doc.exists:
                current_data = doc.to_dict()
                nodes_map = current_data.get('nodes', {})
                print(f"Backend: Existing mindmap nodes count: {len(nodes_map)}")
                
                # 1. Update Parent
                if node_id in nodes_map:
                    # Append new children IDs
                    new_child_ids = [c['id'] for c in children]
                    existing_children = nodes_map[node_id].get('children', [])
                    # Avoid duplicates
                    updated_children = list(set(existing_children + new_child_ids))
                    nodes_map[node_id]['children'] = updated_children
                    nodes_map[node_id]['hasMore'] = False
                    print(f"Backend: Updated parent {node_id} with {len(new_child_ids)} new children")
                else:
                    print(f"Backend: WARNING: Parent node {node_id} NOT FOUND in nodes_map!")
                
                # 2. Add New Nodes
                for child in children:
                     nodes_map[child['id']] = child
                     # Ensure new nodes have children=[]
                     if 'children' not in nodes_map[child['id']]:
                         nodes_map[child['id']]['children'] = []
                
                # Save back
                doc_ref.update({'nodes': nodes_map})
                print(f"Backend: Firestore updated successfully for mindmap {mindmap_id}")
            else:
                print(f"Backend: WARNING: Mindmap document {mindmap_id} not found in Firestore!")

        return jsonify({"children": children}), 200
    except Exception as e:
        import traceback
        print(f"Mindmap Expansion Error: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500



# --- SESSION SCOPED MINDMAP ENDPOINTS ---
@app.route('/sessions/<session_id>/mindmaps', methods=['GET', 'POST'])
def handle_session_mindmaps(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    # New collection path: users/{uid}/sessions/{session_id}/mindmaps
    col_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('mindmaps')

    if request.method == 'GET':
        try:
            # Fetch user's mindmaps and sort in-memory to avoid index issues
            docs = col_ref.stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            
            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            if not data.get('nodes') or not data.get('root_id'):
                return jsonify({"error": "Missing mindmap data"}), 400
            
            data['timestamp'] = datetime.now().isoformat()
            
            # If an ID is provided, update existing document, else create new
            doc_id = data.get('id')
            if doc_id:
                doc_ref = col_ref.document(doc_id)
                doc_ref.set(data, merge=True)
            else:
                update_time, doc_ref = col_ref.add(data)
            
            data['id'] = doc_ref.id
            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

# --- SESSION SCOPED FLASHCARD ENDPOINTS ---
@app.route('/sessions/<session_id>/mindmaps/<mid>', methods=['GET'])
def get_single_session_mindmap(session_id, mid):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    try:
        doc = db.collection('users').document(uid).collection('sessions').document(session_id).collection('mindmaps').document(mid).get()
        if not doc.exists:
            return jsonify({"error": "Mindmap not found"}), 404
        
        data = doc.to_dict()
        data['id'] = doc.id
        return jsonify(data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sessions/<session_id>/flashcards', methods=['GET', 'POST'])
def handle_session_flashcards(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    # New collection path: users/{uid}/sessions/{session_id}/flashcards
    col_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('flashcards')

    if request.method == 'GET':
        try:
            # Fetch user's flashcards and sort in-memory to avoid index issues
            docs = col_ref.stream()
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                items.append(data)
            
            # Sort by timestamp descending
            items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return jsonify(items), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        try:
            data = request.json
            if 'cards' not in data or not data.get('title'):
                return jsonify({"error": "Missing flashcard data (cards or title)"}), 400
            
            data['timestamp'] = datetime.now().isoformat()
            
            doc_id = data.get('id')
            if doc_id:
                doc_ref = col_ref.document(doc_id)
                doc_ref.set(data, merge=True)
            else:
                update_time, doc_ref = col_ref.add(data)
            
            data['id'] = doc_ref.id
            return jsonify(data), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

def background_flashcard_task(uid, topic, content, session_id):
    """Background task for generating flashcards and notifying the user."""
    try:
        # 1. RETRIEVE: Search bookshelf for context (RAG)
        rag_context = ""
        # Get session-scoped bookshelf items if session_id is provided
        if session_id:
            docs = db.collection('users').document(uid).collection('sessions').document(session_id).collection('bookshelf').stream()
        else:
             docs = []

        bookshelf_items = []
        for doc in docs:
            item = doc.to_dict()
            item['id'] = doc.id
            bookshelf_items.append(item)
        
        # Search using BookshelfRAG
        if bookshelf_items:
            search_results = BookshelfRAG.search(bookshelf_items, topic, user_id=uid)
            context_pieces = [r.get('content', '') for r in search_results]
            if context_pieces:
                rag_context = "\n\n".join(context_pieces)
        
        # 2. COMBINE: Use topic, content, and RAG context directly for generation
        content_for_generator = f"""Topic: {topic}
Original Content: {content or 'N/A'}

Additional Book Context:
{rag_context if rag_context else 'No specific book context found.'}

Please generate comprehensive flashcards covering this topic using the provided context and your internal expertise."""

        # 3. GENERATE
        print(f"DEBUG APP: Generating cards for topic='{topic}'. Content Len: {len(content_for_generator)}")
        print(f"DEBUG APP: Generator instance: {flashcard_generator}")
        
        flashcard_set = flashcard_generator.generate(
            content=content_for_generator,
            title=topic or "Generated Flashcards",
            difficulty="mixed"
        )
        print(f"DEBUG APP: Generated {len(flashcard_set.cards)} cards from generator.")
        
        # 4. SAVE AND NOTIFY IF SUCCESSFUL
        if flashcard_set.cards:
            flashcard_data = flashcard_set.to_dict()
            flashcard_data['timestamp'] = datetime.now().isoformat()
            
            # Save to Session Scope if available, else Global (legacy fallback)
            if session_id:
                doc_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('flashcards').add(flashcard_data)
            else:
                doc_ref = db.collection('users').document(uid).collection('flashcards').add(flashcard_data)

            doc_id = doc_ref[1].id if isinstance(doc_ref, tuple) else doc_ref.id
            
            if session_id:
                messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
                notification_msg = {
                    "role": "assistant",
                    "content": f"✅ Your flashcards for **{topic}** are ready! You can view them in the 'View All Output' section or open them directly.",
                    "type": "notification",
                    "timestamp": datetime.now().isoformat(),
                    "action": {
                        "type": "open_flashcards",
                        "id": doc_id,
                        "title": topic
                    }
                }
                messages_ref.add(notification_msg)
                print(f"✅ Notified user {uid} about flashcards: {doc_id}")
        else:
            print(f"⚠️ No flashcards generated for {topic} (provider errors/rate limits).")
            if session_id:
                messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
                messages_ref.add({
                    "sender": "wispen",
                    "content": f"⚠️ I'm sorry, I couldn't generate flashcards for **{topic}** right now because my AI providers are hitting rate limits. Please try again in a few minutes!",
                    "type": "text",
                    "timestamp": datetime.now().isoformat()
                })

    except Exception as e:
        print(f"❌ Background flashcard error: {e}")
        if session_id:
            try:
                messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
                messages_ref.add({
                    "sender": "wispen",
                    "content": f"⚠️ Sorry, I ran into an error while generating flashcards for **{topic}**: {str(e)}",
                    "type": "text",
                    "timestamp": datetime.now().isoformat()
                })
            except: pass

@app.route('/flashcards', methods=['GET'])
def handle_global_flashcards():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    try:
        # Global collection: users/{uid}/flashcards
        col_ref = db.collection('users').document(uid).collection('flashcards')
        docs = col_ref.stream()
        items = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            items.append(data)
        
        # Sort by timestamp descending
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/flashcards/generate', methods=['POST'])
def generate_flashcards_api():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    topic = data.get('topic')
    content = data.get('content') # Optional override content
    session_id = data.get('sessionId') # Optional session for notifications
    
    if not topic and not content:
        return jsonify({"error": "Topic or content is required"}), 400
    
    uid = user['uid']
    
    # Start background thread
    thread = threading.Thread(
        target=background_flashcard_task,
        args=(uid, topic, content, session_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Generation started in the background. You'll be notified in the chat when it's ready!",
        "topic": topic,
        "status": "accepted"
    }), 202
def background_quiz_task(uid, topic, content, session_id):
    """Background task for generating quizzes and notifying the user."""
    print(f"🛠️ Starting background quiz task for user {uid}, topic: {topic}, session: {session_id}")
    valid_session = session_id and session_id != "undefined" and session_id != "null"
    try:
        # 1. RETRIEVE: Search bookshelf for context (RAG)
        rag_context = ""
        if valid_session:
            docs = db.collection('users').document(uid).collection('sessions').document(session_id).collection('bookshelf').stream()
            bookshelf_items = []
            for doc in docs:
                item = doc.to_dict()
                bookshelf_items.append(item.get('content', ''))
            
            if bookshelf_items:
                rag_context = "\n\n".join(bookshelf_items[:15]) # Take top 15 chunks
                print(f"📚 Aggregated {len(bookshelf_items)} chunks for context.")
        
        # 2. COMBINE: Fetch memory profile for personalization
        memory_doc = db.collection('users').document(uid).collection('memory').document('profile').get()
        student_memory = memory_doc.to_dict() if memory_doc.exists else {}
        
        content_for_generator = {
            "topic": topic,
            "content": content or 'N/A',
            "rag_context": rag_context,
            "memory": student_memory
        }

        # 3. GENERATE
        print(f"🤖 Calling personalized quiz generator for '{topic}'...")
        quiz_set = quiz_generator.generate(
            content=content_for_generator,
            topic=topic or "Generated Quiz",
            num_questions=10
        )
        print(f"✅ Generated {len(quiz_set.questions)} questions.")
        
        # 4. SAVE AND NOTIFY
        if quiz_set.questions:
            quiz_data = quiz_set.to_dict()
            quiz_data['timestamp'] = datetime.now().isoformat()
            
            if valid_session:
                print(f"💾 Saving quiz to session {session_id}...")
                doc_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('quizzes').add(quiz_data)
            else:
                print(f"💾 Saving quiz to global collection...")
                doc_ref = db.collection('users').document(uid).collection('quizzes').add(quiz_data)

            doc_id = doc_ref[1].id if isinstance(doc_ref, tuple) else doc_ref.id
            print(f"✨ Quiz saved with ID: {doc_id}")
            
            if valid_session:
                messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
                notification_msg = {
                    "role": "assistant",
                    "content": f"✅ Your quiz for **{topic}** is ready! It has {len(quiz_set.questions)} questions. Ready to test yourself?",
                    "type": "notification",
                    "timestamp": datetime.now().isoformat(),
                    "action": {
                        "type": "open_quiz",
                        "id": doc_id,
                        "title": topic
                    }
                }
                messages_ref.add(notification_msg)
                print(f"✅ Notified user {uid} about quiz: {doc_id}")
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Error in background quiz task: {e}")
        print(error_trace)
        if valid_session:
            try:
                messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')
                messages_ref.add({
                    "role": "assistant",
                    "content": f"⚠️ Sorry, I ran into an error while generating your quiz: {str(e)}",
                    "type": "text",
                    "timestamp": datetime.now().isoformat()
                })
            except: pass

@app.route('/quizzes/generate', methods=['POST'])
def generate_quizzes_api():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    topic = data.get('topic')
    content = data.get('content')
    session_id = data.get('sessionId')
    
    if not topic and not content:
        return jsonify({"error": "Topic or content is required"}), 400
    
    uid = user['uid']
    
    # Start background thread
    thread = threading.Thread(
        target=background_quiz_task,
        args=(uid, topic, content, session_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Quiz generation started in the background. You'll be notified soon!",
        "topic": topic,
        "status": "accepted"
    }), 202

@app.route('/sessions/<session_id>/quizzes', methods=['GET'])
def handle_session_quizzes(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    col_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('quizzes')

    try:
        docs = col_ref.stream()
        items = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            items.append(data)
        
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/quizzes', methods=['GET'])
def handle_global_quizzes():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    try:
        col_ref = db.collection('users').document(uid).collection('quizzes')
        docs = col_ref.stream()
        items = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            items.append(data)
        
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SESSION MESSAGES ENDPOINTS ---
@app.route('/sessions/<session_id>/videos', methods=['GET'])
def handle_session_videos(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    # Videos are stored in their own 'videos' collection
    print(f"DEBUG: Querying videos for users/{uid}/sessions/{session_id}/videos")
    col_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('videos')

    try:
        # Fetch directly from videos collection
        docs = col_ref.stream()
        items = []
        count = 0
        for doc in docs:
            count += 1
            data = doc.to_dict()
            data['id'] = doc.id
            items.append(data)
        
        items.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return jsonify(items), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- SESSION MESSAGES ENDPOINTS ---
@app.route('/sessions/<session_id>/messages', methods=['GET', 'POST'])
def handle_session_messages(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    messages_ref = db.collection('users').document(uid).collection('sessions').document(session_id).collection('messages')

    if request.method == 'GET':
        print(f"DEBUG: Processing GET /messages for session {session_id}")
        try:
            docs = list(messages_ref.order_by('timestamp', direction=firestore.Query.ASCENDING).stream())
            print(f"DEBUG: Found {len(docs)} messages in Firestore for session {session_id}")
            items = []
            for doc in docs:
                data = doc.to_dict()
                data['id'] = doc.id
                print(f"DEBUG: Msg {doc.id} | TS: {data.get('timestamp')} | Sender: {data.get('sender')}")
                items.append(data)
            return jsonify(items), 200
        except Exception as e:
            print(f"DEBUG: Error fetching messages: {e}")
            return jsonify({"error": str(e)}), 500

    elif request.method == 'POST':
        print(f"DEBUG: Processing POST /messages for session {session_id}")
        try:
            data = request.get_json(silent=True)
            if not data or not data.get('sender') or not data.get('content'):
                print(f"DEBUG: Invalid payload: {data}")
                return jsonify({"error": "Missing sender or content"}), 400
            
            # Use client-provided ID if available to prevent duplication
            client_msg_id = data.get('id')
            ai_msg_id = data.get('aiMessageId')

            data['timestamp'] = datetime.now().isoformat()
            data['sender'] = 'user' # Ensure explicit
            data['type'] = 'text' if not data.get('type') else data.get('type')
            
            # Remove client-specific IDs before saving to Firestore
            msg_to_save = data.copy()
            if 'aiMessageId' in msg_to_save: del msg_to_save['aiMessageId']
            if 'id' in msg_to_save: del msg_to_save['id']

            try:
                if client_msg_id:
                    print(f"DEBUG: Saving user message with ID {client_msg_id}")
                    messages_ref.document(client_msg_id).set(msg_to_save)
                else:
                    print(f"DEBUG: Adding user message with auto-ID")
                    messages_ref.add(msg_to_save)
                print("DEBUG: User message saved successfully.")
            except Exception as e:
                print(f"DEBUG: CRITICAL ERROR saving user message: {e}")
                raise e
            
            # TRIGGER PERSONALIZATION ENGINE
            print(f"DEBUG: Triggering personalization update for user {uid}")
            memory_engine.update_async(uid)
            
            # Context Preparation
            rag_context = ""
            try:
                if BookshelfRAG:
                    print(f"DEBUG: Calling RAG Search for: {data['content'][:50]}...")
                    # CORRECT ORDER: (bookshelf_items, query, user_id)
                    # We pass [] for bookshelf_items to use global/OpenSearch search
                    rag_context = BookshelfRAG.search([], data['content'], user_id=uid)
                    print(f"DEBUG: RAG search complete. Context length: {len(rag_context)}")
            except Exception as e:
                print(f"DEBUG: RAG Error: {e}")

            # Memory & History Context
            student_memory = {}
            conversation_history = []
            try:
                memory_ref = db.collection('users').document(uid).collection('student_profile').document('memory')
                memory_doc = memory_ref.get()
                student_memory = memory_doc.to_dict() if memory_doc.exists else {}
                
                # Fetch history for AI context
                history_docs = messages_ref.order_by('timestamp', direction=firestore.Query.ASCENDING).stream()
                for doc in history_docs:
                    if doc.id == client_msg_id: continue
                    m_data = doc.to_dict()
                    role = 'assistant' if m_data.get('sender') in ['wispen', 'ai'] else 'user'
                    conversation_history.append({"role": role, "content": m_data.get('content', '')})
                
                conversation_history = conversation_history[-15:]
            except Exception as e:
                print(f"DEBUG: Context error: {e}")

            detailed_feedback = student_memory.get('detailed_feedback', '')
            
            enriched_message = f"""
Student Profile Context:
{detailed_feedback}

RAG Search Context:
{rag_context}

User's Input:
{data['content']}
"""

            # Stream Response
            def generate():
                try:
                    full_content = ""
                    print(f"DEBUG: Starting AI stream for message: {data['content'][:50]}...")
                    
                    for chunk in GroqChat.chat_stream(enriched_message, conversation_history):
                        full_content += chunk
                        yield chunk
                    
                    # Save AI Response
                    ai_message = {
                        "sender": "wispen", 
                        "content": full_content,
                        "type": "text",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    try:
                        if ai_msg_id:
                            print(f"DEBUG: Explicitly saving AI response to document {ai_msg_id}")
                            messages_ref.document(ai_msg_id).set(ai_message)
                        else:
                            print(f"DEBUG: Adding AI response with auto-ID")
                            messages_ref.add(ai_message)
                        print("DEBUG: AI response saved successfully.")
                    except Exception as e:
                        print(f"DEBUG: ERROR saving AI response: {e}")
                    
                except Exception as e:
                    print(f"Streaming Error: {e}")
                    yield f"\n[Error: {str(e)}]"

            return Response(stream_with_context(generate()), mimetype='text/plain')

        except Exception as e:
            print(f"DEBUG: EXCEPTION in handle_session_messages: {e}")
            return jsonify({"error": str(e)}), 500

    
@app.route('/tts', methods=['POST'])
def tts_endpoint():
    """Generate speech from text using Groq TTS"""
    try:
        data = request.json
        text = data.get('text')
        print(f"DEBUG: TTS Request for text: {text[:50]}...", flush=True)
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
            
        # Call Edge TTS (Streamed for Speed)
        return Response(stream_with_context(EdgeTTS.generate_speech_stream(text)), mimetype="audio/mpeg")

        
    except Exception as e:
        print(f"TTS Error: {e}")
        return jsonify({'error': str(e)}), 500

def background_index_task(uid, data, doc_id, opensearch_manager):
    try:
        # We need to extract text if it's not already in 'content' in a searchable way
        # If 'content' is base64 (for PDF), we need to extract it.
        # Re-use BookshelfRAG extraction logic if possible, or simple decoding
        
        text_content = ""
        # If it's a text file uploaded as raw text
        if data.get('fileType') == 'text' and data.get('content'):
                try:
                    text_content = base64.b64decode(data['content']).decode('utf-8')
                except:
                    text_content = data.get('content', '') # Maybe it wasn't base64
        
        # If it's a PDF, we might need to rely on the background worker or do it here.
        # For now, let's assume the client might send extracted text OR we extract it here.
        # But BookshelfRAG has the extraction logic.
            
        if not text_content and data.get('storageUrl'):
                # Trigger async extraction/indexing could be better, but for now let's try to get what we can
                # This might point to the localized file path if we just uploaded it
                pass

        # IMPORTANT: In the /upload Flow (BookshelfNebula.tsx), we are NOT sending the full content in the JSON 
        # for the /bookshelf POST. We are sending metadata.
        # The file was uploaded to /upload (local) or Storage.
        
        # So we need to fetch the file content to index it.
        file_path = data.get('filePath') # This is often the URL
        
        # If we have a local path (from our proxy upload)
        # We can try to read it.
        
        # For this implementation, let's check if we can read the file from the Upload folder 
        # if the URL matches our host.
        
        # Actually, BookshelfRAG already has robust extraction logic.
        # We can use it!
        
        # Fetch content for indexing
        if not text_content:
            # Use BookshelfRAG to extract text for indexing
            # We need to simulate the item dict
            temp_item = data.copy()
            temp_item['id'] = doc_id
            
            # We need to forcefully extract text
            file_bytes = None
            if temp_item.get('content'):
                    try: file_bytes = base64.b64decode(temp_item['content'])
                    except: pass
            elif temp_item.get('storageUrl'):
                try:
                    resp = requests.get(temp_item['storageUrl'], timeout=10)
                    if resp.status_code == 200: file_bytes = resp.content
                except: pass
            
            if file_bytes:
                    text_content = BookshelfRAG.extract_text(file_bytes, temp_item.get('fileType', 'other'))
        
        if text_content:
            doc_body = {
                "title": data.get('title', 'Untitled'),
                "content": text_content,
                "file_type": data.get('fileType', 'unknown'),
                "storage_url": data.get('storageUrl', ''),
                "user_id": uid,
                "timestamp": datetime.now().isoformat()
            }
            opensearch_manager.index_document(doc_id, doc_body)
            print(f"✅ Indexed document {doc_id} to OpenSearch")
        else:
            print(f"⚠️ Could not extract text for indexing {doc_id}")
    except Exception as e:
        print(f"❌ Error in background indexing: {e}")

@app.route('/quizzes/score', methods=['POST'])
def save_quiz_score():
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    uid = user['uid']
    quiz_id = data.get('quizId')
    session_id = data.get('sessionId')
    score = data.get('score')
    total = data.get('total')
    
    if quiz_id is None or score is None or total is None:
        return jsonify({"error": "Missing quizId, score, or total"}), 400
        
    try:
        # Save score to a dedicated subcollection for the personalization engine
        score_data = {
            "quizId": quiz_id,
            "score": score,
            "total": total,
            "timestamp": datetime.now().isoformat(),
            "sessionId": session_id
        }
        
        db.collection('users').document(uid).collection('quiz_scores').add(score_data)
        
        # Also trigger background memory update
        memory_engine.update_async(uid)
        
        return jsonify({"success": True}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.before_request
def log_request_info():
    print(f"--- 📥 START REQUEST: {request.method} {request.path} ---")
    data = request.get_json(silent=True)
    if data:
        print(f"Body: {data}")

@app.after_request
def log_response_info(response):
    print(f"--- 📤 END REQUEST: {request.method} {request.path} | Status: {response.status_code} ---")
    return response

# --- VIDEO ENDPOINTS ---
@app.route('/videos/generate', methods=['POST'])
def generate_video():
    """Trigger background MP4 video generation with Cloudinary upload."""
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    data = request.json
    topic = data.get('topic')
    session_id = data.get('sessionId')
    
    if not topic:
        return jsonify({"error": "Missing topic"}), 400
    
    if not video_gen_service:
        return jsonify({"error": "Video service not available"}), 503
        
    # Start background thread for MP4 generation
    thread = threading.Thread(
        target=video_gen_service.generate_video_background_task,
        args=(topic, uid, session_id)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Video generation started. You'll be notified when it's ready!",
        "topic": topic,
        "status": "processing"
    }), 202

@app.route('/videos/test_generate', methods=['POST'])
def test_generate_video():
    # TEST ONLY: No auth required
    data = request.json
    topic = data.get('topic', 'Photosynthesis')
    try:
        scene = video_agent.generate_scene(topic, "test_user", "test_session")
        return jsonify(scene), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/sessions/<session_id>/videos', methods=['GET'])
def get_session_videos(session_id):
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    try:
        docs = db.collection('users').document(uid).collection('sessions').document(session_id).collection('videos').order_by('timestamp', direction=firestore.Query.DESCENDING).stream()
        videos = []
        for doc in docs:
            v_data = doc.to_dict()
            v_data['id'] = doc.id
            # Convert timestamp to ISO string if it exists
            if 'timestamp' in v_data and not isinstance(v_data['timestamp'], str):
                v_data['timestamp'] = v_data['timestamp'].isoformat()
            videos.append(v_data)
        return jsonify(videos), 200
    except Exception as e:
        print(f"Error fetching session videos: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/daily_quests', methods=['GET'])
def get_daily_quests():
    """Generate AI-powered daily study quests based on user memory and calendar."""
    user = get_user_from_token()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    
    uid = user['uid']
    
    try:
        # 1. Fetch user memory/profile for personalization
        memory_context = ""
        try:
            memory_doc = db.collection('users').document(uid).collection('memory').document('profile').get()
            if memory_doc.exists:
                memory_data = memory_doc.to_dict()
                memory_context = memory_data.get('detailed_feedback', '')
        except Exception as e:
            print(f"Memory fetch error: {e}")
        
        # 2. Fetch user's calendar events for today
        calendar_context = ""
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            events_ref = db.collection('users').document(uid).collection('calendar_events')
            events = list(events_ref.stream())
            upcoming = []
            for doc in events:
                event = doc.to_dict()
                event_date = event.get('date', '')
                if event_date and event_date >= today:
                    upcoming.append(f"- {event.get('title', 'Untitled')} ({event.get('type', 'task')}): {event_date}")
            if upcoming:
                calendar_context = "Upcoming events:\n" + "\n".join(upcoming[:5])
        except Exception as e:
            print(f"Calendar fetch error: {e}")
        
        # 3. Generate quests using Llama (fast model)
        prompt = f"""You are a helpful AI study planner. Generate exactly 3 personalized study tasks for today.

Student Context:
{memory_context if memory_context else "New student, general academic focus."}

{calendar_context if calendar_context else "No specific calendar events."}

Current Date: {datetime.now().strftime("%B %d, %Y")}

Generate 3 study tasks in this EXACT JSON format (no markdown, no extra text):
[
  {{"subject": "Subject Name", "task": "Brief task description"}},
  {{"subject": "Subject Name", "task": "Brief task description"}},
  {{"subject": "Subject Name", "task": "Brief task description"}}
]

Rules:
- Keep tasks actionable and specific
- Vary the subjects
- Tasks should be achievable today
- No time durations or deadlines
- Respond ONLY with valid JSON array"""

        quests = []
        try:
            response = GroqChat.chat(prompt, model="llama-3.1-8b-instant")
            
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]
            if response.endswith("```"):
                response = response[:-3]
            
            import json
            quests = json.loads(response.strip())
        except Exception as e:
            print(f"Quest generation error: {e}")
            # Fallback to sensible defaults based on common subjects
            quests = [
                {"subject": "Mathematics", "task": "Practice problem solving"},
                {"subject": "Science", "task": "Review key concepts"},
                {"subject": "Language", "task": "Reading comprehension"}
            ]
        
        return jsonify({"quests": quests}), 200
        
    except Exception as e:
        print(f"Daily quests error: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.get_default('port')
    parser.add_argument('--port', type=int, default=5000)
    args = parser.parse_args()
    
    print(f"🚀 Starting Flask Server on http://0.0.0.0:{args.port} (Reloader Disabled)")
    app.run(host='0.0.0.0', port=args.port, debug=True, use_reloader=False)
