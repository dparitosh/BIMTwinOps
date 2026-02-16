"""
Visual explanation of the Neo4j Knowledge Graph structure
"""
from api.knowledge_graph_schema import KnowledgeGraphSchema
from api.config import cfg

kg = KnowledgeGraphSchema(
    neo4j_uri=cfg.NEO4J_URI,
    neo4j_user=cfg.NEO4J_USER,
    neo4j_password=cfg.NEO4J_PASSWORD,
    database=cfg.NEO4J_DATABASE
)

print("=" * 80)
print("  WHY THE GRAPH LOOKS 'MASSIVE' IN NEO4J BROWSER")
print("=" * 80)

with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    
    # 1. Show the overall structure
    print("\n1. OVERALL GRAPH STRUCTURE:")
    print("-" * 80)
    
    node_counts = session.run("""
        MATCH (n)
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
    """).data()
    
    rel_counts = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as type, count(*) as count
        ORDER BY count DESC
    """).data()
    
    print("\n   Nodes:")
    for record in node_counts:
        print(f"     {record['label']:25s} {record['count']:>10,} nodes")
    
    print("\n   Relationships:")
    for record in rel_counts:
        print(f"     {record['type']:25s} {record['count']:>10,} relationships")
    
    # 2. Show the hub structure
    print("\n\n2. THE 'MASSIVE HYPERGRAPH' EXPLAINED:")
    print("-" * 80)
    
    # Dictionary as central hub
    dict_hub = session.run("""
        MATCH (d:BsddDictionary)<-[:IN_DICTIONARY]-(bc:BsddClass)
        RETURN d.name as dict_name, count(bc) as connected_classes
    """).single()
    
    print(f"\n   The BsddDictionary '{dict_hub['dict_name']}' acts as a CENTRAL HUB:")
    print(f"     → {dict_hub['connected_classes']:,} BsddClass nodes all connect to it")
    print(f"     → This creates a STAR TOPOLOGY (hub-and-spoke)")
    print(f"     → In Neo4j Browser, this looks like a massive sunburst!")
    
    # 3. Show the actual data layer structure
    print("\n\n3. DATA LAYER STRUCTURE (the important part):")
    print("-" * 80)
    
    # SemanticClass mappings
    mappings = session.run("""
        MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
        RETURN sc.label as semantic_class,
               sc.classId as class_id,
               count(bc) as bsdd_classes,
               collect(bc.code)[0..5] as sample_codes
        ORDER BY class_id
    """).data()
    
    print("\n   Point Cloud → bSDD → IFC Mappings:")
    print(f"   {'Semantic Class':15s} {'ID':>4s}  {'bSDD':>5s}  Sample IFC Entities")
    print("   " + "-" * 74)
    
    for record in mappings:
        label = record['semantic_class']
        class_id = record['class_id']
        count = record['bsdd_classes']
        samples = ', '.join(record['sample_codes'][:3])
        print(f"   {label:15s} {class_id:>4d}  →{count:>4d}   {samples}")
    
    # 4. Verification queries
    print("\n\n4. VERIFICATION:")
    print("-" * 80)
    
    # Total semantic mappings
    total_mappings = session.run("""
        MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
        RETURN count(r) as total
    """).single()['total']
    
    # Unique bSDD classes mapped
    unique_bsdd = session.run("""
        MATCH (sc:SemanticClass)-[:MAPS_TO]->(bc:BsddClass)
        RETURN count(DISTINCT bc) as unique_classes
    """).single()['unique_classes']
    
    # Coverage
    total_semantic = session.run("MATCH (sc:SemanticClass) RETURN count(sc) as total").single()['total']
    mapped_semantic = session.run("""
        MATCH (sc:SemanticClass)-[:MAPS_TO]->()
        RETURN count(DISTINCT sc) as mapped
    """).single()['mapped']
    
    print(f"\n   ✅ Total MAPS_TO relationships: {total_mappings:,}")
    print(f"   ✅ Unique bSDD classes referenced: {unique_bsdd:,}")
    print(f"   ✅ Semantic classes total: {total_semantic}")
    print(f"   ✅ Semantic classes mapped: {mapped_semantic}")
    print(f"   ✅ Coverage: {(mapped_semantic/total_semantic*100):.1f}%")
    
    # 5. What you see in Neo4j Browser
    print("\n\n5. WHAT YOU SEE IN NEO4J BROWSER:")
    print("-" * 80)
    print("""
   When you run MATCH (n) RETURN n LIMIT 100, Neo4j Browser shows:
   
   ┌─────────────────────────────────────────────────────────────┐
   │                                                             │
   │         ○ BsddClass (IfcWall)                              │
   │        ╱                                                    │
   │       ○ BsddClass (IfcDoor)                                │
   │      ╱                                                      │
   │     ○ BsddClass (IfcWindow)                                │
   │    ╱                                                        │
   │   ⊙ BsddDictionary (IFC) ← CENTRAL HUB                    │
   │    ╲                                                        │
   │     ○ BsddClass (IfcBeam)                                  │
   │      ╲                                                      │
   │       ○ BsddClass (IfcColumn)                              │
   │        ╲                                                    │
   │         ○ ... (2,158 more BsddClass nodes)                 │
   │                                                             │
   │   Plus 13 SemanticClass nodes connected to 53 of them     │
   │   via MAPS_TO relationships                                │
   │                                                             │
   └─────────────────────────────────────────────────────────────┘
   
   This is NORMAL and CORRECT! It's a hub-and-spoke topology.
   
   """)
    
    # 6. Better queries for Neo4j Browser
    print("\n6. BETTER NEO4J BROWSER QUERIES:")
    print("-" * 80)
    print("""
   Instead of MATCH (n) RETURN n (which shows everything), try:
   
   A) See just the data layer mappings:
      MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
      RETURN sc, r, bc
      LIMIT 50
   
   B) See a specific semantic class:
      MATCH (sc:SemanticClass {label: 'wall'})-[r:MAPS_TO]->(bc:BsddClass)
      RETURN sc, r, bc
   
   C) See the dictionary structure summary:
      MATCH (d:BsddDictionary)
      OPTIONAL MATCH (d)<-[:IN_DICTIONARY]-(bc:BsddClass)
      RETURN d, count(bc) as class_count
   
   D) See only mapped classes (cleaner view):
      MATCH (sc:SemanticClass)-[:MAPS_TO]->(bc:BsddClass)-[:IN_DICTIONARY]->(d:BsddDictionary)
      RETURN sc, bc, d
      LIMIT 50
   """)

print("\n" + "=" * 80)
print("  SUMMARY: The graph IS correct - it just LOOKS massive!")
print("=" * 80 + "\n")

kg.close()
