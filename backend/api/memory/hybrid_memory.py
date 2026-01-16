"""
OpenSearch Hybrid Memory System
Vector + keyword search for agent context retrieval.

This module implements ADR-003 (OpenSearch Hybrid Memory) providing:
1. Semantic search via k-NN vectors (Azure OpenAI embeddings)
2. Keyword search via BM25
3. Hybrid retrieval combining both
4. Persistent conversation memory

Architecture:
- Index: bsdd_tasks_vectors (task-related context)
- Index: bsdd_context_vectors (general knowledge)
- Embeddings: Azure OpenAI text-embedding-ada-002
- Search: Hybrid (0.7 semantic + 0.3 keyword)

Use Cases:
- Agent context retrieval
- Similar task finding
- Semantic code search
- Documentation lookup

References:
- OpenSearch k-NN: https://opensearch.org/docs/latest/search-plugins/knn/index/
- Hybrid Search: https://opensearch.org/docs/latest/search-plugins/hybrid-search/
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime
import json
import hashlib

from opensearchpy import OpenSearch, helpers
from opensearchpy.exceptions import OpenSearchException
import numpy as np

# Azure OpenAI for embeddings
from openai import AzureOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

class OpenSearchConfig:
    """OpenSearch connection configuration"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 9200,
        username: str = "admin",
        password: str = "admin123",
        use_ssl: bool = False,
        verify_certs: bool = False
    ):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.verify_certs = verify_certs
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to OpenSearch client config"""
        return {
            "hosts": [{"host": self.host, "port": self.port}],
            "http_auth": (self.username, self.password),
            "use_ssl": self.use_ssl,
            "verify_certs": self.verify_certs,
            "ssl_show_warn": False
        }


# ============================================================================
# Embedding Service
# ============================================================================

class AzureOpenAIEmbeddings:
    """
    Azure OpenAI embeddings for semantic search
    
    Uses text-embedding-ada-002 (1536 dimensions)
    Batch processing for efficiency
    """
    
    def __init__(
        self,
        azure_endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: str = "text-embedding-ada-002",
        api_version: str = "2024-02-15-preview"
    ):
        """Initialize Azure OpenAI client"""
        import os
        
        self.client = AzureOpenAI(
            azure_endpoint=azure_endpoint or os.getenv("AZURE_OPENAI_ENDPOINT"),
            api_key=api_key or os.getenv("AZURE_OPENAI_API_KEY"),
            api_version=api_version
        )
        self.deployment_name = deployment_name
        self.dimension = 1536  # text-embedding-ada-002 dimension
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for single text
        
        Args:
            text: Text to embed
        
        Returns:
            1536-dimensional vector
        """
        try:
            response = self.client.embeddings.create(
                input=text,
                model=self.deployment_name
            )
            return response.data[0].embedding
        
        except Exception as e:
            logger.error(f"Embedding failed: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * self.dimension
    
    def embed_batch(self, texts: List[str], batch_size: int = 16) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
        
        Returns:
            List of 1536-dimensional vectors
        """
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            try:
                response = self.client.embeddings.create(
                    input=batch,
                    model=self.deployment_name
                )
                batch_embeddings = [item.embedding for item in response.data]
                embeddings.extend(batch_embeddings)
            
            except Exception as e:
                logger.error(f"Batch embedding failed: {str(e)}")
                # Fallback to individual embeddings
                for text in batch:
                    embeddings.append(self.embed_text(text))
        
        return embeddings


# ============================================================================
# Index Management
# ============================================================================

class OpenSearchIndexManager:
    """
    Manage OpenSearch indices for vector search
    
    Creates and configures:
    - bsdd_tasks_vectors: Task-related context
    - bsdd_context_vectors: General knowledge
    
    Both use k-NN with HNSW algorithm
    """
    
    def __init__(self, client: OpenSearch):
        self.client = client
    
    def create_tasks_index(self, index_name: str = "bsdd_tasks_vectors"):
        """
        Create tasks vector index
        
        Schema:
        - task_id: Unique identifier
        - task_description: Full text
        - embedding: 1536-dim vector
        - metadata: task type, priority, status, etc.
        - timestamp: Creation time
        """
        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "knn": True,  # Enable k-NN
                    "knn.algo_param.ef_search": 512  # HNSW search quality
                }
            },
            "mappings": {
                "properties": {
                    "task_id": {"type": "keyword"},
                    "task_description": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1536,
                        "method": {
                            "name": "hnsw",
                            "engine": "lucene",
                            "space_type": "cosinesimil",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "metadata": {
                        "properties": {
                            "task_type": {"type": "keyword"},
                            "priority": {"type": "integer"},
                            "status": {"type": "keyword"},
                            "agent": {"type": "keyword"},
                            "duration_ms": {"type": "integer"}
                        }
                    },
                    "timestamp": {"type": "date"}
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} already exists")
                return
            
            self.client.indices.create(index=index_name, body=mapping)
            logger.info(f"Created index: {index_name}")
        
        except OpenSearchException as e:
            logger.error(f"Failed to create tasks index: {str(e)}")
            raise
    
    def create_context_index(self, index_name: str = "bsdd_context_vectors"):
        """
        Create general context vector index
        
        Schema:
        - context_id: Unique identifier
        - content: Full text
        - embedding: 1536-dim vector
        - metadata: source, category, relevance
        - timestamp: Creation time
        """
        mapping = {
            "settings": {
                "index": {
                    "number_of_shards": 2,
                    "number_of_replicas": 1,
                    "knn": True,
                    "knn.algo_param.ef_search": 512
                }
            },
            "mappings": {
                "properties": {
                    "context_id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1536,
                        "method": {
                            "name": "hnsw",
                            "engine": "lucene",
                            "space_type": "cosinesimil",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "metadata": {
                        "properties": {
                            "source": {"type": "keyword"},
                            "category": {"type": "keyword"},
                            "relevance_score": {"type": "float"},
                            "tags": {"type": "keyword"}
                        }
                    },
                    "timestamp": {"type": "date"}
                }
            }
        }
        
        try:
            if self.client.indices.exists(index=index_name):
                logger.info(f"Index {index_name} already exists")
                return
            
            self.client.indices.create(index=index_name, body=mapping)
            logger.info(f"Created index: {index_name}")
        
        except OpenSearchException as e:
            logger.error(f"Failed to create context index: {str(e)}")
            raise
    
    def delete_index(self, index_name: str):
        """Delete an index"""
        try:
            if self.client.indices.exists(index=index_name):
                self.client.indices.delete(index=index_name)
                logger.info(f"Deleted index: {index_name}")
        except OpenSearchException as e:
            logger.error(f"Failed to delete index: {str(e)}")


# ============================================================================
# Hybrid Memory System
# ============================================================================

class HybridMemorySystem:
    """
    Main interface for agent memory operations
    
    Provides:
    - Store: Add task/context to memory
    - Retrieve: Hybrid search (semantic + keyword)
    - Update: Modify existing entries
    - Delete: Remove entries
    
    Hybrid Search Strategy:
    - 70% weight on semantic similarity (k-NN)
    - 30% weight on keyword match (BM25)
    - Configurable via weights parameter
    """
    
    def __init__(
        self,
        config: Optional[OpenSearchConfig] = None,
        embedding_service: Optional[AzureOpenAIEmbeddings] = None
    ):
        """Initialize hybrid memory system"""
        
        # Create OpenSearch client
        if config is None:
            config = OpenSearchConfig()
        
        self.client = OpenSearch(**config.to_dict())
        
        # Initialize embedding service
        if embedding_service is None:
            embedding_service = AzureOpenAIEmbeddings()
        self.embeddings = embedding_service
        
        # Initialize index manager
        self.index_manager = OpenSearchIndexManager(self.client)
        
        # Create indices if they don't exist
        self._ensure_indices()
        
        logger.info("HybridMemorySystem initialized")
    
    def _ensure_indices(self):
        """Create indices if they don't exist"""
        self.index_manager.create_tasks_index()
        self.index_manager.create_context_index()
    
    def _generate_id(self, content: str) -> str:
        """Generate deterministic ID from content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def store_task(
        self,
        task_description: str,
        metadata: Optional[Dict[str, Any]] = None,
        task_id: Optional[str] = None
    ) -> str:
        """
        Store task in memory
        
        Args:
            task_description: Task text
            metadata: Task metadata (type, priority, status, etc.)
            task_id: Optional custom ID
        
        Returns:
            Task ID
        """
        if task_id is None:
            task_id = self._generate_id(task_description)
        
        # Generate embedding
        embedding = self.embeddings.embed_text(task_description)
        
        # Create document
        doc = {
            "task_id": task_id,
            "task_description": task_description,
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            self.client.index(
                index="bsdd_tasks_vectors",
                id=task_id,
                body=doc
            )
            logger.info(f"Stored task: {task_id}")
            return task_id
        
        except OpenSearchException as e:
            logger.error(f"Failed to store task: {str(e)}")
            raise
    
    def store_context(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        context_id: Optional[str] = None
    ) -> str:
        """
        Store context in memory
        
        Args:
            content: Context text
            metadata: Context metadata (source, category, tags)
            context_id: Optional custom ID
        
        Returns:
            Context ID
        """
        if context_id is None:
            context_id = self._generate_id(content)
        
        # Generate embedding
        embedding = self.embeddings.embed_text(content)
        
        # Create document
        doc = {
            "context_id": context_id,
            "content": content,
            "embedding": embedding,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            self.client.index(
                index="bsdd_context_vectors",
                id=context_id,
                body=doc
            )
            logger.info(f"Stored context: {context_id}")
            return context_id
        
        except OpenSearchException as e:
            logger.error(f"Failed to store context: {str(e)}")
            raise
    
    def hybrid_search_tasks(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search for similar tasks
        
        Args:
            query: Search query
            top_k: Number of results
            semantic_weight: Weight for semantic vs keyword (0.0-1.0)
        
        Returns:
            List of matching tasks with scores
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        # Build hybrid query
        search_body = {
            "size": top_k,
            "query": {
                "hybrid": {
                    "queries": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": query_embedding,
                                    "k": top_k
                                }
                            }
                        },
                        {
                            "match": {
                                "task_description": {
                                    "query": query,
                                    "boost": 1 - semantic_weight
                                }
                            }
                        }
                    ]
                }
            }
        }
        
        try:
            response = self.client.search(
                index="bsdd_tasks_vectors",
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "task_id": hit["_source"]["task_id"],
                    "task_description": hit["_source"]["task_description"],
                    "metadata": hit["_source"].get("metadata", {}),
                    "score": hit["_score"],
                    "timestamp": hit["_source"]["timestamp"]
                })
            
            logger.info(f"Found {len(results)} matching tasks")
            return results
        
        except OpenSearchException as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            return []
    
    def hybrid_search_context(
        self,
        query: str,
        top_k: int = 5,
        semantic_weight: float = 0.7,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search for relevant context
        
        Args:
            query: Search query
            top_k: Number of results
            semantic_weight: Weight for semantic vs keyword
            filters: Optional metadata filters
        
        Returns:
            List of matching context with scores
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_text(query)
        
        # Build hybrid query with optional filters
        queries = [
            {
                "knn": {
                    "embedding": {
                        "vector": query_embedding,
                        "k": top_k
                    }
                }
            },
            {
                "match": {
                    "content": {
                        "query": query,
                        "boost": 1 - semantic_weight
                    }
                }
            }
        ]
        
        # Add filters if provided
        if filters:
            filter_clauses = []
            for key, value in filters.items():
                filter_clauses.append({
                    "term": {f"metadata.{key}": value}
                })
            
            queries.append({
                "bool": {"filter": filter_clauses}
            })
        
        search_body = {
            "size": top_k,
            "query": {
                "hybrid": {"queries": queries}
            }
        }
        
        try:
            response = self.client.search(
                index="bsdd_context_vectors",
                body=search_body
            )
            
            results = []
            for hit in response["hits"]["hits"]:
                results.append({
                    "context_id": hit["_source"]["context_id"],
                    "content": hit["_source"]["content"],
                    "metadata": hit["_source"].get("metadata", {}),
                    "score": hit["_score"],
                    "timestamp": hit["_source"]["timestamp"]
                })
            
            logger.info(f"Found {len(results)} matching contexts")
            return results
        
        except OpenSearchException as e:
            logger.error(f"Hybrid search failed: {str(e)}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        try:
            tasks_count = self.client.count(index="bsdd_tasks_vectors")["count"]
            context_count = self.client.count(index="bsdd_context_vectors")["count"]
            
            return {
                "tasks_stored": tasks_count,
                "contexts_stored": context_count,
                "indices": ["bsdd_tasks_vectors", "bsdd_context_vectors"],
                "embedding_dimension": self.embeddings.dimension
            }
        
        except OpenSearchException as e:
            logger.error(f"Failed to get stats: {str(e)}")
            return {}


# ============================================================================
# Testing & Utilities
# ============================================================================

async def test_hybrid_memory():
    """Test hybrid memory system"""
    
    # Initialize system
    memory = HybridMemorySystem()
    
    # Store sample tasks
    tasks = [
        "Create a new wall with fire rating 90 minutes",
        "Import IFC file from project folder",
        "Segment point cloud for Room 101",
        "Query bSDD for IfcWall properties",
        "Generate compliance report for fire safety"
    ]
    
    print("Storing tasks...")
    for task in tasks:
        task_id = memory.store_task(
            task,
            metadata={"status": "pending", "priority": 1}
        )
        print(f"  Stored: {task_id[:8]}...")
    
    # Store sample context
    contexts = [
        "Fire-rated walls must have minimum 60-minute rating",
        "IFC files use STEP format with .ifc extension",
        "Point cloud segmentation uses PointNet++ architecture",
        "bSDD provides standardized building dictionaries",
        "Compliance reports require ISO 19650 metadata"
    ]
    
    print("\nStoring contexts...")
    for context in contexts:
        context_id = memory.store_context(
            context,
            metadata={"source": "documentation", "category": "knowledge"}
        )
        print(f"  Stored: {context_id[:8]}...")
    
    # Test hybrid search
    print("\nTesting hybrid search...")
    
    queries = [
        "fire safety requirements",
        "import building model",
        "machine learning segmentation"
    ]
    
    for query in queries:
        print(f"\nQuery: {query}")
        print("=" * 60)
        
        # Search tasks
        task_results = memory.hybrid_search_tasks(query, top_k=2)
        print("\nTop Tasks:")
        for i, result in enumerate(task_results, 1):
            print(f"{i}. [{result['score']:.3f}] {result['task_description']}")
        
        # Search context
        context_results = memory.hybrid_search_context(query, top_k=2)
        print("\nTop Contexts:")
        for i, result in enumerate(context_results, 1):
            print(f"{i}. [{result['score']:.3f}] {result['content']}")
    
    # Show stats
    print("\n" + "=" * 60)
    print("Memory Statistics")
    print("=" * 60)
    stats = memory.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_hybrid_memory())
