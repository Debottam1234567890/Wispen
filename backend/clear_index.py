
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

index_name = 'bookshelf'
if client.indices.exists(index=index_name):
    print(f"Deleting index '{index_name}'...")
    client.indices.delete(index=index_name)
    print("Deleted.")
else:
    print(f"Index '{index_name}' not found.")
