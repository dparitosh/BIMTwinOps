"""
Knowledge Graph API Routes for BIMTwinOps
Provides REST endpoints for bSDD integration, GenAI queries, and knowledge graph operations
"""
import os
import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .bsdd_client import BSDDClient, BSDDEnvironment
from .knowledge_graph_schema import KnowledgeGraphSchema
from .genai_service import BIMTwinOpsGenAI

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize router
router = APIRouter(prefix="/api/kg", tags=["Knowledge Graph"])

# Initialize clients (singleton pattern)
_bsdd_client = None
_kg_schema = None
_genai_service = None


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
            neo4j_password=os.getenv("NEO4J_PASSWORD")  # Required - validated by BIMTwinOpsGenAI
        )
    return _genai_service


# Request/Response Models
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


# bSDD Endpoints
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
            # Get IFC dictionary by default
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


# GenAI Endpoints
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


# Knowledge Graph Query Endpoints
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


# Health check
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
    
    all_healthy = all(status == "healthy" for status in health.values())
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": health
    }
