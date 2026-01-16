"""
bSDD Data Ingestion Pipeline
Fetches data from buildingSMART Data Dictionary and populates Neo4j knowledge graph
"""
import logging
from typing import List, Optional, Dict
from bsdd_client import BSDDClient, BSDDEnvironment
from knowledge_graph_schema import KnowledgeGraphSchema
import time
from datetime import datetime

logger = logging.getLogger(__name__)


class BSDDIngestionPipeline:
    """
    Pipeline to fetch bSDD data and populate the knowledge graph
    Handles incremental updates and error recovery
    """
    
    def __init__(
        self,
        bsdd_client: BSDDClient,
        kg_schema: KnowledgeGraphSchema,
        batch_size: int = 100
    ):
        """
        Initialize ingestion pipeline
        
        Args:
            bsdd_client: Initialized bSDD API client
            kg_schema: Initialized knowledge graph schema
            batch_size: Number of items to process in each batch
        """
        self.bsdd = bsdd_client
        self.kg = kg_schema
        self.batch_size = batch_size
        self.stats = {
            "dictionaries_processed": 0,
            "classes_processed": 0,
            "properties_processed": 0,
            "relationships_created": 0,
            "errors": []
        }
    
    def ingest_all_dictionaries(
        self,
        organization_filter: Optional[List[str]] = None,
        status_filter: str = "Active"
    ):
        """
        Fetch and ingest all dictionaries from bSDD
        
        Args:
            organization_filter: Optional list of organization codes to include
            status_filter: Status to filter by (Active, Preview, Inactive)
        """
        logger.info("Fetching dictionaries from bSDD...")
        try:
            dictionaries = self.bsdd.get_dictionaries()
            
            # Apply filters
            if organization_filter:
                dictionaries = [
                    d for d in dictionaries
                    if d.organization_code in organization_filter
                ]
            
            if status_filter:
                dictionaries = [
                    d for d in dictionaries
                    if d.status == status_filter
                ]
            
            logger.info(f"Processing {len(dictionaries)} dictionaries...")
            
            for i, dictionary in enumerate(dictionaries):
                try:
                    logger.info(
                        f"[{i+1}/{len(dictionaries)}] Processing: {dictionary.name} ({dictionary.version})"
                    )
                    self.ingest_dictionary(dictionary.uri)
                    self.stats["dictionaries_processed"] += 1
                    
                    # Rate limiting
                    time.sleep(0.5)
                    
                except Exception as e:
                    error_msg = f"Failed to ingest dictionary {dictionary.uri}: {e}"
                    logger.error(error_msg)
                    self.stats["errors"].append(error_msg)
            
            logger.info("Dictionary ingestion completed!")
            self._print_stats()
            
        except Exception as e:
            logger.error(f"Failed to fetch dictionaries: {e}")
            raise
    
    def ingest_dictionary(
        self,
        dictionary_uri: str,
        include_classes: bool = True,
        include_properties: bool = True,
        max_classes: Optional[int] = None
    ):
        """
        Ingest a specific dictionary with its classes and properties
        
        Args:
            dictionary_uri: URI of the dictionary to ingest
            include_classes: Whether to include classes
            include_properties: Whether to include class properties
            max_classes: Maximum number of classes to process (for testing)
        """
        try:
            # Get dictionary info (from cache if available)
            dictionaries = self.bsdd.get_dictionaries()
            dictionary = next(
                (d for d in dictionaries if d.uri == dictionary_uri),
                None
            )
            
            if not dictionary:
                raise ValueError(f"Dictionary not found: {dictionary_uri}")
            
            # Create dictionary node in knowledge graph
            logger.info(f"Creating dictionary node: {dictionary.name}")
            self.kg.create_bsdd_dictionary_node(
                uri=dictionary.uri,
                name=dictionary.name,
                version=dictionary.version,
                organization_code=dictionary.organization_code,
                status=dictionary.status,
                language_code=dictionary.language_code,
                license=dictionary.license,
                release_date=dictionary.release_date,
                more_info_url=dictionary.more_info_url
            )
            
            if include_classes:
                self._ingest_dictionary_classes(
                    dictionary_uri,
                    include_properties,
                    max_classes
                )
        
        except Exception as e:
            logger.error(f"Failed to ingest dictionary {dictionary_uri}: {e}")
            raise
    
    def _ingest_dictionary_classes(
        self,
        dictionary_uri: str,
        include_properties: bool = True,
        max_classes: Optional[int] = None
    ):
        """Ingest all classes from a dictionary"""
        logger.info(f"Fetching classes for dictionary: {dictionary_uri}")
        
        try:
            # Search for all classes (empty search returns all)
            classes = self.bsdd.search_classes(dictionary_uri)
            
            if max_classes:
                classes = classes[:max_classes]
            
            logger.info(f"Found {len(classes)} classes to process")
            
            for i, bsdd_class in enumerate(classes):
                try:
                    if (i + 1) % 10 == 0:
                        logger.info(f"  Processing class {i+1}/{len(classes)}...")
                    
                    # Get full class details
                    detailed_class = self.bsdd.get_class_details(
                        dictionary_uri,
                        bsdd_class.uri,
                        include_properties=include_properties,
                        include_relations=True
                    )
                    
                    # Create class node
                    self.kg.create_bsdd_class_node(
                        uri=detailed_class.uri,
                        code=detailed_class.code,
                        name=detailed_class.name,
                        dictionary_uri=dictionary_uri,
                        definition=detailed_class.definition,
                        class_type=detailed_class.class_type,
                        synonyms=detailed_class.synonyms,
                        related_ifc_entities=detailed_class.related_ifc_entities
                    )
                    
                    self.stats["classes_processed"] += 1
                    
                    # Ingest properties
                    if include_properties and detailed_class.properties:
                        self._ingest_class_properties(
                            detailed_class.uri,
                            detailed_class.properties
                        )
                    
                    # Ingest relationships
                    if detailed_class.relations:
                        self._ingest_class_relationships(
                            detailed_class.uri,
                            detailed_class.relations
                        )
                    
                    # Link parent class if exists
                    if detailed_class.parent_class_uri:
                        try:
                            self.kg.create_class_relationship(
                                detailed_class.uri,
                                detailed_class.parent_class_uri,
                                "IsChildOf"
                            )
                            self.stats["relationships_created"] += 1
                        except Exception as e:
                            logger.warning(f"Failed to link parent class: {e}")
                    
                    # Rate limiting
                    time.sleep(0.3)
                    
                except Exception as e:
                    error_msg = f"Failed to process class {bsdd_class.uri}: {e}"
                    logger.warning(error_msg)
                    self.stats["errors"].append(error_msg)
                    continue
        
        except Exception as e:
            logger.error(f"Failed to fetch classes: {e}")
            raise
    
    def _ingest_class_properties(
        self,
        class_uri: str,
        properties: List[Dict]
    ):
        """Ingest properties for a class"""
        for prop in properties:
            try:
                # Create property node
                self.kg.create_bsdd_property_node(
                    uri=prop.get("uri", ""),
                    code=prop.get("code", ""),
                    name=prop.get("name", ""),
                    definition=prop.get("definition") or prop.get("description"),
                    data_type=prop.get("dataType"),
                    units=prop.get("units", []),
                    physical_quantity=prop.get("physicalQuantity"),
                    dimension=prop.get("dimension"),
                    pattern=prop.get("pattern"),
                    is_required=prop.get("isRequired", False)
                )
                
                # Link property to class
                self.kg.link_class_to_property(
                    class_uri=class_uri,
                    property_uri=prop.get("uri", ""),
                    property_set=prop.get("propertySet"),
                    is_required=prop.get("isRequired", False)
                )
                
                self.stats["properties_processed"] += 1
                self.stats["relationships_created"] += 1
                
            except Exception as e:
                logger.warning(f"Failed to process property: {e}")
                continue
    
    def _ingest_class_relationships(
        self,
        class_uri: str,
        relations: List[Dict]
    ):
        """Ingest relationships between classes"""
        for relation in relations:
            try:
                related_uri = relation.get("relatedClassUri")
                relation_type = relation.get("relationType")
                
                if not related_uri or not relation_type:
                    continue
                
                self.kg.create_class_relationship(
                    from_class_uri=class_uri,
                    to_class_uri=related_uri,
                    relation_type=relation_type
                )
                
                self.stats["relationships_created"] += 1
                
            except Exception as e:
                logger.warning(f"Failed to create relationship: {e}")
                continue
    
    def ingest_ifc_dictionary(
        self,
        version: str = "4.3"
    ):
        """
        Ingest IFC dictionary specifically
        
        Args:
            version: IFC version (e.g., "4.3", "4.0")
        """
        logger.info(f"Ingesting IFC {version} dictionary...")
        
        try:
            # Find IFC dictionary
            dictionaries = self.bsdd.get_dictionaries()
            ifc_dict = next(
                (d for d in dictionaries 
                 if "ifc" in d.name.lower() and version in d.version),
                None
            )
            
            if not ifc_dict:
                logger.warning(f"IFC {version} dictionary not found")
                return
            
            logger.info(f"Found IFC dictionary: {ifc_dict.name} - {ifc_dict.uri}")
            
            # Ingest the dictionary
            self.ingest_dictionary(
                ifc_dict.uri,
                include_classes=True,
                include_properties=True
            )
            
            logger.info("IFC dictionary ingestion completed!")
            
        except Exception as e:
            logger.error(f"Failed to ingest IFC dictionary: {e}")
            raise
    
    def create_ifc_entity_mappings(
        self,
        ifc_entities: List[str]
    ):
        """
        Create mappings between IFC entities and bSDD classes
        
        Args:
            ifc_entities: List of IFC entity names to map
        """
        logger.info(f"Creating IFC entity mappings for {len(ifc_entities)} entities...")
        
        for entity in ifc_entities:
            try:
                # Find bSDD classes mapped to this IFC entity
                mapped_classes = self.bsdd.get_ifc_mappings(entity)
                
                logger.info(f"Found {len(mapped_classes)} mappings for {entity}")
                
                # Create mapping relationships in knowledge graph
                for bsdd_class in mapped_classes:
                    # Note: This assumes IFC elements are already in the graph
                    # In practice, you'd query existing IFC elements and create links
                    logger.debug(f"  {entity} -> {bsdd_class.name}")
                
            except Exception as e:
                logger.warning(f"Failed to map {entity}: {e}")
                continue
    
    def _print_stats(self):
        """Print ingestion statistics"""
        logger.info("\n=== Ingestion Statistics ===")
        logger.info(f"Dictionaries processed: {self.stats['dictionaries_processed']}")
        logger.info(f"Classes processed: {self.stats['classes_processed']}")
        logger.info(f"Properties processed: {self.stats['properties_processed']}")
        logger.info(f"Relationships created: {self.stats['relationships_created']}")
        logger.info(f"Errors encountered: {len(self.stats['errors'])}")
        
        if self.stats['errors']:
            logger.warning("\nFirst 5 errors:")
            for error in self.stats['errors'][:5]:
                logger.warning(f"  - {error}")


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Initialize clients
    bsdd_client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
    
    kg_schema = KnowledgeGraphSchema(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password")
    )
    
    try:
        # Create schema first
        logger.info("Creating knowledge graph schema...")
        kg_schema.create_schema()
        
        # Initialize pipeline
        pipeline = BSDDIngestionPipeline(bsdd_client, kg_schema)
        
        # Example 1: Ingest IFC dictionary only
        logger.info("\n=== Ingesting IFC Dictionary ===")
        pipeline.ingest_ifc_dictionary(version="4.3")
        
        # Example 2: Ingest specific dictionary
        # pipeline.ingest_dictionary(
        #     dictionary_uri="https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
        #     max_classes=50  # Limit for testing
        # )
        
        # Example 3: Ingest all active dictionaries from specific organizations
        # pipeline.ingest_all_dictionaries(
        #     organization_filter=["buildingsmart", "nlsfb"],
        #     status_filter="Active"
        # )
        
        # Example 4: Create IFC entity mappings
        # common_ifc_entities = [
        #     "IfcWall", "IfcDoor", "IfcWindow", "IfcSlab", "IfcBeam",
        #     "IfcColumn", "IfcSpace", "IfcBuildingStorey", "IfcBuilding"
        # ]
        # pipeline.create_ifc_entity_mappings(common_ifc_entities)
        
    finally:
        kg_schema.close()
