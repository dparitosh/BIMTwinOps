"""
bSDD Ingestion Manager with BaseX Synchronization
Handles the full lifecycle of fetching, storing (BaseX), and ingesting (Neo4j) bSDD dictionaries.
"""
import logging
import json
import io
from typing import Optional, Dict, Any, List
from datetime import datetime
try:
    import pandas as pd
except ImportError:
    pd = None

# Import services
from bsdd_ingestion import BSDDIngestionPipeline
from basex_client import BaseXService
from bsdd_client import BSDDClient
from knowledge_graph_schema import KnowledgeGraphSchema

logger = logging.getLogger(__name__)

class SyncManager:
    """
    Coordinates synchronization between bSDD source, BaseX storage, and Neo4j Knowledge Graph.
    Ensures data consistency and auditability.
    """
    
    def __init__(
        self,
        bsdd_client: BSDDClient,
        kg_schema: KnowledgeGraphSchema,
        basex_service: BaseXService,
        ingestion_pipeline: Optional[BSDDIngestionPipeline] = None
    ):
        self.bsdd_client = bsdd_client
        self.kg_schema = kg_schema
        self.basex_service = basex_service
        self.ingestion_pipeline = ingestion_pipeline or BSDDIngestionPipeline(bsdd_client, kg_schema)
        
    def sync_dictionary(self, dictionary_uri: str) -> Dict[str, Any]:
        """
        Full sync process for a dictionary:
        1. Fetch metadata and content from bSDD
        2. Store raw content in BaseX (Source of Truth)
        3. Ingest into Neo4j
        4. Link Neo4j node to BaseX document
        """
        logger.info(f"Starting sync for dictionary: {dictionary_uri}")
        result = {
            "uri": dictionary_uri,
            "status": "pending",
            "steps": [],
            "errors": []
        }
        
        try:
            # Step 1: Fetch Metadata
            dictionaries = self.bsdd_client.get_dictionaries()
            dictionary = next((d for d in dictionaries if d.uri == dictionary_uri), None)
            if not dictionary:
                raise ValueError(f"Dictionary not found: {dictionary_uri}")
            
            result["steps"].append("fetched_metadata")
            
            # Step 2: Fetch Full Content (for archiving)
            # Since the API splits calls (classes, properties), we construct a composite archive object
            # or we store individual parts. 
            # Strategy: Fetch all classes and properties to build a snapshot.
            
            logger.info("Fetching full dictionary content for archive...")
            classes = self.bsdd_client.get_dictionary_classes(dictionary_uri)
            # Check if get_dictionary_properties exists or handle error
            try:
                properties = self.bsdd_client.get_dictionary_properties(dictionary_uri)
            except Exception:
                properties = []
                
            archive_data = {
                "metadata": {
                    "uri": dictionary.uri,
                    "name": dictionary.name,
                    "version": dictionary.version,
                    "organization_code": dictionary.organization_code,
                    "status": dictionary.status,
                    "language_code": dictionary.language_code,
                    "fetched_at": datetime.now().isoformat()
                },
                "classes": [c.__dict__ for c in classes], # Simplistic serialization
                "properties": [p.__dict__ for p in properties]
            }
            
            # Serialize
            # Custom encoder might be needed for sophisticated objects, but dataclasses usually dict-convertible
            # Using str() or default=str for safety on non-standard types
            content_json = json.dumps(archive_data, default=str, indent=2)
            
            # Step 3: Store in BaseX
            logger.info("Storing in BaseX...")
            # Path: dictionaries/{organization}/{name}/{version}.json
            # Sanitize path segments
            def sanitize(s): return "".join(x for x in str(s) if x.isalnum() or x in "-_")
            
            org = sanitize(dictionary.organization_code)
            name = sanitize(dictionary.name)
            ver = sanitize(dictionary.version)
            
            basex_path = f"dictionaries/{org}/{name}/{ver}.json"
            
            self.basex_service.store_document(basex_path, content_json)
            self.basex_service.log_audit(
                "import_dictionary", 
                f"Imported {dictionary_uri} version {dictionary.version}"
            )
            result["steps"].append("stored_in_basex")
            result["basex_path"] = basex_path
            
            # Step 4: Ingest into Neo4j using the Pipeline
            # We modify the pipeline call or update the node afterwards
            logger.info("Ingesting into Neo4j...")
            self.ingestion_pipeline.ingest_dictionary(dictionary_uri)
            
            # Step 5: Update Neo4j Node with BaseX Link
            # The ingestion pipeline created the node. Now we update it.
            # We reuse create_bsdd_dictionary_node which performs a MERGE/SET
            self.kg_schema.create_bsdd_dictionary_node(
                uri=dictionary.uri,
                name=dictionary.name,
                version=dictionary.version,
                organization_code=dictionary.organization_code,
                status=dictionary.status,
                language_code=dictionary.language_code,
                license=dictionary.license,
                release_date=dictionary.release_date,
                more_info_url=dictionary.more_info_url,
                basex_uri=basex_path # The link!
            )
            
            result["steps"].append("ingested_neo4j")
            result["status"] = "success"
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            result["status"] = "failed"
            result["errors"].append(str(e))
            
        return result

    def validate_sync(self, dictionary_uri: str) -> bool:
        """
        Verify that Neo4j and BaseX are in sync for a given dictionary.
        Checks:
        1. Dictionary node exists in Neo4j
        2. Dictionary node has basexUri property
        3. Document exists at basexUri in BaseX
        """
        try:
            # Check Neo4j
            query = f"MATCH (d:BsddDictionary {{uri: $uri}}) RETURN d.basexUri as path, d.version as version"
            result = self.kg_schema.execute_query(query, {"uri": dictionary_uri})
            
            if not result:
                logger.warning(f"Validation failed: Dictionary not found in Neo4j: {dictionary_uri}")
                return False
                
            basex_path = result[0].get("path")
            if not basex_path:
                logger.warning(f"Validation failed: No BaseX URI linked in Neo4j for {dictionary_uri}")
                return False
                
            # Check BaseX
            try:
                # We try to get the document info or content
                self.basex_service.get_document(basex_path)
                return True
            except Exception:
                logger.warning(f"Validation failed: Document not found in BaseX at {basex_path}")
                return False
                
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False

    def import_from_json(self, json_content: Dict[str, Any]) -> Dict[str, Any]:
        """Import dictionary from JSON content"""
        result = {"status": "pending", "steps": []}
        try:
            d_data = json_content.get("dictionary", {})
            # Ensure URI
            if not d_data.get("uri"):
                 d_data["uri"] = f"urn:bsdd:manual:{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # BaseX Path
            def sanitize(s): return "".join(x for x in str(s) if x.isalnum() or x in "-_")
            org = sanitize(d_data.get("organizationCode", "manual"))
            name = sanitize(d_data.get("name", "import"))
            ver = sanitize(d_data.get("version", "1.0"))
            basex_path = f"manual/{org}/{name}/{ver}.json"

            # Store
            self.basex_service.store_document(basex_path, json.dumps(json_content, default=str))
            result["steps"].append("stored_in_basex")

            # Ingest
            self.ingestion_pipeline.ingest_from_json(json_content)
            result["steps"].append("ingested_neo4j")

            # Link (Update Dict Node with BaseX URI)
            self.kg_schema.create_bsdd_dictionary_node(
                uri=d_data.get("uri"),
                name=d_data.get("name"),
                version=d_data.get("version"),
                organization_code=d_data.get("organizationCode"),
                status=d_data.get("status"),
                language_code=d_data.get("languageCode"),
                license=d_data.get("license"),
                release_date=d_data.get("releaseDate"),
                more_info_url=d_data.get("moreInfoUrl"),
                basex_uri=basex_path
            )

            result["status"] = "success"
            result["uri"] = d_data["uri"]

        except Exception as e:
            logger.error(f"JSON Import failed: {e}")
            result["status"] = "failed"
            result["error"] = str(e)
        return result

    def import_from_excel(self, file_content: bytes) -> Dict[str, Any]:
        """Import dictionary from Excel content"""
        if pd is None:
            raise ImportError("pandas not installed")

        try:
            # Read Excel
            xls = pd.ExcelFile(io.BytesIO(file_content))
            
            # Helper to safely get sheet data
            def get_data(sheet_name):
                if sheet_name in xls.sheet_names:
                    return pd.read_excel(xls, sheet_name, keep_default_na=False).to_dict("records")
                return []

            # 1. Dictionary
            d_data = {}
            if "Dictionary" in xls.sheet_names:
                dict_df = pd.read_excel(xls, "Dictionary", keep_default_na=False)
                if not dict_df.empty:
                    # Normalize keys to lowerCamelCase or whatever our node creation expects
                    # For now just passing as is, assuming user follows template
                    d_data = dict_df.iloc[0].to_dict()
                    # Basic normalization
                    if "OrganizationCode" in d_data: d_data["organizationCode"] = d_data.pop("OrganizationCode")
                    if "LanguageCode" in d_data: d_data["languageCode"] = d_data.pop("LanguageCode")
                    if "ReleaseDate" in d_data: d_data["releaseDate"] = d_data.pop("ReleaseDate")
                    if "MoreInfoUrl" in d_data: d_data["moreInfoUrl"] = d_data.pop("MoreInfoUrl")
                    # Name, URI usually match
                    keys = list(d_data.keys())
                    for k in keys:
                        d_data[k[0].lower() + k[1:]] = d_data.pop(k)

            # 2. Classes
            classes = get_data("Class")
            # Normalize class keys
            for c in classes:
                if "Code" in c: c["code"] = c.pop("Code")
                if "ClassType" in c: c["classType"] = c.pop("ClassType")
                if "RelatedIfcEntityNames" in c: c["relatedIfcEntityNames"] = str(c.pop("RelatedIfcEntityNames")).split(",")
            
            # 3. Properties
            properties = get_data("Property")
            for p in properties:
                if "DataType" in p: p["dataType"] = p.pop("DataType")
                if "PhysicalQuantity" in p: p["physicalQuantity"] = p.pop("PhysicalQuantity")

            # Assemble JSON
            json_content = {
                "dictionary": d_data,
                "classes": classes,
                "properties": properties
            }
            
            # Delegate to JSON import
            return self.import_from_json(json_content)

        except Exception as e:
            logger.error(f"Excel Import failed: {e}")
            return {"status": "failed", "error": str(e)}

