# BIMTwinOps bSDD Knowledge Graph Integration

## Overview
BIMTwinOps now integrates with **buildingSMART Data Dictionary (bSDD)** to provide standardized building data, GenAI-powered semantic search, and intelligent property recommendations.

## Key Features

### 1. **bSDD Integration**
- Access to 100+ standardized building dictionaries
- IFC entity to bSDD class mappings
- Property definitions and allowed values
- Classification relationships and hierarchies

### 2. **Knowledge Graph**
- Neo4j-powered semantic graph database
- Nodes: bSDD Dictionaries, Classes, Properties, IFC Elements, Point Cloud Segments
- Relationships: Mappings, classifications, spatial relationships
- Cypher query support for complex data retrieval

### 3. **GenAI Capabilities**
- **Semantic Search**: Natural language queries over knowledge graph
- **Property Recommendations**: AI-powered suggestions for element properties
- **Classification Mapping**: Intelligent classification suggestions
- **Chat Interface**: Conversational access to building standards

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  BIMTwinOps Frontend                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ KG Browser│  │AI Assistant│  │Property Recomm.│  │
│  └──────────┘  └──────────┘  └──────────────────┘  │
└──────────────────────┬──────────────────────────────┘
                       │ REST API + GraphQL
┌──────────────────────┴──────────────────────────────┐
│              FastAPI Backend (/api/kg/*)            │
│  ┌────────────┐  ┌────────────┐  ┌───────────────┐ │
│  │bSDD Client │  │GenAI Service│  │KG Schema Mgr │ │
│  │            │  │             │  │  + BaseX Mgr │ │
│  └─────┬──────┘  └──────┬─────┘  └───┬───────┬───┘ │
└────────┼─────────────────┼────────────┼───────┼─────┘
         │                 │            │       │
    ┌────▼────┐      ┌─────▼──────┐ ┌──▼───┐ ┌▼─────┐
    │  bSDD   │      │Azure OpenAI│ │Neo4j │ │BaseX │
    │GraphQL  │      │   GPT-4o   │ │Graph │ │ XML/ │
    │REST API │      │            │ │  DB  │ │ JSON │
    │         │      │            │ │      │ │  DB  │
    └─────────┘      └────────────┘ └──┬───┘ └──┬───┘
                                       │◄───sync──►│
                                       │           │
                                    Graph       Original
                                  Relationships  Documents
                                  Real-time      Versions
                                   Queries    Audit Trail
```

### Database Roles

**Neo4j (Graph Database)**:
- Semantic relationships (Class hierarchies, IFC mappings)
- Real-time graph traversals and queries
- Spatial relationships (building topology)
- Property graph patterns

**BaseX (XML/JSON Database)**:
- Original bSDD import files (JSON/XML)
- Complete version history (all dictionary versions)
- Audit trail and change tracking
- Document transformations (XQuery)
- Fast document retrieval by URI

**Synchronization**: BaseX stores originals → Neo4j processes into graph → Both stay in sync

## Setup Instructions

### 1. Install Dependencies
```powershell
cd D:\SMART_BIM\backend\api
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and configure:

```env
# Neo4j Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

### 3. Initialize Knowledge Graph Schema
```powershell
cd D:\SMART_BIM\backend\api
python knowledge_graph_schema.py
```

### 4. Ingest bSDD Data (Optional)
```powershell
# Ingest IFC 4.3 dictionary
python bsdd_ingestion.py
```

### 5. Start Backend Server
```powershell
cd D:\SMART_BIM\backend\api
uvicorn main:app --reload --port 8001
```

## API Endpoints

### bSDD Endpoints

#### Get All Dictionaries
```http
GET /api/kg/bsdd/dictionaries
```

#### Search Classes
```http
POST /api/kg/bsdd/search
Content-Type: application/json

{
  "dictionary_uri": "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3",
  "search_text": "wall",
  "related_ifc_entity": "IfcWall",
  "language_code": "en-GB"
}
```

#### Get Class Details
```http
GET /api/kg/bsdd/class/{class_uri}?dictionary_uri={dict_uri}
```

#### Get IFC-to-bSDD Mappings
```http
GET /api/kg/bsdd/ifc-mappings/IfcWall
```

### GenAI Endpoints

#### Semantic Search
```http
POST /api/kg/ai/semantic-search
Content-Type: application/json

{
  "query": "Find all properties for load-bearing walls",
  "context_type": "bsdd",
  "limit": 10
}
```

#### Property Recommendations
```http
POST /api/kg/ai/recommend-properties
Content-Type: application/json

{
  "element_type": "IfcWall",
  "context": {
    "phase": "design",
    "region": "EU"
  }
}
```

#### Classification Suggestions
```http
POST /api/kg/ai/suggest-classifications
Content-Type: application/json

{
  "element_description": "External load-bearing wall made of concrete",
  "available_systems": ["IFC", "bSDD", "Uniclass"]
}
```

#### Chat Interface
```http
POST /api/kg/ai/chat
Content-Type: application/json

{
  "message": "What properties should I capture for windows?",
  "conversation_history": []
}
```

### Knowledge Graph Endpoints

#### Get Graph Statistics
```http
GET /api/kg/graph/stats
```

#### Execute Cypher Query
```http
POST /api/kg/graph/cypher
Content-Type: application/json

{
  "query": "MATCH (c:BsddClass)-[:HAS_PROPERTY]->(p:BsddProperty) RETURN c.name, count(p) as property_count LIMIT 10",
  "parameters": {}
}
```

#### Health Check
```http
GET /api/kg/health
```

## Code Structure

```
backend/api/
├── bsdd_client.py              # bSDD API client (GraphQL + REST)
├── knowledge_graph_schema.py   # Neo4j schema definition
├── bsdd_ingestion.py          # Data ingestion pipeline
├── genai_service.py           # Azure OpenAI GenAI service
├── kg_routes.py               # FastAPI routes for KG/AI
├── main.py                    # Main FastAPI application
└── requirements.txt           # Python dependencies
```

## Knowledge Graph Schema

### Node Types
- **BsddDictionary**: Standard dictionaries (IFC, Uniclass, etc.)
- **BsddClass**: Classifications (walls, doors, etc.)
- **BsddProperty**: Standardized properties
- **BsddUnit**: Units of measurement
- **IfcElement**: IFC building elements
- **PointCloudSegment**: Segmented point cloud data
- **SemanticClass**: Semantic labels (13 classes from PointNet)

### Relationships
- `IN_DICTIONARY`: Class belongs to dictionary
- `HAS_PROPERTY`: Class has property
- `IS_PARENT_OF` / `IS_SUBCLASS_OF`: Class hierarchy
- `MAPS_TO_BSDD`: IFC/PC element maps to bSDD class
- `RELATED_TO`: Related classifications
- `IFC_ENTITY_MAPPING`: IFC entity relationships

## Usage Examples

### Example 1: Find Properties for IfcWall
```python
import requests

response = requests.get("http://localhost:8001/api/kg/bsdd/ifc-mappings/IfcWall")
mappings = response.json()

for mapping in mappings["mappings"]:
    print(f"{mapping['name']}: {mapping['definition']}")
```

### Example 2: AI Property Recommendations
```python
import requests

response = requests.post(
    "http://localhost:8001/api/kg/ai/recommend-properties",
    json={
        "element_type": "IfcWindow",
        "context": {"phase": "construction", "region": "US"}
    }
)

properties = response.json()["properties"]
for prop in properties:
    print(f"✓ {prop['name']}: {prop['why_needed']}")
```

### Example 3: Semantic Search
```python
import requests

response = requests.post(
    "http://localhost:8001/api/kg/ai/semantic-search",
    json={
        "query": "What are the thermal properties for exterior walls?",
        "context_type": "bsdd",
        "limit": 10
    }
)

results = response.json()["results"]
print(results["summary"])
```

### Example 4: Chat with Knowledge Graph
```python
import requests

conversation = []
messages = [
    "What properties should I capture for concrete beams?",
    "How about for steel beams?",
    "What's the difference in load-bearing requirements?"
]

for msg in messages:
    response = requests.post(
        "http://localhost:8001/api/kg/ai/chat",
        json={
            "message": msg,
            "conversation_history": conversation
        }
    )
    
    ai_response = response.json()["response"]
    print(f"User: {msg}")
    print(f"AI: {ai_response}\n")
    
    conversation.append({"role": "user", "content": msg})
    conversation.append({"role": "assistant", "content": ai_response})
```

## Data Ingestion

### Ingest Specific Dictionary
```python
from bsdd_client import BSDDClient, BSDDEnvironment
from knowledge_graph_schema import KnowledgeGraphSchema
from bsdd_ingestion import BSDDIngestionPipeline

# Initialize
client = BSDDClient(environment=BSDDEnvironment.PRODUCTION)
kg = KnowledgeGraphSchema(neo4j_uri="bolt://localhost:7687", 
                          neo4j_user="neo4j", 
                          neo4j_password="password")

# Create schema
kg.create_schema()

# Ingest IFC 4.3
pipeline = BSDDIngestionPipeline(client, kg)
pipeline.ingest_ifc_dictionary(version="4.3")
```

### Ingest All Active Dictionaries
```python
pipeline.ingest_all_dictionaries(
    organization_filter=["buildingsmart", "digibase"],
    status_filter="Active"
)
```

## GenAI Capabilities

### Supported Tasks
1. **Natural Language Queries**: Convert English to Cypher queries
2. **Property Recommendation**: Suggest properties based on element type
3. **Classification Mapping**: Map elements to standard classifications
4. **Semantic Enrichment**: Identify data gaps and suggest improvements
5. **Conversational Interface**: Chat-based knowledge exploration

### RAG (Retrieval-Augmented Generation)
The GenAI service uses RAG pattern:
1. User asks question
2. System retrieves relevant context from Neo4j
3. LLM generates response using retrieved context
4. Response includes both data and reasoning

## Best Practices

### 1. Query Optimization
- Use indexes on frequently queried properties
- Limit result sets appropriately
- Cache frequently accessed bSDD data

### 2. Data Ingestion
- Start with IFC dictionary first
- Ingest incrementally by organization
- Monitor error logs during ingestion

### 3. GenAI Usage
- Provide context in requests for better recommendations
- Use conversation history for multi-turn chats
- Validate AI-generated Cypher queries before execution

### 4. Security
- Add authentication for `/api/kg/graph/cypher` endpoint
- Validate user inputs
- Rate limit GenAI endpoints
- Use environment variables for credentials

## Troubleshooting

### Issue: bSDD API Connection Failed
```
Solution: Check internet connection, verify bSDD service status at https://api.bsdd.buildingsmart.org
```

### Issue: Azure OpenAI Rate Limit
```
Solution: Implement exponential backoff, use caching, or upgrade Azure OpenAI tier
```

### Issue: Neo4j Connection Failed
```
Solution: Verify Neo4j is running, check credentials, ensure bolt://localhost:7687 is accessible
```

### Issue: Slow GenAI Responses
```
Solution: Reduce context size, use smaller models for simple queries, implement response caching
```

## Future Enhancements

- [ ] Vector embeddings for semantic similarity search
- [ ] Automatic IFC property mapping
- [ ] Point cloud to bSDD automatic classification
- [ ] Multi-language support for bSDD queries
- [ ] Custom dictionary upload
- [ ] GraphRAG for complex multi-hop queries
- [ ] Automated data quality validation
- [ ] Export to IDS (Information Delivery Specification)

## References

- **bSDD Documentation**: https://github.com/buildingSMART/bSDD
- **bSDD API Swagger**: https://app.swaggerhub.com/apis/buildingSMART/Dictionaries/v1
- **bSDD GraphQL**: https://api.bsdd.buildingsmart.org/graphql
- **Neo4j Cypher**: https://neo4j.com/docs/cypher-manual/
- **Azure OpenAI**: https://learn.microsoft.com/en-us/azure/ai-services/openai/

## Support

For issues or questions:
- Create an issue in the repository
- Check bSDD forums: https://forums.buildingsmart.org/
- Neo4j community: https://community.neo4j.com/

---

**BIMTwinOps** - Enterprise Digital Twin Operations Platform
Powered by bSDD, Neo4j, and Azure OpenAI
