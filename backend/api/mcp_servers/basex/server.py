"""
MCP Server: BaseX
Provides document storage, version management, and XQuery operations as MCP tools.

BaseX is a native XML/JSON database that serves as the source of truth for
original bSDD documents. It provides:
- Immutable document storage
- Complete version history
- Audit trail for all operations
- XQuery transformations

Tools:
1. store_document - Store original JSON/XML documents with versioning
2. get_versions - Retrieve version history for a document
3. query_xquery - Execute XQuery queries for transformations
4. get_audit_trail - Retrieve audit log for documents

References:
- BaseX Documentation: https://docs.basex.org/
- BaseX Python Client: https://github.com/BaseXdb/basex-api
- ADR-004: Hybrid Database Architecture
"""

from typing import Any, Dict, List, Optional, Union
import logging
import json
from datetime import datetime
from urllib.parse import quote
import hashlib

# MCP imports
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# BaseX client imports
try:
    from basexclient import BaseXClient
except ImportError:
    # Provide a mock for development if basexclient not installed
    class BaseXClient:
        def __init__(self, host, port, username, password):
            self.host = host
            self.port = port
            raise ImportError("basexclient not installed. Run: pip install basex-client")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseXMCPServer:
    """
    MCP Server for BaseX document database operations
    
    This server provides standardized tools for AI agents to interact
    with BaseX for document storage, versioning, and XQuery operations.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 1984,
        username: str = "admin",
        password: str = "admin"
    ):
        """
        Initialize BaseX MCP Server
        
        Args:
            host: BaseX server host
            port: BaseX server port (default 1984 for client/server)
            username: BaseX username
            password: BaseX password
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.session: Optional[BaseXClient] = None
        self.server = Server("basex-mcp-server")
        
        # Database name for bSDD documents
        self.db_name = "bsdd_documents"
        
        # Register tool handlers
        self._register_tools()
    
    def connect(self):
        """Establish connection to BaseX server"""
        try:
            self.session = BaseXClient(
                self.host,
                self.port,
                self.username,
                self.password
            )
            
            # Create database if it doesn't exist
            try:
                self.session.execute(f"CHECK {self.db_name}")
            except Exception:
                logger.info(f"Creating database: {self.db_name}")
                self.session.execute(f"CREATE DB {self.db_name}")
            
            logger.info(f"Connected to BaseX at {self.host}:{self.port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to BaseX: {str(e)}")
            raise
    
    def disconnect(self):
        """Close BaseX connection"""
        if self.session:
            self.session.close()
            logger.info("Disconnected from BaseX")
    
    def _register_tools(self):
        """Register MCP tools"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """List all available BaseX tools"""
            return [
                Tool(
                    name="store_document",
                    description=(
                        "Store an original bSDD document (JSON/XML) in BaseX with automatic versioning. "
                        "Creates immutable storage with full version history and audit trail. "
                        "Use this whenever importing new bSDD data to preserve the original."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "Unique URI identifier for the document (e.g., bSDD dictionary URI)"
                            },
                            "content": {
                                "type": "string",
                                "description": "Document content as JSON or XML string"
                            },
                            "content_type": {
                                "type": "string",
                                "enum": ["json", "xml"],
                                "description": "Document format",
                                "default": "json"
                            },
                            "metadata": {
                                "type": "object",
                                "description": "Additional metadata (source, import_date, user_id, etc.)",
                                "properties": {
                                    "source": {"type": "string"},
                                    "import_date": {"type": "string"},
                                    "user_id": {"type": "string"},
                                    "description": {"type": "string"}
                                },
                                "default": {}
                            }
                        },
                        "required": ["uri", "content", "content_type"]
                    }
                ),
                Tool(
                    name="get_versions",
                    description=(
                        "Retrieve complete version history for a document by URI. "
                        "Returns all versions with timestamps, checksums, and metadata. "
                        "Use this to track changes, compare versions, or restore previous states."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "URI of the document to retrieve versions for"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of versions to return (most recent first)",
                                "default": 10
                            },
                            "include_content": {
                                "type": "boolean",
                                "description": "Whether to include full document content in results",
                                "default": False
                            }
                        },
                        "required": ["uri"]
                    }
                ),
                Tool(
                    name="query_xquery",
                    description=(
                        "Execute an XQuery query for document transformation and analysis. "
                        "Supports complex queries for filtering, transforming, and analyzing documents. "
                        "Use this for data validation, format conversion, or complex document queries."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "XQuery expression to execute"
                            },
                            "context": {
                                "type": "string",
                                "description": "Optional context document URI to query against",
                                "default": None
                            },
                            "bindings": {
                                "type": "object",
                                "description": "Optional variable bindings for the query",
                                "default": {}
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="get_audit_trail",
                    description=(
                        "Retrieve audit trail showing all operations performed on documents. "
                        "Returns chronological log of stores, updates, and queries with timestamps. "
                        "Use this for compliance, debugging, or understanding document history."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "uri": {
                                "type": "string",
                                "description": "Optional URI to filter audit trail for specific document",
                                "default": None
                            },
                            "operation_type": {
                                "type": "string",
                                "enum": ["store", "query", "delete", "all"],
                                "description": "Filter by operation type",
                                "default": "all"
                            },
                            "start_date": {
                                "type": "string",
                                "description": "ISO 8601 start date for filtering (e.g., '2026-01-01T00:00:00Z')",
                                "default": None
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of audit entries to return",
                                "default": 100
                            }
                        },
                        "required": []
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool invocations"""
            
            if not self.session:
                self.connect()
            
            try:
                if name == "store_document":
                    result = await self._store_document(**arguments)
                elif name == "get_versions":
                    result = await self._get_versions(**arguments)
                elif name == "query_xquery":
                    result = await self._query_xquery(**arguments)
                elif name == "get_audit_trail":
                    result = await self._get_audit_trail(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2)
                )]
                
            except Exception as e:
                logger.error(f"Error executing {name}: {str(e)}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    async def _store_document(
        self,
        uri: str,
        content: str,
        content_type: str = "json",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Store a document with versioning"""
        
        metadata = metadata or {}
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        # Calculate checksum for content
        checksum = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        # Create version number (query existing versions)
        version_query = f"""
        let $versions := db:open('{self.db_name}')//document[@uri='{uri}']/version
        return if (exists($versions)) 
               then max($versions/@number/number()) + 1
               else 1
        """
        
        try:
            version_result = self.session.query(version_query).execute()
            version_number = int(version_result) if version_result else 1
        except (ValueError, AttributeError):
            version_number = 1
        
        # Create document structure
        if content_type == "json":
            # Store JSON as structured data
            doc_xml = f"""
            <document uri="{uri}" type="json" stored_at="{timestamp}">
                <version number="{version_number}" checksum="{checksum}" timestamp="{timestamp}">
                    <metadata>
                        <source>{metadata.get('source', 'unknown')}</source>
                        <import_date>{metadata.get('import_date', timestamp)}</import_date>
                        <user_id>{metadata.get('user_id', 'system')}</user_id>
                        <description>{metadata.get('description', '')}</description>
                    </metadata>
                    <content><![CDATA[{content}]]></content>
                </version>
            </document>
            """
        else:
            # Store XML directly
            doc_xml = f"""
            <document uri="{uri}" type="xml" stored_at="{timestamp}">
                <version number="{version_number}" checksum="{checksum}" timestamp="{timestamp}">
                    <metadata>
                        <source>{metadata.get('source', 'unknown')}</source>
                        <import_date>{metadata.get('import_date', timestamp)}</import_date>
                        <user_id>{metadata.get('user_id', 'system')}</user_id>
                        <description>{metadata.get('description', '')}</description>
                    </metadata>
                    <content><![CDATA[{content}]]></content>
                </version>
            </document>
            """
        
        # Store document using ADD command
        safe_uri = quote(uri, safe='')
        resource_name = f"document_{safe_uri}_v{version_number}.xml"
        
        self.session.execute(f"OPEN {self.db_name}")
        self.session.add(resource_name, doc_xml)
        
        # Log audit trail
        await self._log_audit("store", uri, {
            "version": version_number,
            "checksum": checksum,
            "timestamp": timestamp,
            "metadata": metadata
        })
        
        return {
            "success": True,
            "uri": uri,
            "version": version_number,
            "checksum": checksum,
            "timestamp": timestamp,
            "size_bytes": len(content)
        }
    
    async def _get_versions(
        self,
        uri: str,
        limit: int = 10,
        include_content: bool = False
    ) -> Dict[str, Any]:
        """Retrieve version history for a document"""
        
        # XQuery to get versions
        if include_content:
            query = f"""
            for $version in db:open('{self.db_name}')//document[@uri='{uri}']/version
            order by $version/@timestamp descending
            return $version
            """
        else:
            query = f"""
            for $version in db:open('{self.db_name}')//document[@uri='{uri}']/version
            order by $version/@timestamp descending
            return
                <version number="{{$version/@number}}" 
                         checksum="{{$version/@checksum}}" 
                         timestamp="{{$version/@timestamp}}">
                    {{$version/metadata}}
                </version>
            """
        
        query += f" [position() <= {limit}]"
        
        try:
            result = self.session.query(query).execute()
            
            # Parse XML result
            versions = []
            if result:
                # Simple parsing (in production, use proper XML parser)
                import re
                version_pattern = r'version number="(\d+)" checksum="([^"]+)" timestamp="([^"]+)"'
                matches = re.finditer(version_pattern, result)
                
                for match in matches:
                    versions.append({
                        "version": int(match.group(1)),
                        "checksum": match.group(2),
                        "timestamp": match.group(3)
                    })
            
            return {
                "success": True,
                "uri": uri,
                "version_count": len(versions),
                "versions": versions
            }
            
        except Exception as e:
            logger.error(f"Error retrieving versions: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "uri": uri,
                "versions": []
            }
    
    async def _query_xquery(
        self,
        query: str,
        context: Optional[str] = None,
        bindings: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute an XQuery query"""
        
        bindings = bindings or {}
        
        try:
            # Open database
            self.session.execute(f"OPEN {self.db_name}")
            
            # Set context if provided
            if context:
                query = f"let $doc := db:open('{self.db_name}')//document[@uri='{context}'] return {query}"
            
            # Execute query
            query_obj = self.session.query(query)
            
            # Bind variables
            for key, value in bindings.items():
                query_obj.bind(key, value)
            
            result = query_obj.execute()
            
            # Log audit trail
            await self._log_audit("query", context or "all", {
                "query": query[:100],  # First 100 chars
                "bindings": bindings
            })
            
            return {
                "success": True,
                "result": result,
                "query": query,
                "context": context
            }
            
        except Exception as e:
            logger.error(f"XQuery execution failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }
    
    async def _get_audit_trail(
        self,
        uri: Optional[str] = None,
        operation_type: str = "all",
        start_date: Optional[str] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """Retrieve audit trail"""
        
        # Build XQuery for audit trail
        conditions = []
        
        if uri:
            conditions.append(f"$entry/uri = '{uri}'")
        
        if operation_type != "all":
            conditions.append(f"$entry/operation = '{operation_type}'")
        
        if start_date:
            conditions.append(f"$entry/timestamp >= '{start_date}'")
        
        where_clause = " and ".join(conditions) if conditions else "true()"
        
        query = f"""
        for $entry in db:open('audit_log')//entry
        where {where_clause}
        order by $entry/timestamp descending
        return $entry
        """
        
        query += f" [position() <= {limit}]"
        
        try:
            # Note: In production, audit log should be in separate database
            result = self.session.query(query).execute()
            
            return {
                "success": True,
                "entry_count": result.count('\n') if result else 0,
                "entries": result or "No audit entries found",
                "filters": {
                    "uri": uri,
                    "operation_type": operation_type,
                    "start_date": start_date
                }
            }
            
        except Exception as e:
            # Audit log might not exist yet
            logger.warning(f"Audit trail query failed: {str(e)}")
            return {
                "success": False,
                "error": "Audit log not available",
                "entries": []
            }
    
    async def _log_audit(
        self,
        operation: str,
        uri: str,
        details: Dict[str, Any]
    ):
        """Log an operation to the audit trail"""
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        
        audit_xml = f"""
        <entry timestamp="{timestamp}">
            <operation>{operation}</operation>
            <uri>{uri}</uri>
            <details>{json.dumps(details)}</details>
        </entry>
        """
        
        try:
            # Create audit log database if it doesn't exist
            try:
                self.session.execute("CHECK audit_log")
            except Exception:
                self.session.execute("CREATE DB audit_log")
            
            self.session.execute("OPEN audit_log")
            resource_name = f"audit_{timestamp.replace(':', '-')}.xml"
            self.session.add(resource_name, audit_xml)
            
        except Exception as e:
            # Don't fail if audit logging fails
            logger.warning(f"Audit logging failed: {str(e)}")


async def main():
    """Run the BaseX MCP server"""
    import os
    
    # Get configuration from environment
    basex_host = os.getenv("BASEX_HOST", "localhost")
    basex_port = int(os.getenv("BASEX_PORT", "1984"))
    basex_user = os.getenv("BASEX_USER", "admin")
    basex_password = os.getenv("BASEX_PASSWORD", "admin")
    
    # Create and run server
    server_instance = BaseXMCPServer(
        host=basex_host,
        port=basex_port,
        username=basex_user,
        password=basex_password
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
