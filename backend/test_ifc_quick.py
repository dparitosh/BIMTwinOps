import requests

segment = {
    "segment_id": "test",
    "semantic_class_id": 2,
    "semantic_label": "wall",
    "point_count": 100,
    "centroid": [0, 0, 0]
}

r = requests.post("http://127.0.0.1:8001/api/pointcloud/enrich", json=segment, timeout=5)
result = r.json()

print(f"Status: {r.status_code}")
print(f"bSDD Classes: {len(result['bsdd_classes'])}")
print(f"IFC Entities: {len(result['ifc_entities'])}")
print(f"IFC Entities: {result['ifc_entities']}")
