"""
Knowledge Graph API Routes for BIMTwinOps
Provides REST endpoints for bSDD integration, GenAI queries, and knowledge graph operations
"""
import os
import json
import logging
from typing import List, Dict, Optional, Any

from fastapi import APIRouter, HTTPException, Query, Body, UploadFile, File, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .bsdd_client import BSDDClient, BSDDEnvironment
from .knowledge_graph_schema import KnowledgeGraphSchema
from .genai_service import BIMTwinOpsGenAI
from .basex_client import BaseXService
from .sync_manager import SyncManager
from .agents.compliance_agent import ComplianceAgent
from .ifc_mapping import (
    validate_ifc_ids_references,
    get_bsdd_dictionary_uri,
    get_bsdd_class_uri,
    get_bsdd_property_uri,
    get_bsdd_material_uri,
    map_bsdd_dictionary_to_ifc_classification,
    map_bsdd_class_to_ifc_classification_reference,
    map_bsdd_property_to_ifc_property_single_value,
    map_bsdd_material_to_ifc_material
)

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

# Initialize clients (singleton pattern)
_bsdd_client = None
_kg_schema = None
_genai_service = None
_basex_service = None
_sync_manager = None


def get_bsdd_client() -> BSDDClient:
    """Get or create bSDD client singleton"""
    global _bsdd_client
    if _bsdd_client is None:
        _bsdd_client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
    return _bsdd_client


def get_kg_schema() -> KnowledgeGraphSchema:
    """Get or create knowledge graph schema singleton"""
    global _kg_schema
    if _kg_schema is None:
        neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            raise HTTPException(
                status_code=500,
                detail="NEO4J_PASSWORD environment variable is required"
            )
        _kg_schema = KnowledgeGraphSchema(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=neo4j_password
        )
    return _kg_schema


def get_basex_service() -> BaseXService:
    global _basex_service
    if _basex_service is None:
        _basex_service = BaseXService()
    return _basex_service


def get_sync_manager() -> SyncManager:
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = SyncManager(
            bsdd_client=get_bsdd_client(),
            kg_schema=get_kg_schema(),
            basex_service=get_basex_service()
        )
    return _sync_manager


def get_genai_service() -> BIMTwinOpsGenAI:
    """Get or create GenAI service singleton"""
    global _genai_service
    if _genai_service is None:
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not azure_endpoint or not azure_api_key:
            raise HTTPException(
                status_code=500,
                detail="Azure OpenAI credentials not configured"
            )
        
        _genai_service = BIMTwinOpsGenAI(
            azure_endpoint=azure_endpoint,
            azure_api_key=azure_api_key,
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD")
        )
    return _genai_service


# =============================================================================
# Request/Response Models
# =============================================================================

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., description="Natural language search query")
    context_type: str = Field("all", description="Context type: bsdd, ifc, pointcloud, all")
    limit: int = Field(10, ge=1, le=100, description="Maximum results")


class PropertyRecommendationRequest(BaseModel):
    element_type: str = Field(..., description="Building element type (e.g., IfcWall)")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ClassificationSuggestionRequest(BaseModel):
    element_description: str = Field(..., description="Element description")
    available_systems: Optional[List[str]] = Field(
        None,
        description="Classification systems to consider"
    )


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        None,
        description="Previous conversation messages"
    )


class BSDDSearchRequest(BaseModel):
    dictionary_uri: Optional[str] = Field(None, description="Specific dictionary URI")
    search_text: Optional[str] = Field(None, description="Search text")
    related_ifc_entity: Optional[str] = Field(None, description="IFC entity filter")
    language_code: str = Field("en-GB", description="Language code")


class AdvancedSearchRequest(BaseModel):
    query: Optional[str] = Field(None, description="Text to search in code, name, or definition")
    type: Optional[str] = Field(None, description="'class', 'property', or None (both)")
    status: Optional[str] = Field(None, description="Status filter (Active, Inactive, Preview)")
    dictionary_uri: Optional[str] = Field(None, description="Restrict to a specific dictionary")
    description: Optional[str] = Field(None, description="Search in description field")
    limit: int = Field(20, ge=1, le=100, description="Max results")


class BatchClassAssociationRequest(BaseModel):
    associations: List[Dict[str, Any]]


class BatchAssociationResult(BaseModel):
    index: int
    success: bool
    error: Optional[str] = None
    ifc_object: Optional[dict] = None


# =============================================================================
# Compliance & Validation Endpoints
# =============================================================================

