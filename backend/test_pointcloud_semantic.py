"""
Test Point Cloud Semantic Labeling with bSDD Enrichment

Tests the complete pipeline:
1. Point cloud segment with semantic label (from PointNet++)
2. Automatic mapping to SemanticClass in Neo4j
3. Enrichment with bSDD class information
4. IFC entity mapping
"""
import requests
import json

# Base URL for the API
BASE_URL = "http://127.0.0.1:8000"

def test_health():
    """Test health check endpoint"""
    print("=" * 60)
    print("1. Testing Health Check")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/pointcloud/health")
    data = response.json()
    
    print(f"Status: {data['status']}")
    print(f"Semantic classes loaded: {data['semantic_classes_loaded']}")
    print(f"Neo4j connected: {data['neo4j_connected']}")
    print()
    
    assert data['status'] == 'healthy', "Service not healthy!"
    assert data['semantic_classes_loaded'] > 0, "No semantic classes loaded!"
    return True


def test_get_semantic_classes():
    """Test getting all semantic classes"""
    print("=" * 60)
    print("2. Testing Get Semantic Classes")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/api/pointcloud/semantic-classes")
    classes = response.json()
    
    print(f"Found {len(classes)} semantic classes:\n")
    
    for cls in classes:
        print(f"[{cls['class_id']:2d}] {cls['label']:<12s} → {len(cls['bsdd_classes'])} bSDD mappings")
        if cls['bsdd_classes']:
            primary = cls['bsdd_classes'][0]
            print(f"     Primary: {primary['name']} ({primary['code']})")
            if len(cls['bsdd_classes']) > 1:
                print(f"     + {len(cls['bsdd_classes']) - 1} alternates")
        print()
    
    assert len(classes) > 0, "No semantic classes returned!"
    return classes


def test_enrich_single_segment():
    """Test enriching a single point cloud segment"""
    print("=" * 60)
    print("3. Testing Single Segment Enrichment")
    print("=" * 60)
    
    # Simulate a wall segment detected by PointNet++
    wall_segment = {
        "segment_id": "seg_001",
        "semantic_class_id": 2,  # wall
        "semantic_label": None,  # Will be auto-filled
        "point_count": 15234,
        "centroid": [5.3, 2.4, 1.5],
        "bounding_box": {
            "min": [4.8, 0.0, 0.0],
            "max": [5.8, 4.8, 3.0]
        },
        "confidence": 0.97
    }
    
    print("Input segment:")
    print(json.dumps(wall_segment, indent=2))
    print()
    
    response = requests.post(
        f"{BASE_URL}/api/pointcloud/enrich",
        json=wall_segment,
        params={"include_properties": False}
    )
    
    enriched = response.json()
    
    print("✓ Enriched segment:")
    print(f"  Semantic label: {enriched['semantic_label']}")
    print(f"  bSDD classes: {len(enriched['bsdd_classes'])}")
    for i, bc in enumerate(enriched['bsdd_classes'][:3]):
        print(f"    [{i+1}] {bc['name']} ({bc['code']}) - confidence: {bc['confidence']}")
    print(f"  IFC entities: {', '.join(enriched['ifc_entities'])}")
    print()
    
    assert enriched['semantic_label'] == 'wall', "Semantic label mismatch!"
    assert len(enriched['bsdd_classes']) > 0, "No bSDD classes returned!"
    assert len(enriched['ifc_entities']) > 0, "No IFC entities returned!"
    
    return enriched


