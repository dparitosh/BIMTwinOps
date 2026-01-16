"""
Test MCP Host with Real Servers

This script:
1. Initializes the MCP host
2. Starts connections to all MCP servers
3. Discovers available tools
4. Tests basic tool execution
5. Reports health status
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_host.mcp_host import get_mcp_host
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Test MCP Host"""
    
    print("=" * 60)
    print("MCP Host Integration Test")
    print("=" * 60)
    
    # Initialize MCP host (will start connections to all servers)
    print("\n1. Initializing MCP Host...")
    try:
        host = await get_mcp_host()
        print("   ✅ MCP Host initialized")
    except Exception as e:
        print(f"   ❌ Failed to initialize: {str(e)}")
        return
    
    # Check health status
    print("\n2. Checking server health...")
    health = await host.health_status()
    print(f"   Healthy: {health['healthy']}/{health['total']} servers")
    for server, status in health['servers'].items():
        connected = status.get('connected', False) if isinstance(status, dict) else status
        icon = "✅" if connected else "❌"
        status_text = 'Connected' if connected else 'Disconnected'
        print(f"   {icon} {server}: {status_text}")
    
    # Discover tools
    print("\n3. Discovering available tools...")
    tools = await host.discover_tools()
    total_tools = sum(len(server_tools) for server_tools in tools.values())
    print(f"   Found {total_tools} tools across {len(tools)} servers:")
    
    for server, server_tools in tools.items():
        print(f"\n   {server} ({len(server_tools)} tools):")
        for tool in server_tools:
            print(f"     • {tool['name']}")
            print(f"       {tool['description'][:80]}...")
    
    # Test Neo4j query
    print("\n4. Testing Neo4j query...")
    try:
        result = await host.execute_tool(
            server_name="neo4j",
            tool_name="cypher_query",
            query="MATCH (n) RETURN count(n) as total LIMIT 1"
        )
        print(f"   ✅ Query successful")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ❌ Query failed: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Test bSDD search
    print("\n5. Testing bSDD search...")
    try:
        result = await host.execute_tool(
            server_name="bsdd",
            tool_name="search_dictionaries",
            search_text="IfcWall"
        )
        print(f"   ✅ Search successful")
        print(f"   Found {len(result.get('dictionaries', []))} dictionaries")
    except Exception as e:
        print(f"   ❌ Search failed: {str(e)}")
    
    # Test BaseX query
    print("\n6. Testing BaseX query...")
    try:
        result = await host.execute_tool(
            server_name="basex",
            tool_name="query_xquery",
            query="count(collection())"
        )
        print(f"   ✅ Query successful")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"   ❌ Query failed: {str(e)}")
    
    # Shutdown
    print("\n7. Shutting down...")
    await host.shutdown()
    print("   ✅ Clean shutdown")
    
    print("\n" + "=" * 60)
    print("✅ MCP Host test complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
