import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.opensearch_client import OpenSearchManager

def test_search():
    print("🔍 Testing OpenSearch Query...")
    
    os_manager = OpenSearchManager()
    
    # Test searches
    queries = [
        "fourth chapter",
        "chapter 4",
        "systems of equations",
        "precalculus"
    ]
    
    # Known user ID from sync
    user_id = "ecOkatnslATnBBS9tQFyKzgPx8t2"
    
    for query in queries:
        print(f"\n--- Query: '{query}' ---")
        results = os_manager.search(query, user_id, top_k=3)
        
        if results:
            print(f"✅ Found {len(results)} results")
            for i, res in enumerate(results, 1):
                print(f"\n{i}. Title: {res.get('title', 'N/A')}")
                print(f"   Score: {res.get('score', 'N/A')}")
                print(f"   Content Preview: {res.get('content', '')[:200]}...")
        else:
            print("❌ No results found")

if __name__ == "__main__":
    test_search()
