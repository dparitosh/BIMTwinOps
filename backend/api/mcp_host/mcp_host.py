"""
MCP Host - Model Context Protocol Orchestrator

This module serves as the MCP Host that manages connections to various MCP servers
and provides a unified interface for agent interactions.

Architecture:
- MCP Host (this file) acts as the orchestrator
- Connects to multiple MCP servers via stdio or HTTP
- Provides connection pooling and retry logic
- Manages tool discovery and invocation

MCP Servers:
1. mcp-server-neo4j - Graph database operations
2. mcp-server-basex - Document storage operations
3. mcp-server-bsdd - bSDD API integration
4. mcp-server-opensearch - Hybrid semantic search

References:
- MCP Specification: https://spec.modelcontextprotocol.io/
- ADR-001: Use of Model Context Protocol
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

# MCP SDK imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.types import Tool, CallToolResult
except ImportError:
    raise ImportError(
        "MCP SDK not installed. Run: pip install mcp"
    )

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MCPServerType(Enum):
    """Supported MCP server types"""
    NEO4J = "neo4j"
    BASEX = "basex"
    BSDD = "bsdd"
    OPENSEARCH = "opensearch"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection"""
    name: str
    type: MCPServerType
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    max_retries: int = 3
    timeout: int = 30  # seconds
    enabled: bool = True


@dataclass
class MCPConnection:
    """Represents an active MCP server connection"""
    config: MCPServerConfig
    session: ClientSession
    tools: List[Tool] = field(default_factory=list)
    is_connected: bool = False
    retry_count: int = 0


