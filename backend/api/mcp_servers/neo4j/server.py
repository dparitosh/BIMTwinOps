"""MCP Server: Neo4j

Provides graph database operations as MCP tools for AI agents.

Tools:
1. cypher_query - Execute read-only Cypher queries
2. create_nodes - Create nodes in the graph
3. create_relationships - Create relationships between nodes
4. update_properties - Update node/relationship properties

References:
- Neo4j Python Driver: https://neo4j.com/docs/python-manual/current/
- MCP Specification: https://spec.modelcontextprotocol.io/
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import logging
import json

_neo4j_graph_database: Any = None

try:
    # neo4j dependency may be optional in some dev/test contexts
    from neo4j import GraphDatabase as _neo4j_graph_database  # type: ignore[attr-defined]
except ImportError:  # pragma: no cover
    _neo4j_graph_database = None

NEO4J_TOOL_ERRORS: tuple[type[BaseException], ...] = ()
try:  # pragma: no cover
    from neo4j.exceptions import Neo4jError

    NEO4J_TOOL_ERRORS = (Neo4jError,)
except ImportError:
    NEO4J_TOOL_ERRORS = ()

TOOL_EXECUTION_ERRORS: tuple[type[BaseException], ...] = (
    ValueError,
    RuntimeError,
    TypeError,
    KeyError,
) + NEO4J_TOOL_ERRORS

if TYPE_CHECKING:
    from neo4j import Driver  # type: ignore[attr-defined]
else:  # pragma: no cover
    Driver = Any  # type: ignore[misc,assignment]

# MCP imports
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Neo4jMCPServer:
    """
    MCP Server for Neo4j graph database operations
    
    This server provides standardized tools for AI agents to interact
    with the Neo4j knowledge graph.
    """
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password"
    ):
        """
        Initialize Neo4j MCP Server
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        self.driver: Optional[Driver] = None
        self.uri = uri
        self.user = user
        self.password = password
        self.server = Server("neo4j-mcp-server")
        
        # Register tool handlers
        self._register_tools()
    
    def _require_driver(self) -> Driver:
        """Ensure a live Neo4j driver exists (connects lazily)."""
        if self.driver is None:
            self.connect()
        if self.driver is None:
            raise RuntimeError("Neo4j driver not initialized")
        return self.driver

    def connect(self):
        """Establish connection to Neo4j database."""
        if _neo4j_graph_database is None:  # pragma: no cover
            raise RuntimeError(
                "Neo4j Python driver is not available. Install 'neo4j' to use the Neo4j MCP server."
            )

        try:
            self.driver = _neo4j_graph_database.driver(self.uri, auth=(self.user, self.password))
            # Verify connectivity
            self._require_driver().verify_connectivity()
            logger.info("Connected to Neo4j at %s", self.uri)
        except Exception:  # pylint: disable=broad-except
            logger.exception("Failed to connect to Neo4j")
            raise
    
    def disconnect(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Disconnected from Neo4j")
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available Neo4j tools"""
            return [
                Tool(
                    name="cypher_query",
                    description=(
                        "Execute a read-only Cypher query on the Neo4j graph database. "
                        "Use this for retrieving data, counting nodes, finding relationships, "
                        "and analyzing graph patterns. Supports parameterized queries."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Cypher query string (read-only operations only)"
                            },
                            "parameters": {
                                "type": "object",
                                "description": "Optional query parameters as key-value pairs",
                                "default": {}
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 100
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="create_nodes",
                    description=(
                        "Create new nodes in the Neo4j graph. Supports batch creation "
                        "of multiple nodes with labels and properties. Returns created node IDs."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "nodes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "labels": {
                                            "type": "array",
                                            "items": {"type": "string"},
                                            "description": "Node labels (e.g., ['BsddDictionary', 'Active'])"
                                        },
                                        "properties": {
                                            "type": "object",
                                            "description": "Node properties as key-value pairs"
                                        }
                                    },
                                    "required": ["labels", "properties"]
                                },
                                "description": "Array of nodes to create"
                            }
                        },
                        "required": ["nodes"]
                    }
                ),
                Tool(
                    name="create_relationships",
                    description=(
                        "Create relationships between existing nodes in the graph. "
                        "Supports batch relationship creation with properties."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "relationships": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "from_uri": {
                                            "type": "string",
                                            "description": "URI of the source node"
                                        },
                                        "to_uri": {
                                            "type": "string",
                                            "description": "URI of the target node"
                                        },
                                        "type": {
                                            "type": "string",
                                            "description": "Relationship type (e.g., 'HAS_PROPERTY', 'IN_DICTIONARY')"
                                        },
                                        "properties": {
                                            "type": "object",
                                            "description": "Relationship properties",
                                            "default": {}
                                        }
                                    },
                                    "required": ["from_uri", "to_uri", "type"]
                                },
                                "description": "Array of relationships to create"
                            }
                        },
                        "required": ["relationships"]
                    }
                ),
                Tool(
                    name="update_properties",
                    description=(
                        "Update properties of existing nodes or relationships. "
                        "Can add new properties or modify existing ones."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_type": {
                                "type": "string",
                                "enum": ["node", "relationship"],
                                "description": "Whether updating a node or relationship"
                            },
                            "uri": {
                                "type": "string",
                                "description": "URI of the node/relationship to update"
                            },
                            "properties": {
                                "type": "object",
                                "description": "Properties to set/update"
                            },
                            "merge": {
                                "type": "boolean",
                                "description": "If true, merge with existing properties; if false, replace all",
                                "default": True
                            }
                        },
                        "required": ["target_type", "uri", "properties"]
                    }
                ),
                Tool(
                    name="delete_nodes",
                    description=(
                        "Delete nodes by URI (safe, deterministic). "
                        "Use this only for explicitly approved destructive operations."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uris": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "URIs of nodes to delete"
                            },
                            "detach": {
                                "type": "boolean",
                                "description": "If true, DETACH DELETE (also removes relationships)",
                                "default": True
                            }
                        },
                        "required": ["uris"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
            """Handle tool invocations"""

            self._require_driver()
            
            try:
                if name == "cypher_query":
                    result = await self._cypher_query(**arguments)
                elif name == "create_nodes":
                    result = await self._create_nodes(**arguments)
                elif name == "create_relationships":
                    result = await self._create_relationships(**arguments)
                elif name == "update_properties":
                    result = await self._update_properties(**arguments)
                elif name == "delete_nodes":
                    result = await self._delete_nodes(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except TOOL_EXECUTION_ERRORS as e:
                logger.exception("Error executing tool %s", name)
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    async def _cypher_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Execute a read-only Cypher query"""
        
        # Security: Ensure read-only operations
        query_upper = query.strip().upper()
        write_keywords = ['CREATE', 'MERGE', 'DELETE', 'REMOVE', 'SET', 'DROP']
        if any(keyword in query_upper for keyword in write_keywords):
            raise ValueError(
                "Write operations not allowed in cypher_query. "
                "Use create_nodes, create_relationships, or update_properties instead."
            )
        
        # Add LIMIT if not present
        if 'LIMIT' not in query_upper:
            query = f"{query} LIMIT {limit}"
        
        with self._require_driver().session() as session:
            result = session.run(query, parameters or {})
            
            records = []
            for record in result:
                # Convert record to dictionary
                record_dict = {}
                for key in record.keys():
                    value = record[key]
                    # Handle Neo4j node/relationship objects
                    if hasattr(value, '__dict__'):
                        record_dict[key] = dict(value)
                    else:
                        record_dict[key] = value
                records.append(record_dict)
            
            return {
                "success": True,
                "count": len(records),
                "records": records,
                "query": query
            }
    
    async def _create_nodes(self, nodes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple nodes"""
        
        created_ids = []
        
        with self._require_driver().session() as session:
            for node_def in nodes:
                labels = ':'.join(node_def['labels'])
                properties = node_def['properties']
                
                # Create Cypher query
                query = f"""
                CREATE (n:{labels})
                SET n = $properties
                RETURN elementId(n) as id
                """
                
                result = session.run(query, {"properties": properties})
                record = result.single()
                if record:
                    created_ids.append(record["id"])
        
        return {
            "success": True,
            "created_count": len(created_ids),
            "node_ids": created_ids
        }
    
    async def _create_relationships(
        self,
        relationships: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create multiple relationships"""
        
        created_count = 0
        
        with self._require_driver().session() as session:
            for rel_def in relationships:
                from_uri = rel_def['from_uri']
                to_uri = rel_def['to_uri']
                rel_type = rel_def['type']
                properties = rel_def.get('properties', {})
                
                # Create relationship
                query = f"""
                MATCH (from {{uri: $from_uri}})
                MATCH (to {{uri: $to_uri}})
                CREATE (from)-[r:{rel_type}]->(to)
                SET r = $properties
                RETURN elementId(r) as id
                """
                
                result = session.run(query, {
                    "from_uri": from_uri,
                    "to_uri": to_uri,
                    "properties": properties
                })
                
                if result.single():
                    created_count += 1
        
        return {
            "success": True,
            "created_count": created_count
        }
    
    async def _update_properties(
        self,
        target_type: str,
        uri: str,
        properties: Dict[str, Any],
        merge: bool = True
    ) -> Dict[str, Any]:
        """Update properties of a node or relationship"""

        with self._require_driver().session() as session:
            if target_type == "node":
                if merge:
                    query = """
                    MATCH (n {uri: $uri})
                    SET n += $properties
                    RETURN elementId(n) as id, labels(n) as labels
                    """
                else:
                    query = """
                    MATCH (n {uri: $uri})
                    SET n = $properties
                    SET n.uri = $uri
                    RETURN elementId(n) as id, labels(n) as labels
                    """
                
                result = session.run(query, {"uri": uri, "properties": properties})
                record = result.single()
                
                if record:
                    return {
                        "success": True,
                        "id": record["id"],
                        "labels": record["labels"]
                    }
                else:
                    return {"success": False, "error": "Node not found"}
            
            else:  # relationship
                raise NotImplementedError("Relationship property updates not yet implemented")

    async def _delete_nodes(self, uris: List[str], detach: bool = True) -> Dict[str, Any]:
        """Delete nodes by URI."""

        deleted: List[Dict[str, Any]] = []

        with self._require_driver().session() as session:
            for uri in uris:
                # Count first to report whether it existed
                count_result = session.run(
                    "MATCH (n {uri: $uri}) RETURN count(n) as c",
                    {"uri": uri},
                ).single()
                existed = bool(count_result and count_result.get("c", 0) > 0)

                if detach:
                    session.run(
                        "MATCH (n {uri: $uri}) DETACH DELETE n",
                        {"uri": uri},
                    )
                else:
                    session.run(
                        "MATCH (n {uri: $uri}) DELETE n",
                        {"uri": uri},
                    )

                deleted.append({"uri": uri, "deleted": existed})

        return {
            "success": True,
            "requested": len(uris),
            "deleted": sum(1 for d in deleted if d.get("deleted")),
            "results": deleted,
        }


async def main():
    """Run the Neo4j MCP server"""
    import os
    
    # Get configuration from environment
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "password")
    
    # Create and run server
    server_instance = Neo4jMCPServer(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password
    )
    
    # Run stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server_instance.server.run(
            read_stream,
            write_stream,
            server_instance.server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
