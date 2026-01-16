"""
GraphQL API for Knowledge Graph
Provides GraphQL interface to query Neo4j knowledge graph with bSDD integration
"""
import os
import logging
from typing import List, Optional, Dict, Any
import strawberry
from strawberry.fastapi import GraphQLRouter
from dotenv import load_dotenv

from .knowledge_graph_schema import KnowledgeGraphSchema
from .bsdd_client import BSDDClient, BSDDEnvironment

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize clients
_kg_schema = None
_bsdd_client = None


def get_kg_schema() -> KnowledgeGraphSchema:
    """Get or create knowledge graph schema singleton"""
    global _kg_schema
    if _kg_schema is None:
        _kg_schema = KnowledgeGraphSchema(
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "password")
        )
    return _kg_schema


def get_bsdd_client() -> BSDDClient:
    """Get or create bSDD client singleton"""
    global _bsdd_client
    if _bsdd_client is None:
        _bsdd_client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
    return _bsdd_client


# ============================================================================
# GraphQL Types
# ============================================================================

@strawberry.type
class BsddDictionary:
    """bSDD Dictionary node"""
    uri: str
    name: str
    version: str
    organization_code: str
    status: str
    language_code: str
    license: Optional[str] = None
    release_date: Optional[str] = None
    more_info_url: Optional[str] = None
    classes_count: Optional[int] = None
    properties_count: Optional[int] = None


@strawberry.type
class BsddClass:
    """bSDD Class node"""
    uri: str
    code: str
    name: str
    definition: Optional[str] = None
    class_type: Optional[str] = None
    dictionary_uri: Optional[str] = None
    parent_class_uri: Optional[str] = None
    related_ifc_entities: List[str]
    synonyms: List[str]
    
    @strawberry.field
    def properties(self) -> List["BsddProperty"]:
        """Get properties for this class"""
        kg = get_kg_schema()
        query = """
        MATCH (c:BsddClass {uri: $uri})-[:HAS_PROPERTY]->(p:BsddProperty)
        RETURN p
        """
        result = kg.execute_query(query, {"uri": self.uri})
        properties = []
        for record in result:
            prop_data = dict(record["p"])
            properties.append(BsddProperty(
                uri=prop_data.get("uri", ""),
                code=prop_data.get("code", ""),
                name=prop_data.get("name", ""),
                definition=prop_data.get("definition"),
                data_type=prop_data.get("dataType"),
                units=prop_data.get("units", []),
                physical_quantity=prop_data.get("physicalQuantity")
            ))
        return properties
    
    @strawberry.field
    def relations(self) -> List["ClassRelation"]:
        """Get relations for this class"""
        kg = get_kg_schema()
        query = """
        MATCH (c:BsddClass {uri: $uri})-[r:RELATED_TO|IS_SUBCLASS_OF|IS_PARENT_OF]->(related:BsddClass)
        RETURN type(r) as relationType, related
        """
        result = kg.execute_query(query, {"uri": self.uri})
        relations = []
        for record in result:
            related_data = dict(record["related"])
            relations.append(ClassRelation(
                relation_type=record["relationType"],
                related_class_uri=related_data.get("uri", ""),
                related_class_name=related_data.get("name", "")
            ))
        return relations


@strawberry.type
class BsddProperty:
    """bSDD Property node"""
    uri: str
    code: str
    name: str
    definition: Optional[str] = None
    data_type: Optional[str] = None
    units: List[str]
    physical_quantity: Optional[str] = None
    
    @strawberry.field
    def classes(self) -> List[BsddClass]:
        """Get classes that use this property"""
        kg = get_kg_schema()
        query = """
        MATCH (p:BsddProperty {uri: $uri})<-[:HAS_PROPERTY]-(c:BsddClass)
        RETURN c
        """
        result = kg.execute_query(query, {"uri": self.uri})
        classes = []
        for record in result:
            class_data = dict(record["c"])
            classes.append(BsddClass(
                uri=class_data.get("uri", ""),
                code=class_data.get("code", ""),
                name=class_data.get("name", ""),
                definition=class_data.get("definition"),
                class_type=class_data.get("classType"),
                related_ifc_entities=class_data.get("relatedIfcEntities", []),
                synonyms=class_data.get("synonyms", [])
            ))
        return classes


