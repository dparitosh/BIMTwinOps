"""
Complete Data Layer Integration Test

Demonstrates the full pipeline:
1. Point cloud segment with semantic classification
2. Enrichment with bSDD classes and IFC entities
3. Validation of enriched data
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8001/api/pointcloud"

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def test_health():
    """Test health endpoint"""
    print_section("1. Health Check")
    
    response = requests.get(f"{BASE_URL}/health", timeout=5)
    health = response.json()
    
    print(f"Status: {response.status_code}")
    print(json.dumps(health, indent=2))
    
    assert response.status_code == 200
    assert health["status"] == "healthy"
    assert health["semantic_classes_loaded"] == 12
    print("\n✅ Health check passed!")
    
    return health

def test_semantic_classes():
    """Test semantic classes endpoint"""
    print_section("2. Semantic Classes")
    
    response = requests.get(f"{BASE_URL}/semantic-classes", timeout=5)
    classes = response.json()
    
    print(f"Status: {response.status_code}")
    print(f"Total classes: {len(classes)}\n")
    
    # Show summary
    for cls in classes:
        bsdd_count = len(cls["bsdd_classes"])
        print(f"  {cls['class_id']:2d}. {cls['label']:15s} → {bsdd_count:2d} bSDD classes")
    
    assert response.status_code == 200
    assert len(classes) == 12
    print("\n✅ Semantic classes retrieved!")
    
    return classes

def test_enrich_wall():
    """Test enrichment for a wall segment"""
    print_section("3. Enrich Wall Segment")
    
    segment = {
        "segment_id": "wall_001",
        "semantic_class_id": 2,
        "semantic_label": "wall",
        "point_count": 15000,
        "centroid": [10.5, 5.2, 1.5],
        "bounding_box": {
            "min": [10.0, 5.0, 0.0],
            "max": [11.0, 5.5, 3.0]
        },
        "confidence": 0.95
    }
    
    print("Input segment:")
    print(json.dumps(segment, indent=2))
    
    response = requests.post(f"{BASE_URL}/enrich", json=segment, timeout=5)
    enriched = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"\nEnriched segment:")
    print(f"  Semantic Label: {enriched['semantic_label']}")
    print(f"  bSDD Classes: {len(enriched['bsdd_classes'])}")
    print(f"  IFC Entities: {len(enriched['ifc_entities'])}")
    
    print(f"\nTop 3 bSDD Classes:")
    for i, cls in enumerate(enriched['bsdd_classes'][:3]):
        print(f"  {i+1}. {cls['name']:25s} ({cls['code']})")
        print(f"     Confidence: {cls['confidence']}, Priority: {cls['priority']}")
    
    print(f"\nAll IFC Entities:")
    for entity in enriched['ifc_entities']:
        print(f"  - {entity}")
    
    assert response.status_code == 200
    assert enriched['semantic_label'] == 'wall'
    assert len(enriched['bsdd_classes']) == 12  # wall has 12 bSDD mappings
    assert len(enriched['ifc_entities']) == 12
    print("\n✅ Wall segment enrichment successful!")
    
    return enriched

def test_enrich_batch():
    """Test batch enrichment"""
    print_section("4. Batch Enrichment")
    
    segments = [
        {
            "segment_id": "ceiling_001",
            "semantic_class_id": 0,
            "semantic_label": "ceiling",
            "point_count": 8000,
            "centroid": [5.0, 5.0, 3.0],
            "confidence": 0.92
        },
        {
            "segment_id": "floor_001",
            "semantic_class_id": 1,
            "semantic_label": "floor",
            "point_count": 12000,
            "centroid": [5.0, 5.0, 0.0],
            "confidence": 0.98
        },
        {
            "segment_id": "door_001",
            "semantic_class_id": 7,
            "semantic_label": "door",
            "point_count": 2000,
            "centroid": [10.0, 5.0, 1.2],
            "confidence": 0.89
        }
    ]
    
    print(f"Input: {len(segments)} segments")
    for seg in segments:
        print(f"  - {seg['segment_id']:15s} ({seg['semantic_label']})")
    
    response = requests.post(f"{BASE_URL}/enrich/batch", json=segments, timeout=10)
    enriched_batch = response.json()
    
    print(f"\nStatus: {response.status_code}")
    print(f"Enriched: {len(enriched_batch)} segments\n")
    
    for seg in enriched_batch:
        print(f"  {seg['segment_id']:15s} → {len(seg['bsdd_classes'])} bSDD classes, {len(seg['ifc_entities'])} IFC entities")
    
    assert response.status_code == 200
    assert len(enriched_batch) == 3
    assert all(len(seg['ifc_entities']) >= 1 for seg in enriched_batch)
    print("\n✅ Batch enrichment successful!")
    
    return enriched_batch

def main():
    """Run all tests"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "  DATA LAYER INTEGRATION TEST".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    try:
        # Run tests
        health = test_health()
        classes = test_semantic_classes()
        wall = test_enrich_wall()
        batch = test_enrich_batch()
        
        # Final summary
        print_section("SUMMARY")
        print("✅ All tests passed!")
        print(f"\n   Semantic classes loaded: {health['semantic_classes_loaded']}")
        print(f"   Neo4j connected: {health['neo4j_connected']}")
        print(f"   Total API endpoints: 4")
        print(f"   Tested segments: 4 (1 wall + 3 batch)")
        print(f"   Total bSDD classes enriched: {len(wall['bsdd_classes']) + sum(len(s['bsdd_classes']) for s in batch)}")
        
        print("\n" + "█" * 80)
        print("█" + " " * 78 + "█")
        print("█" + "  DATA LAYER COMPLETE - ALL SYSTEMS OPERATIONAL".center(78) + "█")
        print("█" + " " * 78 + "█")
        print("█" * 80 + "\n")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to backend server!")
        print("   Make sure the server is running on http://127.0.0.1:8001")
        print("   Run: cd backend && python -m uvicorn api.main:app --host 127.0.0.1 --port 8001")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
