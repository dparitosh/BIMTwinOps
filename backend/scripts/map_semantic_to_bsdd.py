#!/usr/bin/env python3
"""
Create SemanticClass → BsddClass Mappings in Neo4j

This script establishes relationships between point cloud semantic classes
and their corresponding bSDD classes in the knowledge graph.

Usage:
    python backend/scripts/map_semantic_to_bsdd.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from api.knowledge_graph_schema import KnowledgeGraphSchema
from api.config import cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Mapping rules: SemanticClass label → list of preferred bSDD class codes (in priority order)
SEMANTIC_TO_BSDD_MAPPING = {
    "ceiling": ["IfcCoveringCEILING", "IfcCovering"],
    "floor": ["IfcSlabFLOOR", "IfcSlab", "IfcCoveringFLOORING"],
    "wall": ["IfcWall", "IfcWallSTANDARD"],
    "beam": ["IfcBeam", "IfcBeamBEAM"],
    "column": ["IfcColumn", "IfcColumnCOLUMN"],
    "window": ["IfcWindow", "IfcWindowWINDOW"],
    "door": ["IfcDoor", "IfcDoorDOOR"],
    "table": ["IfcFurnitureTABLE", "IfcFurniture"],
    "chair": ["IfcFurnitureCHAIR", "IfcFurniture"],
    "sofa": ["IfcFurnitureSOFA", "IfcFurniture"],
    "bookcase": ["IfcFurniture"],
    "board": ["IfcCoveringSKIRTINGBOARD", "IfcDistributionBoard"],
    # "clutter" intentionally has no mapping
}


def create_mappings():
    """Create MAPS_TO relationships between SemanticClass and BsddClass nodes"""
    logger.info("=" * 60)
    logger.info("Creating SemanticClass → BsddClass Mappings")
    logger.info("=" * 60)
    
    kg = KnowledgeGraphSchema(
        neo4j_uri=cfg.NEO4J_URI,
        neo4j_user=cfg.NEO4J_USER,
        neo4j_password=cfg.NEO4J_PASSWORD,
        database=cfg.NEO4J_DATABASE
    )
    
    stats = {
        "semantic_classes": 0,
        "mappings_created": 0,
        "no_match": []
    }
    
    with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
        for semantic_label, bsdd_codes in SEMANTIC_TO_BSDD_MAPPING.items():
            stats["semantic_classes"] += 1
            
            # Find the semantic class
            result = session.run("""
                MATCH (sc:SemanticClass {label: $label})
                RETURN sc.label as label, sc.classId as id
            """, label=semantic_label)
            
            semantic_node = result.single()
            if not semantic_node:
                logger.warning(f"SemanticClass '{semantic_label}' not found")
                continue
            
            # Try to match with bSDD classes in priority order
            mapped = False
            for bsdd_code in bsdd_codes:
                result = session.run("""
                    MATCH (sc:SemanticClass {label: $semantic_label})
                    MATCH (bc:BsddClass)
                    WHERE bc.code = $bsdd_code OR bc.code CONTAINS $bsdd_code
                    MERGE (sc)-[r:MAPS_TO]->(bc)
                    SET r.confidence = $confidence,
                        r.priority = $priority,
                        r.mappingType = 'auto'
                    RETURN bc.name as name, bc.code as code
                    LIMIT 1
                """, 
                semantic_label=semantic_label,
                bsdd_code=bsdd_code,
                confidence=1.0 if bsdd_codes.index(bsdd_code) == 0 else 0.8,
                priority=bsdd_codes.index(bsdd_code)
                )
                
                match = result.single()
                if match:
                    logger.info(f"✓ {semantic_label:12s} [ID:{semantic_node['id']:2d}] → {match['name']} ({match['code']})")
                    stats["mappings_created"] += 1
                    mapped = True
                    break
            
            if not mapped:
                logger.warning(f"✗ {semantic_label:12s} [ID:{semantic_node['id']:2d}] → No bSDD match found")
                stats["no_match"].append(semantic_label)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Mapping Complete")
    logger.info("=" * 60)
    logger.info(f"Semantic classes processed: {stats['semantic_classes']}")
    logger.info(f"Mappings created: {stats['mappings_created']}")
    logger.info(f"Unmatched: {len(stats['no_match'])}")
    if stats['no_match']:
        logger.info(f"  Unmatched classes: {', '.join(stats['no_match'])}")
    
    # Get relationship counts
    with kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
        result = session.run("""
            MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
            RETURN count(r) as count
        """)
        total_mappings = result.single()["count"]
        logger.info(f"\nTotal MAPS_TO relationships in graph: {total_mappings}")
    
    kg.close()


if __name__ == "__main__":
    try:
        create_mappings()
    except Exception as e:
        logger.error(f"Failed to create mappings: {e}", exc_info=True)
        sys.exit(1)
