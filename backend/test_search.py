
import os
from opensearchpy import OpenSearch
from dotenv import load_dotenv

# Load env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env'))

host = os.getenv('OPENSEARCH_HOST', 'localhost')
port = int(os.getenv('OPENSEARCH_PORT', 9200))
auth = (os.getenv('OPENSEARCH_USER', 'admin'), os.getenv('OPENSEARCH_PASSWORD', 'admin'))

print(f"Connecting to {host}:{port} with auth {auth}...")

client = OpenSearch(
    hosts=[{'host': host, 'port': port}],
    http_compress=True,
    http_auth=auth,
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

try:
    info = client.info()
    print("Successfully connected to OpenSearch:")
    print(info)
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)

index_name = 'bookshelf'
if client.indices.exists(index=index_name):
    print(f"\nIndex '{index_name}' exists.")
    
    # Count documents
    count = client.count(index=index_name)
    print(f"Total documents: {count['count']}")
    
    # Search for "Chapter 3"
    print("\nSearching for 'Chapter 3'...")
    response = client.search(
        index=index_name,
        body={
            "query": {
                "match": {
                    "content": "Chapter 3"
                }
            },
            "size": 5
        }
    )
    
    print(f"Found {response['hits']['total']['value']} hits.")
    for hit in response['hits']['hits']:
        print(f" - {hit['_source'].get('title')} (Score: {hit['_score']})")
        print(f"   Snippet: {hit['_source'].get('content')[:100]}...")

else:
    print(f"\nIndex '{index_name}' DOES NOT exist.")
