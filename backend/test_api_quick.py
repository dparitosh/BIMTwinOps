"""
Quick API test for Point Cloud Semantic Labeling
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8008"

print("Testing Point Cloud Semantic API...\n")

# 1. Test semantic classes endpoint
try:
    response = requests.get(f"{BASE_URL}/api/pointcloud/semantic-classes", timeout=5)
    if response.status_code == 200:
        classes = response.json()
        print(f"✓ Semantic Classes API working - {len(classes)} classes available")
        
        # Show first few
        for cls in classes[:3]:
            bsdd_count = len(cls.get('bsdd_classes', []))
            print(f"  [{cls['class_id']}] {cls['label']}: {bsdd_count} bSDD mappings")
    else:
        print(f"✗ API returned status {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"✗ Error: {e}")

print()

# 2. Test enrichment
try:
    test_segment = {
        "segment_id": "test_wall_001",
        "semantic_class_id": 2,  # wall
        "point_count": 1000,
        "centroid": [5.0, 2.5, 1.5]
    }
    
    response = requests.post(
        f"{BASE_URL}/api/pointcloud/enrich",
        json=test_segment,
        timeout=5
    )
    
    if response.status_code == 200:
        enriched = response.json()
        print("✓ Enrichment API working")
        print(f"  Semantic label: {enriched['semantic_label']}")
        print(f"  bSDD classes: {len(enriched['bsdd_classes'])}")
        print(f"  IFC entities: {enriched['ifc_entities'][:3] if enriched['ifc_entities'] else 'none'}")
    else:
        print(f"✗ Enrichment failed: {response.status_code}")
        print(response.text)
except Exception as e:
    print(f"✗ Error: {e}")

print("\n✓ Data layer integration complete!")
