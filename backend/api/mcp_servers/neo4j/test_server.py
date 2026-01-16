"""
Test script for Neo4j MCP Server

This script demonstrates how to test the Neo4j MCP server using the MCP Inspector
or programmatically.
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import asyncio
import sys
sys.path.append('../../')

from mcp.mcp_host import MCPHost, MCPServerConfig, MCPServerType


async def test_neo4j_mcp_server():
    """Test the Neo4j MCP server functionality"""
    
    print("=" * 60)
    print("Neo4j MCP Server Test")
    print("=" * 60)
    
    # Create MCP host with Neo4j server configuration
    host = MCPHost(pool_size=5)
    
    config = MCPServerConfig(
        name="neo4j",
        type=MCPServerType.NEO4J,
        command="python",
        args=["-m", "mcp_servers.neo4j.server"],
        env={
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        },
        enabled=True
    )
    
    try:
        # Initialize host with Neo4j server
        print("\n1. Initializing MCP Host...")
        await host.initialize([config])
        print("   ✓ MCP Host initialized")
        
        # Discover tools
        print("\n2. Discovering available tools...")
        tools = await host.discover_tools()
        
        if "neo4j" in tools:
            print(f"   ✓ Found {len(tools['neo4j'])} tools:")
            for tool in tools['neo4j']:
                print(f"     - {tool['name']}: {tool['description'][:60]}...")
        else:
            print("   ✗ Neo4j server not available")
            return
        
        # Test 1: Execute a simple query
        print("\n3. Testing cypher_query tool...")
        try:
            result = await host.execute_tool(
                server_name="neo4j",
                tool_name="cypher_query",
                query="MATCH (n) RETURN count(n) as total_nodes",
                parameters={}
            )
            print(f"   ✓ Query executed successfully")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   ✗ Query failed: {str(e)}")
        
        # Test 2: Create a test node
        print("\n4. Testing create_nodes tool...")
        try:
            result = await host.execute_tool(
                server_name="neo4j",
                tool_name="create_nodes",
                nodes=[{
                    "labels": ["TestNode", "MCPTest"],
                    "properties": {
                        "uri": "test://mcp/node/1",
                        "name": "Test Node from MCP",
                        "created_at": "2026-01-15T12:00:00Z",
                        "test": True
                    }
                }]
            )
            print(f"   ✓ Node created successfully")
            print(f"   Result: {result}")
        except Exception as e:
            print(f"   ✗ Node creation failed: {str(e)}")
        
        # Test 3: Query the created node
        print("\n5. Verifying created node...")
        try:
            result = await host.execute_tool(
                server_name="neo4j",
                tool_name="cypher_query",
                query="MATCH (n:MCPTest) RETURN n",
                parameters={}
            )
            print(f"   ✓ Verification successful")
            print(f"   Found {len(result.get('records', []))} test node(s)")
        except Exception as e:
            print(f"   ✗ Verification failed: {str(e)}")
        
        # Check health
        print("\n6. Checking server health...")
        health = await host.health_status()
        print(f"   Health: {health['healthy']}/{health['total']} servers healthy")
        print(f"   Status: {health['servers']}")
        
        print("\n" + "=" * 60)
        print("Test completed!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\nCleaning up...")
        await host.shutdown()
        print("✓ Shutdown complete")


async def cleanup_test_data():
    """Remove test data from Neo4j"""
    
    print("\nCleaning up test data...")
    
    host = MCPHost(pool_size=1)
    config = MCPServerConfig(
        name="neo4j",
        type=MCPServerType.NEO4J,
        command="python",
        args=["-m", "mcp_servers.neo4j.server"],
        env={
            "NEO4J_URI": "bolt://localhost:7687",
            "NEO4J_USER": "neo4j",
            "NEO4J_PASSWORD": "password"
        }
    )
    
    await host.initialize([config])
    
    try:
        result = await host.execute_tool(
            server_name="neo4j",
            tool_name="cypher_query",
            query="MATCH (n:MCPTest) DELETE n",
            parameters={}
        )
        print("✓ Test data cleaned")
    except Exception as e:
        print(f"Cleanup note: {str(e)}")
    
    await host.shutdown()


if __name__ == "__main__":
    print("\nNeo4j MCP Server Test Suite")
    print("This requires:")
    print("  1. Neo4j running at bolt://localhost:7687")
    print("  2. Credentials: neo4j/password")
    print("  3. MCP SDK installed (pip install mcp)")
    print()
    
    choice = input("Run tests? (y/n): ")
    
    if choice.lower() == 'y':
        asyncio.run(test_neo4j_mcp_server())
        
        cleanup = input("\nCleanup test data? (y/n): ")
        if cleanup.lower() == 'y':
            asyncio.run(cleanup_test_data())
    else:
        print("Test cancelled.")
