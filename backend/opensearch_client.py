import os
import time
from opensearchpy import OpenSearch
from dotenv import load_dotenv

# Load env if not already loaded
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

class OpenSearchManager:
    def __init__(self, host='localhost', port=9200):
        # Allow env overrides
        host = os.getenv('OPENSEARCH_HOST', host)
        port = int(os.getenv('OPENSEARCH_PORT', port))
        
        auth = (os.getenv('OPENSEARCH_USER', 'admin'), os.getenv('OPENSEARCH_PASSWORD', 'admin'))
        
        # If using standard local dev setup without SSL/Auth, we might need to adjust
        # But standard OpenSearch docker usually has SSL/Auth enabled by default (admin/admin), self-signed certs.
        
        self.client = OpenSearch(
            hosts=[{'host': host, 'port': port}],
            http_compress=True, # enables gzip compression for request bodies
            http_auth=auth,
            use_ssl=True,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False
        )
        
        self.index_name = 'bookshelf'
        self.create_index_if_not_exists()

    def create_index_if_not_exists(self):
        """Create the bookshelf index with appropriate mappings"""
        if not self.client.indices.exists(index=self.index_name):
            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0
                    }
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},  # NEW: unique chunk identifier
                        "book_id": {"type": "keyword"},   # NEW: parent book reference
                        "title": {"type": "text"},
                        "content": {"type": "text"},
                        "page_start": {"type": "integer"},  # NEW: chunk page range
                        "page_end": {"type": "integer"},    # NEW: chunk page range
                        "file_type": {"type": "keyword"},
                        "storage_url": {"type": "keyword"},
                        "user_id": {"type": "keyword"}, # Important for multi-tenant
                        "timestamp": {"type": "date"}
                    }
                }
            }
            self.client.indices.create(index=self.index_name, body=index_body)
            print(f"Index '{self.index_name}' created.")
        else:
            # print(f"Index '{self.index_name}' already exists.")
            pass

    def index_document(self, doc_id, document):
        """Index a document. helper to add checks or preprocessing if needed."""
        response = self.client.index(
            index=self.index_name,
            body=document,
            id=doc_id,
            refresh=True # Make searchable immediately (good for this use case, careful in high load)
        )
        return response

    def delete_document(self, doc_id):
        try:
            self.client.delete(index=self.index_name, id=doc_id)
            return True
        except Exception as e:
            print(f"Error deleting document {doc_id}: {e}")
            return False

    def search(self, query, user_id, top_k=5):
        """Search for query within user's documents"""
        body = {
            "size": top_k,
            "query": {
                "bool": {
                    "must": [
                        {"match": {"content": query}},
                        {"term": {"user_id.keyword": user_id}}
                    ],
                    "should": [
                        {"term": {"file_type.keyword": {"value": "toc", "boost": 3.0}}},
                        {"match": {"title": {"query": "Table of Contents", "boost": 2.0}}}
                    ]
                }
            },
            "highlight": {
                "fields": {
                    "content": {}
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }
        }
        
        response = self.client.search(index=self.index_name, body=body)
        
        results = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            highlight = hit.get('highlight', {}).get('content', [])
            snippet = highlight[0] if highlight else source['content'][:200]
            
            results.append({
                "id": hit['_id'],
                "score": hit['_score'],
                "title": source.get('title'),
                "content": snippet, # Return snippet for display/context
                "full_content": source.get('content'), # Optional: return full text if needed
                "source": source.get('title') # Alias for RAG compatibility
            })
            
        return results

# Singleton instance for easy import
# Initialize carefully to avoid module level side effects if DB down, 
# but for this simple app, we can instantiate lazily or here.
ws_manager = None
try:
    # ws_manager = OpenSearchManager() # Commented out to avoid connection error on import if not running
    pass
except Exception:
    pass
