"""
GraphQL API for Knowledge Graph
Provides GraphQL interface to query Neo4j knowledge graph with bSDD integration
"""
import os
import logging
from typing import List, Optional, Dict, Any
import strawberry
from strawberry.scalars import JSON
from strawberry.fastapi import GraphQLRouter

from .knowledge_graph_schema import KnowledgeGraphSchema
from .bsdd_client import BSDDClient
from .ifc_mapping import (
    map_bsdd_dictionary_to_ifc_classification,
    map_bsdd_class_to_ifc_classification_reference,
    map_bsdd_property_to_ifc_property_single_value,
    map_bsdd_material_to_ifc_material
)

# Reuse singletons from kg_routes to avoid duplicate Neo4j drivers
from .kg_routes import get_kg_schema, get_bsdd_client   # noqa: E402

logger = logging.getLogger(__name__)


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

    @strawberry.field
    def class_properties(self) -> List["BsddClassProperty"]:
        """Get properties with class-specific context (required, defaults, etc.)"""
        kg = get_kg_schema()
        query = """
        MATCH (c:BsddClass {uri: $uri})-[r:HAS_PROPERTY]->(p:BsddProperty)
        RETURN p, r
        """
        result = kg.execute_query(query, {"uri": self.uri})
        class_props = []
        for record in result:
            prop_data = dict(record["p"])
            rel_data = dict(record["r"]) if record.get("r") else {}
            class_props.append(BsddClassProperty(
                property_uri=prop_data.get("uri", ""),
                property_name=prop_data.get("name", ""),
                property_code=prop_data.get("code", ""),
                is_required=rel_data.get("isRequired", False),
                is_required_for_exchange=rel_data.get("isRequiredForExchange", False),
                property_set=rel_data.get("propertySet"),
                predefined_value=rel_data.get("predefinedValue"),
                min_value=rel_data.get("minValue"),
                max_value=rel_data.get("maxValue"),
                pattern=rel_data.get("pattern")
            ))
        return class_props


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

    @strawberry.field
    def allowed_values(self) -> List["BsddAllowedValue"]:
        """Get allowed values for this property"""
        kg = get_kg_schema()
        query = """
        MATCH (p:BsddProperty {uri: $uri})-[:HAS_ALLOWED_VALUE]->(av:BsddAllowedValue)
        RETURN av
        """
        result = kg.execute_query(query, {"uri": self.uri})
        values = []
        for record in result:
            av_data = dict(record["av"])
            values.append(BsddAllowedValue(
                uri=av_data.get("uri", ""),
                value=av_data.get("value", ""),
                code=av_data.get("code"),
                description=av_data.get("description"),
                sort_number=av_data.get("sortNumber")
            ))
        return values

    @strawberry.field
    def unit(self) -> Optional["BsddUnit"]:
        """Get the unit for this property"""
        kg = get_kg_schema()
        query = """
        MATCH (p:BsddProperty {uri: $uri})-[:HAS_UNIT]->(u:BsddUnit)
        RETURN u LIMIT 1
        """
        result = kg.execute_query(query, {"uri": self.uri})
        if result:
            u_data = dict(result[0]["u"])
            return BsddUnit(
                uri=u_data.get("uri", ""),
                code=u_data.get("code", ""),
                name=u_data.get("name", ""),
                symbol=u_data.get("symbol")
            )
        return None


@strawberry.type
class BsddAllowedValue:
    """bSDD Allowed Value for enumerated properties"""
    uri: str
    value: str
    code: Optional[str] = None
    description: Optional[str] = None
    sort_number: Optional[int] = None


@strawberry.type
class BsddUnit:
    """bSDD Unit of measurement"""
    uri: str
    code: str
    name: str
    symbol: Optional[str] = None