@strawberry.type
class IfcElement:
    """IFC Element node"""
    global_id: str
    ifc_type: str
    name: Optional[str] = None
    description: Optional[str] = None
    object_type: Optional[str] = None
    
    @strawberry.field
    def bsdd_mappings(self) -> List[BsddClass]:
        """Get bSDD classes mapped to this IFC element"""
        kg = get_kg_schema()
        query = """
        MATCH (ifc:IfcElement {globalId: $global_id})-[:MAPS_TO_BSDD]->(bsdd:BsddClass)
        RETURN bsdd
        """
        result = kg.execute_query(query, {"global_id": self.global_id})
        mappings = []
        for record in result:
            bsdd_data = dict(record["bsdd"])
            mappings.append(BsddClass(
                uri=bsdd_data.get("uri", ""),
                code=bsdd_data.get("code", ""),
                name=bsdd_data.get("name", ""),
                definition=bsdd_data.get("definition"),
                class_type=bsdd_data.get("classType"),
                related_ifc_entities=bsdd_data.get("relatedIfcEntities", []),
                synonyms=bsdd_data.get("synonyms", [])
            ))
        return mappings
    
    @strawberry.field
    def point_cloud_segments(self) -> List["PointCloudSegment"]:
        """Get point cloud segments corresponding to this IFC element"""
        kg = get_kg_schema()
        query = """
        MATCH (ifc:IfcElement {globalId: $global_id})-[:CORRESPONDS_TO]->(seg:PointCloudSegment)
        RETURN seg
        """
        result = kg.execute_query(query, {"global_id": self.global_id})
        segments = []
        for record in result:
            seg_data = dict(record["seg"])
            segments.append(PointCloudSegment(
                segment_id=seg_data.get("segmentId", ""),
                semantic_label=seg_data.get("semanticLabel", ""),
                confidence=seg_data.get("confidence"),
                point_count=seg_data.get("pointCount")
            ))
        return segments


@strawberry.type
class PointCloudSegment:
    """Point Cloud Segment node"""
    segment_id: str
    semantic_label: str
    confidence: Optional[float] = None
    point_count: Optional[int] = None
    
    @strawberry.field
    def bsdd_mappings(self) -> List[BsddClass]:
        """Get bSDD classes mapped to this point cloud segment"""
        kg = get_kg_schema()
        query = """
        MATCH (seg:PointCloudSegment {segmentId: $segment_id})-[:MAPS_TO_BSDD]->(bsdd:BsddClass)
        RETURN bsdd
        """
        result = kg.execute_query(query, {"segment_id": self.segment_id})
        mappings = []
        for record in result:
            bsdd_data = dict(record["bsdd"])
            mappings.append(BsddClass(
                uri=bsdd_data.get("uri", ""),
                code=bsdd_data.get("code", ""),
                name=bsdd_data.get("name", ""),
                definition=bsdd_data.get("definition"),
                class_type=bsdd_data.get("classType"),
                related_ifc_entities=bsdd_data.get("relatedIfcEntities", []),
                synonyms=bsdd_data.get("synonyms", [])
            ))
        return mappings


@strawberry.type
class ClassRelation:
    """Relationship between bSDD classes"""
    relation_type: str
    related_class_uri: str
    related_class_name: str


@strawberry.type
class GraphStats:
    """Knowledge graph statistics"""
    total_nodes: int
    total_relationships: int
    bsdd_dictionaries_count: int
    bsdd_classes_count: int
    bsdd_properties_count: int
    ifc_elements_count: int
    point_cloud_segments_count: int
    node_type_distribution: Dict[str, int]


