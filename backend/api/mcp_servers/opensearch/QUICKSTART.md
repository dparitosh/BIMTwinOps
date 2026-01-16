# OpenSearch MCP Server - Quick Start Guide

## Overview

The OpenSearch MCP server provides semantic search and document management capabilities for the SMART_BIM agent system.

## Installation

### 1. Install OpenSearch (Docker - Recommended)

```bash
docker run -d \
  --name opensearch \
  -p 9200:9200 \
  -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "OPENSEARCH_INITIAL_ADMIN_PASSWORD=Admin@123" \
  opensearchproject/opensearch:latest
```

Wait ~30 seconds for startup, then verify:
```bash
curl http://localhost:9200
```

### 2. Install Python Dependencies

```bash
cd backend/api/mcp_servers/opensearch
pip install opensearch-py pydantic mcp
```

Or from project root:
```bash
pip install -r requirements.txt  # (if opensearch-py is added)
```

### 3. Test Connection

```bash
python test_connection.py
```

Expected output:
```
✅ Connected successfully!
   Version: 2.x.x
   Cluster: opensearch-cluster
```

## Configuration

Set environment variables (optional):

```bash
# .env file
OPENSEARCH_URL=http://localhost:9200
OPENSEARCH_INDEX=bim_memory
OPENSEARCH_USER=admin          # Optional
OPENSEARCH_PASSWORD=Admin@123  # Optional
```

## Usage Examples

### 1. Create Index

```python
from opensearch.server import OpenSearchClient

client = OpenSearchClient()
client.connect()

# Create index with vector support
result = client.create_index(
    index_name="bim_memory",
    vector_dimension=384
)
print(result)  # {'status': 'created', 'index': 'bim_memory'}
```

### 2. Store Documents

```python
# Store BIM element
document = {
    "name": "Wall-001",
    "description": "Fire rated exterior wall",
    "semantic_name": "wall",
    "category": "IfcWall",
    "fire_rating": 90,
    "height": 3.5
}

result = client.store_document(
    document=document,
    doc_id="wall-001",
    index="bim_memory"
)
print(result)  # {'id': 'wall-001', 'result': 'created'}
```

### 3. Semantic Search

```python
# Search for fire rated elements
results = client.search_semantic(
    query="fire rated walls",
    index="bim_memory",
    size=10,
    min_score=0.5
)

for result in results:
    print(f"{result['source']['name']}: score={result['score']:.2f}")
```

### 4. Retrieve Document

```python
# Get specific document
result = client.get_document(
    doc_id="wall-001",
    index="bim_memory"
)

if result['found']:
    print(result['source'])
```

## Integration with Agent System

The Query Agent automatically uses OpenSearch for semantic queries:

```python
# User query
"Find all fire rated walls"

# Agent routes to OpenSearch
result = await query_agent.process({
    "user_input": "Find all fire rated walls"
})

# Returns semantic search results
```

## Running the MCP Server

### Standalone Mode (for testing):
```bash
python server.py
```

### MCP Mode (stdio):
```bash
python -m opensearch
```

### Via MCP Host:
The MCP Host automatically starts the OpenSearch server when initialized:
```python
from mcp_host.mcp_host import get_mcp_host

host = await get_mcp_host()
# OpenSearch server is now available
```

## Populating with BIM Data

### Load IFC Metadata

```python
import ifcopenshell

# Parse IFC file
ifc_file = ifcopenshell.open("project.ifc")

# Extract and index walls
for wall in ifc_file.by_type("IfcWall"):
    document = {
        "name": wall.Name or f"Wall-{wall.id()}",
        "description": wall.Description or "",
        "semantic_name": "wall",
        "category": "IfcWall",
        "global_id": wall.GlobalId,
        # Add more properties...
    }
    
    client.store_document(
        document=document,
        doc_id=wall.GlobalId,
        index="bim_memory"
    )

print("IFC elements indexed!")
```

### Load Point Cloud Segments

```python
import numpy as np

# Load segmented point cloud
segments = np.load("segments.npy", allow_pickle=True)

for i, segment in enumerate(segments):
    document = {
        "name": f"Segment-{i}",
        "semantic_name": segment['label'],
        "category": f"PointCloud-{segment['label']}",
        "num_points": len(segment['points']),
        "centroid": segment['centroid'].tolist(),
        # Add embedding if available
    }
    
    client.store_document(
        document=document,
        index="bim_memory"
    )

print("Point cloud segments indexed!")
```

## Testing

Run the comprehensive test suite:

```bash
python test_server.py
```

Tests include:
- ✅ Connection verification
- ✅ Index creation
- ✅ Document storage
- ✅ Semantic search
- ✅ Document retrieval
- ✅ BIM-specific queries

## Troubleshooting

### Issue: Connection refused

**Solution**: Ensure OpenSearch is running
```bash
docker ps | grep opensearch
curl http://localhost:9200
```

### Issue: Index already exists

**Solution**: Delete and recreate
```bash
curl -X DELETE http://localhost:9200/bim_memory
```

### Issue: No search results

**Causes**:
1. Documents not indexed yet → Check with `curl http://localhost:9200/bim_memory/_count`
2. min_score too high → Lower to 0.1
3. Query mismatch → Check document field names

### Issue: opensearch-py not installed

**Solution**:
```bash
pip install opensearch-py
```

## Performance Tips

1. **Batch Indexing**: Use bulk API for large datasets
2. **Refresh Interval**: Set `refresh_interval=-1` during bulk load
3. **Shard Configuration**: Use 1 shard for small datasets (<10k docs)
4. **Vector Dimension**: Match embedding model (384 for MiniLM, 768 for BERT)

## Next Steps

1. ✅ Start OpenSearch container
2. ✅ Test connection
3. ✅ Create bim_memory index
4. ⏳ Load IFC metadata (see example above)
5. ⏳ Load point cloud segments
6. ⏳ Test semantic queries via agent

## Resources

- [OpenSearch Documentation](https://opensearch.org/docs/latest/)
- [Python Client API](https://opensearch-project.github.io/opensearch-py/)
- [Vector Search Guide](https://opensearch.org/docs/latest/search-plugins/knn/)
