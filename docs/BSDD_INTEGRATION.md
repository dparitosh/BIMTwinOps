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
NEO4J_DATABASE=bimtwin

# LLM Provider (azure_openai | ollama)
LLM_PROVIDER=ollama

# Ollama (local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:1b

# Azure OpenAI (cloud LLM)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# BaseX XML Database
BASEX_HOST=localhost
BASEX_PORT=1984
BASEX_USER=admin
BASEX_PASSWORD=admin
BASEX_DB=bimtwinops

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# Redis (caching & sessions)
REDIS_HOST=localhost
REDIS_PORT=6379
```

### 3. Initialize Knowledge Graph Schema
```powershell
cd D:\SMART_BIM\backend
python scripts/init_neo4j_schema.py --seed
```

### 4. Ingest bSDD Data (Optional)
```powershell
cd D:\SMART_BIM\backend
python -m api.bsdd_ingestion
```

### 5. Start Backend Server
```powershell
cd D:\SMART_BIM\backend
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
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

### GraphQL Endpoint

#### GraphiQL Interactive UI
```http
GET /api/graphql
```
Browse to `http://localhost:8000/api/graphql` for the interactive GraphiQL explorer.

#### GraphQL Queries
```http
POST /api/graphql
Content-Type: application/json

{
  "query": "{ bsddClasses(limit: 5) { uri name code classType dictionaryUri } }"
}
```

Supported root queries:
- `bsddDictionaries` — list all dictionaries
- `bsddClasses(dictionaryUri, limit, offset)` — list/filter classes
- `bsddClass(uri)` — single class with properties, relations, hierarchy
- `bsddProperties(classUri, limit)` — list properties
- `kgStats` — node/relationship counts

### Additional KG Endpoints

The KG router (`/api/kg`) exposes 34 endpoints beyond the ones documented above:

| Method | Path | Description |
|--------|------|-------------|
| POST | `/suggest-fixes` | AI-powered fix suggestions |
| POST | `/check-compliance` | Compliance checking |
| POST | `/validate-ids-reference` | IDS reference validation |
| GET | `/ids-uri/dictionary` | Resolve dictionary URI |
| GET | `/ids-uri/class` | Resolve class URI |
| GET | `/ids-uri/property` | Resolve property URI |
| GET | `/ids-uri/material` | Resolve material URI |
| POST | `/batch-associate/classes` | Batch class association |
| GET | `/export-ifc/{uri}` | Export as IFC |
| GET | `/export/{uri}` | Generic export |
| POST | `/import/json` | Import JSON data |
| POST | `/import/excel` | Import Excel data |
| POST | `/validate` | Validate data |
| GET | `/classes/{uri}/hierarchy` | Class hierarchy |
| GET | `/classes/{uri}/properties` | Class properties |
| GET | `/classes/{uri}/relations` | Class relations |
| GET | `/properties/{uri}/allowed-values` | Property allowed values |
| GET | `/properties/{uri}/relations` | Property relations |
| GET | `/search/advanced` | Advanced search |
| PUT | `/dictionaries/{uri}/status` | Update dictionary status |
| GET | `/dictionaries/{uri}/versions` | Dictionary versions |
| POST | `/dictionaries/{uri}/translate` | Translate dictionary |
| DELETE | `/dictionaries/{uri}` | Delete dictionary |

Main app also exposes:
- `GET /health/neo4j` — Neo4j connectivity check
- `POST /upload` — Point cloud upload + segmentation
- `POST /chat` — LLM chat with KG context

## Code Structure

```
backend/
├── api/
│   ├── config.py                   # Centralized configuration singleton
│   ├── main.py                     # Main FastAPI application (66 routes)
│   ├── bsdd_client.py             # bSDD API client (GraphQL + REST)
│   ├── bsdd_ingestion.py          # Data ingestion pipeline
│   ├── knowledge_graph_schema.py  # Neo4j schema definition & management
│   ├── kg_routes.py               # FastAPI routes for KG/AI/bSDD (34 endpoints)
│   ├── kg_graphql.py             # Strawberry GraphQL API + GraphiQL UI
│   ├── genai_service.py          # LLM GenAI service (Azure OpenAI / Ollama)
│   ├── basex_client.py           # BaseX XML/JSON database client
│   ├── requirements.txt          # Python dependencies
│   ├── agents/                    # Multi-agent orchestration (planning, query, action)
│   ├── approvals/                 # Approval workflow API & store
│   ├── generative_ui/            # Dynamic UI component generation
│   ├── mcp_host/                 # Model Context Protocol host
│   ├── mcp_servers/              # MCP tool servers (neo4j, bsdd, opensearch, basex)
│   ├── memory/                   # Hybrid memory (short + long term)
│   └── security/                 # Security layer & middleware
├── scripts/
│   └── init_neo4j_schema.py      # Schema initialization & seed data
└── pointnet_s3dis/               # PointNet++ point cloud segmentation
```

## Knowledge Graph Schema

### Node Types (17 labels)

**Building Model Nodes:**
- **IfcElement**: IFC building elements (walls, doors, windows, etc.)
- **IfcSpace**: IFC spatial zones
- **IfcBuilding**: IFC building entities
- **IfcStorey**: IFC building storeys

