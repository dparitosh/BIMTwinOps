# OpenSearch MCP Server

MCP server for OpenSearch semantic search and document management.

## Features

- **Hybrid Semantic Search**: Multi-field text search with BM25 scoring
- **Vector Support**: KNN vector search with HNSW indexing
- **Document Storage**: Index documents with automatic timestamps
- **Index Management**: Create indices with vector mappings

## Tools

### 1. search_semantic
Perform hybrid semantic search across documents.

**Arguments**:
- `query` (required): Search query text
- `index` (optional): Index name (default: bim_memory)
- `size` (optional): Number of results (default: 10)
- `min_score` (optional): Minimum relevance score (default: 0.5)

**Example**:
```python
result = await call_tool("search_semantic", {
    "query": "fire rated walls",
    "size": 5
})
```

### 2. store_document
Store document in OpenSearch with optional embedding.

**Arguments**:
- `document` (required): Document data as dict
- `doc_id` (optional): Document ID (auto-generated if not provided)
- `index` (optional): Index name (default: bim_memory)
- `embedding` (optional): Vector embedding as list of floats

**Example**:
```python
result = await call_tool("store_document", {
    "document": {
        "name": "Wall-001",
        "description": "Fire rated wall",
        "fire_rating": 90
    },
    "doc_id": "wall-001"
})
```

### 3. create_index
Create OpenSearch index with vector support.

**Arguments**:
- `index_name` (required): Name of the index
- `vector_dimension` (optional): Embedding dimension (default: 384)
- `settings` (optional): Custom index settings

**Example**:
```python
result = await call_tool("create_index", {
    "index_name": "bim_memory",
    "vector_dimension": 384
})
```

### 4. get_document
Retrieve document by ID.

**Arguments**:
- `doc_id` (required): Document ID
- `index` (optional): Index name (default: bim_memory)

**Example**:
```python
result = await call_tool("get_document", {
    "doc_id": "wall-001"
})
```

## Configuration

Set environment variables:

```bash
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_INDEX=bim_memory
OPENSEARCH_USER=admin          # Optional
OPENSEARCH_PASSWORD=admin      # Optional
```

## Installation

```bash
cd backend/api/mcp_servers/opensearch
uv venv
uv pip install -e .
```

## Running

### As MCP Server (stdio):
```bash
uv run python -m opensearch
```

### Standalone:
```bash
python server.py
```

## Testing

```bash
python test_server.py
```

## Dependencies

- `mcp>=1.0.0`: Model Context Protocol SDK
- `opensearch-py>=2.3.0`: OpenSearch Python client
- `pydantic>=2.0.0`: Data validation

## Index Schema

Default mapping includes:
- `name` (text): Entity name
- `description` (text): Description
- `content` (text): Full content
- `semantic_name` (keyword): Semantic label
- `category` (keyword): Category
- `indexed_at` (date): Indexing timestamp
- `embedding` (knn_vector): Vector embedding (384-dim)

## Architecture

```
OpenSearchClient
├── search_semantic() - Multi-field BM25 search
├── store_document() - Index with embedding
├── create_index() - Create with vector mapping
└── get_document() - Retrieve by ID

MCP Server
├── list_tools() - Expose 4 tools
└── call_tool() - Route to OpenSearchClient
```

## Error Handling

- **NotFoundError**: Index/document not found → Returns empty results
- **RequestError**: Invalid request → Raises with details
- **ConnectionError**: OpenSearch unreachable → Server starts but tools fail

## Performance

- **Search**: <100ms for small indices (<10k docs)
- **Indexing**: <50ms per document
- **Vector Search**: <200ms with HNSW (when vectors used)

## Integration with Agent System

Used by Query Agent for:
- Semantic search across IFC metadata
- Point cloud segment retrieval
- Document similarity matching

Used by Action Agent for:
- Storing processed segments
- Indexing IFC elements
- Building knowledge base
