"""
Simple MCP Test (Windows-compatible)
Tests MCP servers without Unicode characters
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

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_host.mcp_host import get_mcp_host
import logging

logging.basicConfig(level=logging.INFO)  # Show all logs to debug
logger = logging.getLogger(__name__)


async def main():
    print("=" * 60)
    print("MCP Integration Test")
    print("=" * 60)
    
    # Initialize MCP host
    print("\n[1/6] Initializing MCP Host...")
    host = await get_mcp_host()
    print("     SUCCESS: MCP Host initialized")
    
    # Check health
    print("\n[2/6] Checking server health...")
    health = await host.health_status()
    print(f"     {health['healthy']}/{health['total']} servers healthy")
    for server, status in health['servers'].items():
        connected = status.get('connected', False) if isinstance(status, dict) else status
        status_text = "ONLINE" if connected else "OFFLINE"
        print(f"     - {server}: {status_text}")
    
    # Discover tools
    print("\n[3/6] Discovering tools...")
    tools = await host.discover_tools()
    total_tools = sum(len(server_tools) for server_tools in tools.values())
    print(f"     Found {total_tools} tools across {len(tools)} servers")
    
    # Test Neo4j
    print("\n[4/6] Testing Neo4j query...")
    try:
        result = await host.call_tool(
            server_name="neo4j",
            tool_name="cypher_query",
            query="MATCH (n) RETURN count(n) as total LIMIT 1"
        )
        print(f"     SUCCESS: {result}")
    except Exception as e:
        print(f"     FAILED: {str(e)}")
    
    # Test bSDD
    print("\n[5/6] Testing bSDD search...")
    try:
        result = await host.call_tool(
            server_name="bsdd",
            tool_name="search_dictionaries",
            search_text="Wall"
        )
        print(f"     SUCCESS: Found data")
    except Exception as e:
        print(f"     FAILED: {str(e)}")
    
    # Test BaseX
    print("\n[6/6] Testing BaseX query...")
    try:
        result = await host.call_tool(
            server_name="basex",
            tool_name="query_xquery",
            query="1 + 1"
        )
        print(f"     SUCCESS: {result}")
    except Exception as e:
        print(f"     FAILED: {str(e)}")
    
    # Cleanup
    await host.shutdown()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
