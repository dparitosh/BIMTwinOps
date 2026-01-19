"""
GenAI Service for BIMTwinOps
Integrates Azure OpenAI for semantic search, natural language queries, and intelligent recommendations
"""
import os
import logging
from typing import List, Dict, Optional, Any
from openai import AzureOpenAI
from neo4j import GraphDatabase
import json

logger = logging.getLogger(__name__)


class BIMTwinOpsGenAI:
    """
    GenAI service for BIMTwinOps knowledge graph
    Provides natural language interface to bSDD-powered knowledge graph
    """
    
    def __init__(
        self,
        azure_endpoint: str,
        azure_api_key: str,
        azure_api_version: str = "2024-08-01-preview",
        deployment_name: str = "gpt-4o",
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: Optional[str] = None
    ):
        """
        Initialize GenAI service
        
        Args:
            azure_endpoint: Azure OpenAI endpoint URL
            azure_api_key: Azure OpenAI API key
            azure_api_version: API version
            deployment_name: Name of the deployed model
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
        """
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            api_version=azure_api_version
        )
        self.deployment = deployment_name
        
        # Validate Neo4j password is provided
        if not neo4j_password:
            neo4j_password = os.getenv("NEO4J_PASSWORD")
        if not neo4j_password:
            raise ValueError("neo4j_password is required - set NEO4J_PASSWORD env var or pass explicitly")
        
        self.neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        # System prompts for different tasks
        self.system_prompts = {
            "kg_query": """You are an expert in building information modeling (BIM), 
IFC standards, and buildingSMART Data Dictionary (bSDD). You help users query 
a knowledge graph containing standardized building data. 

When users ask questions, analyze their intent and generate appropriate Cypher 
queries to retrieve relevant information from the Neo4j knowledge graph.

The knowledge graph contains:
- bSDD Dictionaries, Classes, Properties
- IFC Elements with bSDD mappings
- Point cloud segments with semantic labels
- Spatial relationships between building elements

Return responses in JSON format with: {cypher_query, explanation, parameters}""",

            "property_recommendation": """You are an expert in building property standards 
and bSDD (buildingSMART Data Dictionary). Based on building element types and contexts, 
recommend appropriate standardized properties from bSDD that should be captured.

Consider:
- Element type and function
- Lifecycle phase requirements
- Regional standards and regulations
- Industry best practices

Return recommendations in JSON format with: {properties: [{name, definition, why_needed}]}""",

            "classification_mapping": """You are an expert in building classification systems 
including IFC, Uniclass, Omniclass, and bSDD. Help map building elements to appropriate 
standardized classifications.

Consider:
- Element characteristics and function
- Spatial context and relationships
- Industry domain requirements
- Interoperability needs

Return mappings in JSON format with: {classifications: [{system, code, name, confidence}]}""",

            "semantic_enrichment": """You are an expert in semantic data enrichment for 
digital twins. Analyze building data and suggest enrichments using bSDD standards.

Consider:
- Missing property values
- Incomplete classifications
- Relationship gaps
- Data quality improvements

Return suggestions in JSON format with: {enrichments: [{type, target, suggestion, rationale}]}"""
        }
    
    def close(self):
        """Close Neo4j connection"""
        self.neo4j_driver.close()
    
    def semantic_search(
        self,
        query: str,
        context_type: str = "all",
        limit: int = 10
    ) -> List[Dict]:
        """
        Perform semantic search across knowledge graph using GenAI
        
        Args:
            query: Natural language search query
            context_type: Type of context to search (bsdd, ifc, pointcloud, all)
            limit: Maximum number of results
            
        Returns:
            List of relevant results with explanations
        """
        logger.info(f"Semantic search: {query}")
        
        try:
            # Use LLM to convert query to Cypher
            cypher_result = self._generate_cypher_query(query, context_type)
            
            if not cypher_result.get("cypher_query"):
                return []
            
            # Execute Cypher query
            with self.neo4j_driver.session() as session:
                results = session.run(
                    cypher_result["cypher_query"],
                    cypher_result.get("parameters", {})
                ).data()
            
            # Enhance results with AI-generated summaries
            enhanced_results = self._enhance_results_with_ai(
                results,
                query,
                limit
            )
            
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _generate_cypher_query(
        self,
        natural_language_query: str,
        context_type: str = "all"
    ) -> Dict:
        """
        Generate Cypher query from natural language using LLM
        
        Args:
            natural_language_query: User's question in natural language
            context_type: Context to focus on
            
        Returns:
            Dictionary with cypher_query, explanation, parameters
        """
        # Build context-specific schema information
        schema_context = self._get_schema_context(context_type)
        
        prompt = f"""Given the following Neo4j knowledge graph schema:

{schema_context}

User Question: {natural_language_query}

Generate a Cypher query to answer this question. Return only valid JSON with this structure:
{{
    "cypher_query": "MATCH ... RETURN ...",
    "explanation": "This query finds...",
    "parameters": {{}}
}}

Important:
- Use proper Cypher syntax
- Include LIMIT clauses when appropriate
- Handle optional relationships with OPTIONAL MATCH
- Return clear property names
- Explain what the query does
"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.system_prompts["kg_query"]},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Generated Cypher: {result.get('cypher_query')}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate Cypher query: {e}")
            return {"cypher_query": None, "explanation": str(e), "parameters": {}}
    
    def _get_schema_context(self, context_type: str = "all") -> str:
        """Get relevant schema information for query generation"""
        schema = """
