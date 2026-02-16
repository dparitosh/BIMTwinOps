#!/usr/bin/env python3
"""
IFC 4.3 Dictionary Ingestion Script

Fetches and ingests the full IFC 4.3 dictionary from bSDD into Neo4j.
This includes:
- 2163+ classes
- Properties for each class
- Relationships between classes

Usage:
    # Full ingestion:
    python backend/scripts/ingest_ifc43.py

    # Test with limited classes:
    python backend/scripts/ingest_ifc43.py --max-classes 100

    # With detailed class fetching (slower but more complete):
    python backend/scripts/ingest_ifc43.py --fetch-details

Environment Variables:
    NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, NEO4J_DATABASE
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

# Load .env from backend directory
load_dotenv(Path(__file__).parent.parent / ".env")

from api.bsdd_client import BSDDClient, BSDDEnvironment
from api.knowledge_graph_schema import KnowledgeGraphSchema
from api.bsdd_ingestion import BSDDIngestionPipeline
from api.config import cfg

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Ingest IFC 4.3 dictionary from bSDD")
    parser.add_argument(
        "--uri",
        default=cfg.NEO4J_URI,
        help="Neo4j connection URI"
    )
    parser.add_argument(
        "--user",
        default=cfg.NEO4J_USER,
        help="Neo4j username"
    )
    parser.add_argument(
        "--password",
        default=cfg.NEO4J_PASSWORD,
        help="Neo4j password"
    )
    parser.add_argument(
        "--database",
        default=cfg.NEO4J_DATABASE,
        help="Neo4j database name"
    )
    parser.add_argument(
        "--max-classes",
        type=int,
        default=None,
        help="Maximum number of classes to ingest (for testing)"
    )
    parser.add_argument(
        "--fetch-details",
        action="store_true",
        help="Fetch detailed class information (slower, more complete)"
    )
    parser.add_argument(
        "--include-properties",
        action="store_true",
        default=True,
        help="Include class properties (default: True)"
    )
    
    args = parser.parse_args()
    
    if not args.password:
        logger.error("Neo4j password required. Set NEO4J_PASSWORD environment variable")
        sys.exit(1)
    
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("IFC 4.3 Dictionary Ingestion")
    logger.info("=" * 60)
    logger.info("Started: %s", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("")
    
    try:
        # Initialize clients
        logger.info("Initializing bSDD client...")
        bsdd_client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
        
        logger.info("Connecting to Neo4j at %s (database=%s)...", args.uri, args.database)
        kg_schema = KnowledgeGraphSchema(
            neo4j_uri=args.uri,
            neo4j_user=args.user,
            neo4j_password=args.password,
            database=args.database
        )
        
        logger.info("Initializing ingestion pipeline...")
        pipeline = BSDDIngestionPipeline(
            bsdd_client=bsdd_client,
            kg_schema=kg_schema,
            batch_size=100
        )
        
        # Find IFC 4.3 dictionary
        logger.info("")
        logger.info("Finding IFC 4.3 dictionary...")
        dictionaries = bsdd_client.get_dictionaries()
        ifc43 = next(
            (d for d in dictionaries if d.name == "IFC" and "4.3" in d.version),
            None
        )
        
        if not ifc43:
            logger.error("IFC 4.3 dictionary not found!")
            sys.exit(1)
        
        logger.info("✓ Found IFC 4.3:")
        logger.info("  Name: %s", ifc43.name)
        logger.info("  Version: %s", ifc43.version)
        logger.info("  Status: %s", ifc43.status)
        logger.info("  URI: %s", ifc43.uri)
        logger.info("")
        
        # Update pipeline to use optimized ingestion
        logger.info("Starting ingestion...")
        logger.info("  Max classes: %s", args.max_classes or "ALL (2163+)")
        logger.info("  Include properties: %s", args.include_properties)
        logger.info("  Fetch detailed classes: %s", args.fetch_details)
        logger.info("")
        
        # Monkey-patch the _ingest_dictionary_classes method to pass fetch_detailed_classes
        original_method = pipeline._ingest_dictionary_classes
        
        def patched_method(dict_uri, include_props=True, max_cls=None):
            return original_method(
                dict_uri,
                include_props,
                max_cls,
                fetch_detailed_classes=args.fetch_details
            )
        
        pipeline._ingest_dictionary_classes = patched_method
        
        # Run ingestion
        pipeline.ingest_dictionary(
            dictionary_uri=ifc43.uri,
            include_classes=True,
            include_properties=args.include_properties,
            max_classes=args.max_classes
        )
        
        # Print results
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Ingestion Complete!")
        logger.info("=" * 60)
        logger.info("Finished: %s", end_time.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("Duration: %s", str(duration).split('.')[0])
        logger.info("")
        logger.info("Statistics:")
        logger.info("  Dictionaries: %d", pipeline.stats["dictionaries_processed"])
        logger.info("  Classes: %d", pipeline.stats["classes_processed"])
        logger.info("  Properties: %d", pipeline.stats["properties_processed"])
        logger.info("  Relationships: %d", pipeline.stats["relationships_created"])
        logger.info("  Errors: %d", len(pipeline.stats["errors"]))
        
        if pipeline.stats["errors"]:
            logger.info("")
            logger.info("Errors encountered:")
            for error in pipeline.stats["errors"][:10]:  # Show first 10
                logger.warning("  - %s", error)
            if len(pipeline.stats["errors"]) > 10:
                logger.warning("  ... and %d more", len(pipeline.stats["errors"]) - 10)
        
        # Get graph statistics
        with kg_schema.driver.session(database=args.database) as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            node_counts = {r["label"]: r["count"] for r in result}
            
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            rel_counts = {r["type"]: r["count"] for r in result}
        
        logger.info("")
        logger.info("Neo4j Graph Statistics:")
        logger.info("  Node Types:")
        for label, count in node_counts.items():
            logger.info("    %s: %d", label, count)
        logger.info("  Relationship Types:")
        for rel_type, count in rel_counts.items():
            logger.info("    %s: %d", rel_type, count)
        
        logger.info("=" * 60)
        
        kg_schema.close()
        sys.exit(0)
        
    except Exception as e:
        logger.error("Ingestion failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
