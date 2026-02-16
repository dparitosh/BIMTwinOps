#!/usr/bin/env python3
"""
Neo4j Schema Initialization Script

This script sets up the Neo4j knowledge graph schema for BIMTwinOps:
1. Creates constraints (uniqueness for URIs, GlobalIDs)
2. Creates indexes for common query patterns
3. Optionally seeds sample bSDD data

Usage:
    # From repository root:
    python backend/scripts/init_neo4j_schema.py

    # With sample data:
    python backend/scripts/init_neo4j_schema.py --seed

    # Custom Neo4j connection:
    python backend/scripts/init_neo4j_schema.py --uri bolt://localhost:7687 --user neo4j --password mypassword

Requirements:
    - Neo4j server running
    - NEO4J_PASSWORD environment variable (or --password argument)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(Path(__file__).parent.parent / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_schema(uri: str, user: str, password: str, database: str = None) -> bool:
    """Initialize Neo4j schema with constraints and indexes."""
    from api.knowledge_graph_schema import KnowledgeGraphSchema
    
    logger.info("Connecting to Neo4j at %s (database=%s)...", uri, database or 'default')
    
    try:
        schema = KnowledgeGraphSchema(
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            database=database
        )
        
        logger.info("Creating schema constraints and indexes...")
        schema.create_schema()
        
        # Get schema info
        info = schema.get_schema_info()
        logger.info("Schema initialized successfully!")
        logger.info("  Constraints: %d", len(info.get("nodes", [])))
        logger.info("  Indexes: %d", len(info.get("relationships", [])))
        
        schema.close()
        return True
        
    except Exception as e:
        logger.error("Failed to initialize schema: %s", e)
        return False


def seed_sample_data(uri: str, user: str, password: str, database: str = None) -> bool:
    """Seed Neo4j with sample bSDD data for development."""
    from api.knowledge_graph_schema import KnowledgeGraphSchema
    
    logger.info("Seeding sample data...")
    
    try:
        schema = KnowledgeGraphSchema(
            neo4j_uri=uri,
            neo4j_user=user,
            neo4j_password=password,
            database=database
        )
        
        # Sample bSDD Dictionary
        logger.info("  Creating sample bSDD dictionary...")
        schema.create_bsdd_dictionary_node(
            uri="https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
            name="IFC",
            version="4.3",
            organization_code="buildingsmart",
            status="Preview",
            language_code="en",
            license="CC BY-ND 4.0"
        )
        
        # Sample bSDD Classes
        sample_classes = [
            {
                "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall",
                "code": "IfcWall",
                "name": "Wall",
                "definition": "The wall represents a vertical construction that may bound or subdivide spaces.",
                "class_type": "Class",
                "dictionary_uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
                "related_ifc_entities": ["IfcWall", "IfcWallStandardCase"],
                "synonyms": ["Wall", "Partition", "Barrier"]
            },
            {
                "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcDoor",
                "code": "IfcDoor",
                "name": "Door",
                "definition": "The door is a building element that is predominately used to provide controlled access for people.",
                "class_type": "Class",
                "dictionary_uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
                "related_ifc_entities": ["IfcDoor", "IfcDoorStandardCase"],
                "synonyms": ["Door", "Entrance", "Portal"]
            },
            {
                "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWindow",
                "code": "IfcWindow",
                "name": "Window",
                "definition": "The window is a building element that is predominately used to provide natural light and ventilation.",
                "class_type": "Class",
                "dictionary_uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
                "related_ifc_entities": ["IfcWindow", "IfcWindowStandardCase"],
                "synonyms": ["Window", "Glazing", "Opening"]
            },
        ]
        
        for cls in sample_classes:
            logger.info("  Creating class: %s", cls["name"])
            schema.create_bsdd_class_node(**cls)
        
        # Sample bSDD Properties
        sample_properties = [
            {
                "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/FireRating",
                "code": "FireRating",
                "name": "Fire Rating",
                "definition": "The fire rating of the element in minutes.",
                "data_type": "Real",
                "units": ["minute", "min"],
                "physical_quantity": "Time"
            },
            {
                "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/ThermalTransmittance",
                "code": "ThermalTransmittance",
                "name": "Thermal Transmittance",
                "definition": "The rate of heat transfer through the element (U-value).",
                "data_type": "Real",
                "units": ["W/(m²·K)"],
                "physical_quantity": "Thermal Transmittance"
            },
            {
                "uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/prop/AcousticRating",
                "code": "AcousticRating",
                "name": "Acoustic Rating",
                "definition": "The acoustic rating (sound reduction index) in decibels.",
                "data_type": "Real",
                "units": ["dB"],
                "physical_quantity": "Sound Level"
            },
        ]
        
        for prop in sample_properties:
            logger.info("  Creating property: %s", prop["name"])
            schema.create_bsdd_property_node(**prop)
        
        # Link properties to classes
        logger.info("  Linking properties to classes...")
        with schema._session() as session:
            # FireRating for Wall
            session.run("""
                MATCH (c:BsddClass {code: 'IfcWall'})
                MATCH (p:BsddProperty {code: 'FireRating'})
                MERGE (c)-[:HAS_PROPERTY {isRequired: false, propertySet: 'Pset_WallCommon'}]->(p)
            """)
            
            # ThermalTransmittance for Window
            session.run("""
                MATCH (c:BsddClass {code: 'IfcWindow'})
                MATCH (p:BsddProperty {code: 'ThermalTransmittance'})
                MERGE (c)-[:HAS_PROPERTY {isRequired: false, propertySet: 'Pset_WindowCommon'}]->(p)
            """)
            
            # AcousticRating for Door
            session.run("""
                MATCH (c:BsddClass {code: 'IfcDoor'})
                MATCH (p:BsddProperty {code: 'AcousticRating'})
                MERGE (c)-[:HAS_PROPERTY {isRequired: false, propertySet: 'Pset_DoorCommon'}]->(p)
            """)
        
        # Sample Semantic Classes (for point cloud)
        semantic_classes = [
            {"label": "ceiling", "class_id": 0, "color": "#F0E68C"},
            {"label": "floor", "class_id": 1, "color": "#8B4513"},
            {"label": "wall", "class_id": 2, "color": "#D2691E"},
            {"label": "beam", "class_id": 3, "color": "#A0522D"},
            {"label": "column", "class_id": 4, "color": "#CD853F"},
            {"label": "window", "class_id": 5, "color": "#87CEEB"},
            {"label": "door", "class_id": 6, "color": "#DEB887"},
            {"label": "table", "class_id": 7, "color": "#BC8F8F"},
            {"label": "chair", "class_id": 8, "color": "#F4A460"},
            {"label": "sofa", "class_id": 9, "color": "#DAA520"},
            {"label": "bookcase", "class_id": 10, "color": "#B8860B"},
            {"label": "board", "class_id": 11, "color": "#FFE4B5"},
            {"label": "clutter", "class_id": 12, "color": "#808080"},
        ]
        
        logger.info("  Creating semantic classes for point cloud...")
        for sc in semantic_classes:
            with schema._session() as session:
                session.run("""
                    MERGE (sc:SemanticClass {label: $label})
                    SET sc.classId = $class_id,
                        sc.color = $color
                """, sc)
        
        schema.close()
        logger.info("Sample data seeded successfully!")
        return True
        
    except Exception as e:
        logger.error("Failed to seed sample data: %s", e)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Initialize Neo4j schema for BIMTwinOps"
    )
    parser.add_argument(
        "--uri",
        default=os.getenv("NEO4J_URI", ""),
        help="Neo4j connection URI (or set NEO4J_URI env var)"
    )
    parser.add_argument(
        "--user",
        default=os.getenv("NEO4J_USER", ""),
        help="Neo4j username (or set NEO4J_USER env var)"
    )
    parser.add_argument(
        "--password",
        default=os.getenv("NEO4J_PASSWORD"),
        help="Neo4j password (or set NEO4J_PASSWORD env var)"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed sample bSDD data for development"
    )
    parser.add_argument(
        "--database",
        default=os.getenv("NEO4J_DATABASE"),
        help="Neo4j database name (or set NEO4J_DATABASE env var)"
    )
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Skip schema creation, only seed data"
    )
    
    args = parser.parse_args()
    
    if not args.password:
        logger.error("Neo4j password required. Set NEO4J_PASSWORD or use --password")
        sys.exit(1)
    
    success = True
    
    # Initialize schema
    if not args.skip_schema:
        if not init_schema(args.uri, args.user, args.password, args.database):
            success = False
    
    # Seed sample data
    if args.seed:
        if not seed_sample_data(args.uri, args.user, args.password, args.database):
            success = False
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
