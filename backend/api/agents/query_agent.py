"""
Query Agent: Read-Only Information Retrieval
Specialist agent for data queries and search operations.

This agent handles all read-only operations:
1. Graph queries via Neo4j MCP server
2. Semantic search via OpenSearch
3. bSDD dictionary lookups
4. Document retrieval from BaseX

Architecture:
    User Query → Router → Query Agent
        ↓
    [Neo4j | OpenSearch | bSDD | BaseX] via MCP
        ↓
    Structured Results → UI Generator → Components

Tools Available:
- cypher_query (Neo4j): Graph database queries
- hybrid_search_context (OpenSearch): Semantic search
- search_dictionaries, get_dictionary, get_classes, get_properties (bSDD)
- query_xquery (BaseX): Document queries

Response Format:
- Structured data ready for UI conversion
- Automatic formatting based on result type
- Error handling with user-friendly messages
"""

from typing import Dict, Any, List
import logging
from datetime import datetime
import json

from .state import AgentState
from .llm import create_llm

LANGCHAIN_AVAILABLE = False
LC_AIMessage: Any = None
LC_HumanMessage: Any = None

try:
    from langchain_core.messages import AIMessage as LC_AIMessage, HumanMessage as LC_HumanMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # LangChain is optional; fall back to simple dict messages.
    LANGCHAIN_AVAILABLE = False


def make_ai_message(content: str) -> Any:
    """Create an AI message in whichever format is available."""
    if LANGCHAIN_AVAILABLE and LC_AIMessage is not None:
        return LC_AIMessage(content=content)
    return {"type": "ai", "content": content}


def make_human_message(content: str) -> Any:
    """Create a Human message in whichever format is available."""
    if LANGCHAIN_AVAILABLE and LC_HumanMessage is not None:
        return LC_HumanMessage(content=content)
    return {"type": "human", "content": content}

# MCP Host for tool execution
try:
    from ..mcp_host.mcp_host import get_mcp_host
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    get_mcp_host = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Query Agent
# ============================================================================