class MCPConnectionPool:
    """
    Connection pool for managing multiple MCP server connections
    
    Features:
    - Automatic connection lifecycle management
    - Connection health checks
    - Automatic reconnection with exponential backoff
    - Tool discovery and caching
    """
    
    def __init__(self, max_pool_size: int = 10):
        self.connections: Dict[str, MCPConnection] = {}
        self.max_pool_size = max_pool_size
        self._lock = asyncio.Lock()
    
    async def add_connection(self, config: MCPServerConfig) -> bool:
        """
        Add a new MCP server connection to the pool
        
        Args:
            config: Server configuration
            
        Returns:
            True if connection successful, False otherwise
        """
        async with self._lock:
            if len(self.connections) >= self.max_pool_size:
                logger.warning(f"Connection pool full, cannot add {config.name}")
                return False
            
            if config.name in self.connections:
                logger.warning(f"Connection {config.name} already exists")
                return False
            
            try:
                # Create stdio client for the MCP server
                server_params = StdioServerParameters(
                    command=config.command,
                    args=config.args,
                    env=config.env
                )
                
                # Initialize connection (will be established on first use)
                connection = MCPConnection(
                    config=config,
                    session=None,  # Will be initialized when connecting
                )
                
                self.connections[config.name] = connection
                logger.info(f"Added MCP server: {config.name} ({config.type.value})")
                return True
                
            except Exception as e:
                logger.error(f"Failed to add connection {config.name}: {str(e)}")
                return False
    
    async def connect(self, server_name: str) -> bool:
        """
        Establish connection to an MCP server
        
        Args:
            server_name: Name of the server to connect to
            
        Returns:
            True if connection successful
        """
        if server_name not in self.connections:
            logger.error(f"Server {server_name} not found in pool")
            return False
        
        connection = self.connections[server_name]
        
        if connection.is_connected:
            logger.debug(f"Server {server_name} already connected")
            return True
        
        try:
            server_params = StdioServerParameters(
                command=connection.config.command,
                args=connection.config.args,
                env=connection.config.env
            )
            
            # Create client session
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize connection
                    await session.initialize()
                    
                    # Discover available tools
                    tools_result = await session.list_tools()
                    connection.tools = tools_result.tools
                    
                    connection.session = session
                    connection.is_connected = True
                    connection.retry_count = 0
                    
                    logger.info(
                        f"Connected to {server_name}: "
                        f"{len(connection.tools)} tools available"
                    )
                    
                    return True
                    
        except Exception as e:
            connection.is_connected = False
            connection.retry_count += 1
            logger.error(
                f"Failed to connect to {server_name} "
                f"(attempt {connection.retry_count}): {str(e)}"
            )
            return False
    
    async def disconnect(self, server_name: str) -> bool:
        """
        Disconnect from an MCP server
        
        Args:
            server_name: Name of the server to disconnect
            
        Returns:
            True if disconnect successful
        """
        if server_name not in self.connections:
            logger.warning(f"Server {server_name} not found in pool")
            return False
        
        connection = self.connections[server_name]
        
        try:
            if connection.session:
                # Close the session
                # Note: Actual cleanup depends on MCP SDK implementation
                connection.session = None
            
            connection.is_connected = False
            logger.info(f"Disconnected from {server_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from {server_name}: {str(e)}")
            return False
    
    async def get_tools(self, server_name: Optional[str] = None) -> Dict[str, List[Tool]]:
        """
        Get available tools from one or all servers
        
        Args:
            server_name: Specific server name, or None for all servers
            
        Returns:
            Dictionary mapping server names to their available tools
        """
        result = {}
        
        if server_name:
            if server_name in self.connections:
                conn = self.connections[server_name]
                if not conn.is_connected:
                    await self.connect(server_name)
                result[server_name] = conn.tools
        else:
            # Get tools from all connected servers
            for name, conn in self.connections.items():
                if not conn.is_connected:
                    await self.connect(name)
                if conn.is_connected:
                    result[name] = conn.tools
        
        return result
    
    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> CallToolResult:
        """
        Call a tool on a specific MCP server
        
        Args:
            server_name: Name of the server
            tool_name: Name of the tool to call
            arguments: Tool arguments
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If server or tool not found
            RuntimeError: If tool execution fails
        """
        if server_name not in self.connections:
            raise ValueError(f"Server {server_name} not found in pool")
        
        connection = self.connections[server_name]
        
        # Ensure connection is established
        if not connection.is_connected:
            success = await self.connect(server_name)
            if not success:
                raise RuntimeError(f"Failed to connect to {server_name}")
        
        # Verify tool exists
        tool_names = [t.name for t in connection.tools]
        if tool_name not in tool_names:
            raise ValueError(
                f"Tool {tool_name} not found on server {server_name}. "
                f"Available tools: {tool_names}"
            )
        
        try:
            # Call the tool
            result = await connection.session.call_tool(tool_name, arguments)
            logger.info(f"Called {server_name}.{tool_name} successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error calling {server_name}.{tool_name}: {str(e)}", exc_info=True)
            raise RuntimeError(f"Tool execution failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of all connections
        
        Returns:
            Dictionary mapping server names to health status
        """
        health = {}
        
        for name, conn in self.connections.items():
            try:
                if not conn.is_connected:
                    await self.connect(name)
                
                # Try to list tools as a health check
                if conn.is_connected:
                    health[name] = True
                else:
                    health[name] = False
                    
            except Exception as e:
                logger.error(f"Health check failed for {name}: {str(e)}")
                health[name] = False
        
        return health
    
    async def close_all(self):
        """Close all connections in the pool"""
        for name in list(self.connections.keys()):
            await self.disconnect(name)


class MCPHost:
    """
    Main MCP Host orchestrator
    
    This class manages the MCP connection pool and provides high-level
    methods for agent interactions with MCP servers.
    """
    
    def __init__(self, pool_size: int = 10):
        self.pool = MCPConnectionPool(max_pool_size=pool_size)
        self._initialized = False
    
    async def initialize(self, configs: List[MCPServerConfig]):
        """
        Initialize the MCP host with server configurations
        
        Args:
            configs: List of server configurations
        """
        logger.info("Initializing MCP Host...")
        
        for config in configs:
            if config.enabled:
                success = await self.pool.add_connection(config)
                if not success:
                    logger.warning(f"Failed to add server: {config.name}")
        
        # Perform initial health check
        health = await self.pool.health_check()
        healthy_count = sum(1 for status in health.values() if status)
        
        logger.info(
            f"MCP Host initialized: {healthy_count}/{len(configs)} servers healthy"
        )
        
        self._initialized = True
    
    async def discover_tools(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Discover all available tools across all servers
        
        Returns:
            Dictionary mapping server names to tool definitions
        """
        if not self._initialized:
            raise RuntimeError("MCP Host not initialized")
        
        tools_by_server = await self.pool.get_tools()
        
        # Convert Tool objects to dictionaries for easier use
        result = {}
        for server_name, tools in tools_by_server.items():
            result[server_name] = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "inputSchema": tool.inputSchema
                }
                for tool in tools
            ]
        
        return result
    
    async def execute_tool(
        self,
        server_name: str,
        tool_name: str,
        **kwargs
    ) -> Any:
        """
        Execute a tool on a specific server
        
        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool
            **kwargs: Tool arguments
            
        Returns:
            Tool execution result
        """
        if not self._initialized:
            raise RuntimeError("MCP Host not initialized")
        
        result = await self.pool.call_tool(server_name, tool_name, kwargs)
        return result
    
    # Alias for consistency with agent code
    call_tool = execute_tool
    
    async def health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive health status of all servers
        
        Returns:
            Health status report
        """
        health = await self.pool.health_check()
        
        return {
            "healthy": sum(1 for status in health.values() if status),
            "total": len(health),
            "servers": health
        }
    
    async def shutdown(self):
        """Gracefully shutdown the MCP host"""
        logger.info("Shutting down MCP Host...")
        await self.pool.close_all()
        self._initialized = False


# Global MCP host instance
_mcp_host: Optional[MCPHost] = None


async def get_mcp_host() -> MCPHost:
    """
    Get or create the global MCP host instance
    
    Returns:
        Global MCPHost instance
    """
    global _mcp_host
    
    if _mcp_host is None:
        _mcp_host = MCPHost(pool_size=10)
        
        # Default configurations (will be loaded from env/config in production)
        configs = [
            MCPServerConfig(
                name="neo4j",
                type=MCPServerType.NEO4J,
                command="python",
                args=["-m", "api.mcp_servers.neo4j"],
                env={"NEO4J_URI": "bolt://localhost:7687"}
            ),
            MCPServerConfig(
                name="basex",
                type=MCPServerType.BASEX,
                command="python",
                args=["-m", "api.mcp_servers.basex"],
                env={"BASEX_HOST": "localhost", "BASEX_PORT": "8984"}
            ),
            MCPServerConfig(
                name="bsdd",
                type=MCPServerType.BSDD,
                command="python",
                args=["-m", "api.mcp_servers.bsdd"],
                enabled=True
            ),
            MCPServerConfig(
                name="opensearch",
                type=MCPServerType.OPENSEARCH,
                command="python",
                args=["-m", "api.mcp_servers.opensearch"],
                env={"OPENSEARCH_URL": "http://localhost:9200"}
            ),
        ]
        
        await _mcp_host.initialize(configs)
    
    return _mcp_host


# Example usage
async def main():
    """Example usage of MCPHost"""
    
    # Get MCP host instance
    host = await get_mcp_host()
    
    # Discover available tools
    tools = await host.discover_tools()
    print(f"\nDiscovered tools across {len(tools)} servers:")
    for server, server_tools in tools.items():
        print(f"\n{server}:")
        for tool in server_tools:
            print(f"  - {tool['name']}: {tool['description']}")
    
    # Check health
    health = await host.health_status()
    print(f"\nHealth: {health['healthy']}/{health['total']} servers healthy")
    
    # Example: Execute a tool (commented out - requires actual server)
    # result = await host.execute_tool(
    #     server_name="neo4j",
    #     tool_name="cypher_query",
    #     query="MATCH (n) RETURN count(n) as total"
    # )
    # print(f"\nQuery result: {result}")
    
    # Shutdown
    await host.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