@strawberry.type
class BsddClassProperty:
    """bSDD Class-Property relationship with contextual metadata
    
    This represents the association between a class and a property,
    including context-specific attributes like whether it's required,
    default values, and allowed values specific to this class context.
    """
    property_uri: str
    property_name: str
    property_code: str
    is_required: bool = False
    is_required_for_exchange: bool = False
    property_set: Optional[str] = None
    predefined_value: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    pattern: Optional[str] = None
    
    @strawberry.field
    def property_details(self) -> Optional[BsddProperty]:
        """Get the full property details"""
        kg = get_kg_schema()
        query = """
        MATCH (p:BsddProperty {uri: $uri})
        RETURN p
        """
        result = kg.execute_query(query, {"uri": self.property_uri})
        if result:
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
        return None


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
class NodeTypeCount:
    """Count of nodes by type - used for GraphStats distribution"""
    node_type: str
    count: int


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
    node_type_distribution: List[NodeTypeCount]


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
    def export_ifc_dictionary(self, uri: str) -> JSON:
        """Export bSDD dictionary as IFC-compliant objects"""
        kg = get_kg_schema()
        # Get dictionary node
        query = "MATCH (d:BsddDictionary {uri: $uri}) RETURN d"
        results = kg.execute_query(query, {"uri": uri})
        if not results:
            return {"error": "Dictionary not found"}
        dict_data = dict(results[0]["d"])
        ifc_dict = map_bsdd_dictionary_to_ifc_classification(dict_data)

        # Get classes
        query = "MATCH (c:BsddClass)-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $uri}) RETURN c"
        class_results = kg.execute_query(query, {"uri": uri})
        ifc_classes = [map_bsdd_class_to_ifc_classification_reference(dict(cr["c"])) for cr in class_results]

        # Get properties
        query = "MATCH (p:BsddProperty)<-[:HAS_PROPERTY]-(c:BsddClass)-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $uri}) RETURN p"
        prop_results = kg.execute_query(query, {"uri": uri})
        ifc_properties = [map_bsdd_property_to_ifc_property_single_value(dict(pr["p"])) for pr in prop_results]

        # Get materials
        query = "MATCH (c:BsddClass {classType: 'Material'})-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $uri}) RETURN c"
        mat_results = kg.execute_query(query, {"uri": uri})
        ifc_materials = [map_bsdd_material_to_ifc_material(dict(mr["c"])) for mr in mat_results]

        return {
            "IfcClassification": ifc_dict,
            "IfcClassificationReferences": ifc_classes,
            "IfcPropertySingleValues": ifc_properties,
            "IfcMaterials": ifc_materials
        }

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
        OPTIONAL MATCH (c)-[:IN_DICTIONARY]->(d:BsddDictionary)
        OPTIONAL MATCH (parent:BsddClass)-[:IS_PARENT_OF]->(c)
        RETURN c, d.uri AS dictionaryUri, parent.uri AS parentClassUri
        """
        result = kg.execute_query(query, {"uri": uri})
        
        if not result:
            return None
        
        record = result[0]
        class_data = dict(record["c"])
        return BsddClass(
            uri=class_data.get("uri", ""),
            code=class_data.get("code", ""),
            name=class_data.get("name", ""),
            definition=class_data.get("definition"),
            class_type=class_data.get("classType"),
            dictionary_uri=record.get("dictionaryUri"),
            parent_class_uri=record.get("parentClassUri"),
            related_ifc_entities=class_data.get("relatedIfcEntities", []),
            synonyms=class_data.get("synonyms", [])
        )
    
    @strawberry.type
    class BsddClassConnection:
        edges: List[BsddClass]
        end_cursor: Optional[str]
        has_next_page: bool

    @strawberry.field
    def bsdd_classes(
        self,
        dictionary_uri: Optional[str] = None,
        class_type: Optional[str] = None,
        ifc_entity: Optional[str] = None,
        search_text: Optional[str] = None,
        first: Optional[int] = 20,
        after: Optional[str] = None
    ) -> BsddClassConnection:
        """Search bSDD classes with cursor-based pagination"""
        kg = get_kg_schema()
        where_clauses = []
        if dictionary_uri:
            where_clauses.append("EXISTS { (c)-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $dictionary_uri}) }")
        if class_type:
            where_clauses.append("c.classType = $class_type")
        if ifc_entity:
            where_clauses.append("$ifc_entity IN c.relatedIfcEntities")
        if search_text:
            where_clauses.append("(c.name CONTAINS $search_text OR c.definition CONTAINS $search_text)")
        if after:
            where_clauses.append("c.uri > $after")
        where_clause = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        query = f"""
        MATCH (c:BsddClass)
        {where_clause}
        RETURN c
        ORDER BY c.uri
        LIMIT $first
        """
        result = kg.execute_query(query, {
            "dictionary_uri": dictionary_uri,
            "class_type": class_type,
            "ifc_entity": ifc_entity,
            "search_text": search_text,
            "first": first,
            "after": after
        })
        edges = []
        end_cursor = None
        for record in result:
            class_data = dict(record["c"])
            edges.append(BsddClass(
                uri=class_data.get("uri", ""),
                code=class_data.get("code", ""),
                name=class_data.get("name", ""),
                definition=class_data.get("definition"),
                class_type=class_data.get("classType"),
                related_ifc_entities=class_data.get("relatedIfcEntities", []),
                synonyms=class_data.get("synonyms", [])
            ))
            end_cursor = class_data.get("uri", None)
        has_next_page = len(edges) == first
        return BsddClassConnection(edges=edges, end_cursor=end_cursor, has_next_page=has_next_page)
    
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
    def bsdd_allowed_values(
        self,
        property_uri: str,
        limit: Optional[int] = 100
    ) -> List[BsddAllowedValue]:
        """Get allowed values for a specific bSDD property"""
        kg = get_kg_schema()
        query = """
        MATCH (p:BsddProperty {uri: $property_uri})-[:HAS_ALLOWED_VALUE]->(av:BsddAllowedValue)
        RETURN av
        ORDER BY av.sortNumber, av.value
        LIMIT $limit
        """
        result = kg.execute_query(query, {"property_uri": property_uri, "limit": limit})
        
        values = []
        for record in result:
            av_data = dict(record["av"])
            values.append(BsddAllowedValue(
                uri=av_data.get("uri", ""),
                value=av_data.get("value", ""),
                code=av_data.get("code"),
                description=av_data.get("description"),
                sort_number=av_data.get("sortNumber")
            ))
        return values
    
    @strawberry.field
    def bsdd_units(
        self,
        search_text: Optional[str] = None,
        limit: Optional[int] = 100
    ) -> List[BsddUnit]:
        """Search bSDD units of measurement"""
        kg = get_kg_schema()
        
        where_clause = ""
        if search_text:
            where_clause = "WHERE u.name CONTAINS $search_text OR u.code CONTAINS $search_text OR u.symbol CONTAINS $search_text"
        
        query = f"""
        MATCH (u:BsddUnit)
        {where_clause}
        RETURN u
        ORDER BY u.name
        LIMIT $limit
        """
        result = kg.execute_query(query, {"search_text": search_text, "limit": limit})
        
        units = []
        for record in result:
            u_data = dict(record["u"])
            units.append(BsddUnit(
                uri=u_data.get("uri", ""),
                code=u_data.get("code", ""),
                name=u_data.get("name", ""),
                symbol=u_data.get("symbol")
            ))
        return units
    
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
                node_type_distribution=[
                    NodeTypeCount(node_type="BsddDictionary", count=counts.get("dictCount", 0)),
                    NodeTypeCount(node_type="BsddClass", count=counts.get("classCount", 0)),
                    NodeTypeCount(node_type="BsddProperty", count=counts.get("propCount", 0)),
                    NodeTypeCount(node_type="IfcElement", count=counts.get("ifcCount", 0)),
                    NodeTypeCount(node_type="PointCloudSegment", count=counts.get("segCount", 0))
                ]
            )
        
        return GraphStats(
            total_nodes=0,
            total_relationships=0,
            bsdd_dictionaries_count=0,
            bsdd_classes_count=0,
            bsdd_properties_count=0,
            ifc_elements_count=0,
            point_cloud_segments_count=0,
            node_type_distribution=[]
        )


# ============================================================================
# GraphQL Mutations
# ============================================================================


@strawberry.input
class IfcBsddLinkInput:
    ifc_global_id: str
    bsdd_class_uri: str


@strawberry.type
class MutationResult:
    success: bool
    error: Optional[str] = None


@strawberry.type
class Mutation:
    """GraphQL Mutation Root"""

    @strawberry.mutation
    def batch_link_ifc_to_bsdd(self, links: List[IfcBsddLinkInput]) -> List[MutationResult]:
        """Batch link multiple IFC elements to bSDD classes"""
        kg = get_kg_schema()
        results: List[MutationResult] = []
        for link in links:
            try:
                kg.link_ifc_element_to_bsdd(link.ifc_global_id, link.bsdd_class_uri)
                results.append(MutationResult(success=True))
            except Exception as e:
                logger.error(f"Failed to link IFC to bSDD: {e}")
                results.append(MutationResult(success=False, error=str(e)))
        return results

    @strawberry.mutation
    def link_ifc_to_bsdd(self, ifc_global_id: str, bsdd_class_uri: str) -> bool:
        """Create a mapping between an IFC element and a bSDD class"""
        kg = get_kg_schema()
        try:
            kg.link_ifc_element_to_bsdd(ifc_global_id, bsdd_class_uri)
            return True
        except Exception as e:
            logger.error(f"Failed to link IFC to bSDD: {e}")
            return False

    @strawberry.mutation
    def link_segment_to_bsdd(self, segment_id: str, bsdd_class_uri: str) -> bool:
        """Create a mapping between a point cloud segment and a bSDD class"""
        kg = get_kg_schema()
        try:
            kg.link_pointcloud_segment_to_bsdd(segment_id, bsdd_class_uri)
            return True
        except Exception as e:
            logger.error(f"Failed to link segment to bSDD: {e}")
            return False

    @strawberry.mutation
    def create_bsdd_class(
        self,
        uri: str,
        code: str,
        name: str,
        definition: Optional[str] = None,
        class_type: Optional[str] = None,
        dictionary_uri: Optional[str] = None,
        parent_class_uri: Optional[str] = None,
        related_ifc_entities: Optional[List[str]] = None,
        synonyms: Optional[List[str]] = None
    ) -> MutationResult:
        """Create a new bSDD class node"""
        kg = get_kg_schema()
        try:
            kg.create_bsdd_class(
                uri=uri,
                code=code,
                name=name,
                definition=definition,
                class_type=class_type,
                dictionary_uri=dictionary_uri,
                parent_class_uri=parent_class_uri,
                related_ifc_entities=related_ifc_entities or [],
                synonyms=synonyms or []
            )
            return MutationResult(success=True)
        except Exception as e:
            logger.error(f"Failed to create bSDD class: {e}")
            return MutationResult(success=False, error=str(e))


# ============================================================================
# GraphQL Schema
# ============================================================================

schema = strawberry.Schema(query=Query, mutation=Mutation)

# Create GraphQL router for FastAPI
# strawberry >=0.234 uses graphql_ide instead of graphiql; path is set in include_router
try:
    graphql_router = GraphQLRouter(schema, graphql_ide="graphiql")  # strawberry >=0.234
except TypeError:
    graphql_router = GraphQLRouter(schema, graphiql=True)  # strawberry <0.234 fallback


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