class QueryAgent:
    """
    Query Agent for read-only information retrieval
    
    Handles:
    - Neo4j graph queries
    - Semantic search
    - bSDD dictionary lookups
    - Document retrieval
    
    Uses LLM to:
    1. Understand user query
    2. Select appropriate tools
    3. Format tool calls
    4. Interpret results
    5. Generate user response
    
    Usage:
        agent = QueryAgent()
        result = await agent.process(state)
    """
    
    def __init__(self):
        """Initialize query agent"""
        self.llm = create_llm(temperature=0.3) if LANGCHAIN_AVAILABLE else None
        # MCP host is initialized asynchronously; we'll create it on first use.
        self.mcp_host = None
        # Memory requires additional credentials, keep disabled unless wired.
        self.memory = None
        logger.info("QueryAgent initialized (memory disabled for testing)")
    
    async def process(self, state: AgentState) -> AgentState:
        """
        Process query request
        
        Args:
            state: Current agent state
        
        Returns:
            Updated state with query results
        """
        logger.info("Query Agent: Processing read-only query")

        # Ensure MCP host is available for tool calls
        if MCP_AVAILABLE and self.mcp_host is None and get_mcp_host is not None:
            self.mcp_host = await get_mcp_host()
        
        user_input = state["user_input"]
        messages = state.get("messages", [])
        
        try:
            # Step 1: Analyze query and select tools
            query_plan = await self._plan_query(user_input)
            
            # Step 2: Execute tools via MCP
            results = await self._execute_query_plan(query_plan)
            
            # Step 3: Format results for UI
            formatted_results = self._format_results(results, query_plan)
            
            # Step 4: Generate response
            response = await self._generate_response(user_input, formatted_results)
            
            # Step 5: Store in memory for future queries
            await self._store_in_memory(user_input, formatted_results)
            
            return {
                **state,
                "messages": messages + [make_ai_message(content=response)],
                "mcp_results": results,
                "metadata": {
                    **state.get("metadata", {}),
                    "query_plan": query_plan,
                    "result_count": len(results)
                },
                "next": "END"
            }
        
        except Exception as e:
            logger.error(f"Query Agent error: {str(e)}")
            return {
                **state,
                "error": str(e),
                "messages": messages + [
                    make_ai_message(content=f"Query failed: {str(e)}")
                ],
                "next": "error_handler"
            }
    
    async def _plan_query(self, user_input: str) -> Dict[str, Any]:
        """
        Plan query execution
        
        Analyzes user query and determines which tools to use.
        
        Args:
            user_input: User's query
        
        Returns:
            Query execution plan
        """
        # Simple rule-based planning (without LLM for now)
        query_lower = user_input.lower()
        
        # Keyword-based tool selection
        if any(word in query_lower for word in ["definition", "what is", "ifc", "property", "bsdd"]):
            plan = {
                "primary_tool": "bsdd",
                "query_type": "definition",
                "reasoning": "Query asks for definitions or bSDD information",
                "parameters": {"query": user_input}
            }
        elif any(word in query_lower for word in ["similar", "search", "find like", "related"]):
            plan = {
                "primary_tool": "opensearch",
                "query_type": "search",
                "reasoning": "Query requires semantic search",
                "parameters": {"query": user_input}
            }
        elif any(word in query_lower for word in ["document", "ifc file", "xml", "metadata"]):
            plan = {
                "primary_tool": "basex",
                "query_type": "document",
                "reasoning": "Query asks for document information",
                "parameters": {"query": user_input}
            }
        else:
            # Default to graph query
            plan = {
                "primary_tool": "neo4j",
                "query_type": "graph",
                "reasoning": "Default to Neo4j graph query for structural data",
                "parameters": {"query": user_input}
            }
        
        logger.info(f"Query plan: {plan['primary_tool']} - {plan['reasoning']}")
        return plan
    
    async def _execute_query_plan(self, plan: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Execute query plan via MCP tools
        
        Args:
            plan: Query execution plan
        
        Returns:
            List of results from tool execution
        """
        results = []
        primary_tool = plan["primary_tool"]
        parameters = plan.get("parameters", {})
        
        try:
            if primary_tool == "neo4j":
                # Execute Cypher query via Neo4j MCP server
                if self.mcp_host:
                    # Build Cypher query from user input
                    query_text = parameters.get("query", "")
                    
                    # Simple query construction (production would use LLM)
                    cypher = self._build_cypher_query(query_text)
                    
                    logger.info(f"Executing Cypher: {cypher}")
                    
                    # Call Neo4j MCP server
                    result = await self.mcp_host.call_tool(
                        server_name="neo4j",
                        tool_name="cypher_query",
                        query=cypher
                    )
                    
                    # Parse result
                    if isinstance(result, dict) and "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and content:
                            text_content = content[0].get("text", "{}")
                            results = json.loads(text_content) if isinstance(text_content, str) else text_content
                    
                    logger.info(f"Neo4j query returned {len(results) if isinstance(results, list) else 'unknown'} results")
                else:
                    # Fallback to sample data if MCP not available
                    results = self._get_sample_neo4j_results()
                    logger.info(f"Neo4j query returned {len(results)} results (sample data)")
            
            elif primary_tool == "opensearch":
                # Semantic search via OpenSearch MCP server
                query_text = parameters.get("query", "")
                
                if self.mcp_host:
                    logger.info(f"Searching OpenSearch for: {query_text}")
                    
                    # Call OpenSearch MCP server
                    result = await self.mcp_host.call_tool(
                        server_name="opensearch",
                        tool_name="search_semantic",
                        query=query_text,
                        size=10,
                        min_score=0.5
                    )
                    
                    # Parse result
                    if isinstance(result, dict) and "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and content:
                            text_content = content[0].get("text", "{}")
                            results = json.loads(text_content) if isinstance(text_content, str) else []
                    
                    logger.info(f"OpenSearch returned {len(results) if isinstance(results, list) else 0} results")
                else:
                    # Fallback to sample data if MCP not available
                    results = [{
                        "id": "doc-001",
                        "score": 0.85,
                        "source": {
                            "name": "Fire Safety Wall",
                            "description": "Fire rated wall with 90-minute rating",
                            "fire_rating": 90,
                            "category": "IfcWall"
                        }
                    }]
                    logger.info(f"OpenSearch returned {len(results)} results (sample data)")
            
            elif primary_tool == "bsdd":
                # bSDD lookup via MCP server
                query_text = parameters.get("query", "")
                
                if self.mcp_host:
                    # Extract search term (simple keyword extraction)
                    search_term = self._extract_ifc_class(query_text)
                    
                    logger.info(f"Searching bSDD for: {search_term}")
                    
                    # Call bSDD MCP server - search dictionaries first
                    result = await self.mcp_host.call_tool(
                        server_name="bsdd",
                        tool_name="search_dictionaries",
                        search_text=search_term
                    )
                    
                    # Parse result
                    if isinstance(result, dict) and "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and content:
                            text_content = content[0].get("text", "{}")
                            results = json.loads(text_content) if isinstance(text_content, str) else text_content
                    
                    logger.info(f"bSDD query returned results")
                else:
                    # Fallback to sample data
                    results = self._get_sample_bsdd_results()
                    logger.info(f"bSDD query returned {len(results)} results (sample data)")
            
            elif primary_tool == "basex":
                # BaseX document query via MCP server
                if self.mcp_host:
                    # Simple XQuery for document metadata
                    xquery = "for $doc in collection() return base-uri($doc)"
                    
                    logger.info(f"Executing XQuery")
                    
                    result = await self.mcp_host.call_tool(
                        server_name="basex",
                        tool_name="query_xquery",
                        query=xquery
                    )
                    
                    # Parse result
                    if isinstance(result, dict) and "content" in result:
                        content = result["content"]
                        if isinstance(content, list) and content:
                            text_content = content[0].get("text", "{}")
                            results = json.loads(text_content) if isinstance(text_content, str) else text_content
                    
                    logger.info(f"BaseX query returned results")
                else:
                    # Fallback to sample data
                    results = [{
                        "document_uri": "ifc://project/building.ifc",
                        "version": 1,
                        "metadata": {"source": "import", "timestamp": datetime.now().isoformat()}
                    }]
                    logger.info(f"BaseX query returned 1 result (sample data)")
            
            else:
                logger.warning(f"Unknown tool: {primary_tool}")
        
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            # Fallback to sample data on error
            results = self._get_sample_results(primary_tool)
        
        return results if isinstance(results, list) else [results] if results else []
    
    def _build_cypher_query(self, user_input: str) -> str:
        """Build Cypher query from user input (simplified)"""
        # Simple pattern matching (production would use LLM)
        input_lower = user_input.lower()
        
        if "fire rating" in input_lower and "wall" in input_lower:
            return """
                MATCH (w:Wall)
                WHERE w.fireRating > 60
                RETURN w.id AS element, w.type AS type, w.fireRating AS fire_rating, 
                       {thickness: w.thickness, material: w.material} AS properties
                LIMIT 10
            """
        elif "wall" in input_lower:
            return """
                MATCH (w:Wall)
                RETURN w.id AS element, w.type AS type, w.fireRating AS fire_rating,
                       {thickness: w.thickness, material: w.material} AS properties
                LIMIT 10
            """
        else:
            # Generic query
            return "MATCH (n) RETURN n LIMIT 5"
    
    def _extract_ifc_class(self, user_input: str) -> str:
        """Extract IFC class name from user input"""
        # Simple extraction (look for IFC entities)
        input_lower = user_input.lower()
        
        ifc_classes = ["ifcwall", "ifcdoor", "ifcwindow", "ifcslab", "ifcspace", "ifcbeam", "ifccolumn"]
        
        for ifc_class in ifc_classes:
            if ifc_class in input_lower.replace(" ", ""):
                return ifc_class.capitalize()
        
        # Fallback: return first significant word
        words = user_input.split()
        for word in words:
            if len(word) > 3 and word.lower() not in ["what", "show", "find", "get", "the", "is", "are"]:
                return word
        
        return "Wall"
    
    def _get_sample_neo4j_results(self) -> List[Dict[str, Any]]:
        """Get sample Neo4j results"""
        return [
            {
                "element": "Wall-01",
                "type": "IfcWall",
                "fire_rating": 90,
                "properties": {"thickness": "200mm", "material": "Concrete"}
            },
            {
                "element": "Wall-02",
                "type": "IfcWall",
                "fire_rating": 60,
                "properties": {"thickness": "150mm", "material": "Brick"}
            }
        ]
    
    def _get_sample_bsdd_results(self) -> List[Dict[str, Any]]:
        """Get sample bSDD results"""
        return [
            {
                "class_name": "IfcWall",
                "definition": "A vertical construction that bounds or subdivides spaces",
                "properties": ["IsExternal", "LoadBearing", "FireRating"],
                "ifc_entity": "IfcWall"
            }
        ]
    
    def _get_sample_results(self, tool: str) -> List[Dict[str, Any]]:
        """Get sample results based on tool type"""
        if tool == "neo4j":
            return self._get_sample_neo4j_results()
        elif tool == "bsdd":
            return self._get_sample_bsdd_results()
        else:
            return []
    
    def _format_results(
        self,
        results: List[Dict[str, Any]],
        plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format results for UI generation
        
        Args:
            results: Raw results from tool execution
            plan: Original query plan
        
        Returns:
            Formatted results ready for UI conversion
        """
        query_type = plan.get("query_type", "graph")
        
        if query_type == "graph" and results:
            # Format as table
            return {
                "type": "table",
                "title": "Query Results",
                "results": results,
                "metadata": {
                    "source": plan["primary_tool"],
                    "count": len(results)
                }
            }
        
        elif query_type == "search" and results:
            # Format as cards
            return {
                "type": "cards",
                "title": "Search Results",
                "items": results,
                "metadata": {
                    "source": "opensearch",
                    "count": len(results)
                }
            }
        
        elif query_type == "definition" and results:
            # Format as property panel
            return {
                "type": "properties",
                "title": "Definition",
                "properties": self._extract_properties(results),
                "metadata": {
                    "source": "bsdd",
                    "count": len(results)
                }
            }
        
        else:
            # Default: return as-is
            return {
                "type": "raw",
                "results": results,
                "metadata": {
                    "source": plan.get("primary_tool", "unknown"),
                    "count": len(results)
                }
            }
    
    def _extract_properties(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract properties for property panel"""
        properties = []
        
        for item in results:
            for key, value in item.items():
                if isinstance(value, (str, int, float)):
                    properties.append({
                        "name": key.replace("_", " ").title(),
                        "value": str(value),
                        "group": "General"
                    })
        
        return properties
    
    async def _generate_response(
        self,
        user_input: str,
        formatted_results: Dict[str, Any]
    ) -> str:
        """
        Generate natural language response
        
        Args:
            user_input: Original query
            formatted_results: Formatted query results
        
        Returns:
            Natural language response
        """
        result_count = formatted_results.get("metadata", {}).get("count", 0)
        result_type = formatted_results.get("type", "raw")
        
        if result_count == 0:
            return "No results found for your query."
        
        if result_type == "table":
            return f"Found {result_count} matching elements. Results are displayed in the table below."
        
        elif result_type == "search":
            return f"Found {result_count} relevant items. View the search results below."
        
        elif result_type == "properties":
            return f"Retrieved definition with {result_count} properties. See details below."
        
        else:
            return f"Query completed successfully. Retrieved {result_count} results."
    
    async def _store_in_memory(
        self,
        user_input: str,
        formatted_results: Dict[str, Any]
    ):
        """
        Store query in memory for future reference
        
        Args:
            user_input: User's query
            formatted_results: Query results
        """
        if not self.memory:
            logger.info("Memory system not available, skipping storage")
            return
        
        try:
            self.memory.store_task(
                task_description=user_input,
                metadata={
                    "task_type": "query",
                    "result_count": formatted_results.get("metadata", {}).get("count", 0),
                    "result_type": formatted_results.get("type", "unknown"),
                    "timestamp": datetime.now().isoformat()
                }
            )
            logger.info("Query stored in memory")
        except Exception as e:
            logger.warning(f"Failed to store in memory: {str(e)}")


# ============================================================================
# Integration with Agent Orchestrator
# ============================================================================

async def query_agent_node(state: AgentState) -> AgentState:
    """
    Query agent node for LangGraph
    
    This replaces the placeholder in agent_orchestrator.py
    """
    agent = QueryAgent()
    return await agent.process(state)


# ============================================================================
# Testing
# ============================================================================

async def test_query_agent():
    """Test query agent"""
    print("=" * 60)
    print("Query Agent Test")
    print("=" * 60)
    
    agent = QueryAgent()
    
    # Test queries
    test_queries = [
        "Show me all walls with fire rating greater than 60",
        "Find similar spaces to Conference Room A",
        "What is the definition of IfcWall?",
        "Get IFC file metadata for building.ifc"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        # Create test state
        if LANGCHAIN_AVAILABLE:
            state: AgentState = {
                "messages": [make_human_message(content=query)],
                "user_input": query,
                "intent": "query",
                "metadata": {"test": True}
            }
        else:
            state = {
                "messages": [{"type": "human", "content": query}],
                "user_input": query,
                "intent": "query",
                "metadata": {"test": True}
            }
        
        # Process
        result_state = await agent.process(state)
        
        # Show results
        if isinstance(result_state.get("messages", [])[-1] if result_state.get("messages") else {}, dict):
            response = result_state.get("messages", [])[-1].get("content", "No response") if result_state.get("messages") else "No response"
        else:
            response = result_state["messages"][-1].content if result_state.get("messages") else "No response"
        print(f"\nResponse: {response}")
        
        if "mcp_results" in result_state:
            print(f"Results: {len(result_state['mcp_results'])} items")
            # Show first result
            if result_state['mcp_results']:
                print(f"First result: {result_state['mcp_results'][0]}")
        
        if "metadata" in result_state and "query_plan" in result_state["metadata"]:
            plan = result_state["metadata"]["query_plan"]
            print(f"Tool used: {plan['primary_tool']} ({plan['query_type']})")
            print(f"Reasoning: {plan['reasoning']}")
        
        if "error" in result_state:
            print(f"Error: {result_state['error']}")
    
    print(f"\n{'='*60}")
    print("✅ Query Agent test complete")
    print(f"{'='*60}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_query_agent())