Node Types:
- BsddDictionary (uri, name, version, organizationCode, status)
- BsddClass (uri, code, name, definition, classType, relatedIfcEntities)
- BsddProperty (uri, code, name, definition, dataType, units)
- IfcElement (globalId, name, ifcType, properties)
- PointCloudSegment (segmentId, label, semanticClass, pointCount)
- SemanticClass (label, classId, name, color)

Relationship Types:
- (BsddClass)-[:IN_DICTIONARY]->(BsddDictionary)
- (BsddClass)-[:HAS_PROPERTY]->(BsddProperty)
- (BsddClass)-[:IS_PARENT_OF]->(BsddClass)
- (BsddClass)-[:RELATED_TO]->(BsddClass)
- (IfcElement)-[:MAPS_TO_BSDD]->(BsddClass)
- (PointCloudSegment)-[:MAPS_TO_BSDD]->(BsddClass)
- (PointCloudSegment)-[:HAS_SEMANTIC_LABEL]->(SemanticClass)
- (IfcElement)-[:CORRESPONDS_TO]->(PointCloudSegment)
"""
        return schema
    
    def _enhance_results_with_ai(
        self,
        results: List[Dict],
        original_query: str,
        limit: int
    ) -> List[Dict]:
        """Enhance query results with AI-generated summaries and relevance scores"""
        if not results:
            return []
        
        # Truncate results
        results = results[:limit]
        
        # Generate summary
        prompt = f"""User asked: "{original_query}"

Query returned these results:
{json.dumps(results[:3], indent=2)}

Provide a brief, natural language summary of what was found and how it relates 
to the user's question. Be concise (2-3 sentences).

Return JSON: {{"summary": "...", "result_count": N}}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": "You are a helpful BIM data assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            summary = json.loads(response.choices[0].message.content)
            
            return {
                "summary": summary.get("summary", ""),
                "result_count": len(results),
                "results": results
            }
            
        except Exception as e:
            logger.warning(f"Failed to enhance results: {e}")
            return {
                "summary": f"Found {len(results)} results",
                "result_count": len(results),
                "results": results
            }
    
    def recommend_properties(
        self,
        element_type: str,
        context: Optional[Dict] = None
    ) -> List[Dict]:
        """
        Recommend standardized properties for a building element
        
        Args:
            element_type: Type of building element (e.g., "IfcWall", "wall")
            context: Additional context (lifecycle phase, region, etc.)
            
        Returns:
            List of recommended properties with rationale
        """
        logger.info(f"Recommending properties for: {element_type}")
        
        # Get relevant bSDD classes from knowledge graph
        bsdd_classes = self._get_bsdd_classes_for_element(element_type)
        
        context_str = json.dumps(context or {}, indent=2)
        bsdd_context = json.dumps(bsdd_classes[:3], indent=2) if bsdd_classes else "No bSDD mappings found"
        
        prompt = f"""Recommend standardized properties for a building element:

Element Type: {element_type}
Context: {context_str}

Relevant bSDD Classifications:
{bsdd_context}

Based on industry best practices and bSDD standards, recommend 5-10 key properties 
that should be captured for this element. Focus on:
- Essential identification properties
- Functional/performance properties
- Geometric properties
- Material/composition properties
- Lifecycle properties (if relevant to context)

Return JSON with this structure:
{{
    "properties": [
        {{
            "name": "PropertyName",
            "bsdd_uri": "https://...",
            "definition": "What this property represents",
            "data_type": "string|number|boolean",
            "why_needed": "Why this property is important",
            "priority": "critical|high|medium",
            "example_value": "Example value"
        }}
    ]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.system_prompts["property_recommendation"]},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("properties", [])
            
        except Exception as e:
            logger.error(f"Property recommendation failed: {e}")
            return []
    
    def _get_bsdd_classes_for_element(self, element_type: str) -> List[Dict]:
        """Query knowledge graph for bSDD classes related to element type"""
        query = """
        MATCH (c:BsddClass)
        WHERE $element_type IN c.relatedIfcEntities 
           OR toLower(c.name) CONTAINS toLower($search_term)
        OPTIONAL MATCH (c)-[:HAS_PROPERTY]->(p:BsddProperty)
        RETURN c.uri as uri, c.name as name, c.definition as definition,
               collect(DISTINCT p.name)[..10] as common_properties
        LIMIT 5
        """
        
        try:
            with self.neo4j_driver.session() as session:
                results = session.run(query, {
                    "element_type": element_type,
                    "search_term": element_type.replace("Ifc", "")
                }).data()
                return results
        except Exception as e:
            logger.warning(f"Failed to query bSDD classes: {e}")
            return []
    
    def suggest_classifications(
        self,
        element_description: str,
        available_systems: List[str] = None
    ) -> List[Dict]:
        """
        Suggest appropriate classifications for an element
        
        Args:
            element_description: Description of the element
            available_systems: Classification systems to consider (IFC, Uniclass, etc.)
            
        Returns:
            List of suggested classifications with confidence scores
        """
        if available_systems is None:
            available_systems = ["IFC", "bSDD", "Uniclass", "Omniclass"]
        
        # Query knowledge graph for similar classifications
        kg_suggestions = self._query_similar_classifications(element_description)
        
        prompt = f"""Suggest appropriate classifications for this building element:

