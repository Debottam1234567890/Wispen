import sys
import os
import time

# Ensure backend path is in sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from opensearch_client import OpenSearchManager

def verify():
    print("🚀 Starting OpenSearch Verification...")
    
    try:
        manager = OpenSearchManager()
        print("✅ Client initialized")
        
        # 1. Create Index (should depend on init)
        if manager.client.indices.exists(index=manager.index_name):
            print(f"✅ Index '{manager.index_name}' exists")
        else:
            print(f"❌ Index '{manager.index_name}' missing!")
            return

        # 2. Index Document
        test_id = "test_doc_123"
        test_uid = "test_user_777"
        doc = {
            "title": "Verification Manual",
            "content": "OpenSearch is a distributed search and analytics suite. It is great for RAG.",
            "file_type": "text",
            "storage_url": "http://localhost/test",
            "user_id": test_uid,
            "timestamp": "2024-01-01T00:00:00"
        }
        
        print("📥 Indexing test document...")
        manager.index_document(test_id, doc)
        time.sleep(1) # Wait for refresh (index_document has refresh=True but safety first)
        
        # 3. Search
        print("🔍 Searching for 'distributed search'...")
        results = manager.search("distributed search", test_uid)
        
        if len(results) > 0:
            print("✅ Verification Successful! Results found:")
            for res in results:
                print(f"   - {res['title']} (Score: {res['score']})")
                print(f"     Content: {res['content']}")
        else:
            print("❌ Search failed to find the document.")
            
        # 4. Clean up
        print("🧹 Cleaning up...")
        manager.delete_document(test_id)
        
        # Check deletion
        time.sleep(1)
        results = manager.search("distributed search", test_uid)
        if len(results) == 0:
            print("✅ Cleanup Successful")
        else:
            print("⚠️ Cleanup might have failed or index lag")

    except Exception as e:
        print(f"❌ Verification Failed with Exception: {e}")

if __name__ == "__main__":
    verify()
