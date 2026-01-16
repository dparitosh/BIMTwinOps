"""
Test OpenSearch Hybrid Memory Setup
Validates connection and creates indices.
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.hybrid_memory import (
    HybridMemorySystem,
    OpenSearchConfig,
    AzureOpenAIEmbeddings
)


def test_connection():
    """Test OpenSearch connection"""
    print("Testing OpenSearch connection...")
    print("=" * 60)
    
    config = OpenSearchConfig(
        host="localhost",
        port=9200,
        username="admin",
        password="admin123",
        use_ssl=False,
        verify_certs=False
    )
    
    try:
        from opensearchpy import OpenSearch
        client = OpenSearch(**config.to_dict())
        
        # Test connection
        info = client.info()
        print(f"✅ Connected to OpenSearch")
        print(f"   Version: {info['version']['number']}")
        print(f"   Cluster: {info['cluster_name']}")
        
        # Check k-NN plugin
        plugins = client.cat.plugins(format="json")
        knn_plugin = any(p['component'] == 'opensearch-knn' for p in plugins)
        
        if knn_plugin:
            print(f"✅ k-NN plugin enabled")
        else:
            print(f"⚠️  k-NN plugin not found (required for vector search)")
        
        return True
    
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False


def test_index_creation():
    """Test index creation"""
    print("\nTesting index creation...")
    print("=" * 60)
    
    try:
        # Note: Skip embeddings for now if Azure OpenAI not configured
        config = OpenSearchConfig(
            host="localhost",
            port=9200,
            username="admin",
            password="admin123"
        )
        
        from opensearchpy import OpenSearch
        from memory.hybrid_memory import OpenSearchIndexManager
        
        client = OpenSearch(**config.to_dict())
        manager = OpenSearchIndexManager(client)
        
        # Create indices
        print("Creating bsdd_tasks_vectors index...")
        manager.create_tasks_index()
        print("✅ Tasks index ready")
        
        print("Creating bsdd_context_vectors index...")
        manager.create_context_index()
        print("✅ Context index ready")
        
        # List indices
        indices = client.cat.indices(format="json")
        bsdd_indices = [idx for idx in indices if 'bsdd' in idx['index']]
        
        print(f"\nBSDD Indices ({len(bsdd_indices)}):")
        for idx in bsdd_indices:
            print(f"  - {idx['index']}: {idx['docs.count']} docs, {idx['store.size']}")
        
        return True
    
    except Exception as e:
        print(f"❌ Index creation failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("OpenSearch Hybrid Memory Setup Test")
    print("=" * 60 + "\n")
    
    # Test connection
    if not test_connection():
        print("\n❌ Setup incomplete: Connection failed")
        return
    
    # Test index creation
    if not test_index_creation():
        print("\n❌ Setup incomplete: Index creation failed")
        return
    
    print("\n" + "=" * 60)
    print("✅ OpenSearch setup complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Configure Azure OpenAI endpoint for embeddings")
    print("2. Test hybrid search with sample data")
    print("3. Integrate with agent orchestrator")


if __name__ == "__main__":
    main()
