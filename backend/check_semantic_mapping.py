"""Check SemanticClass nodes and their potential bSDD mappings"""
from api.knowledge_graph_schema import KnowledgeGraphSchema
from api.config import cfg

kg = KnowledgeGraphSchema(
    neo4j_uri=cfg.NEO4J_URI,
    neo4j_user=cfg.NEO4J_USER,
    neo4j_password=cfg.NEO4J_PASSWORD,
    database=cfg.NEO4J_DATABASE
)

print("=" * 60)
print("SEMANTIC CLASS NODES IN NEO4J")
print("=" * 60)

with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    result = session.run('''
        MATCH (s:SemanticClass)
        RETURN s.label as name, s.classId as code, s.color as color
        ORDER BY s.classId
    ''')
    
    semantic_classes = []
    print("\nPoint Cloud Semantic Classes:\n")
    for r in result:
        semantic_classes.append({
            "name": r["name"],
            "code": r["code"],
            "color": r["color"]
        })
        print(f"  [{r['code']:2d}] {r['name']:<12s} - {r['color']}")

print(f"\nTotal: {len(semantic_classes)} semantic classes")

# Now check for potential bSDD class mappings
print("\n" + "=" * 60)
print("POTENTIAL bSDD CLASS MAPPINGS")
print("=" * 60)

# Map semantic class names to possible IFC class name patterns
semantic_to_ifc_patterns = {
    "ceiling": ["ceiling"],
    "floor": ["floor", "slab"],
    "wall": ["wall"],
    "beam": ["beam"],
    "column": ["column"],
    "window": ["window"],
    "door": [" door"],
    "table": ["furniture", "table"],
    "chair": ["furniture", "chair"],
    "sofa": ["furniture", "sofa"],
    "bookcase": ["furniture", "bookcase"],
    "board": ["board", "panel"]
}

print("\nSearching for matching bSDD classes...\n")

for sc in semantic_classes:
    if not sc["name"]:
        continue
    
    sc_lower = sc["name"].lower()
    patterns = semantic_to_ifc_patterns.get(sc_lower, [sc_lower])
    
    found_match = False
    for pattern in patterns:
        with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
            result = session.run('''
                MATCH (b:BsddClass)
                WHERE toLower(b.name) CONTAINS $pattern
                   OR toLower(b.code) CONTAINS $pattern
                RETURN b.name as name, b.code as code, b.uri as uri
                LIMIT 5
            ''', pattern=pattern)
            
            matches = list(result)
            if matches:
                print(f"✓ {sc['name']:<12s} [ID:{sc['code']:2d}] → {len(matches)} bSDD matches:")
                for m in matches[:3]:  # Show top 3
                    print(f"      - {m['name']} ({m['code']})")
                found_match = True
                break
    
    if not found_match:
        print(f"✗ {sc['name']:<12s} [ID:{sc['code']:2d}] → No bSDD matches")

kg.close()