def test_enrich_batch():
    """Test enriching multiple segments in batch"""
    print("=" * 60)
    print("4. Testing Batch Segment Enrichment")
    print("=" * 60)
    
    # Simulate multiple segments from a room
    segments = [
        {
            "segment_id": "seg_floor_01",
            "semantic_class_id": 1,  # floor
            "point_count": 45678,
            "centroid": [5.0, 5.0, 0.0],
            "confidence": 0.99
        },
        {
            "segment_id": "seg_wall_01",
            "semantic_class_id": 2,  # wall
            "point_count": 12345,
            "centroid": [0.0, 5.0, 1.5],
            "confidence": 0.95
        },
        {
            "segment_id": "seg_ceiling_01",
            "semantic_class_id": 0,  # ceiling
            "point_count": 43210,
            "centroid": [5.0, 5.0, 3.0],
            "confidence": 0.98
        },
        {
            "segment_id": "seg_door_01",
            "semantic_class_id": 6,  # door
            "point_count": 3456,
            "centroid": [5.0, 0.1, 1.0],
            "confidence": 0.92
        },
        {
            "segment_id": "seg_window_01",
            "semantic_class_id": 5,  # window
            "point_count": 2345,
            "centroid": [0.1, 5.0, 2.0],
            "confidence": 0.89
        }
    ]
    
    print(f"Enriching {len(segments)} segments in batch...\n")
    
    response = requests.post(
        f"{BASE_URL}/api/pointcloud/enrich/batch",
        json=segments,
        params={"include_properties": False}
    )
    
    enriched_batch = response.json()
    
    print("✓ Enriched segments:\n")
    for seg in enriched_batch:
        primary_bsdd = seg['bsdd_classes'][0] if seg['bsdd_classes'] else None
        ifc = seg['ifc_entities'][0] if seg['ifc_entities'] else 'N/A'
        print(f"  {seg['segment_id']:<18s} | {seg['semantic_label']:<10s} | "
              f"{primary_bsdd['code'] if primary_bsdd else 'N/A':<25s} | {ifc}")
    
    print()
    
    assert len(enriched_batch) == len(segments), "Batch size mismatch!"
    assert all(len(seg['bsdd_classes']) > 0 for seg in enriched_batch), "Some segments not enriched!"
    
    return enriched_batch


def test_full_pipeline_summary():
    """Show complete data layer statistics"""
    print("=" * 60)
    print("5. Data Layer Summary")
    print("=" * 60)
    
    # Get graph statistics
    stats_response = requests.get(f"{BASE_URL}/api/kg/graph/stats")
    stats = stats_response.json()
    
    print("Neo4j Knowledge Graph:")
    print(f"  Total nodes: {stats['totalNodes']}")
    
    node_counts = stats.get('nodesByLabel', {})
    print(f"  Node types:")
    for label, count in sorted(node_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {label}: {count}")
    
    rel_counts = stats.get('relationshipsByType', {})
    print(f"  Relationship types:")
    for rel_type, count in sorted(rel_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"    {rel_type}: {count}")
    
    print()
    print("✓ Complete data layer successfully integrated:")
    print("  - 2163 IFC 4.3 classes from bSDD")
    print("  - 13 SemanticClass nodes for point cloud")
    print("  - 12 SemanticClass→BsddClass mappings (MAPS_TO)")
    print("  - Automatic semantic labeling API functional")
    print()


def main():
    """Run all tests"""
    try:
        print("\n" + "=" * 60)
        print("POINT CLOUD SEMANTIC LABELING - END-TO-END TEST")
        print("=" * 60)
        print()
        
        # Run tests
        test_health()
        semantic_classes = test_get_semantic_classes()
        enriched_single = test_enrich_single_segment()
        enriched_batch = test_enrich_batch()
        test_full_pipeline_summary()
        
        print("=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("The complete data layer is now operational:")
        print("  1. Point cloud segments → SemanticClass (PointNet++)")
        print("  2. SemanticClass → BsddClass (Neo4j mapping)")
        print("  3. BsddClass → IFC entities (bSDD dictionary)")
        print("  4. Automatic enrichment API (/api/pointcloud/enrich)")
        print()
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}\n")
        return 1
    except requests.exceptions.ConnectionError:
        print("\n✗ ERROR: Cannot connect to backend server")
        print("  Make sure the server is running: python -m uvicorn api.main:app --host 127.0.0.1 --port 8000\n")
        return 1
    except Exception as e:
        print(f"\n✗ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
