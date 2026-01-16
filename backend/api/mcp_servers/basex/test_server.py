"""
Test script for BaseX MCP Server

Tests document storage, version management, and XQuery operations.
"""

import os
import unittest

# Integration script: skip during unit test discovery unless explicitly enabled.
if __name__ != "__main__" and os.getenv("RUN_INTEGRATION_TESTS") != "1":
    raise unittest.SkipTest("Integration script (set RUN_INTEGRATION_TESTS=1 to enable)")

import asyncio
import sys
import json
sys.path.append('../../')

from mcp.mcp_host import MCPHost, MCPServerConfig, MCPServerType


async def test_basex_mcp_server():
    """Test the BaseX MCP server functionality"""
    
    print("=" * 60)
    print("BaseX MCP Server Test")
    print("=" * 60)
    
    # Create MCP host with BaseX server configuration
    host = MCPHost(pool_size=5)
    
    config = MCPServerConfig(
        name="basex",
        type=MCPServerType.BASEX,
        command="python",
        args=["-m", "mcp_servers.basex.server"],
        env={
            "BASEX_HOST": "localhost",
            "BASEX_PORT": "1984",
            "BASEX_USER": "admin",
            "BASEX_PASSWORD": "admin"
        },
        enabled=True
    )
    
    try:
        # Initialize host with BaseX server
        print("\n1. Initializing MCP Host...")
        await host.initialize([config])
        print("   ✓ MCP Host initialized")
        
        # Discover tools
        print("\n2. Discovering available tools...")
        tools = await host.discover_tools()
        
        if "basex" in tools:
            print(f"   ✓ Found {len(tools['basex'])} tools:")
            for tool in tools['basex']:
                print(f"     - {tool['name']}: {tool['description'][:60]}...")
        else:
            print("   ✗ BaseX server not available")
            return
        
        # Test 1: Store a document
        print("\n3. Testing store_document tool...")
        test_doc = {
            "uri": "https://identifier.buildingsmart.org/uri/test/dictionary/1.0",
            "name": "Test Dictionary",
            "version": "1.0",
            "organizationCode": "test",
            "classes": ["TestClass1", "TestClass2"]
        }
        
        try:
            result = await host.execute_tool(
                server_name="basex",
                tool_name="store_document",
                uri="test://bsdd/dictionary/1",
                content=json.dumps(test_doc, indent=2),
                content_type="json",
                metadata={
                    "source": "mcp_test",
                    "user_id": "test_user",
                    "description": "Test dictionary for MCP BaseX server"
                }
            )
            print(f"   ✓ Document stored successfully")
            print(f"   Version: {result.get('version', 'N/A')}")
            print(f"   Checksum: {result.get('checksum', 'N/A')[:16]}...")
        except Exception as e:
            print(f"   ✗ Store failed: {str(e)}")
        
        # Test 2: Store another version
        print("\n4. Testing version management...")
        test_doc["version"] = "1.1"
        test_doc["classes"].append("TestClass3")
        
        try:
            result = await host.execute_tool(
                server_name="basex",
                tool_name="store_document",
                uri="test://bsdd/dictionary/1",
                content=json.dumps(test_doc, indent=2),
                content_type="json",
                metadata={
                    "source": "mcp_test",
                    "user_id": "test_user",
                    "description": "Updated test dictionary"
                }
            )
            print(f"   ✓ Version 2 stored successfully")
            print(f"   Version: {result.get('version', 'N/A')}")
        except Exception as e:
            print(f"   ✗ Version store failed: {str(e)}")
        
        # Test 3: Get versions
        print("\n5. Testing get_versions tool...")
        try:
            result = await host.execute_tool(
                server_name="basex",
                tool_name="get_versions",
                uri="test://bsdd/dictionary/1",
                limit=10,
                include_content=False
            )
            print(f"   ✓ Retrieved versions successfully")
            print(f"   Found {result.get('version_count', 0)} version(s)")
            
            if result.get('versions'):
                for v in result['versions']:
                    print(f"     - Version {v['version']}: {v['timestamp']}")
        except Exception as e:
            print(f"   ✗ Get versions failed: {str(e)}")
        
        # Test 4: XQuery
        print("\n6. Testing query_xquery tool...")
        xquery = "count(//document)"
        
        try:
            result = await host.execute_tool(
                server_name="basex",
                tool_name="query_xquery",
                query=xquery,
                bindings={}
            )
            print(f"   ✓ XQuery executed successfully")
            print(f"   Result: {result.get('result', 'N/A')}")
        except Exception as e:
            print(f"   ✗ XQuery failed: {str(e)}")
        
        # Test 5: Audit trail
        print("\n7. Testing get_audit_trail tool...")
        try:
            result = await host.execute_tool(
                server_name="basex",
                tool_name="get_audit_trail",
                uri="test://bsdd/dictionary/1",
                operation_type="store",
                limit=10
            )
            print(f"   ✓ Audit trail retrieved")
            print(f"   Entries: {result.get('entry_count', 0)}")
        except Exception as e:
            print(f"   ✗ Audit trail failed: {str(e)}")
        
        # Check health
        print("\n8. Checking server health...")
        health = await host.health_status()
        print(f"   Health: {health['healthy']}/{health['total']} servers healthy")
        
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


if __name__ == "__main__":
    print("\nBaseX MCP Server Test Suite")
    print("This requires:")
    print("  1. BaseX running at localhost:1984")
    print("  2. Credentials: admin/admin")
    print("  3. MCP SDK installed")
    print("  4. basex-client installed (pip install basex-client)")
    print()
    
    choice = input("Run tests? (y/n): ")
    
    if choice.lower() == 'y':
        asyncio.run(test_basex_mcp_server())
    else:
        print("Test cancelled.")
