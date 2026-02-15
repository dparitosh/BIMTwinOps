"""
Comprehensive Semantic Class Alignment Check

Verifies that ALL semantic classes have proper bSDD mappings and the complete pipeline works.
"""
import requests
from api.knowledge_graph_schema import KnowledgeGraphSchema
from api.config import cfg

kg = KnowledgeGraphSchema(
    neo4j_uri=cfg.NEO4J_URI,
    neo4j_user=cfg.NEO4J_USER,
    neo4j_password=cfg.NEO4J_PASSWORD,
    database=cfg.NEO4J_DATABASE
)

print("=" * 70)
print("COMPREHENSIVE SEMANTIC CLASS ALIGNMENT CHECK")
print("=" * 70)

# 1. Check all SemanticClass nodes
print("\n1. Checking SemanticClass Nodes...")
with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    result = session.run("""
        MATCH (sc:SemanticClass)
        RETURN sc.label as label, sc.classId as id, sc.color as color
        ORDER BY sc.classId
    """)
    semantic_classes = list(result)
    print(f"   Found {len(semantic_classes)} SemanticClass nodes")
    for sc in semantic_classes:
        print(f"     [{sc['id']:2d}] {sc['label']:<12s} - {sc['color']}")

# 2. Check MAPS_TO relationships
print("\n2. Checking SemanticClass → BsddClass Mappings...")
with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    result = session.run("""
        MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
        RETURN sc.label as semantic_label,
               sc.classId as semantic_id,
               bc.name as bsdd_name,
               bc.code as bsdd_code,
               r.confidence as confidence,
               r.priority as priority
        ORDER BY sc.classId, r.priority
    """)
    mappings = list(result)
    print(f"   Found {len(mappings)} MAPS_TO relationships")
    
    # Group by semantic class
    by_semantic = {}
    for m in mappings:
        sid = m['semantic_id']
        if sid not in by_semantic:
            by_semantic[sid] = []
        by_semantic[sid].append(m)
    
    for sc in semantic_classes:
        sid = sc['id']
        sc_mappings = by_semantic.get(sid, [])
        if sc_mappings:
            print(f"   ✓ [{sid:2d}] {sc['label']:<12s} → {len(sc_mappings)} mapping(s)")
            for i, m in enumerate(sc_mappings):
                priority_marker = "PRIMARY" if m['priority'] == 0 else f"ALT-{m['priority']}"
                print(f"       [{priority_marker}] {m['bsdd_name']} ({m['bsdd_code']}) - conf: {m['confidence']}")
        else:
            print(f"   ✗ [{sid:2d}] {sc['label']:<12s} → NO MAPPINGS")

# 3. Check unmapped semantic classes
print("\n3. Finding Unmapped Semantic Classes...")
with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    result = session.run("""
        MATCH (sc:SemanticClass)
        WHERE NOT (sc)-[:MAPS_TO]->(:BsddClass)
        RETURN sc.label as label, sc.classId as id
        ORDER BY sc.classId
    """)
    unmapped = list(result)
    if unmapped:
        print(f"   ⚠ Found {len(unmapped)} unmapped semantic classes:")
        for u in unmapped:
            print(f"     [{u['id']:2d}] {u['label']}")
    else:
        print("   ✓ All semantic classes have bSDD mappings!")

# 4. Verify bSDD classes exist
print("\n4. Verifying bSDD Class References...")
with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    result = session.run("""
        MATCH (sc:SemanticClass)-[:MAPS_TO]->(bc:BsddClass)
        WITH bc, count(sc) as semantic_count
        RETURN bc.name as name, bc.code as code, semantic_count
        ORDER BY semantic_count DESC, bc.name
    """)
    bsdd_refs = list(result)
    print(f"   Referenced {len(bsdd_refs)} unique bSDD classes:")
    for b in bsdd_refs:
        print(f"     {b['code']:<30s} - {b['name']:<30s} ({b['semantic_count']} refs)")

# 5. Check IFC entity coverage
print("\n5. Checking IFC Entity Coverage...")
with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    result = session.run("""
        MATCH (sc:SemanticClass)-[:MAPS_TO]->(bc:BsddClass)
        WHERE size(bc.relatedIfcEntities) > 0
        RETURN sc.label as semantic_label,
               bc.relatedIfcEntities as ifc_entities
        ORDER BY semantic_label
    """)
    ifc_coverage = list(result)
    
    all_ifc_entities = set()
    for rec in ifc_coverage:
        if rec['ifc_entities']:
            all_ifc_entities.update(rec['ifc_entities'])
    
    print(f"   ✓ Semantic classes map to {len(all_ifc_entities)} unique IFC entities:")
    for ifc in sorted(all_ifc_entities):
        print(f"     - {ifc}")

# 6. Test API if available
print("\n6. Testing Point Cloud Semantic API...")
try:
    response = requests.get("http://127.0.0.1:8000/api/pointcloud/health", timeout=3)
    if response.status_code == 200:
        health = response.json()
        print(f"   ✓ API Status: {health.get('status', 'unknown')}")
        print(f"   ✓ Semantic classes loaded: {health.get('semantic_classes_loaded', 0)}")
        print(f"   ✓ Neo4j connected: {health.get('neo4j_connected', False)}")
    else:
        print(f"   ⚠ API returned status {response.status_code}")
except Exception as e:
    print(f"   ⚠ API not accessible: {e}")

# 7. Summary statistics
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    # Count nodes
    result = session.run("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
    """)
    node_stats = list(result)
    
    # Count relationships
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
    """)
    rel_stats = list(result)
    
    print(f"\nNode Types:")
    for stat in node_stats:
        print(f"  {stat['label']:<25s}: {stat['count']:>6d}")
    
    print(f"\nRelationship Types:")
    for stat in rel_stats:
        print(f"  {stat['type']:<25s}: {stat['count']:>6d}")

# Check coverage
mapped_count = len([sc for sc in semantic_classes if sc['id'] in by_semantic])
total_count = len(semantic_classes)
coverage_pct = (mapped_count / total_count * 100) if total_count > 0 else 0

print(f"\nAlignment Coverage:")
print(f"  SemanticClass nodes: {total_count}")
print(f"  Mapped to bSDD: {mapped_count}")
print(f"  Coverage: {coverage_pct:.1f}%")
print(f"  Total MAPS_TO relationships: {len(mappings)}")

if coverage_pct == 100:
    print(f"\n{'✓' * 35}")
    print("✓ COMPLETE ALIGNMENT VERIFIED")
    print(f"{'✓' * 35}")
else:
    print(f"\n{'⚠' * 35}")
    print(f"⚠ INCOMPLETE ALIGNMENT: {total_count - mapped_count} classes unmapped")
    print(f"{'⚠' * 35}")

kg.close()