@strawberry.type
class SearchResult:
    """Generic search result"""
    result_type: str  # "class", "property", "ifc_element", "segment"
    uri: str
    name: str
    description: Optional[str] = None
    score: Optional[float] = None


# ============================================================================
# GraphQL Queries
# ============================================================================

@strawberry.type
class Query:
    """GraphQL Query Root"""
    
    @strawberry.field
    def bsdd_dictionaries(
        self,
        organization_code: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[BsddDictionary]:
        """Get all bSDD dictionaries in the knowledge graph"""
        kg = get_kg_schema()
        query = """
        MATCH (d:BsddDictionary)
        WHERE ($org_code IS NULL OR d.organizationCode = $org_code)
          AND ($status IS NULL OR d.status = $status)
        RETURN d
        ORDER BY d.name
        LIMIT $limit
        """
        result = kg.execute_query(query, {
            "org_code": organization_code,
            "status": status,
            "limit": limit
        })
        
        dictionaries = []
        for record in result:
            dict_data = dict(record["d"])
            dictionaries.append(BsddDictionary(
                uri=dict_data.get("uri", ""),
                name=dict_data.get("name", ""),
                version=dict_data.get("version", ""),
                organization_code=dict_data.get("organizationCode", ""),
                status=dict_data.get("status", ""),
                language_code=dict_data.get("languageCode", "en-GB"),
                license=dict_data.get("license"),
                release_date=dict_data.get("releaseDate"),
                more_info_url=dict_data.get("moreInfoUrl")
            ))
        return dictionaries
    
    @strawberry.field
    def bsdd_class(self, uri: str) -> Optional[BsddClass]:
        """Get a specific bSDD class by URI"""
        kg = get_kg_schema()
        query = """
        MATCH (c:BsddClass {uri: $uri})
        RETURN c
        """
        result = kg.execute_query(query, {"uri": uri})
        
        if not result:
            return None
        
        class_data = dict(result[0]["c"])
        return BsddClass(
            uri=class_data.get("uri", ""),
            code=class_data.get("code", ""),
            name=class_data.get("name", ""),
            definition=class_data.get("definition"),
            class_type=class_data.get("classType"),
            dictionary_uri=class_data.get("dictionaryUri"),
            parent_class_uri=class_data.get("parentClassUri"),
            related_ifc_entities=class_data.get("relatedIfcEntities", []),
            synonyms=class_data.get("synonyms", [])
        )
    
    @strawberry.field
    def bsdd_classes(
        self,
        dictionary_uri: Optional[str] = None,
        class_type: Optional[str] = None,
        ifc_entity: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[BsddClass]:
        """Search bSDD classes with filters"""
        kg = get_kg_schema()
        
        # Build dynamic query based on filters
        where_clauses = []
        if dictionary_uri:
            where_clauses.append("c.dictionaryUri = $dictionary_uri")
        if class_type:
            where_clauses.append("c.classType = $class_type")
        if ifc_entity:
            where_clauses.append("$ifc_entity IN c.relatedIfcEntities")
        if search_text:
            where_clauses.append("(c.name CONTAINS $search_text OR c.definition CONTAINS $search_text)")
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (c:BsddClass)
        {where_clause}
        RETURN c
        ORDER BY c.name
        LIMIT $limit
        """
        
        result = kg.execute_query(query, {
            "dictionary_uri": dictionary_uri,
            "class_type": class_type,
            "ifc_entity": ifc_entity,
            "search_text": search_text,
            "limit": limit
        })
        
        classes = []
        for record in result:
            class_data = dict(record["c"])
            classes.append(BsddClass(
                uri=class_data.get("uri", ""),
                code=class_data.get("code", ""),
                name=class_data.get("name", ""),
                definition=class_data.get("definition"),
                class_type=class_data.get("classType"),
                related_ifc_entities=class_data.get("relatedIfcEntities", []),
                synonyms=class_data.get("synonyms", [])
            ))
        return classes
    
    @strawberry.field
    def bsdd_property(self, uri: str) -> Optional[BsddProperty]:
        """Get a specific bSDD property by URI"""
        kg = get_kg_schema()
        query = """
        MATCH (p:BsddProperty {uri: $uri})
        RETURN p
        """
        result = kg.execute_query(query, {"uri": uri})
        
        if not result:
            return None
        
        prop_data = dict(result[0]["p"])
        return BsddProperty(
            uri=prop_data.get("uri", ""),
            code=prop_data.get("code", ""),
            name=prop_data.get("name", ""),
            definition=prop_data.get("definition"),
            data_type=prop_data.get("dataType"),
            units=prop_data.get("units", []),
            physical_quantity=prop_data.get("physicalQuantity")
        )
    
    @strawberry.field
    def bsdd_properties(
        self,
        class_uri: Optional[str] = None,
        data_type: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[BsddProperty]:
        """Search bSDD properties with filters"""
        kg = get_kg_schema()
        
        if class_uri:
            query = """
            MATCH (c:BsddClass {uri: $class_uri})-[:HAS_PROPERTY]->(p:BsddProperty)
            WHERE ($data_type IS NULL OR p.dataType = $data_type)
              AND ($search_text IS NULL OR p.name CONTAINS $search_text OR p.definition CONTAINS $search_text)
            RETURN p
            ORDER BY p.name
            LIMIT $limit
            """
        else:
            query = """
            MATCH (p:BsddProperty)
            WHERE ($data_type IS NULL OR p.dataType = $data_type)
              AND ($search_text IS NULL OR p.name CONTAINS $search_text OR p.definition CONTAINS $search_text)
            RETURN p
            ORDER BY p.name
            LIMIT $limit
            """
        
        result = kg.execute_query(query, {
            "class_uri": class_uri,
            "data_type": data_type,
            "search_text": search_text,
            "limit": limit
        })
        
        properties = []
        for record in result:
            prop_data = dict(record["p"])
            properties.append(BsddProperty(
                uri=prop_data.get("uri", ""),
                code=prop_data.get("code", ""),
                name=prop_data.get("name", ""),
                definition=prop_data.get("definition"),
                data_type=prop_data.get("dataType"),
                units=prop_data.get("units", []),
                physical_quantity=prop_data.get("physicalQuantity")
            ))
        return properties
    
    @strawberry.field
    def ifc_element(self, global_id: str) -> Optional[IfcElement]:
        """Get a specific IFC element by GlobalId"""
        kg = get_kg_schema()
        query = """
        MATCH (ifc:IfcElement {globalId: $global_id})
        RETURN ifc
        """
        result = kg.execute_query(query, {"global_id": global_id})
        
        if not result:
            return None
        
        ifc_data = dict(result[0]["ifc"])
        return IfcElement(
            global_id=ifc_data.get("globalId", ""),
            ifc_type=ifc_data.get("ifcType", ""),
            name=ifc_data.get("name"),
            description=ifc_data.get("description"),
            object_type=ifc_data.get("objectType")
        )
    
    @strawberry.field
    def ifc_elements(
        self,
        ifc_type: Optional[str] = None,
        search_text: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[IfcElement]:
        """Search IFC elements with filters"""
        kg = get_kg_schema()
        
        where_clauses = []
        if ifc_type:
            where_clauses.append("ifc.ifcType = $ifc_type")
        if search_text:
            where_clauses.append("(ifc.name CONTAINS $search_text OR ifc.description CONTAINS $search_text)")
        
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        query = f"""
        MATCH (ifc:IfcElement)
        {where_clause}
        RETURN ifc
        ORDER BY ifc.name
        LIMIT $limit
        """
        
        result = kg.execute_query(query, {
            "ifc_type": ifc_type,
            "search_text": search_text,
            "limit": limit
        })
        
        elements = []
        for record in result:
            ifc_data = dict(record["ifc"])
            elements.append(IfcElement(
                global_id=ifc_data.get("globalId", ""),
                ifc_type=ifc_data.get("ifcType", ""),
                name=ifc_data.get("name"),
                description=ifc_data.get("description"),
                object_type=ifc_data.get("objectType")
            ))
        return elements
    
    @strawberry.field
    def point_cloud_segment(self, segment_id: str) -> Optional[PointCloudSegment]:
        """Get a specific point cloud segment by ID"""
        kg = get_kg_schema()
        query = """
        MATCH (seg:PointCloudSegment {segmentId: $segment_id})
        RETURN seg
        """
        result = kg.execute_query(query, {"segment_id": segment_id})
        
        if not result:
            return None
        
        seg_data = dict(result[0]["seg"])
        return PointCloudSegment(
            segment_id=seg_data.get("segmentId", ""),
            semantic_label=seg_data.get("semanticLabel", ""),
            confidence=seg_data.get("confidence"),
            point_count=seg_data.get("pointCount")
        )
    
    @strawberry.field
    def search(
        self,
        query_text: str,
        result_types: Optional[List[str]] = None,
        limit: Optional[int] = 50
    ) -> List[SearchResult]:
        """Universal search across all node types"""
        kg = get_kg_schema()
        
        # If no types specified, search all
        if not result_types:
            result_types = ["class", "property", "ifc_element", "segment"]
        
        results = []
        
        # Search bSDD classes
        if "class" in result_types:
            query = """
            MATCH (c:BsddClass)
            WHERE c.name CONTAINS $query_text OR c.definition CONTAINS $query_text
            RETURN 'class' as type, c.uri as uri, c.name as name, c.definition as description
            LIMIT $limit
            """
            class_results = kg.execute_query(query, {"query_text": query_text, "limit": limit})
            for record in class_results:
                results.append(SearchResult(
                    result_type=record["type"],
                    uri=record["uri"],
                    name=record["name"],
                    description=record.get("description")
                ))
        
        # Search bSDD properties
        if "property" in result_types:
            query = """
            MATCH (p:BsddProperty)
            WHERE p.name CONTAINS $query_text OR p.definition CONTAINS $query_text
            RETURN 'property' as type, p.uri as uri, p.name as name, p.definition as description
            LIMIT $limit
            """
            prop_results = kg.execute_query(query, {"query_text": query_text, "limit": limit})
            for record in prop_results:
                results.append(SearchResult(
                    result_type=record["type"],
                    uri=record["uri"],
                    name=record["name"],
                    description=record.get("description")
                ))
        
        return results[:limit]
    
    @strawberry.field
    def graph_stats(self) -> GraphStats:
        """Get knowledge graph statistics"""
        kg = get_kg_schema()
        
        # Count total nodes and relationships
        query = """
        MATCH (n)
        WITH count(n) as nodeCount
        MATCH ()-[r]->()
        RETURN nodeCount, count(r) as relCount
        """
        result = kg.execute_query(query, {})
        total_nodes = result[0]["nodeCount"] if result else 0
        total_rels = result[0]["relCount"] if result else 0
        
        # Count by node type
        query = """
        MATCH (d:BsddDictionary) WITH count(d) as dictCount
        MATCH (c:BsddClass) WITH dictCount, count(c) as classCount
        MATCH (p:BsddProperty) WITH dictCount, classCount, count(p) as propCount
        MATCH (ifc:IfcElement) WITH dictCount, classCount, propCount, count(ifc) as ifcCount
        MATCH (seg:PointCloudSegment) WITH dictCount, classCount, propCount, ifcCount, count(seg) as segCount
        RETURN dictCount, classCount, propCount, ifcCount, segCount
        """
        result = kg.execute_query(query, {})
        
        if result:
            counts = result[0]
            return GraphStats(
                total_nodes=total_nodes,
                total_relationships=total_rels,
                bsdd_dictionaries_count=counts.get("dictCount", 0),
                bsdd_classes_count=counts.get("classCount", 0),
                bsdd_properties_count=counts.get("propCount", 0),
                ifc_elements_count=counts.get("ifcCount", 0),
                point_cloud_segments_count=counts.get("segCount", 0),
                node_type_distribution={
                    "BsddDictionary": counts.get("dictCount", 0),
                    "BsddClass": counts.get("classCount", 0),
                    "BsddProperty": counts.get("propCount", 0),
                    "IfcElement": counts.get("ifcCount", 0),
                    "PointCloudSegment": counts.get("segCount", 0)
                }
            )
        
        return GraphStats(
            total_nodes=0,
            total_relationships=0,
            bsdd_dictionaries_count=0,
            bsdd_classes_count=0,
            bsdd_properties_count=0,
            ifc_elements_count=0,
            point_cloud_segments_count=0,
            node_type_distribution={}
        )


# ============================================================================
# GraphQL Mutations
# ============================================================================

@strawberry.type
class Mutation:
    """GraphQL Mutation Root"""
    
    @strawberry.mutation
    def link_ifc_to_bsdd(
        self,
        ifc_global_id: str,
        bsdd_class_uri: str
    ) -> bool:
        """Create a mapping between an IFC element and a bSDD class"""
        kg = get_kg_schema()
        try:
            kg.link_ifc_element_to_bsdd(ifc_global_id, bsdd_class_uri)
            return True
        except Exception as e:
            logger.error(f"Failed to link IFC to bSDD: {e}")
            return False
    
    @strawberry.mutation
    def link_segment_to_bsdd(
        self,
        segment_id: str,
        bsdd_class_uri: str
    ) -> bool:
        """Create a mapping between a point cloud segment and a bSDD class"""
        kg = get_kg_schema()
        try:
            kg.link_pointcloud_segment_to_bsdd(segment_id, bsdd_class_uri)
            return True
        except Exception as e:
            logger.error(f"Failed to link segment to bSDD: {e}")
            return False


# ============================================================================
# GraphQL Schema
# ============================================================================

schema = strawberry.Schema(query=Query, mutation=Mutation)

# Create GraphQL router for FastAPI
graphql_router = GraphQLRouter(
    schema,
    path="/api/graphql",
    graphiql=True  # Enable GraphiQL UI
)


# ============================================================================
# Example Queries
# ============================================================================

"""
Example GraphQL Queries:

# Get all bSDD dictionaries
{
  bsddDictionaries(limit: 10) {
    uri
    name
    version
    organizationCode
    status
  }
}

# Get a specific class with properties and relations
{
  bsddClass(uri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall") {
    uri
    name
    definition
    relatedIfcEntities
    properties {
      code
      name
      dataType
      units
    }
    relations {
      relationType
      relatedClassName
    }
  }
}

# Search for classes
{
  bsddClasses(searchText: "wall", limit: 10) {
    uri
    name
    definition
    classType
    relatedIfcEntities
  }
}

# Get IFC element with bSDD mappings and point cloud segments
{
  ifcElement(globalId: "2O2Fr$t4X7Zf8NOew3FLZA") {
    globalId
    ifcType
    name
    bsddMappings {
      uri
      name
      definition
      properties {
        code
        name
        dataType
      }
    }
    pointCloudSegments {
      segmentId
      semanticLabel
      confidence
    }
  }
}

# Universal search
{
  search(queryText: "thermal", limit: 20) {
    resultType
    uri
    name
    description
  }
}

# Get graph statistics
{
  graphStats {
    totalNodes
    totalRelationships
    bsddDictionariesCount
    bsddClassesCount
    bsddPropertiesCount
    ifcElementsCount
    pointCloudSegmentsCount
    nodeTypeDistribution
  }
}

# Mutation: Link IFC to bSDD
mutation {
  linkIfcToBsdd(
    ifcGlobalId: "2O2Fr$t4X7Zf8NOew3FLZA",
    bsddClassUri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall"
  )
}
"""