@router.post("/suggest-fixes")
async def suggest_fixes(entities: list = Body(...)):
    """
    Use GenAI (LLM) to suggest automated fixes for non-compliant IFC entities.
    Expects a JSON array of entities.
    Returns suggestions for each entity.
    """
    agent = ComplianceAgent()
    results = [agent.suggest_fixes(e) for e in entities]
    return {"suggestions": results}


@router.post("/check-compliance")
async def check_compliance(entities: list = Body(...)):
    """
    Check IFC entities for bSDD compliance using ComplianceAgent.
    Expects a JSON array of entities with 'uri', 'classification', 'property', 'material'.
    Returns compliance results.
    """
    agent = ComplianceAgent()
    result = agent.validate_entities(entities)
    return result


@router.post("/validate-ids-reference")
async def validate_ids_reference(entities: list = Body(...)):
    """
    Validate a list of IFC/IDS entities for correct bSDD referencing.
    Expects a JSON array of entities, each with a 'uri' field.
    Returns errors and compliance status.
    """
    result = validate_ifc_ids_references(entities)
    return result


# =============================================================================
# IDS URI Endpoints
# =============================================================================

@router.get("/ids-uri/dictionary")
async def ids_uri_dictionary(organization_code: str, dictionary_code: str, version: str):
    """Generate IDS-compliant URI for bSDD dictionary"""
    return {"uri": get_bsdd_dictionary_uri(organization_code, dictionary_code, version)}


@router.get("/ids-uri/class")
async def ids_uri_class(organization_code: str, dictionary_code: str, version: str, class_code: str):
    """Generate IDS-compliant URI for bSDD class"""
    return {"uri": get_bsdd_class_uri(organization_code, dictionary_code, version, class_code)}


@router.get("/ids-uri/property")
async def ids_uri_property(organization_code: str, dictionary_code: str, version: str, property_code: str):
    """Generate IDS-compliant URI for bSDD property"""
    return {"uri": get_bsdd_property_uri(organization_code, dictionary_code, version, property_code)}


@router.get("/ids-uri/material")
async def ids_uri_material(organization_code: str, dictionary_code: str, version: str, material_code: str):
    """Generate IDS-compliant URI for bSDD material"""
    return {"uri": get_bsdd_material_uri(organization_code, dictionary_code, version, material_code)}


# =============================================================================
# Batch Association Endpoints
# =============================================================================

@router.post("/batch-associate/classes", status_code=status.HTTP_200_OK)
async def batch_associate_classes(request: BatchClassAssociationRequest):
    """Batch associate bSDD classes with IFC objects"""
    results = []
    for idx, assoc in enumerate(request.associations):
        try:
            ifc_obj = map_bsdd_class_to_ifc_classification_reference(assoc.get("bsdd_class", {}))
            results.append(BatchAssociationResult(index=idx, success=True, ifc_object=ifc_obj))
        except Exception as e:
            results.append(BatchAssociationResult(index=idx, success=False, error=str(e)))
    return {"results": [r.dict() for r in results]}


# =============================================================================
# Export Endpoints
# =============================================================================

