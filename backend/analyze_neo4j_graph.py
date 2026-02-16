"""
Comprehensive Neo4j Knowledge Graph Analysis
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
print("  COMPLETE NEO4J KNOWLEDGE GRAPH ANALYSIS")
print("=" * 80)

with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
    
    # 1. Get all node labels and counts
    print("\n1. NODE TYPES AND COUNTS:")
    print("-" * 80)
    result = session.run("""
        MATCH (n)
        RETURN labels(n) as labels, count(*) as count
        ORDER BY count DESC
    """)
    
    total_nodes = 0
    for record in result:
        labels = record["labels"]
        count = record["count"]
        total_nodes += count
        print(f"   {', '.join(labels):50s} {count:>10,}")
    
    print(f"\n   {'TOTAL NODES':50s} {total_nodes:>10,}")
    
    # 2. Get all relationship types and counts
    print("\n\n2. RELATIONSHIP TYPES AND COUNTS:")
    print("-" * 80)
    result = session.run("""
        MATCH ()-[r]->()
        RETURN type(r) as rel_type, count(*) as count
        ORDER BY count DESC
    """)
    
    total_rels = 0
    for record in result:
        rel_type = record["rel_type"]
        count = record["count"]
        total_rels += count
        print(f"   {rel_type:50s} {count:>10,}")
    
    print(f"\n   {'TOTAL RELATIONSHIPS':50s} {total_rels:>10,}")
    
    # 3. Graph structure patterns
    print("\n\n3. GRAPH STRUCTURE PATTERNS:")
    print("-" * 80)
    
    # bSDD specific nodes
    print("\n   bSDD Component:")
    bsdd_nodes = session.run("""
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label STARTS WITH 'Bsdd')
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
    """)
    for record in bsdd_nodes:
        print(f"     - {record['label']:40s} {record['count']:>10,}")
    
    # Semantic Class nodes
    print("\n   Point Cloud Semantic:")
    semantic = session.run("""
        MATCH (n:SemanticClass)
        RETURN count(n) as count
    """)
    print(f"     - SemanticClass {semantic.single()['count']:>33,}")
    
    # Dictionary/Classification nodes
    print("\n   IFC/Classification:")
    ifc_nodes = session.run("""
        MATCH (n)
        WHERE any(label IN labels(n) WHERE label IN ['Dictionary', 'Class', 'Classification'])
        RETURN labels(n)[0] as label, count(*) as count
        ORDER BY count DESC
    """)
    for record in ifc_nodes:
        print(f"     - {record['label']:40s} {record['count']:>10,}")
    
    # 4. Key relationship patterns
    print("\n\n4. KEY RELATIONSHIP PATTERNS:")
    print("-" * 80)
    
    patterns = [
        ("SemanticClass → bSDD", "MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass) RETURN count(r) as count"),
        ("BsddClass → Dictionary", "MATCH (bc:BsddClass)-[r:IN_DICTIONARY]->(d) RETURN count(r) as count"),
        ("Class → Properties", "MATCH (c)-[r:HAS_PROPERTY]->(p) RETURN count(r) as count"),
        ("Dictionary Hierarchy", "MATCH (d)-[r:HAS_CLASS|CONTAINS]->(c) RETURN count(r) as count"),
        ("Property Relations", "MATCH (p)-[r:PROPERTY_OF|HAS_ALLOWED_VALUE]->(n) RETURN count(r) as count"),
    ]
    
    for pattern_name, query in patterns:
        result = session.run(query)
        count = result.single()["count"]
        if count > 0:
            print(f"   {pattern_name:40s} {count:>10,} relationships")
    
    # 5. Sample nodes from each type
    print("\n\n5. SAMPLE NODES (showing first 3 of each major type):")
    print("-" * 80)
    
    # BsddClass samples
    print("\n   BsddClass samples:")
    bsdd_samples = session.run("""
        MATCH (n:BsddClass)
        RETURN n.name as name, n.code as code
        LIMIT 3
    """)
    for record in bsdd_samples:
        print(f"     - {record['name']:30s} ({record['code']})")
    
    # SemanticClass samples
    print("\n   SemanticClass samples:")
    semantic_samples = session.run("""
        MATCH (n:SemanticClass)
        RETURN n.label as label, n.classId as id
        ORDER BY n.classId
        LIMIT 3
    """)
    for record in semantic_samples:
        print(f"     - {record['label']:30s} (ID: {record['id']})")
    
    # Dictionary samples
    print("\n   Dictionary samples:")
    dict_samples = session.run("""
        MATCH (n)
        WHERE 'Dictionary' IN labels(n) OR 'BsddDictionary' IN labels(n)
        RETURN labels(n)[0] as type, coalesce(n.name, n.uri) as name
        LIMIT 3
    """)
    for record in dict_samples:
        print(f"     - {record['type']:30s} {record['name']}")
    
    # 6. Connectivity analysis
    print("\n\n6. GRAPH CONNECTIVITY:")
    print("-" * 80)
    
    # Average degree
    avg_degree = session.run("""
        MATCH (n)
        WITH n, size((n)-[]-()) as degree
        RETURN avg(degree) as avg_degree, max(degree) as max_degree
    """)
    record = avg_degree.single()
    print(f"   Average node degree: {record['avg_degree']:.2f}")
    print(f"   Maximum node degree: {record['max_degree']}")
    
    # Hub nodes (most connected)
    print("\n   Top 5 most connected nodes:")
    hubs = session.run("""
        MATCH (n)
        WITH n, size((n)-[]-()) as degree
        WHERE degree > 0
        RETURN labels(n)[0] as type, 
               coalesce(n.name, n.label, n.code, n.uri) as name,
               degree
        ORDER BY degree DESC
        LIMIT 5
    """)
    for record in hubs:
        print(f"     {record['degree']:>5} connections - {record['type']:20s} {record['name']}")
    
    # 7. Semantic → bSDD → IFC chain
    print("\n\n7. COMPLETE DATA LAYER VERIFICATION:")
    print("-" * 80)
    print("\n   SemanticClass → BsddClass → IFC mapping chain:")
    
    mapping_chain = session.run("""
        MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
        RETURN sc.label as semantic_label,
               count(bc) as bsdd_count,
               collect(bc.code)[0..3] as sample_codes
        ORDER BY bsdd_count DESC
    """)
    
    for record in mapping_chain:
        label = record['semantic_label']
        count = record['bsdd_count']
        samples = record['sample_codes']
        print(f"     {label:15s} → {count:2d} bSDD classes (e.g., {', '.join(samples[:2])}...)")

print("\n" + "=" * 80)
print("  ANALYSIS COMPLETE")
print("=" * 80 + "\n")

kg.close()
