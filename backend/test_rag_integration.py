
import sys
import os
from dotenv import load_dotenv

# Add root to python path to import chatbot_enhanced
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chatbot_enhanced import BookshelfRAG
from backend.opensearch_client import OpenSearchManager

# Load env variables
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

def test_integration():
    print("Testing BookshelfRAG integration with OpenSearchManager...")
    
    try:
        # 1. Initialize Manager
        manager = OpenSearchManager()
        print("✅ OpenSearchManager initialized")
        
        # 2. Test Search
        query = "what was the third chapter"
        user_id = "test_user" # OpenSearch likely has data for specific users, but let's try to search broadly or check what user IDs are there.
        # From previous test_search.py, we saw hits. The hits likely have a user_id. 
        # In test_search.py we didn't filter by user. 
        # But BookshelfRAG.search requires a user_id and FILTERS by it.
        # We need to use a user_id that has data.
        # Let's peek at the data again to find a valid user_id
        
        # user_id used in app.py comes from the token.
        # Use known user_id with book data
        user_id = 'ecOkatnslATnBBS9tQFyKzgPx8t2'
        print(f"Using user_id: {user_id}")

        # 3. Call RAG search with injection
        print(f"Calling BookshelfRAG.search('{query}', user_id='{user_id}')...")
        results = BookshelfRAG.search([], query, user_id=user_id, opensearch_client=manager)
        
        if results:
            print(f"✅ Success! Got {len(results)} results.")
            for r in results:
                print(f" - {r.get('source')} (Score: {r.get('score')})")
        else:
            print("❌ No results returned from RAG search.")
            
    except Exception as e:
        print(f"❌ Test Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_integration()