@router.get("/export-ifc/{uri:path}")
async def export_dictionary_as_ifc(uri: str):
    """Export bSDD dictionary as IFC-compliant objects"""
    try:
        kg = get_kg_schema()
        query = "MATCH (d:BsddDictionary {uri: $uri}) RETURN d"
        results = kg.execute_query(query, {"uri": uri})
        if not results:
            raise HTTPException(status_code=404, detail="Dictionary not found")
        dict_data = dict(results[0]["d"])
        ifc_dict = map_bsdd_dictionary_to_ifc_classification(dict_data)

        query = "MATCH (c:BsddClass)-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $uri}) RETURN c"
        class_results = kg.execute_query(query, {"uri": uri})
        ifc_classes = [map_bsdd_class_to_ifc_classification_reference(dict(cr["c"])) for cr in class_results]

        query = "MATCH (p:BsddProperty)<-[:HAS_PROPERTY]-(c:BsddClass)-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $uri}) RETURN p"
        prop_results = kg.execute_query(query, {"uri": uri})
        ifc_properties = [map_bsdd_property_to_ifc_property_single_value(dict(pr["p"])) for pr in prop_results]

        query = "MATCH (c:BsddClass {classType: 'Material'})-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $uri}) RETURN c"
        mat_results = kg.execute_query(query, {"uri": uri})
        ifc_materials = [map_bsdd_material_to_ifc_material(dict(mr["c"])) for mr in mat_results]

        return {
            "IfcClassification": ifc_dict,
            "IfcClassificationReferences": ifc_classes,
            "IfcPropertySingleValues": ifc_properties,
            "IfcMaterials": ifc_materials
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export IFC error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/{uri:path}")
async def export_dictionary(uri: str):
    """Export bSDD dictionary to JSON from Archive (P2.1.3)"""
    try:
        kg = get_kg_schema()
        basex = get_basex_service()
        
        query = "MATCH (d:BsddDictionary {uri: $uri}) RETURN d.basexUri as path"
        results = kg.execute_query(query, {"uri": uri})
        
        if not results or not results[0].get("path"):
            raise HTTPException(status_code=404, detail="Dictionary not found or not archived")
             
        path = results[0]["path"]
        content = basex.get_document(path)
        
        try:
            return json.loads(content)
        except:
            return JSONResponse(content={"raw": content})
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# bSDD Endpoints
# =============================================================================

@router.get("/bsdd/dictionaries")
async def get_bsdd_dictionaries():
    """Get all available bSDD dictionaries"""
    try:
        client = get_bsdd_client()
        dictionaries = client.get_dictionaries()
        
        return {
            "count": len(dictionaries),
            "dictionaries": [
                {
                    "uri": d.uri,
                    "name": d.name,
                    "version": d.version,
                    "organizationCode": d.organization_code,
                    "status": d.status,
                    "languageCode": d.language_code,
                    "license": d.license,
                    "releaseDate": d.release_date,
                    "moreInfoUrl": d.more_info_url
                }
                for d in dictionaries
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get dictionaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/bsdd/search")
async def search_bsdd_classes(request: BSDDSearchRequest):
    """Search for bSDD classes"""
    try:
        client = get_bsdd_client()
        
        if not request.dictionary_uri:
            dictionaries = client.get_dictionaries()
            ifc_dict = next(
                (d for d in dictionaries if "ifc" in d.name.lower() and "4.3" in d.version),
                None
            )
            if not ifc_dict:
                raise HTTPException(status_code=404, detail="IFC dictionary not found")
            dictionary_uri = ifc_dict.uri
        else:
            dictionary_uri = request.dictionary_uri
        
        classes = client.search_classes(
            dictionary_uri=dictionary_uri,
            search_text=request.search_text,
            related_ifc_entity=request.related_ifc_entity,
            language_code=request.language_code
        )
        
        return {
            "count": len(classes),
            "dictionary_uri": dictionary_uri,
            "classes": [
                {
                    "uri": c.uri,
                    "code": c.code,
                    "name": c.name,
                    "definition": c.definition,
                    "classType": c.class_type,
                    "relatedIfcEntities": c.related_ifc_entities,
                    "synonyms": c.synonyms
                }
                for c in classes
            ]
        }
    except Exception as e:
        logger.error(f"bSDD search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bsdd/class/{class_uri:path}")
async def get_bsdd_class_details(
    class_uri: str,
    dictionary_uri: str = Query(..., description="Dictionary URI"),
    include_properties: bool = Query(True, description="Include properties"),
    include_relations: bool = Query(True, description="Include relations")
):
    """Get detailed information about a bSDD class"""
    try:
        client = get_bsdd_client()
        
        bsdd_class = client.get_class_details(
            dictionary_uri=dictionary_uri,
            class_uri=class_uri,
            include_properties=include_properties,
            include_relations=include_relations
        )
        
        return {
            "uri": bsdd_class.uri,
            "code": bsdd_class.code,
            "name": bsdd_class.name,
            "definition": bsdd_class.definition,
            "classType": bsdd_class.class_type,
            "relatedIfcEntities": bsdd_class.related_ifc_entities,
            "synonyms": bsdd_class.synonyms,
            "parentClassUri": bsdd_class.parent_class_uri,
            "properties": bsdd_class.properties if include_properties else [],
            "relations": bsdd_class.relations if include_relations else []
        }
    except Exception as e:
        logger.error(f"Failed to get class details: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bsdd/ifc-mappings/{ifc_entity}")
async def get_ifc_bsdd_mappings(ifc_entity: str):
    """Get bSDD classes mapped to an IFC entity"""
    try:
        client = get_bsdd_client()
        mappings = client.get_ifc_mappings(ifc_entity)
        
        return {
            "ifcEntity": ifc_entity,
            "count": len(mappings),
            "mappings": [
                {
                    "uri": c.uri,
                    "code": c.code,
                    "name": c.name,
                    "definition": c.definition,
                    "classType": c.class_type
                }
                for c in mappings
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get IFC mappings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Import/Export Endpoints (P2.1)
# =============================================================================

@router.post("/import/json")
async def import_json(file: UploadFile = File(...)):
    """Import bSDD Dictionary from JSON file (P2.1.1)"""
    try:
        content = await file.read()
        json_content = json.loads(content)
        manager = get_sync_manager()
        result = manager.import_from_json(json_content)
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/import/excel")
async def import_excel(file: UploadFile = File(...)):
    """Import bSDD Dictionary from Excel file (P2.1.2)"""
    try:
        content = await file.read()
        manager = get_sync_manager()
        result = manager.import_from_excel(content)
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result.get("error"))
        return result
    except Exception as e:
        logger.error(f"Import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate")
async def validate_dictionary(file: UploadFile = File(...)):
    """Validate dictionary file (P2.1.4)"""
    try:
        content = await file.read()
        data = json.loads(content)
        errors = []
        if "dictionary" not in data:
            errors.append("Missing 'dictionary' object")
        if "classes" not in data:
            errors.append("Missing 'classes' array")
        
        if errors:
            return {"status": "invalid", "errors": errors}
             
        return {"status": "valid"}
    except Exception as e:
        return {"status": "invalid", "errors": [str(e)]}


# =============================================================================
# Enhanced Query Endpoints (P2.2)
# =============================================================================

@router.get("/classes/{uri:path}/hierarchy")
async def get_class_hierarchy(uri: str):
    """Get class hierarchy (P2.2.1)"""
    try:
        kg = get_kg_schema()
        return kg.get_class_hierarchy(uri)
    except Exception as e:
        logger.error(f"Hierarchy query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classes/{uri:path}/properties")
async def get_class_properties(uri: str):
    """Get class properties (P2.2.2)"""
    try:
        kg = get_kg_schema()
        return kg.get_class_properties(uri)
    except Exception as e:
        logger.error(f"Properties query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classes/{uri:path}/relations")
async def get_class_relations(uri: str):
    """Get class relations (P2.2.3)"""
    try:
        kg = get_kg_schema()
        return kg.get_class_relations(uri)
    except Exception as e:
        logger.error(f"Relations query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{uri:path}/allowed-values")
async def get_property_allowed_values(uri: str):
    """Get property allowed values (P2.2.4)"""
    try:
        kg = get_kg_schema()
        return kg.get_property_allowed_values(uri)
    except Exception as e:
        logger.error(f"Allowed values query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/properties/{uri:path}/relations")
async def get_property_relations(uri: str):
    """Get property relations (P2.2.5)"""
    try:
        kg = get_kg_schema()
        return kg.get_property_relations(uri)
    except Exception as e:
        logger.error(f"Property relations query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/advanced")
async def advanced_search(
    query: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    dictionary_uri: Optional[str] = Query(None),
    description: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """Advanced search for classes/properties (P2.2.6)"""
    try:
        kg = get_kg_schema()
        results = kg.advanced_search(
            query=query, type=type, status=status,
            dictionary_uri=dictionary_uri, description=description, limit=limit
        )
        return {"count": len(results), "results": results}
    except Exception as e:
        logger.error(f"Advanced search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Management Endpoints (P2.3)
# =============================================================================

@router.put("/dictionaries/{uri}/status")
async def update_dictionary_status(uri: str, status_val: str = Body(..., alias="status", embed=True)):
    """Update dictionary status (Preview/Active/Inactive) (P2.3.1)"""
    try:
        kg = get_kg_schema()
        query = "MATCH (d:BsddDictionary {uri: $uri}) SET d.status = $status RETURN d"
        result = kg.execute_query(query, {"uri": uri, "status": status_val})
        return {"updated": bool(result), "status": status_val}
    except Exception as e:
        logger.error(f"Status update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dictionaries/{uri}/versions")
async def get_dictionary_versions(uri: str):
    """List all versions of a dictionary (P2.3.2)"""
    try:
        kg = get_kg_schema()
        query = "MATCH (d:BsddDictionary {name: $name}) RETURN d.version as version, d.status as status ORDER BY d.version DESC"
        name = uri.split("/")[-2] if "/" in uri else uri
        results = kg.execute_query(query, {"name": name})
        return {"versions": results}
    except Exception as e:
        logger.error(f"Version list failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dictionaries/{uri}/translate")
async def add_dictionary_translation(uri: str, language_code: str = Body(...), translation: dict = Body(...)):
    """Add translation to dictionary (P2.3.3)"""
    try:
        kg = get_kg_schema()
        query = "MATCH (d:BsddDictionary {uri: $uri}) SET d.translations = coalesce(d.translations, []) + $translation RETURN d"
        result = kg.execute_query(query, {"uri": uri, "translation": {"language": language_code, "data": translation}})
        return {"updated": bool(result), "language": language_code}
    except Exception as e:
        logger.error(f"Translation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/dictionaries/{uri}")
async def delete_dictionary(uri: str, soft_delete: bool = Query(True)):
    """Delete dictionary (soft or hard) (P2.3.4)"""
    try:
        kg = get_kg_schema()
        if soft_delete:
            query = "MATCH (d:BsddDictionary {uri: $uri}) SET d.deleted = true RETURN d"
        else:
            query = "MATCH (d:BsddDictionary {uri: $uri}) DETACH DELETE d"
        result = kg.execute_query(query, {"uri": uri})
        return {"deleted": bool(result), "soft": soft_delete}
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# GenAI Endpoints
# =============================================================================

@router.post("/ai/semantic-search")
async def semantic_search(request: SemanticSearchRequest):
    """
    Perform semantic search across knowledge graph using GenAI
    Returns relevant results with AI-generated summaries
    """
    try:
        genai = get_genai_service()
        results = genai.semantic_search(
            query=request.query,
            context_type=request.context_type,
            limit=request.limit
        )
        
        return {
            "query": request.query,
            "results": results
        }
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/recommend-properties")
async def recommend_properties(request: PropertyRecommendationRequest):
    """
    Get AI-powered property recommendations for a building element
    Returns standardized properties from bSDD with rationale
    """
    try:
        genai = get_genai_service()
        properties = genai.recommend_properties(
            element_type=request.element_type,
            context=request.context
        )
        
        return {
            "elementType": request.element_type,
            "count": len(properties),
            "properties": properties
        }
    except Exception as e:
        logger.error(f"Property recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/suggest-classifications")
async def suggest_classifications(request: ClassificationSuggestionRequest):
    """
    Get AI-powered classification suggestions for an element
    Returns appropriate classifications with confidence scores
    """
    try:
        genai = get_genai_service()
        classifications = genai.suggest_classifications(
            element_description=request.element_description,
            available_systems=request.available_systems
        )
        
        return {
            "description": request.element_description,
            "count": len(classifications),
            "classifications": classifications
        }
    except Exception as e:
        logger.error(f"Classification suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/chat")
async def chat(request: ChatRequest):
    """
    Natural language chat interface for knowledge graph
    Provides conversational access to building data and standards
    """
    try:
        genai = get_genai_service()
        response = genai.chat(
            message=request.message,
            conversation_history=request.conversation_history
        )
        
        return {
            "message": request.message,
            "response": response
        }
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Knowledge Graph Query Endpoints
# =============================================================================

@router.get("/graph/stats")
async def get_graph_stats():
    """Get statistics about the knowledge graph"""
    try:
        kg = get_kg_schema()
        stats = kg.get_schema_info()
        
        return {
            "nodes": stats.get("nodes", []),
            "relationships": stats.get("relationships", [])
        }
    except Exception as e:
        logger.error(f"Failed to get graph stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/cypher")
async def execute_cypher(
    query: str = Body(..., embed=True),
    parameters: Optional[Dict[str, Any]] = Body(None, embed=True)
):
    """
    Execute a custom Cypher query (admin only - add auth in production)
    For advanced users to directly query the knowledge graph
    """
    try:
        kg = get_kg_schema()
        
        with kg.driver.session() as session:
            result = session.run(query, parameters or {})
            data = result.data()
        
        return {
            "query": query,
            "parameters": parameters,
            "result_count": len(data),
            "results": data
        }
    except Exception as e:
        logger.error(f"Cypher query failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Health Check
# =============================================================================

@router.get("/health")
async def health_check():
    """Check health of knowledge graph services"""
    health = {
        "bsdd_client": "unknown",
        "neo4j": "unknown",
        "genai": "unknown"
    }
    
    try:
        client = get_bsdd_client()
        client.get_dictionaries()
        health["bsdd_client"] = "healthy"
    except Exception as e:
        health["bsdd_client"] = f"error: {str(e)}"
    
    try:
        kg = get_kg_schema()
        with kg.driver.session() as session:
            session.run("RETURN 1")
        health["neo4j"] = "healthy"
    except Exception as e:
        health["neo4j"] = f"error: {str(e)}"
    
    try:
        genai = get_genai_service()
        health["genai"] = "healthy"
    except Exception as e:
        health["genai"] = f"error: {str(e)}"
    
    all_healthy = all(s == "healthy" for s in health.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": health
    }
