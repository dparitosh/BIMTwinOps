"""
Point Cloud Semantic Labeling Service

Provides API endpoints for enriching point cloud segments with bSDD semantic information.
"""
import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .knowledge_graph_schema import KnowledgeGraphSchema
from .config import cfg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pointcloud", tags=["Point Cloud"])


class PointCloudSegment(BaseModel):
    """A segment of a point cloud with semantic classification"""
    segment_id: str
    semantic_class_id: int  # 0-12 matching S3DIS classes
    semantic_label: Optional[str] = None
    point_count: int
    centroid: List[float]  # [x, y, z]
    bounding_box: Optional[Dict[str, List[float]]] = None  # {min: [x,y,z], max: [x,y,z]}
    confidence: Optional[float] = None


class EnrichedSegment(PointCloudSegment):
    """Point cloud segment enriched with bSDD semantic information"""
    bsdd_classes: List[Dict[str, Any]] = []
    ifc_entities: List[str] = []
    properties: List[Dict[str, Any]] = []


class PointCloudSemanticService:
    """Service for semantic labeling and bSDD enrichment of point cloud data"""
    
    def __init__(self):
        self.kg = KnowledgeGraphSchema(
            neo4j_uri=cfg.NEO4J_URI,
            neo4j_user=cfg.NEO4J_USER,
            neo4j_password=cfg.NEO4J_PASSWORD,
            database=cfg.NEO4J_DATABASE
        )
        self._load_semantic_mapping()
    
    def _load_semantic_mapping(self):
        """Load SemanticClass → BsddClass mappings from Neo4j"""
        self.semantic_mappings = {}
        
        with self.kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (sc:SemanticClass)-[r:MAPS_TO]->(bc:BsddClass)
                RETURN sc.label as semantic_label,
                       sc.classId as semantic_id,
                       bc.name as bsdd_name,
                       bc.code as bsdd_code,
                       bc.uri as bsdd_uri,
                       bc.relatedIfcEntities as ifc_entities,
                       r.confidence as confidence,
                       r.priority as priority
                ORDER BY sc.classId, r.priority
            """)
            
            for record in result:
                semantic_id = record["semantic_id"]
                if semantic_id not in self.semantic_mappings:
                    self.semantic_mappings[semantic_id] = {
                        "label": record["semantic_label"],
                        "bsdd_classes": []
                    }
                
                self.semantic_mappings[semantic_id]["bsdd_classes"].append({
                    "name": record["bsdd_name"],
                    "code": record["bsdd_code"],
                    "uri": record["bsdd_uri"],
                    "ifc_entities": record["ifc_entities"] or [],
                    "confidence": record["confidence"],
                    "priority": record["priority"]
                })
        
        logger.info(f"Loaded semantic mappings for {len(self.semantic_mappings)} classes")
    
    def enrich_segment(
        self,
        segment: PointCloudSegment,
        include_properties: bool = False
    ) -> EnrichedSegment:
        """
        Enrich a point cloud segment with bSDD semantic information
        
        Args:
            segment: Point cloud segment with semantic classification
            include_properties: Include bSDD properties for the class
            
        Returns:
            Enriched segment with bSDD information
        """
        enriched = EnrichedSegment(**segment.dict())
        
        # Get semantic mapping
        mapping = self.semantic_mappings.get(segment.semantic_class_id)
        if not mapping:
            logger.warning(f"No mapping found for semantic class ID {segment.semantic_class_id}")
            return enriched
        
        # Set semantic label if not provided
        if not enriched.semantic_label:
            enriched.semantic_label = mapping["label"]
        
        # Add bSDD classes
        enriched.bsdd_classes = mapping["bsdd_classes"]
        
        # Extract unique IFC entities from bSDD codes
        # The bSDD code IS the IFC entity name (e.g., "IfcWall", "IfcWallSTANDARD")
        ifc_entities = set()
        for bsdd_class in mapping["bsdd_classes"]:
            code = bsdd_class.get("code", "")
            if code:
                ifc_entities.add(code)
            # Also add from ifc_entities field if available
            ifc_entities.update(bsdd_class.get("ifc_entities", []))
        enriched.ifc_entities = sorted(list(ifc_entities))
        
        # Optionally fetch properties
        if include_properties and mapping["bsdd_classes"]:
            primary_class_uri = mapping["bsdd_classes"][0]["uri"]
            enriched.properties = self._get_class_properties(primary_class_uri)
        
        return enriched
    
    def enrich_batch(
        self,
        segments: List[PointCloudSegment],
        include_properties: bool = False
    ) -> List[EnrichedSegment]:
        """Enrich multiple segments in batch"""
        return [self.enrich_segment(seg, include_properties) for seg in segments]
    
    def _get_class_properties(self, class_uri: str) -> List[Dict[str, Any]]:
        """Get properties for a bSDD class"""
        with self.kg.driver.session(database=cfg.NEO4J_DATABASE) as session:
            result = session.run("""
                MATCH (bc:BsddClass {uri: $uri})-[:HAS_PROPERTY]->(bp:BsddProperty)
                RETURN bp.name as name,
                       bp.code as code,
                       bp.dataType as data_type,
                       bp.definition as definition
                LIMIT 50
            """, uri=class_uri)
            
            return [
                {
                    "name": r["name"],
                    "code": r["code"],
                    "data_type": r["data_type"],
                    "definition": r["definition"]
                }
                for r in result
            ]
    
    def get_semantic_classes(self) -> List[Dict[str, Any]]:
        """Get all available semantic classes with their bSDD mappings"""
        return [
            {
                "class_id": class_id,
                "label": mapping["label"],
                "bsdd_classes": mapping["bsdd_classes"]
            }
            for class_id, mapping in sorted(self.semantic_mappings.items())
        ]


# Initialize service
_service = None

def get_service() -> PointCloudSemanticService:
    """Get or create semantic labeling service instance"""
    global _service
    if _service is None:
        _service = PointCloudSemanticService()
    return _service


# API Endpoints

@router.post("/enrich", response_model=EnrichedSegment)
async def enrich_segment(segment: PointCloudSegment, include_properties: bool = False):
    """
    Enrich a point cloud segment with bSDD semantic information
    
    Automatically adds:
    - bSDD class information
    - IFC entity mappings
    - Optional: bSDD properties
    """
    try:
        service = get_service()
        return service.enrich_segment(segment, include_properties)
    except Exception as e:
        logger.error(f"Failed to enrich segment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enrich/batch", response_model=List[EnrichedSegment])
async def enrich_batch(segments: List[PointCloudSegment], include_properties: bool = False):
    """Enrich multiple point cloud segments in batch"""
    try:
        service = get_service()
        return service.enrich_batch(segments, include_properties)
    except Exception as e:
        logger.error(f"Failed to enrich batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/semantic-classes")
async def get_semantic_classes():
    """Get all available semantic classes and their bSDD mappings"""
    try:
        service = get_service()
        return service.get_semantic_classes()
    except Exception as e:
        logger.error(f"Failed to get semantic classes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """Health check for point cloud semantic service"""
    try:
        service = get_service()
        return {
            "status": "healthy",
            "semantic_classes_loaded": len(service.semantic_mappings),
            "neo4j_connected": service.kg.driver is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