**Point Cloud Nodes:**
- **PointCloudSegment**: Segmented point cloud data (`segmentId`, `semanticLabel`, `confidence`, `pointCount`)
- **SemanticClass**: Semantic labels (13 classes from PointNet++)

**bSDD Standard Nodes:**
- **BsddDictionary**: Standard dictionaries (IFC, Uniclass, etc.)
- **BsddClass**: Classifications (IfcWall, IfcDoor, etc.)
- **BsddProperty**: Standardized properties (AcousticRating, FireRating, etc.)
- **BsddClassProperty**: Class-specific property bindings
- **BsddUnit**: Units of measurement
- **BsddAllowedValue**: Enumerated allowed values for properties
- **BsddClassRelation**: Inter-class relationships
- **BsddPropertyRelation**: Inter-property relationships

**General Nodes:**
- **Property**: Generic property definitions
- **Classification**: Classification system entries
- **Material**: Material definitions

### Relationships (26 types)

**Spatial:**
- `CONTAINS`: Spatial containment (building → storeys → spaces)
- `LOCATED_IN`: Element location within a space
- `CONNECTED_TO`: Physical connection between elements
- `NEAR`: Proximity relationship (point cloud KNN)

**Classification:**
- `HAS_CLASSIFICATION`: Element has classification
- `CLASSIFIED_AS`: Element classified as type
- `IS_SUBCLASS_OF`: Class inheritance (child → parent)
- `IS_PARENT_OF`: Inverse hierarchy (parent → child)
- `HAS_PARENT_CLASS`: Direct parent class reference

**Property:**
- `HAS_PROPERTY`: Class/element has property
- `HAS_CLASS_PROPERTY`: Class has class-specific property binding
- `REFERENCES_PROPERTY`: Class property references a global property
- `PROPERTY_OF`: Property belongs to element
- `HAS_ALLOWED_VALUE`: Property has enumerated value
- `HAS_UNIT`: Property has unit of measurement

**bSDD:**
- `MAPS_TO_BSDD`: IFC/PC element maps to bSDD class
- `IFC_ENTITY_MAPPING`: IFC entity to bSDD mapping
- `RELATED_TO`: Related classifications
- `EQUIVALENT_TO`: Equivalent classes across dictionaries
- `HAS_CLASS_RELATION`: Class has relation to another class
- `HAS_PROPERTY_RELATION`: Property has relation to another property

**Point Cloud:**
- `SEGMENT_OF`: Segment belongs to scan
- `HAS_SEMANTIC_LABEL`: Segment has semantic class label
- `CORRESPONDS_TO`: Point cloud segment corresponds to IFC element

**Dictionary Organization:**
- `IN_DICTIONARY`: Class/property belongs to dictionary
- `VERSION_OF`: Dictionary version lineage

## Usage Examples

### Example 1: Find Properties for IfcWall
```python
import requests

response = requests.get("http://localhost:8000/api/kg/bsdd/ifc-mappings/IfcWall")
mappings = response.json()

for mapping in mappings["mappings"]:
    print(f"{mapping['name']}: {mapping['definition']}")
```

### Example 2: AI Property Recommendations
```python
import requests

response = requests.post(
    "http://localhost:8000/api/kg/ai/recommend-properties",
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
    "http://localhost:8000/api/kg/ai/semantic-search",
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
        "http://localhost:8000/api/kg/ai/chat",
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
                          neo4j_password="password",
                          database="bimtwin")

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
    status_filter="Preview"  # IFC 4.3 uses status "Preview"
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

## bSDD API Cross-Validation (IFC 4.3)

Validated against live bSDD API on 2026-02-15:

| Field | Live API Value |
|-------|---------------|
| Dictionary Name | **IFC** |
| Dictionary URI | `https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3` |
| Version | **4.3** |
| Status | **Preview** |
| Organization | buildingSMART International |
| Total Classes | **2163** |
| Languages | 17 (EN, DE, ES, JA, NL, NO, PT, RU, ZH, IT, PL, DA, CS, PT-BR, SV, HR, IS) |
| License | CC BY-ND 4.0 |
| Class structure | `Uri`, `Code`, `Name`, `ClassType`, `ReferenceCode`, `ParentClassCode` |
| Property structure | `PropertyCode`, `DataType`, `PropertySet`, `PropertyValueKind`, `AllowedValues` |
| Class hierarchy (e.g. IfcWall) | IfcRoot → IfcObjectDefinition → IfcObject → IfcProduct → IfcElement → IfcBuiltElement → IfcWall |

> **Note**: The seed data in `init_neo4j_schema.py` uses `name="IFC"` and `status="Preview"` to match the live API.

## References

- **bSDD Documentation**: https://github.com/buildingSMART/bSDD
- **bSDD API Swagger**: https://app.swaggerhub.com/apis/buildingSMART/Dictionaries/v1
- **bSDD GraphQL**: https://api.bsdd.buildingsmart.org/graphql
- **bSDD IFC 4.3 Dictionary**: https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3
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
