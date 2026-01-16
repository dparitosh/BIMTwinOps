"""
Simple OpenSearch connectivity test
Tests connection without full MCP server setup
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import sys
import os

# Check if opensearch-py is available
try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    print("✅ opensearch-py installed")
except ImportError:
    print("❌ opensearch-py not installed")
    print("Run: pip install opensearch-py")
    sys.exit(1)

# Test connection
OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")

print(f"\n{'='*60}")
print("OpenSearch Connection Test")
print(f"{'='*60}")
print(f"URL: {OPENSEARCH_URL}")

try:
    # Parse URL
    url = OPENSEARCH_URL.replace("http://", "").replace("https://", "")
    host, port = url.split(":") if ":" in url else (url, "9200")
    
    # Connect
    client = OpenSearch(
        hosts=[{"host": host, "port": int(port)}],
        use_ssl=False,
        verify_certs=False,
        connection_class=RequestsHttpConnection,
        timeout=5
    )
    
    # Test connection
    info = client.info()
    version = info.get("version", {}).get("number", "unknown")
    cluster = info.get("cluster_name", "unknown")
    
    print(f"\n✅ Connected successfully!")
    print(f"   Version: {version}")
    print(f"   Cluster: {cluster}")
    
    # List indices
    indices = client.cat.indices(format="json")
    print(f"\n📊 Found {len(indices)} indices:")
    for idx in indices[:5]:  # Show first 5
        print(f"   - {idx['index']} ({idx['docs.count']} docs)")
    
    print(f"\n[SUCCESS] OpenSearch is operational!")
    
except ConnectionError as e:
    print(f"\n❌ Connection failed: {e}")
    print("\n💡 To start OpenSearch:")
    print("   Docker: docker run -d -p 9200:9200 -p 9600:9600 \\")
    print("           -e \"discovery.type=single-node\" \\")
    print("           opensearchproject/opensearch:latest")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    
print(f"\n{'='*60}")
