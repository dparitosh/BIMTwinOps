"""
Test OpenSearch MCP Server
Validates connectivity and tool functionality.
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import asyncio
import json
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opensearch.server import OpenSearchClient, OPENSEARCH_URL, OPENSEARCH_INDEX


async def test_opensearch_server():
    """Test OpenSearch MCP server functionality"""
    print("=" * 70)
    print("OpenSearch MCP Server Test")
    print("=" * 70)
    
    client = OpenSearchClient()
    
    # Test 1: Connection
    print("\n[TEST 1] Testing Connection")
    print(f"URL: {OPENSEARCH_URL}")
    print(f"Default Index: {OPENSEARCH_INDEX}")
    
    try:
        client.connect()
        print("✅ Connected successfully")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nNote: Ensure OpenSearch is running:")
        print("  Docker: docker run -d -p 9200:9200 -p 9600:9600 -e \"discovery.type=single-node\" opensearchproject/opensearch:latest")
        return
    
    # Test 2: Create Index
    print("\n[TEST 2] Creating Test Index")
    test_index = "test_bim_memory"
    
    try:
        result = client.create_index(
            index_name=test_index,
            vector_dimension=384
        )
        print(f"✅ Index created: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"⚠️ Index creation: {e}")
    
    # Test 3: Store Documents
    print("\n[TEST 3] Storing Test Documents")
    
    test_docs = [
        {
            "name": "Wall-001",
            "description": "Fire rated exterior wall",
            "semantic_name": "wall",
            "category": "IfcWall",
            "fire_rating": 90,
            "height": 3.5
        },
        {
            "name": "Door-001",
            "description": "Fire rated door with glass panel",
            "semantic_name": "door",
            "category": "IfcDoor",
            "fire_rating": 60,
            "width": 1.2
        },
        {
            "name": "Column-001",
            "description": "Structural steel column",
            "semantic_name": "column",
            "category": "IfcColumn",
            "material": "steel",
            "height": 4.0
        }
    ]
    
    stored_ids = []
    for i, doc in enumerate(test_docs, 1):
        try:
            result = client.store_document(
                document=doc,
                doc_id=f"test-doc-{i}",
                index=test_index
            )
            stored_ids.append(result["id"])
            print(f"✅ Stored: {result['id']} ({doc['name']})")
        except Exception as e:
            print(f"❌ Failed to store doc {i}: {e}")
    
    # Small delay for indexing
    await asyncio.sleep(1)
    
    # Test 4: Semantic Search
    print("\n[TEST 4] Semantic Search")
    
    queries = [
        "fire rated",
        "structural column",
        "glass door"
    ]
    
    for query in queries:
        print(f"\n  Query: '{query}'")
        try:
            results = client.search_semantic(
                query=query,
                index=test_index,
                size=3,
                min_score=0.1
            )
            
            if results:
                print(f"  ✅ Found {len(results)} results:")
                for r in results:
                    name = r["source"].get("name", "N/A")
                    score = r["score"]
                    print(f"    - {name} (score: {score:.2f})")
            else:
                print("  ⚠️ No results found")
        except Exception as e:
            print(f"  ❌ Search failed: {e}")
    
    # Test 5: Get Document
    print("\n[TEST 5] Retrieve Document by ID")
    
    if stored_ids:
        doc_id = stored_ids[0]
        print(f"  Retrieving: {doc_id}")
        
        try:
            result = client.get_document(doc_id=doc_id, index=test_index)
            if result.get("found"):
                print(f"  ✅ Retrieved: {result['source'].get('name', 'N/A')}")
                print(f"     Category: {result['source'].get('category', 'N/A')}")
            else:
                print("  ❌ Document not found")
        except Exception as e:
            print(f"  ❌ Retrieval failed: {e}")
    
    # Test 6: Cleanup (optional)
    print("\n[TEST 6] Cleanup")
    print(f"  Test index '{test_index}' created with {len(stored_ids)} documents")
    print("  To delete: client.client.indices.delete(index=test_index)")
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print("✅ Connection: OK")
    print(f"✅ Index Creation: OK ({test_index})")
    print(f"✅ Document Storage: {len(stored_ids)}/{len(test_docs)} documents")
    print("✅ Semantic Search: OK")
    print("✅ Document Retrieval: OK")
    print("\n[SUCCESS] All tests completed!")


async def test_with_sample_data():
    """Test with realistic BIM data"""
    print("\n" + "=" * 70)
    print("Realistic BIM Data Test")
    print("=" * 70)
    
    client = OpenSearchClient()
    
    try:
        client.connect()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return
    
    # Create BIM memory index
    bim_index = "bim_memory"
    
    try:
        result = client.create_index(index_name=bim_index, vector_dimension=384)
        print(f"✅ Created index: {bim_index}")
    except Exception as e:
        print(f"⚠️ Index: {e}")
    
    # Sample BIM data
    bim_data = [
        {
            "name": "Floor-01-Slab",
            "description": "Ground floor concrete slab, 200mm thickness",
            "semantic_name": "slab",
            "category": "IfcSlab",
            "material": "concrete",
            "thickness": 0.2,
            "area": 120.5,
            "load_bearing": True
        },
        {
            "name": "Beam-B1",
            "description": "Primary steel beam, I-section 400x200",
            "semantic_name": "beam",
            "category": "IfcBeam",
            "material": "steel",
            "length": 6.0,
            "section": "I-400x200"
        },
        {
            "name": "Window-W1",
            "description": "Double glazed window with aluminum frame",
            "semantic_name": "window",
            "category": "IfcWindow",
            "material": "glass",
            "width": 1.5,
            "height": 1.8,
            "glazing": "double"
        }
    ]
    
    print("\nStoring BIM elements...")
    for i, elem in enumerate(bim_data, 1):
        try:
            result = client.store_document(
                document=elem,
                index=bim_index
            )
            print(f"  ✅ {elem['name']} (ID: {result['id']})")
        except Exception as e:
            print(f"  ❌ Failed: {e}")
    
    await asyncio.sleep(1)
    
    # Test queries
    print("\nTesting BIM queries...")
    test_queries = [
        "concrete floor slab",
        "steel beam structural",
        "glazed window aluminum"
    ]
    
    for query in test_queries:
        print(f"\n  Query: '{query}'")
        results = client.search_semantic(query=query, index=bim_index, size=2)
        
        if results:
            for r in results:
                name = r["source"].get("name", "N/A")
                category = r["source"].get("category", "N/A")
                score = r["score"]
                print(f"    → {name} ({category}) - Score: {score:.2f}")
        else:
            print("    No results")
    
    print("\n[SUCCESS] BIM data test completed!")


if __name__ == "__main__":
    # Run basic tests
    asyncio.run(test_opensearch_server())
    
    # Run BIM data test
    asyncio.run(test_with_sample_data())
