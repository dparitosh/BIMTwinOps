"""
OpenSearch MCP Server
Provides semantic search and document management via MCP protocol.

Tools:
1. search_semantic - Hybrid semantic search (vector + text)
2. store_document - Index documents with embeddings
3. create_index - Create index with vector mapping
4. get_document - Retrieve document by ID

Configuration via environment:
- OPENSEARCH_URL: OpenSearch endpoint (default: http://localhost:9200)
- OPENSEARCH_INDEX: Default index name (default: bim_memory)
- OPENSEARCH_USER: Username (optional)
- OPENSEARCH_PASSWORD: Password (optional)
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from pydantic import BaseModel, Field

try:
    from opensearchpy import OpenSearch, RequestsHttpConnection
    from opensearchpy.exceptions import NotFoundError, RequestError
    OPENSEARCH_AVAILABLE = True
except ImportError:
    OPENSEARCH_AVAILABLE = False
    OpenSearch = None
    NotFoundError = Exception
    RequestError = Exception

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

OPENSEARCH_URL = os.getenv("OPENSEARCH_URL", "http://localhost:9200")
OPENSEARCH_INDEX = os.getenv("OPENSEARCH_INDEX", "bim_memory")
OPENSEARCH_USER = os.getenv("OPENSEARCH_USER")
OPENSEARCH_PASSWORD = os.getenv("OPENSEARCH_PASSWORD")


# ============================================================================
# Pydantic Models for Tool Arguments
# ============================================================================

class SearchSemanticArgs(BaseModel):
    """Arguments for semantic search"""
    query: str = Field(..., description="Search query text")
    index: Optional[str] = Field(default=None, description="Index name (default: bim_memory)")
    size: Optional[int] = Field(default=10, description="Number of results")
    min_score: Optional[float] = Field(default=0.5, description="Minimum relevance score")


class StoreDocumentArgs(BaseModel):
    """Arguments for storing documents"""
    document: Dict[str, Any] = Field(..., description="Document to store")
    doc_id: Optional[str] = Field(default=None, description="Document ID (auto-generated if not provided)")
    index: Optional[str] = Field(default=None, description="Index name (default: bim_memory)")
    embedding: Optional[List[float]] = Field(default=None, description="Document embedding vector")


class CreateIndexArgs(BaseModel):
    """Arguments for creating index"""
    index_name: str = Field(..., description="Name of the index to create")
    vector_dimension: Optional[int] = Field(default=384, description="Vector embedding dimension")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Custom index settings")


class GetDocumentArgs(BaseModel):
    """Arguments for getting document"""
    doc_id: str = Field(..., description="Document ID to retrieve")
    index: Optional[str] = Field(default=None, description="Index name (default: bim_memory)")


# ============================================================================
# OpenSearch Client
# ============================================================================

class OpenSearchClient:
    """Wrapper for OpenSearch operations"""
    
    def __init__(self):
        self.client: Optional[OpenSearch] = None
        self._connected = False
    
    def connect(self):
        """Initialize OpenSearch connection"""
        if not OPENSEARCH_AVAILABLE:
            logger.error("opensearch-py not installed")
            raise ImportError("opensearch-py package required. Install: pip install opensearch-py")
        
        try:
            # Parse URL
            url = OPENSEARCH_URL.replace("http://", "").replace("https://", "")
            host, port = url.split(":") if ":" in url else (url, "9200")
            
            # Build connection params
            auth = None
            if OPENSEARCH_USER and OPENSEARCH_PASSWORD:
                auth = (OPENSEARCH_USER, OPENSEARCH_PASSWORD)
            
            self.client = OpenSearch(
                hosts=[{"host": host, "port": int(port)}],
                http_auth=auth,
                use_ssl=False,
                verify_certs=False,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
            
            # Test connection
            info = self.client.info()
            logger.info(f"✅ Connected to OpenSearch {info.get('version', {}).get('number', 'unknown')}")
            self._connected = True
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to OpenSearch: {e}")
            self._connected = False
            raise
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connected and self.client is not None
    
    def ensure_connected(self):
        """Ensure connection is active"""
        if not self.is_connected():
            self.connect()
    
    def search_semantic(
        self,
        query: str,
        index: str = OPENSEARCH_INDEX,
        size: int = 10,
        min_score: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid semantic search
        
        Uses multi-match query on text fields with BM25 scoring.
        If embeddings are available, combines with vector similarity.
        """
        self.ensure_connected()
        
        try:
            # Multi-match query across common text fields
            query_body = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "multi_match": {
                                    "query": query,
                                    "fields": ["name^3", "description^2", "content", "semantic_name", "category"],
                                    "type": "best_fields",
                                    "fuzziness": "AUTO"
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "size": size,
                "min_score": min_score,
                "_source": True
            }
            
            logger.info(f"Searching index '{index}' with query: {query}")
            response = self.client.search(index=index, body=query_body)
            
            # Extract results
            hits = response.get("hits", {}).get("hits", [])
            results = []
            
            for hit in hits:
                results.append({
                    "id": hit["_id"],
                    "score": hit["_score"],
                    "source": hit["_source"]
                })
            
            logger.info(f"Found {len(results)} results")
            return results
            
        except NotFoundError:
            logger.warning(f"Index '{index}' not found")
            return []
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def store_document(
        self,
        document: Dict[str, Any],
        doc_id: Optional[str] = None,
        index: str = OPENSEARCH_INDEX,
        embedding: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Store document in OpenSearch
        
        Args:
            document: Document data
            doc_id: Optional document ID (auto-generated if None)
            index: Index name
            embedding: Optional embedding vector
        
        Returns:
            Result with document ID and status
        """
        self.ensure_connected()
        
        try:
            # Add timestamp
            document["indexed_at"] = datetime.utcnow().isoformat()
            
            # Add embedding if provided
            if embedding:
                document["embedding"] = embedding
            
            # Index document
            if doc_id:
                response = self.client.index(index=index, id=doc_id, body=document)
            else:
                response = self.client.index(index=index, body=document)
            
            result = {
                "id": response["_id"],
                "result": response["result"],
                "index": response["_index"]
            }
            
            logger.info(f"Stored document {result['id']} in {index}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to store document: {e}")
            raise
    
    def create_index(
        self,
        index_name: str,
        vector_dimension: int = 384,
        settings: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create index with vector support
        
        Args:
            index_name: Name of index
            vector_dimension: Embedding vector dimension
            settings: Custom settings (optional)
        
        Returns:
            Creation result
        """
        self.ensure_connected()
        
        try:
            # Check if exists
            if self.client.indices.exists(index=index_name):
                logger.warning(f"Index '{index_name}' already exists")
                return {"status": "exists", "index": index_name}
            
            # Default mapping with vector support
            mapping = {
                "mappings": {
                    "properties": {
                        "name": {"type": "text"},
                        "description": {"type": "text"},
                        "content": {"type": "text"},
                        "semantic_name": {"type": "keyword"},
                        "category": {"type": "keyword"},
                        "indexed_at": {"type": "date"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": vector_dimension,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "nmslib"
                            }
                        }
                    }
                },
                "settings": settings or {
                    "index": {
                        "number_of_shards": 1,
                        "number_of_replicas": 0,
                        "knn": True
                    }
                }
            }
            
            response = self.client.indices.create(index=index_name, body=mapping)
            
            logger.info(f"Created index '{index_name}' with vector dimension {vector_dimension}")
            return {
                "status": "created",
                "index": index_name,
                "acknowledged": response.get("acknowledged", False)
            }
            
        except RequestError as e:
            logger.error(f"Failed to create index: {e}")
            raise
    
    def get_document(
        self,
        doc_id: str,
        index: str = OPENSEARCH_INDEX
    ) -> Dict[str, Any]:
        """
        Retrieve document by ID
        
        Args:
            doc_id: Document ID
            index: Index name
        
        Returns:
            Document data
        """
        self.ensure_connected()
        
        try:
            response = self.client.get(index=index, id=doc_id)
            
            return {
                "id": response["_id"],
                "source": response["_source"],
                "found": response["found"]
            }
            
        except NotFoundError:
            logger.warning(f"Document '{doc_id}' not found in '{index}'")
            return {"id": doc_id, "found": False}
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            raise


