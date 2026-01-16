# MCP Servers

This directory contains MCP (Model Context Protocol) server implementations that provide standardized tool interfaces for AI agents.

## Architecture

```
mcp_host.py                 # MCP Host orchestrator
├── Connection Pool         # Manages server connections
├── Tool Discovery         # Discovers available tools
└── Tool Execution         # Executes tools with retry logic

mcp_servers/
├── neo4j/                 # Graph database MCP server
│   ├── server.py         # Server implementation
│   └── tools.py          # Tool definitions
├── basex/                # Document store MCP server
│   ├── server.py
│   └── tools.py
├── bsdd/                 # bSDD API MCP server
│   ├── server.py
│   └── tools.py
└── opensearch/           # Hybrid search MCP server
    ├── server.py
    └── tools.py
```

## MCP Host Usage

```python
from mcp.mcp_host import get_mcp_host

# Get host instance
host = await get_mcp_host()

# Discover tools
tools = await host.discover_tools()

# Execute a tool
result = await host.execute_tool(
    server_name="neo4j",
    tool_name="cypher_query",
    query="MATCH (n:BsddDictionary) RETURN n LIMIT 10"
)

# Check health
health = await host.health_status()
print(f"{health['healthy']}/{health['total']} servers healthy")
```

## Creating a New MCP Server

1. Create a new directory under `mcp_servers/`
2. Implement the server following MCP specification
3. Define tools with JSON schemas
4. Add configuration to `mcp_host.py`
5. Test with MCP Inspector

## Tool Definition Example

```python
@tool
def cypher_query(query: str, parameters: dict = None) -> dict:
    """
    Execute a Cypher query on Neo4j
    
    Args:
        query: Cypher query string
        parameters: Optional query parameters
        
    Returns:
        Query results as dictionary
    """
    # Implementation
    pass
```

## References

- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- ADR-001: Use of Model Context Protocol
