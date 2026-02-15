"""
Knowledge Graph Schema for BIMTwinOps
Defines Neo4j node types, relationships, and constraints for bSDD integration
"""
from typing import Dict, List, Any
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class KnowledgeGraphSchema:
    """
    Defines and manages the knowledge graph schema for BIMTwinOps
    Integrates IFC models, point cloud semantics, and bSDD standardization
    """
    
    # Node Labels
    NODE_LABELS = {
        # Building Model Nodes
        "IFC_ELEMENT": "IfcElement",
        "IFC_SPACE": "IfcSpace",
        "IFC_BUILDING": "IfcBuilding",
        "IFC_STOREY": "IfcStorey",
        
        # Point Cloud Nodes
        "POINT_CLOUD_SEGMENT": "PointCloudSegment",
        "SEMANTIC_CLASS": "SemanticClass",
        
        # bSDD Standard Nodes
        "BSDD_DICTIONARY": "BsddDictionary",
        "BSDD_CLASS": "BsddClass",
        "BSDD_PROPERTY": "BsddProperty",
        "BSDD_CLASS_PROPERTY": "BsddClassProperty",
        "BSDD_UNIT": "BsddUnit",
        "BSDD_ALLOWED_VALUE": "BsddAllowedValue",
        "BSDD_CLASS_RELATION": "BsddClassRelation",
        "BSDD_PROPERTY_RELATION": "BsddPropertyRelation",
        
        # Property and Relationship Nodes
        "PROPERTY": "Property",
        "CLASSIFICATION": "Classification",
        "MATERIAL": "Material"
    }
    
    # Relationship Types
    RELATIONSHIPS = {
        # Spatial Relationships
        "CONTAINS": "CONTAINS",
        "LOCATED_IN": "LOCATED_IN",
        "CONNECTED_TO": "CONNECTED_TO",
        "NEAR": "NEAR",
        
        # Classification Relationships
        "HAS_CLASSIFICATION": "HAS_CLASSIFICATION",
        "CLASSIFIED_AS": "CLASSIFIED_AS",
        "IS_SUBCLASS_OF": "IS_SUBCLASS_OF",
        "IS_PARENT_OF": "IS_PARENT_OF",
        "HAS_PARENT_CLASS": "HAS_PARENT_CLASS",
        
        # Property Relationships
        "HAS_PROPERTY": "HAS_PROPERTY",
        "HAS_CLASS_PROPERTY": "HAS_CLASS_PROPERTY",
        "REFERENCES_PROPERTY": "REFERENCES_PROPERTY",
        "PROPERTY_OF": "PROPERTY_OF",
        "HAS_ALLOWED_VALUE": "HAS_ALLOWED_VALUE",
        "HAS_UNIT": "HAS_UNIT",
        
        # bSDD Relationships
        "MAPS_TO_BSDD": "MAPS_TO_BSDD",
        "IFC_ENTITY_MAPPING": "IFC_ENTITY_MAPPING",
        "RELATED_TO": "RELATED_TO",
        "EQUIVALENT_TO": "EQUIVALENT_TO",
        "HAS_CLASS_RELATION": "HAS_CLASS_RELATION",
        "HAS_PROPERTY_RELATION": "HAS_PROPERTY_RELATION",
        
        # Point Cloud Relationships
        "SEGMENT_OF": "SEGMENT_OF",
        "HAS_SEMANTIC_LABEL": "HAS_SEMANTIC_LABEL",
        "CORRESPONDS_TO": "CORRESPONDS_TO",
        
        # Dictionary Organization
        "IN_DICTIONARY": "IN_DICTIONARY",
        "VERSION_OF": "VERSION_OF"
    }
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str, database: str = None):
        """Initialize connection to Neo4j database"""
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        self._database = database
    
    def _session(self):
        """Create a session targeting the configured database"""
        return self.driver.session(database=self._database)
    
    def close(self):
        """Close Neo4j driver connection"""
        self.driver.close()
    
    def execute_query(self, query: str, parameters: Dict[str, Any]) -> List[Dict]:
        """
        Execute a Cypher query and return results
        Helper method for GraphQL resolvers
        """
        with self._session() as session:
            result = session.run(query, parameters)
            return [record.data() for record in result]
    
    def create_schema(self):
        """Create all constraints and indexes for the knowledge graph"""
        with self._session() as session:
            # Create constraints for unique identifiers
            constraints = [
                # IFC Elements
                f"CREATE CONSTRAINT ifc_element_guid IF NOT EXISTS "
                f"FOR (e:{self.NODE_LABELS['IFC_ELEMENT']}) REQUIRE e.globalId IS UNIQUE",
                
                # Point Cloud Segments
                f"CREATE CONSTRAINT pc_segment_id IF NOT EXISTS "
                f"FOR (s:{self.NODE_LABELS['POINT_CLOUD_SEGMENT']}) REQUIRE s.segmentId IS UNIQUE",
                
                # bSDD Nodes
                f"CREATE CONSTRAINT bsdd_dict_uri IF NOT EXISTS "
                f"FOR (d:{self.NODE_LABELS['BSDD_DICTIONARY']}) REQUIRE d.uri IS UNIQUE",
                
                f"CREATE CONSTRAINT bsdd_class_uri IF NOT EXISTS "
                f"FOR (c:{self.NODE_LABELS['BSDD_CLASS']}) REQUIRE c.uri IS UNIQUE",
                
                f"CREATE CONSTRAINT bsdd_property_uri IF NOT EXISTS "
                f"FOR (p:{self.NODE_LABELS['BSDD_PROPERTY']}) REQUIRE p.uri IS UNIQUE",
                
                f"CREATE CONSTRAINT bsdd_class_property_uri IF NOT EXISTS "
                f"FOR (cp:{self.NODE_LABELS['BSDD_CLASS_PROPERTY']}) REQUIRE cp.uri IS UNIQUE",
                
                f"CREATE CONSTRAINT bsdd_allowed_value_uri IF NOT EXISTS "
                f"FOR (av:{self.NODE_LABELS['BSDD_ALLOWED_VALUE']}) REQUIRE av.uri IS UNIQUE",
                
                # Semantic Classes
                f"CREATE CONSTRAINT semantic_class_label IF NOT EXISTS "
                f"FOR (sc:{self.NODE_LABELS['SEMANTIC_CLASS']}) REQUIRE sc.label IS UNIQUE"
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                    logger.info(f"Created constraint: {constraint[:50]}...")
                except Exception as e:
                    logger.warning(f"Constraint may already exist: {e}")
            
            # Create indexes for common queries
            indexes = [
                # Text search indexes
                f"CREATE INDEX ifc_element_name IF NOT EXISTS "
                f"FOR (e:{self.NODE_LABELS['IFC_ELEMENT']}) ON (e.name)",
                
                f"CREATE INDEX bsdd_class_name IF NOT EXISTS "
                f"FOR (c:{self.NODE_LABELS['BSDD_CLASS']}) ON (c.name)",
                
                f"CREATE INDEX bsdd_class_code IF NOT EXISTS "
                f"FOR (c:{self.NODE_LABELS['BSDD_CLASS']}) ON (c.code)",
                
                f"CREATE INDEX bsdd_property_name IF NOT EXISTS "
                f"FOR (p:{self.NODE_LABELS['BSDD_PROPERTY']}) ON (p.name)",
                
                # Lookup indexes
                f"CREATE INDEX ifc_element_type IF NOT EXISTS "
                f"FOR (e:{self.NODE_LABELS['IFC_ELEMENT']}) ON (e.ifcType)",
                
                f"CREATE INDEX bsdd_dict_org IF NOT EXISTS "
                f"FOR (d:{self.NODE_LABELS['BSDD_DICTIONARY']}) ON (d.organizationCode)",
                
                f"CREATE INDEX semantic_class_id IF NOT EXISTS "
                f"FOR (sc:{self.NODE_LABELS['SEMANTIC_CLASS']}) ON (sc.classId)"
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                    logger.info(f"Created index: {index[:50]}...")
                except Exception as e:
                    logger.warning(f"Index may already exist: {e}")
    
    def create_bsdd_dictionary_node(
        self,
        uri: str,
        name: str,
        version: str,
        organization_code: str,
        status: str,
        language_code: str,
        **kwargs
    ) -> Dict:
        """Create a bSDD Dictionary node"""
        query = f"""
        MERGE (d:{self.NODE_LABELS['BSDD_DICTIONARY']} {{uri: $uri}})
        SET d.name = $name,
            d.version = $version,
            d.organizationCode = $organization_code,
            d.status = $status,
            d.languageCode = $language_code,
            d.license = $license,
            d.releaseDate = $release_date,
            d.moreInfoUrl = $more_info_url,
            d.basexUri = $basex_uri,
            d.lastUpdated = timestamp()
        RETURN d
        """
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "name": name,
                "version": version,
                "organization_code": organization_code,
                "status": status,
                "language_code": language_code,
                "license": kwargs.get("license"),
                "release_date": kwargs.get("release_date"),
                "more_info_url": kwargs.get("more_info_url"),
                "basex_uri": kwargs.get("basex_uri")
            })
            return result.single()[0]
    
    def create_bsdd_class(
        self,
        uri: str,
        code: str,
        name: str,
        definition: str = None,
        class_type: str = None,
        dictionary_uri: str = None,
        parent_class_uri: str = None,
        related_ifc_entities: list = None,
        synonyms: list = None
    ):
        """Create a bSDD Class node and link to dictionary (wrapper for GraphQL)"""
        return self.create_bsdd_class_node(
            uri=uri,
            code=code,
            name=name,
            dictionary_uri=dictionary_uri,
            definition=definition,
            class_type=class_type,
            parent_class_uri=parent_class_uri,
            related_ifc_entities=related_ifc_entities or [],
            synonyms=synonyms or []
        )
    
    def create_bsdd_class_node(
        self,
        uri: str,
        code: str,
        name: str,
        dictionary_uri: str,
        **kwargs
    ) -> Dict:
        """Create a bSDD Class node and link to dictionary"""
        query = f"""
        MATCH (d:{self.NODE_LABELS['BSDD_DICTIONARY']} {{uri: $dictionary_uri}})
        MERGE (c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $uri}})
        SET c.code = $code,
            c.name = $name,
            c.definition = $definition,
            c.classType = $class_type,
            c.synonyms = $synonyms,
            c.relatedIfcEntities = $related_ifc_entities,
            c.lastUpdated = timestamp()
        MERGE (c)-[:{self.RELATIONSHIPS['IN_DICTIONARY']}]->(d)
        RETURN c
        """
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "code": code,
                "name": name,
                "dictionary_uri": dictionary_uri,
                "definition": kwargs.get("definition"),
                "class_type": kwargs.get("class_type"),
                "synonyms": kwargs.get("synonyms", []),
                "related_ifc_entities": kwargs.get("related_ifc_entities", [])
            })
            return result.single()[0]
    
    def create_bsdd_property_node(
        self,
        uri: str,
        code: str,
        name: str,
        **kwargs
    ) -> Dict:
        """Create a bSDD Property node"""
        query = f"""
        MERGE (p:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $uri}})
        SET p.code = $code,
            p.name = $name,
            p.definition = $definition,
            p.dataType = $data_type,
            p.units = $units,
            p.physicalQuantity = $physical_quantity,
            p.dimension = $dimension,
            p.pattern = $pattern,
            p.isRequired = $is_required,
            p.lastUpdated = timestamp()
        RETURN p
        """
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "code": code,
                "name": name,
                "definition": kwargs.get("definition"),
                "data_type": kwargs.get("data_type"),
                "units": kwargs.get("units", []),
                "physical_quantity": kwargs.get("physical_quantity"),
                "dimension": kwargs.get("dimension"),
                "pattern": kwargs.get("pattern"),
                "is_required": kwargs.get("is_required", False)
            })
            return result.single()[0]
    
    def link_class_to_property(
        self,
        class_uri: str,
        property_uri: str,
        property_set: str = None,
        is_required: bool = False
    ):
        """Create HAS_PROPERTY relationship between class and property"""
        query = f"""
        MATCH (c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $class_uri}})
        MATCH (p:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $property_uri}})
        MERGE (c)-[r:{self.RELATIONSHIPS['HAS_PROPERTY']}]->(p)
        SET r.propertySet = $property_set,
            r.isRequired = $is_required
        RETURN r
        """
        
        with self._session() as session:
            session.run(query, {
                "class_uri": class_uri,
                "property_uri": property_uri,
                "property_set": property_set,
                "is_required": is_required
            })
    
    def create_class_relationship(
        self,
        from_class_uri: str,
        to_class_uri: str,
        relation_type: str
    ):
        """Create relationship between two bSDD classes"""
        # Map bSDD relation types to our schema
        relation_mapping = {
            "IsParentOf": self.RELATIONSHIPS['IS_PARENT_OF'],
            "IsChildOf": self.RELATIONSHIPS['IS_SUBCLASS_OF'],
            "IsEqualTo": self.RELATIONSHIPS['EQUIVALENT_TO'],
            "IsSimilarTo": self.RELATIONSHIPS['RELATED_TO'],
            "HasReference": self.RELATIONSHIPS['RELATED_TO']
        }
        
        relationship = relation_mapping.get(relation_type, self.RELATIONSHIPS['RELATED_TO'])
        
        query = f"""
        MATCH (c1:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $from_uri}})
        MATCH (c2:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $to_uri}})
        MERGE (c1)-[r:{relationship}]->(c2)
        SET r.relationType = $relation_type
        RETURN r
        """
        
        with self._session() as session:
            session.run(query, {
                "from_uri": from_class_uri,
                "to_uri": to_class_uri,
                "relation_type": relation_type
            })
    
    def link_ifc_element_to_bsdd(
        self,
        ifc_global_id: str,
        bsdd_class_uri: str,
        confidence: float = 1.0
    ):
        """Create mapping between IFC element and bSDD class"""
        query = f"""
        MATCH (ifc:{self.NODE_LABELS['IFC_ELEMENT']} {{globalId: $ifc_global_id}})
        MATCH (bsdd:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $bsdd_class_uri}})
        MERGE (ifc)-[r:{self.RELATIONSHIPS['MAPS_TO_BSDD']}]->(bsdd)
        SET r.confidence = $confidence,
            r.createdAt = timestamp()
        RETURN r
        """
        
        with self._session() as session:
            session.run(query, {
                "ifc_global_id": ifc_global_id,
                "bsdd_class_uri": bsdd_class_uri,
                "confidence": confidence
            })
    
    def link_pointcloud_segment_to_bsdd(
        self,
        segment_id: str,
        bsdd_class_uri: str,
        confidence: float = 0.8
    ):
        """Create mapping between point cloud segment and bSDD class"""
        query = f"""
        MATCH (seg:{self.NODE_LABELS['POINT_CLOUD_SEGMENT']} {{segmentId: $segment_id}})
        MATCH (bsdd:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $bsdd_class_uri}})
        MERGE (seg)-[r:{self.RELATIONSHIPS['MAPS_TO_BSDD']}]->(bsdd)
        SET r.confidence = $confidence,
            r.createdAt = timestamp()
        RETURN r
        """
        
        with self._session() as session:
            session.run(query, {
                "segment_id": segment_id,
                "bsdd_class_uri": bsdd_class_uri,
                "confidence": confidence
            })
            
    def create_bsdd_class_property_node(
        self, 
        uri: str, 
        class_uri: str,
        property_uri: str,
        property_set: str = None,
        is_required: bool = False,
        **kwargs
    ):
        """
        Create a BsddClassProperty node (reified relationship)
        Links BsddClass -> BsddClassProperty -> BsddProperty
        """
        query = f"""
        MATCH (c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $class_uri}})
        MATCH (p:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $property_uri}})
        
        MERGE (cp:{self.NODE_LABELS['BSDD_CLASS_PROPERTY']} {{uri: $uri}})
        SET cp.propertySet = $property_set,
            cp.isRequired = $is_required,
            cp.minInclusive = $min_inclusive,
            cp.maxInclusive = $max_inclusive,
            cp.symbol = $symbol,
            cp.lastUpdated = timestamp()
            
        MERGE (c)-[:{self.RELATIONSHIPS['HAS_CLASS_PROPERTY']}]->(cp)
        MERGE (cp)-[:{self.RELATIONSHIPS['REFERENCES_PROPERTY']}]->(p)
        
        RETURN cp
        """
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "class_uri": class_uri,
                "property_uri": property_uri,
                "property_set": property_set,
                "is_required": is_required,
                "min_inclusive": kwargs.get("min_inclusive"),
                "max_inclusive": kwargs.get("max_inclusive"),
                "symbol": kwargs.get("symbol")
            })
            return result.single()[0] if result.peek() else None

    def create_bsdd_allowed_value_node(
        self,
        uri: str,
        value: str,
        property_uri: str = None, 
        class_property_uri: str = None,
        description: str = None,
        sort_number: int = None
    ):
        """
        Create a BsddAllowedValue node
        Can be linked to BsddProperty OR BsddClassProperty via HAS_ALLOWED_VALUE
        """
        query = f"""
        MERGE (av:{self.NODE_LABELS['BSDD_ALLOWED_VALUE']} {{uri: $uri}})
        SET av.value = $value,
            av.description = $description,
            av.sortNumber = $sort_number,
            av.lastUpdated = timestamp()
        """
        
        # Link to Property if provided
        if property_uri:
            query += f"""
            WITH av
            MATCH (p:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $property_uri}})
            MERGE (p)-[:{self.RELATIONSHIPS['HAS_ALLOWED_VALUE']}]->(av)
            """
            
        # Link to ClassProperty if provided
        if class_property_uri:
            query += f"""
            WITH av
            MATCH (cp:{self.NODE_LABELS['BSDD_CLASS_PROPERTY']} {{uri: $class_property_uri}})
            MERGE (cp)-[:{self.RELATIONSHIPS['HAS_ALLOWED_VALUE']}]->(av)
            """
            
        query += "RETURN av"
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "value": value,
                "property_uri": property_uri,
                "class_property_uri": class_property_uri,
                "description": description,
                "sort_number": sort_number
            })
            return result.single()[0] if result.peek() else None

    def create_bsdd_class_relation_node(
        self,
        uri: str,
        from_class_uri: str,
        to_class_uri: str,
        relation_type: str,
        **kwargs
    ):
        """
        Create a BsddClassRelation node (reified relationship)
        Links BsddClass (from) -> BsddClassRelation -> BsddClass (to)
        """
        query = f"""
        MATCH (c1:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $from_uri}})
        MATCH (c2:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $to_uri}})
        
        MERGE (cr:{self.NODE_LABELS['BSDD_CLASS_RELATION']} {{uri: $uri}})
        SET cr.relationType = $relation_type,
            cr.description = $description,
            cr.fraction = $fraction,
            cr.lastUpdated = timestamp()
            
        MERGE (c1)-[:{self.RELATIONSHIPS['HAS_CLASS_RELATION']}]->(cr)
        MERGE (cr)-[:{self.RELATIONSHIPS['RELATED_TO']}]->(c2)
        
        RETURN cr
        """
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "from_uri": from_class_uri,
                "to_uri": to_class_uri,
                "relation_type": relation_type,
                "description": kwargs.get("description"),
                "fraction": kwargs.get("fraction")
            })
            return result.single()[0] if result.peek() else None
            
    def create_bsdd_property_relation_node(
        self,
        uri: str,
        from_property_uri: str,
        to_property_uri: str,
        relation_type: str,
        **kwargs
    ):
        """
        Create a BsddPropertyRelation node (reified relationship)
        Links BsddProperty (from) -> BsddPropertyRelation -> BsddProperty (to)
        """
        query = f"""
        MATCH (p1:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $from_uri}})
        MATCH (p2:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $to_uri}})
        
        MERGE (pr:{self.NODE_LABELS['BSDD_PROPERTY_RELATION']} {{uri: $uri}})
        SET pr.relationType = $relation_type,
            pr.description = $description,
            pr.lastUpdated = timestamp()
            
        MERGE (p1)-[:{self.RELATIONSHIPS['HAS_PROPERTY_RELATION']}]->(pr)
        MERGE (pr)-[:{self.RELATIONSHIPS['RELATED_TO']}]->(p2)
        
        RETURN pr
        """
        
        with self._session() as session:
            result = session.run(query, {
                "uri": uri,
                "from_uri": from_property_uri,
                "to_uri": to_property_uri,
                "relation_type": relation_type,
                "description": kwargs.get("description")
            })
            return result.single()[0] if result.peek() else None

    # --- Query Methods (P2.2) ---

    def get_class_hierarchy(self, uri: str, depth: int = 5) -> Dict:
        """Get class hierarchy (parents and children)"""
        # Parents
        parent_query = f"""
        MATCH path = (c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $uri}})-[:{self.RELATIONSHIPS['HAS_PARENT_CLASS']}*1..{depth}]->(parent)
        RETURN [node in nodes(path) | {{uri: node.uri, name: node.name, code: node.code}}] as parents
        """
        
        # Children
        child_query = f"""
        MATCH path = (child)-[:{self.RELATIONSHIPS['HAS_PARENT_CLASS']}*1..1]->(c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $uri}})
        RETURN {{uri: child.uri, name: child.name, code: child.code}} as child
        """
        
        with self._session() as session:
             parents = session.run(parent_query, {"uri": uri}).value()
             children = session.run(child_query, {"uri": uri}).data()
             
             return {
                 "uri": uri,
                 "parents": parents if parents else [],
                 "children": [c["child"] for c in children]
             }

    def get_class_properties(self, uri: str) -> List[Dict]:
        """Get all properties associated with a class, including inherited details"""
        query = f"""
        MATCH (c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $uri}})
        MATCH (c)-[r:{self.RELATIONSHIPS['HAS_CLASS_PROPERTY']}]->(cp:{self.NODE_LABELS['BSDD_CLASS_PROPERTY']})
        OPTIONAL MATCH (cp)-[:{self.RELATIONSHIPS['REFERENCES_PROPERTY']}]->(p:{self.NODE_LABELS['BSDD_PROPERTY']})
        RETURN {{
            uri: cp.uri,
            propertySet: cp.propertySet,
            isRequired: cp.isRequired,
            property: {{
                uri: p.uri,
                code: p.code,
                name: p.name,
                dataType: p.dataType
            }}
        }} as classProperty
        ORDER BY cp.sortNumber ASC
        """
        with self._session() as session:
            return session.run(query, {"uri": uri}).value()

    def get_class_relations(self, uri: str) -> List[Dict]:
        """Get relations involving this class (both direct and reified)"""
        # Direct relationships are covered by specific methods usually.
        # Assuming reified BSDD_CLASS_RELATION here primarily.
        query = f"""
        MATCH (c:{self.NODE_LABELS['BSDD_CLASS']} {{uri: $uri}})
        MATCH (c)-[:{self.RELATIONSHIPS['HAS_CLASS_RELATION']}]->(cr:{self.NODE_LABELS['BSDD_CLASS_RELATION']})
        MATCH (cr)-[:{self.RELATIONSHIPS['RELATED_TO']}]->(target:{self.NODE_LABELS['BSDD_CLASS']})
        RETURN {{
            relationType: cr.relationType,
            description: cr.description,
            targetClass: {{
                uri: target.uri,
                name: target.name,
                code: target.code
            }}
        }} as relation
        """
        with self._session() as session:
             return session.run(query, {"uri": uri}).value()

    def get_property_allowed_values(self, uri: str) -> List[Dict]:
        """Get allowed values for a property"""
        # Can be directly on Property or on ClassProperty
        query = f"""
        MATCH (p)-[:{self.RELATIONSHIPS['HAS_ALLOWED_VALUE']}]->(av:{self.NODE_LABELS['BSDD_ALLOWED_VALUE']})
        WHERE p.uri = $uri
        RETURN {{
             value: av.value,
             description: av.description,
             sortNumber: av.sortNumber
        }} as allowedValue
        ORDER BY av.sortNumber ASC
        """
        with self._session() as session:
            return session.run(query, {"uri": uri}).value()

    def get_property_relations(self, uri: str) -> List[Dict]:
        """Get relations involving this property (reified)"""
        query = f"""
        MATCH (p:{self.NODE_LABELS['BSDD_PROPERTY']} {{uri: $uri}})
        MATCH (p)-[:{self.RELATIONSHIPS['HAS_PROPERTY_RELATION']}]->(pr:{self.NODE_LABELS['BSDD_PROPERTY_RELATION']})
        MATCH (pr)-[:{self.RELATIONSHIPS['RELATED_TO']}]->(target:{self.NODE_LABELS['BSDD_PROPERTY']})
        RETURN {{
            relationType: pr.relationType,
            description: pr.description,
            targetProperty: {{
                uri: target.uri,
                name: target.name
            }}
        }} as relation
        """
        with self._session() as session:
             return session.run(query, {"uri": uri}).value()

    def get_schema_info(self) -> Dict:
        """Get information about the current schema"""
        with self._session() as session:
            # Get node counts
            node_query = """
            MATCH (n)
            RETURN labels(n) as labels, count(n) as count
            """
            nodes = session.run(node_query).data()
            
            # Get relationship counts
            rel_query = """
            MATCH ()-[r]->()
            RETURN type(r) as type, count(r) as count
            """
            relationships = session.run(rel_query).data()
            
            return {
                "nodes": nodes,
                "relationships": relationships
            }

    def advanced_search(self, query: str = None, type: str = None, status: str = None, dictionary_uri: str = None, description: str = None, limit: int = 20) -> list:
        """
        Advanced search for classes/properties with multi-field, type, status, and dictionary filtering.
        Args:
            query: Text to search in code, name, or definition
            type: 'class', 'property', or None (both)
            status: Filter by status (Active, Inactive, Preview)
            dictionary_uri: Restrict to a specific dictionary
            description: Search in description field
            limit: Max results
        Returns:
            List of matching nodes (dicts)
        """
        cypher = []
        params = {}
        if type == 'class':
            cypher.append(f"MATCH (n:{self.NODE_LABELS['BSDD_CLASS']})")
        elif type == 'property':
            cypher.append(f"MATCH (n:{self.NODE_LABELS['BSDD_PROPERTY']})")
        else:
            cypher.append(f"MATCH (n) WHERE n:{self.NODE_LABELS['BSDD_CLASS']} OR n:{self.NODE_LABELS['BSDD_PROPERTY']}")
        
        where = []
        if query:
            where.append("(toLower(n.code) CONTAINS toLower($q) OR toLower(n.name) CONTAINS toLower($q) OR toLower(n.definition) CONTAINS toLower($q))")
            params['q'] = query
        if status:
            where.append("n.status = $status")
            params['status'] = status
        if dictionary_uri:
            where.append("EXISTS { (n)-[:IN_DICTIONARY]->(d:BsddDictionary {uri: $dictionary_uri}) }")
            params['dictionary_uri'] = dictionary_uri
        if description:
            where.append("toLower(n.definition) CONTAINS toLower($desc)")
            params['desc'] = description
        if where:
            cypher.append("WHERE " + " AND ".join(where))
        cypher.append("RETURN n LIMIT $limit")
        params['limit'] = limit
        query_str = "\n".join(cypher)
        with self._session() as session:
            return [r['n'] for r in session.run(query_str, params)]


# Example usage
if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO)
    
    # Initialize schema manager - requires NEO4J_PASSWORD env var
    neo4j_password = os.getenv("NEO4J_PASSWORD")
    if not neo4j_password:
        raise ValueError("Set NEO4J_PASSWORD environment variable")
    
    schema = KnowledgeGraphSchema(
        neo4j_uri=os.getenv("NEO4J_URI", ""),
        neo4j_user=os.getenv("NEO4J_USER", ""),
        neo4j_password=neo4j_password,
        database=os.getenv("NEO4J_DATABASE")
    )
    
    try:
        # Create schema
        print("Creating knowledge graph schema...")
        schema.create_schema()
        
        # Get schema info
        print("\n=== Schema Information ===")
        info = schema.get_schema_info()
        print(f"Nodes: {info['nodes']}")
        print(f"Relationships: {info['relationships']}")
        
    finally:
        schema.close()
