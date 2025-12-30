
import os
from opensearchpy import OpenSearch
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../.env'))

host = os.getenv('OPENSEARCH_HOST', 'localhost')
port = int(os.getenv('OPENSEARCH_PORT', 9200))
auth = (os.getenv('OPENSEARCH_USER', 'admin'), os.getenv('OPENSEARCH_PASSWORD', 'admin'))

client = OpenSearch(
    hosts=[{'host': host, 'port': port}],
    http_auth=auth,
    use_ssl=True,
    verify_certs=False,
    ssl_assert_hostname=False,
    ssl_show_warn=False
)

try:
    count = client.count(index='bookshelf')
    print(f"Total documents: {count['count']}")
    
    # Inspect actual user_ids
    print("Inspecting docs...")
    res = client.search(index='bookshelf', body={"query": {"match_all": {}}, "size": 10})
    for hit in res['hits']['hits']:
        print(f" - ID: {hit['_id']}, UserID: '{hit['_source'].get('user_id')}'")
except Exception as e:
    print(f"Error: {e}")
