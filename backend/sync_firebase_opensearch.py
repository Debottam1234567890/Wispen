import sys
import os
import io  # For PDF processing

# Add parent directory to path to find chatbot_enhanced.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, firestore, storage
from backend.opensearch_client import OpenSearchManager
from chatbot_enhanced import BookshelfRAG
import requests
import base64
from datetime import datetime

# Initialize Firebase (assuming credentials are set up via env or default)
# We can reuse the initialization from app.py or do it manually if standalone
# For standalone script, better to setup again if not running via Flask

def sync_data():
    print("🚀 Starting Firebase -> OpenSearch Sync...")
    
    # 1. Initialize OpenSearch
    try:
        os_manager = OpenSearchManager()
        if not os_manager.client.ping():
            print("❌ Could not connect to OpenSearch. Is it running?")
            return
        print("✅ Connected to OpenSearch")
    except Exception as e:
        print(f"❌ Error connecting to OpenSearch: {e}")
        return

    # 2. Initialize Firebase
    if not firebase_admin._apps:
        # Credential file is in the root directory (parent of backend)
        cred_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "wispen-f4a94-firebase-adminsdk-fbsvc-f1e0e701d7.json")
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred, {
            'storageBucket': 'wispen-f4a94.firebasestorage.app' 
        })
    
    db = firestore.client()
    bucket = storage.bucket()
    from firebase_admin import auth

    # 3. Iterate Auth Users (Since Firestore parent docs might be virtual)
    print("Listing Auth Users...")
    try:
        # iterator for all users
        all_users = auth.list_users().iterate_all()
        total_indexed = 0
        
        for user in all_users:
            uid = user.uid
            print(f"📂 Processing User: {uid} ({user.email})")
            
            bookshelf_ref = db.collection('users').document(uid).collection('bookshelf')
            items = list(bookshelf_ref.stream())
            
            if not items:
                print(f"   - No bookshelf items.")
                continue

            for doc in items:
                item_data = doc.to_dict()
                item_id = doc.id
                item_title = item_data.get('title', 'Untitled')
                
                print(f"   - Processing Item: {item_title} ({item_id})")
                
                # Check content
                text_content = ""
                # A. Check explicit
                if item_data.get('content') and item_data.get('fileType') == 'text':
                     try: text_content = base64.b64decode(item_data['content']).decode('utf-8')
                     except: text_content = item_data.get('content', '')
                
                # B. Download
                if not text_content and item_data.get('storageUrl'):
                    try:
                        print("     Downloading...")
                        resp = requests.get(item_data['storageUrl'])
                        if resp.status_code == 200:
                            file_bytes = resp.content
                            file_type = item_data.get('fileType', 'application/pdf')
                            text_content = BookshelfRAG.extract_text(file_bytes, file_type, max_pages=100)
                    except Exception as e:
                        print(f"     Error: {e}")
                
                # Fix timestamp - OpenSearch date field can't be empty string
                timestamp = item_data.get('timestamp', '')
                if not timestamp or timestamp == '':
                    timestamp = datetime.now().isoformat()
                
                if text_content:
                    # CHUNK THE CONTENT into 5-page segments with OVERLAP for better context
                    PAGES_PER_CHUNK = 5
                    OVERLAP_PAGES = 2
                    STRIDE = PAGES_PER_CHUNK - OVERLAP_PAGES
                    
                    # For PDFs, we know the page boundaries from extraction
                    # For text files, we'll treat the whole thing as one chunk
                    
                    # Detect PDFs by fileType or URL
                    is_pdf = (item_data.get('fileType') == 'application/pdf' or 
                              item_data.get('fileType') == 'pdf' or
                              (item_data.get('storageUrl', '').lower().endswith('.pdf'))
                    )
                    
                    if is_pdf and item_data.get('storageUrl'):
                        # We extracted text, now we need to know how many pages
                        # The extraction gives us continuous text, so we need to re-parse to get page boundaries
                        try:
                            resp2 = requests.get(item_data['storageUrl'], timeout=30)
                            if resp2.status_code == 200:
                                import PyPDF2
                                reader = PyPDF2.PdfReader(io.BytesIO(resp2.content))
                                total_pages = len(reader.pages)
                                
                                print(f"     Creating chunks from {total_pages} pages (Size: {PAGES_PER_CHUNK}, Overlap: {OVERLAP_PAGES})...")
                                
                                # Create chunks with sliding window
                                chunk_num = 0
                                # Ensure we cover everything; simpler loop
                                for start_page in range(0, total_pages, STRIDE):
                                    end_page = min(start_page + PAGES_PER_CHUNK, total_pages)
                                    
                                    # Avoid tiny tail chunks if possible (merge with previous? or just keep)
                                    # If it's just 1 page and overlap is 2, it's redundant.
                                    # But simplistic approach is fine.
                                    
                                    if start_page >= total_pages: break # Should be covered by range but safety check
                                    
                                    # Extract text for this chunk
                                    chunk_text = ""
                                    for page_idx in range(start_page, end_page):
                                        chunk_text += reader.pages[page_idx].extract_text() + "\n"
                                    
                                    if chunk_text.strip():
                                        chunk_id = f"{item_id}_chunk_{chunk_num}"
                                        chunk_doc = {
                                            'user_id': uid,
                                            'book_id': item_id,
                                            'chunk_id': chunk_id,
                                            'title': f"{item_data.get('title', 'Unknown')} (pages {start_page+1}-{end_page})",
                                            'content': chunk_text,
                                            'page_start': start_page + 1,
                                            'page_end': end_page,
                                            'timestamp': timestamp,
                                            'storage_url': item_data.get('storageUrl'),
                                            'file_type': item_data.get('fileType')
                                        }
                                        os_manager.index_document(chunk_id, chunk_doc)
                                        chunk_num += 1

                                # --- SPECIAL TOC CHUNK ---
                                # Index the first 15 pages as a "Table of Contents" / "Chapter List"
                                # This helps when users ask "what is chapter x" or "outline"
                                toc_end = min(15, total_pages)
                                toc_text = ""
                                for p in range(0, toc_end):
                                    if p < len(reader.pages):
                                        toc_text += reader.pages[p].extract_text() + "\n"
                                
                                toc_doc = {
                                    'user_id': uid,
                                    'book_id': item_id,
                                    'chunk_id': f"{item_id}_toc",
                                    'title': f"{item_data.get('title', 'Unknown')} - Table of Contents Structure Chapter List",
                                    'content': "TABLE OF CONTENTS CHAPTER LIST OUTLINE STRUCTURE:\n" + toc_text,
                                    'page_start': 1,
                                    'page_end': toc_end,
                                    'timestamp': timestamp,
                                    'storage_url': item_data.get('storageUrl'),
                                    'file_type': 'toc'
                                }
                                os_manager.index_document(f"{item_id}_toc", toc_doc)
                                print(f"     ✅ Indexed TOC chunk (pages 1-{toc_end})")
                                        
                                total_indexed += chunk_num
                                # Add 1 for the TOC chunk
                                total_indexed += 1 
                                print(f"     ✅ Indexed {chunk_num} chunks.")
                            else:
                                print(f"     ⚠️ Failed to re-download for chunking")
                        except Exception as chunk_err:
                            print(f"     ⚠️ Chunking error: {chunk_err}")
                    else:
                        # Non-PDF: index as single chunk
                        chunk_doc = {
                            'chunk_id': f"{item_id}_chunk_0",
                            'book_id': item_id,
                            'title': item_title,
                            'content': text_content,
                            'page_start': 1,
                            'page_end': 1,
                            'file_type': item_data.get('fileType', 'unknown'),
                            'storage_url': item_data.get('storageUrl', ''),
                            'user_id': uid,
                            'timestamp': timestamp
                        }
                        os_manager.index_document(f"{item_id}_chunk_0", chunk_doc)
                        total_indexed += 1
                        print("     ✅ Indexed as single chunk.")
                else:
                    print("     ⚠️ Empty content.")
                    

    except Exception as ae:
        print(f"Auth List Error: {ae}")

    print(f"✨ Sync Complete. Total Items Indexed: {total_indexed}")

if __name__ == "__main__":
    sync_data()