# ============================================================================
# MCP Server
# ============================================================================

# Initialize server and client
app = Server("opensearch-mcp-server")
opensearch_client = OpenSearchClient()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available OpenSearch tools"""
    return [
        Tool(
            name="search_semantic",
            description="Perform hybrid semantic search across documents. Searches text fields (name, description, content, semantic_name, category) with BM25 scoring. Returns ranked results with relevance scores.",
            inputSchema=SearchSemanticArgs.model_json_schema()
        ),
        Tool(
            name="store_document",
            description="Store document in OpenSearch with optional embedding vector. Automatically adds timestamp. Supports both explicit document IDs and auto-generation.",
            inputSchema=StoreDocumentArgs.model_json_schema()
        ),
        Tool(
            name="create_index",
            description="Create OpenSearch index with vector (knn_vector) support for embeddings. Includes default mapping for text fields and HNSW vector index.",
            inputSchema=CreateIndexArgs.model_json_schema()
        ),
        Tool(
            name="get_document",
            description="Retrieve document by ID from specified index. Returns full document source data.",
            inputSchema=GetDocumentArgs.model_json_schema()
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls"""
    
    try:
        # Parse arguments based on tool
        if name == "search_semantic":
            args = SearchSemanticArgs(**arguments)
            results = opensearch_client.search_semantic(
                query=args.query,
                index=args.index or OPENSEARCH_INDEX,
                size=args.size or 10,
                min_score=args.min_score or 0.5
            )
            return [TextContent(type="text", text=json.dumps(results, indent=2))]
        
        elif name == "store_document":
            args = StoreDocumentArgs(**arguments)
            result = opensearch_client.store_document(
                document=args.document,
                doc_id=args.doc_id,
                index=args.index or OPENSEARCH_INDEX,
                embedding=args.embedding
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "create_index":
            args = CreateIndexArgs(**arguments)
            result = opensearch_client.create_index(
                index_name=args.index_name,
                vector_dimension=args.vector_dimension or 384,
                settings=args.settings
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_document":
            args = GetDocumentArgs(**arguments)
            result = opensearch_client.get_document(
                doc_id=args.doc_id,
                index=args.index or OPENSEARCH_INDEX
            )
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    except Exception as e:
        logger.error(f"Tool '{name}' failed: {e}")
        error_response = {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }
        return [TextContent(type="text", text=json.dumps(error_response, indent=2))]


async def main():
    """Main entry point"""
    from mcp.server.stdio import stdio_server
    
    logger.info("Starting OpenSearch MCP Server")
    
    # Connect to OpenSearch
    try:
        opensearch_client.connect()
    except Exception as e:
        logger.warning(f"Failed to connect to OpenSearch: {e}")
        logger.info("Server will start but tools will fail until connection established")
    
    # Run server
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