Description: {element_description}

Available classification systems: {', '.join(available_systems)}

Similar elements from knowledge graph:
{json.dumps(kg_suggestions[:3], indent=2)}

Suggest the most appropriate classifications. Return JSON:
{{
    "classifications": [
        {{
            "system": "IFC|bSDD|Uniclass|Omniclass",
            "code": "Classification code",
            "name": "Classification name",
            "confidence": 0.0-1.0,
            "reasoning": "Why this classification fits"
        }}
    ]
}}"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "system", "content": self.system_prompts["classification_mapping"]},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("classifications", [])
            
        except Exception as e:
            logger.error(f"Classification suggestion failed: {e}")
            return []
    
    def _query_similar_classifications(self, description: str) -> List[Dict]:
        """Query knowledge graph for similar elements"""
        # Simple keyword-based search (in production, use vector similarity)
        keywords = description.lower().split()[:5]
        
        query = """
        MATCH (c:BsddClass)
        WHERE any(keyword IN $keywords WHERE toLower(c.name) CONTAINS keyword
                                         OR toLower(c.definition) CONTAINS keyword)
        RETURN c.code as code, c.name as name, c.definition as definition,
               c.classType as type
        LIMIT 5
        """
        
        try:
            with self.neo4j_driver.session() as session:
                results = session.run(query, {"keywords": keywords}).data()
                return results
        except Exception as e:
            logger.warning(f"Failed to query similar classifications: {e}")
            return []
    
    def chat(
        self,
        message: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Natural language chat interface for knowledge graph
        
        Args:
            message: User message
            conversation_history: Previous messages in conversation
            
        Returns:
            AI response
        """
        if conversation_history is None:
            conversation_history = []
        
        # Build messages with context from knowledge graph
        messages = [
            {
                "role": "system",
                "content": """You are an AI assistant for BIMTwinOps, an enterprise digital twin platform. 
You have access to a knowledge graph containing:
- Standardized building data from bSDD (buildingSMART Data Dictionary)
- IFC building models
- Point cloud semantic segmentation data
- Spatial relationships and classifications

Help users understand their building data, find standardized properties, 
map classifications, and query the knowledge graph. Be concise and helpful."""
            }
        ]
        
        # Add conversation history
        messages.extend(conversation_history[-5:])  # Last 5 messages for context
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        try:
            response = self.client.chat.completions.create(
                model=self.deployment,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            return f"I'm sorry, I encountered an error: {str(e)}"


# Example usage
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    logging.basicConfig(level=logging.INFO)
    
    # Initialize GenAI service
    genai = BIMTwinOpsGenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o"),
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password")
    )
    
    try:
        # Example 1: Semantic search
        print("\n=== Semantic Search ===")
        results = genai.semantic_search("Find all properties for walls")
        print(json.dumps(results, indent=2))
        
        # Example 2: Property recommendations
        print("\n=== Property Recommendations ===")
        props = genai.recommend_properties(
            element_type="IfcWall",
            context={"phase": "design", "region": "EU"}
        )
        for prop in props:
            print(f"- {prop['name']}: {prop.get('why_needed', '')}")
        
        # Example 3: Classification suggestions
        print("\n=== Classification Suggestions ===")
        classifications = genai.suggest_classifications(
            "External load-bearing wall made of concrete"
        )
        for cls in classifications:
            print(f"- {cls['system']}: {cls['name']} (confidence: {cls['confidence']})")
        
        # Example 4: Chat
        print("\n=== Chat Interface ===")
        response = genai.chat("What properties should I capture for windows?")
        print(response)
        
    finally:
        genai.close()
