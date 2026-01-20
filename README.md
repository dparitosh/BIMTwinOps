# BIMTwinOps

**Enterprise Digital Twin Operations Platform**  
*Powered by buildingSMART Data Dictionary (bSDD), Neo4j Knowledge Graph, and Azure OpenAI GenAI*

---

## 🚀 Overview

BIMTwinOps is a comprehensive digital twin platform that integrates:
- **[Autodesk Platform Services (APS)](https://aps.autodesk.com/)** - BIM model viewing with 40+ custom extensions
- **[PointNet S3DIS](https://github.com/bhupesh-varma/pointnet_s3dis)** - AI-powered 3D point cloud semantic segmentation
- **[buildingSMART Data Dictionary (bSDD)](https://github.com/buildingSMART/bSDD)** - Standardized building classifications and properties
- **Neo4j Knowledge Graph** - Semantic relationships between IFC models, point clouds, and bSDD standards
- **Azure OpenAI GenAI** - Natural language queries, property recommendations, and intelligent classification

## ✨ Key Features

### 🏗️ BIM & Point Cloud Visualization
- **APS Viewer** with 40+ professional extensions (Edit2D, GoogleMaps, Phasing, PotreeExtension, XLS, etc.)
- **Point Cloud Viewer** with PointNet semantic segmentation (13 classes)
- **3-way synchronization**: Annotation panel ↔ Point cloud ↔ Spatial graph
- **Corporate-grade toolbars** with TCS design system

### 🧠 Knowledge Graph & bSDD Integration
- **100+ standard dictionaries**: IFC, Uniclass, Omniclass, and more
- **Semantic relationships**: IFC elements → bSDD classes → Properties
- **IFC-to-bSDD mappings**: Automatic classification of building elements
- **Neo4j graph database**: Rich spatial and classification relationships
- **GraphQL API**: Flexible, efficient queries with GraphiQL playground

### 🤖 GenAI Capabilities
- **Semantic Search**: Natural language queries over knowledge graph
- **Property Recommendations**: AI-powered suggestions for element properties
- **Classification Mapping**: Intelligent classification to multiple standards
- **Chat Interface**: Conversational access to building data and standards
- **RAG (Retrieval-Augmented Generation)**: Context-aware responses using Neo4j data

### 📊 Advanced Analytics
- **Model Analytics**: Spatial analysis, element counting, relationships
- **Project Scheduling**: Timeline visualization and tracking
- **Graph Visualization**: Force-directed spatial relationships
- **Segment Analytics**: Point cloud statistics and distributions

## 🏛️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│            BIMTwinOps Frontend (React + Vite)               │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────────────┐   │
│  │APS Viewer│ │Point Cloud│ │Knowledge Graph Browser   │   │
│  │40+ Ext.  │ │PointNet AI│ │+ AI Chat + Graph Viz     │   │
│  └──────────┘ └───────────┘ └──────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API / WebSocket
┌───────────────────────┴─────────────────────────────────────┐
│                 Backend Services Layer                       │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────────────┐  │
│  │FastAPI   │ │APS Node  │ │Knowledge Graph API         │  │
│  │:8000     │ │:3001     │ │bSDD + GenAI + GraphQL      │  │
│  └──────────┘ └──────────┘ └────────────────────────────┘  │
└───────┬──────────────┬──────────────┬──────────────┬───────┘
        │              │              │              │
  ┌─────▼─────┐  ┌─────▼──────┐  ┌───▼────────┐ ┌───▼────────┐
  │  Neo4j    │  │   APS      │  │  bSDD      │ │   BaseX    │
  │Knowledge  │  │  Cloud     │  │ GraphQL    │ │   XML DB   │
  │Graph:7687 │  │  Services  │  │   API      │ │   :8080    │
  └───────────┘  └────────────┘  └────────────┘ └────────────┘
        │                              │
  ┌─────▼─────┐                  ┌─────▼──────┐
  │  Ollama   │                  │Azure OpenAI│
  │Local LLM  │                  │   GPT-4o   │
  │  :11434   │                  └────────────┘
  └───────────┘
```

### Service Ports

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Frontend | 5173 | HTTP | React + Vite dev server |
| Backend API | 8000 | HTTP | FastAPI REST/GraphQL |
| APS Service | 3001 | HTTP | Autodesk OAuth proxy |
| Neo4j | 7687 | Bolt | Knowledge graph DB |
| Neo4j Browser | 7474 | HTTP | Neo4j web UI |
| Ollama | 11434 | HTTP | Local LLM API |
| BaseX | 8080 | HTTP | XML/XQuery DB + Admin |

## 📁 Project Structure
```
BIMTwinOps/
├── backend/
│   ├── api/                         # FastAPI backend
│   │   ├── main.py                  # Main API + routes
│   │   ├── bsdd_client.py          # bSDD API client (GraphQL/REST)
│   │   ├── knowledge_graph_schema.py # Neo4j schema manager
│   │   ├── bsdd_ingestion.py       # Data ingestion pipeline
│   │   ├── genai_service.py        # Azure OpenAI GenAI service
│   │   ├── kg_routes.py            # Knowledge Graph API routes
│   │   └── requirements.txt         # Python dependencies
│   ├── pointnet_s3dis/              # PointNet S3DIS semantic segmentation
│   │   ├── src/models/              # PyTorch PointNet
│   │   └── online_segmentation.py   # Inference + Neo4j
│   ├── aps-service/                 # Node.js APS service
│   │   └── src/server.js            # OAuth, OSS, Model Derivative
│   └── scripts/                     # kNN computation scripts
├── pointcloud-frontend/             # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx                  # Main app (4 tabs)
│   │   └── components/
│   │       ├── ApsViewer.jsx        # APS Viewer with extensions
│   │       ├── PointCloudViewer.jsx # Three.js point cloud
│   │       ├── GraphViewer.jsx      # Force-directed graph
│   │       ├── AnnotationPanel.jsx  # Hierarchical tree
│   │       └── [30+ extension components]
│   └── public/extensions/           # 40+ APS viewer extensions
├── docs/
│   ├── BSDD_INTEGRATION.md         # bSDD integration guide
│   └── MODULE_INTEGRATION.md        # Architecture docs
└── scripts/
    ├── setup.ps1                    # Install dependencies (run once)
    ├── deploy.ps1                   # Start services with validation
    ├── stop-services.ps1            # Stop all services
    └── configure.ps1                # Interactive port/credential config

```

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **Git** (optional, for cloning)
- **Neo4j 5.x** (desktop or cloud)
- **Ollama** (optional, for local GenAI)

### Windows Installation (2 commands)

```powershell
# 1. Clone the repository (or download ZIP)
git clone https://github.com/dparitosh/BIMTwinOps.git
cd BIMTwinOps

# 2. Run setup (shows all output, validates everything)
.\scripts\setup.ps1

# 3. Deploy services (starts all, validates endpoints, opens browser)
.\scripts\deploy.ps1
```

That's it! The scripts show every step and confirm endpoints are working.

### Script Reference

| Script | Purpose |
|--------|---------|
| `setup.ps1` | One-time install: venv, pip, npm, .env files |
| `deploy.ps1` | Start services + validate endpoints |
| `stop-services.ps1 -All -Force` | Stop all running services |
| `configure.ps1` | Interactive wizard to change ports/credentials |

### Troubleshooting

```powershell
# View backend errors
Get-Content .\.pids\api.err.log -Tail 50

# Check what's running on a port
Get-NetTCPConnection -LocalPort 8000 -State Listen

# Reconfigure ports if conflicts
.\scripts\configure.ps1
.\scripts\deploy.ps1
```

### Manual Setup (alternative)

If you prefer manual control:

```powershell
# Backend
cd backend
python -m venv ..\.venv
..\.venv\Scripts\activate
pip install -r api\requirements.txt
copy .env.example .env
# Edit .env with Neo4j credentials
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000

# Frontend (new terminal)
cd pointcloud-frontend
npm install
copy .env.example .env
npm run dev
```

### 3. Setup APS Service (optional)

Only needed if using Autodesk Platform Services:

```powershell
cd backend\aps-service
npm install
copy .env.example .env
# Edit .env: APS_CLIENT_ID, APS_CLIENT_SECRET
npm run dev
```

## 🔗 Service URLs

After running `.\scripts\deploy.ps1`:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:5173 |
| **Backend API** | http://localhost:8000 |
| **API Docs (Swagger)** | http://localhost:8000/docs |
| **GraphQL Playground** | http://localhost:8000/api/graphql |
| **APS Service** | http://localhost:3001 |

## 📚 Core Modules

### 1. 🧬 PointNet S3DIS Semantic Segmentation

**13 Semantic Classes**: ceiling, floor, wall, beam, column, window, door, chair, table, bookcase, sofa, board, clutter

**Features**:
- Multi-pass inference with 4096-point blocks
- Majority voting for block overlap handling
- Neo4j integration for segment storage
- Spatial properties: centroid, bounding box, point count

### 2. 📖 buildingSMART Data Dictionary (bSDD)

**100+ Standard Dictionaries**:
- **IFC** 4.3, 4.0, 2x3
- **Uniclass** 2015
- **Omniclass**
- **NL-SfB**
- And many more...

**Capabilities**:
- Class definitions and hierarchies
- Property specifications with data types
- Units and allowed values
- IFC entity mappings
- Multi-language support

### 3. 🕸️ Neo4j Knowledge Graph

**Node Types**:
- `BsddDictionary` - Standard dictionaries
- `BsddClass` - Classifications (walls, doors, etc.)
- `BsddProperty` - Standardized properties
- `IfcElement` - IFC building elements
- `PointCloudSegment` - Segmented point cloud data
- `SemanticClass` - Semantic labels

**Relationships**:
- `IN_DICTIONARY` - Class belongs to dictionary
- `HAS_PROPERTY` - Class has property
- `MAPS_TO_BSDD` - IFC/PC element maps to bSDD class
- `IS_PARENT_OF` / `IS_SUBCLASS_OF` - Hierarchies
- `RELATED_TO` - Related classifications
- `CORRESPONDS_TO` - IFC ↔ Point Cloud correspondence

### 3.5 📦 BaseX Document Database (Hybrid Architecture)

**Why Hybrid (BaseX + Neo4j)?**

We use a **hybrid database architecture** to leverage the strengths of both systems:

**BaseX (Native Windows, No Docker)**:
- **Document Storage**: Stores original bSDD JSON/XML files as-is
- **Version Management**: Preserves all historical versions immutably
- **Audit Trail**: Tracks all imports and changes with timestamps
- **XQuery Processing**: Transforms and validates XML/JSON before Neo4j ingestion
- **Lightweight**: ~100-200 MB RAM footprint vs Neo4j's 500 MB-1 GB
- **Port**: HTTP server on 8984, Web UI at http://localhost:8984/dba

**Neo4j (Graph Database)**:
- **Semantic Relationships**: Optimized for complex graph traversals
- **Real-time Queries**: Fast pattern matching and pathfinding
- **Spatial Queries**: Point cloud and geometric relationships
- **Cypher Queries**: Expressive graph query language

**Data Flow**:
```
bSDD API → Import → BaseX (store original) → Neo4j (process graph) → Keep synced
                         ↓                          ↓
                   Original Files              Graph Relationships
                   Version History             Real-time Queries
                   Audit Trail                 Semantic Search
```

**Synchronization**: Unidirectional (BaseX → Neo4j) ensures BaseX remains the source of truth for original documents while Neo4j serves optimized graph queries.

### 4. 🤖 Azure OpenAI GenAI

**RAG-Powered Features**:
1. **Semantic Search**: Natural language → Cypher queries
2. **Property Recommendations**: AI suggests standardized properties
3. **Classification Mapping**: Intelligent element classification
4. **Chat Interface**: Conversational knowledge exploration

**Models Supported**:
- GPT-4o (recommended)
- GPT-4 Turbo
- GPT-3.5 Turbo

### 5. 🎨 APS Viewer Extensions (40+)

**Professional Extensions**:
- **Edit2D**: 2D markup and annotations
- **GoogleMapsLocator**: Geolocation integration
- **PhasingExtension**: Construction phasing
- **PotreeExtension**: Point cloud visualization
- **XLSExtension**: Excel data integration
- **DrawToolExtension**: Drawing tools
- **TransformationExtension**: Model transformations
- And 33 more...

## 📡 API Endpoints

### REST APIs

#### bSDD Endpoints
```http
GET /api/kg/bsdd/dictionaries
POST /api/kg/bsdd/search
GET /api/kg/bsdd/class/{class_uri}
GET /api/kg/bsdd/ifc-mappings/{ifc_entity}
```

#### GenAI Endpoints
```http
POST /api/kg/ai/semantic-search
POST /api/kg/ai/recommend-properties
POST /api/kg/ai/suggest-classifications
POST /api/kg/ai/chat
```

#### Graph Query Endpoints
```http
GET /api/kg/graph/stats
POST /api/kg/graph/cypher
GET /api/kg/health
```

### GraphQL API

**Endpoint**: `http://localhost:8001/api/graphql`  
**Interactive UI**: GraphiQL playground at same URL

**Query Examples**:
```graphql
# Get bSDD class with nested properties
{
  bsddClass(uri: "https://identifier.buildingsmart.org/uri/buildingsmart/ifc/4.3/class/IfcWall") {
    uri
    name
    definition
    properties {
      code
      name
      dataType
      units
    }
    relations {
      relationType
      relatedClassName
    }
  }
}

# Get IFC element with bSDD mappings and point cloud segments
{
  ifcElement(globalId: "2O2Fr$t4X7Zf8NOew3FLZA") {
    globalId
    ifcType
    name
    bsddMappings {
      uri
      name
      properties {
        code
        name
      }
    }
    pointCloudSegments {
      segmentId
      semanticLabel
    }
  }
}

# Universal search
{
  search(queryText: "thermal") {
    resultType
    uri
    name
    description
  }
}
```

**See** [GRAPHQL_API_GUIDE.md](docs/GRAPHQL_API_GUIDE.md) for comprehensive GraphQL documentation.

### Point Cloud APIs
```http
POST /upload                    # Upload .npy point cloud
POST /chat                      # Natural language query
GET /health/neo4j              # Neo4j health check
```

### APS APIs
```http
GET /aps/token                 # Get 2-legged OAuth token
GET /aps/oauth/login           # Start 3-legged OAuth
GET /aps/docs/projects         # Get ACC projects
GET /aps/oss/buckets           # Get OSS buckets
POST /aps/oss/upload           # Upload to OSS
POST /aps/md/translate         # Translate model
```

## 💡 Usage Examples

### Example 1: Semantic Search

```javascript
const response = await fetch('http://localhost:8001/api/kg/ai/semantic-search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: "Find all properties for load-bearing walls",
    context_type: "bsdd",
    limit: 10
  })
});

const results = await response.json();
console.log(results.summary);
```

### Example 2: Property Recommendations

```javascript
const response = await fetch('http://localhost:8001/api/kg/ai/recommend-properties', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    element_type: "IfcWindow",
    context: {
      phase: "construction",
      region: "EU"
    }
  })
});

const { properties } = await response.json();
properties.forEach(prop => {
  console.log(`✓ ${prop.name}: ${prop.why_needed}`);
});
```

### Example 3: IFC-to-bSDD Mapping

```javascript
const response = await fetch('http://localhost:8001/api/kg/bsdd/ifc-mappings/IfcWall');
const { mappings } = await response.json();

mappings.forEach(mapping => {
  console.log(`${mapping.name} (${mapping.code})`);
  console.log(`  URI: ${mapping.uri}`);
  console.log(`  Type: ${mapping.classType}`);
});
```

### Example 4: Chat with Knowledge Graph

```javascript
const conversation = [];
const userMessage = "What thermal properties should I capture for exterior walls?";

const response = await fetch('http://localhost:8001/api/kg/ai/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: userMessage,
    conversation_history: conversation
  })
});

const { response: aiResponse } = await response.json();
console.log(`AI: ${aiResponse}`);
```

## 🎯 Use Cases

### 1. **Standardized BIM Property Capture**
- Upload IFC model to APS Viewer
- AI recommends bSDD-compliant properties
- Export standardized property sets

### 2. **Point Cloud to BIM Classification**
- Upload point cloud (.npy)
- PointNet segments into semantic classes
- AI maps segments to bSDD classifications
- Export as classified IFC

### 3. **Intelligent Data Quality Checks**
- Query knowledge graph for missing properties
- AI suggests data enrichments
- Validate against bSDD standards
- Generate IDS (Information Delivery Specification)

### 4. **Multi-Standard Classification**
- Element description → AI suggestions
- Map to IFC, Uniclass, Omniclass simultaneously
- Export classification mappings
- Ensure interoperability

### 5. **Natural Language BIM Queries**
- "Show me all structural elements on floor 2"
- "Find windows with U-value < 1.5"
- "List fire-rated walls and their properties"
- AI translates to Cypher, executes, and explains

## 🔒 Security Best Practices

1. **API Authentication**: Add JWT/OAuth to `/api/kg/graph/cypher`
2. **Input Validation**: Sanitize all user inputs
3. **Rate Limiting**: Implement rate limits on GenAI endpoints
4. **Environment Variables**: Never commit `.env` files
5. **CORS Configuration**: Restrict origins in production
6. **Cypher Injection Prevention**: Validate queries before execution

## 📈 Performance Optimization

1. **Caching**: bSDD data caching (24h TTL)
2. **Batch Processing**: Bulk property lookups
3. **Indexes**: Neo4j indexes on frequently queried properties
4. **Connection Pooling**: Neo4j and HTTP connection pools
5. **Lazy Loading**: Load knowledge graph data on-demand
6. **Vector Embeddings**: For fast semantic similarity (future)

## 🔄 Data Flow

### Upload & Segmentation Flow

```
User uploads .npy
    ↓
PointNet processes (multi-pass)
    ↓
Segments written to Neo4j
    ↓
AI maps to bSDD classes
    ↓
Knowledge graph enriched
    ↓
UI updates with 3-way sync
```

### Query Flow (RAG Pattern)

```
User asks natural language question
    ↓
GenAI converts to Cypher query
    ↓
Neo4j retrieves relevant data
    ↓
GenAI synthesizes answer with context
    ↓
Response with data + reasoning
```

## 🛠️ Development

### Running Tests

```powershell
# Backend tests
cd backend\api
pytest

# Frontend tests
cd pointcloud-frontend
npm test
```

### Code Quality

```powershell
# Python linting
flake8 backend/api
black backend/api

# JavaScript linting
cd pointcloud-frontend
npm run lint
npm run format
```

### Building for Production

```powershell
# Build frontend
cd pointcloud-frontend
npm run build

# Build Docker images
docker-compose build
docker-compose up -d
```

## 📦 Deployment

### Docker Deployment

```yaml
# docker-compose.yml
version: '3.8'
services:
  neo4j:
    image: neo4j:5.25.1
    environment:
      NEO4J_AUTH: neo4j/password
    ports:
      - "7687:7687"
      - "7474:7474"

  backend:
    build: ./backend/api
    ports:
      - "8001:8001"
    environment:
      NEO4J_URI: bolt://neo4j:7687
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}

  aps-service:
    build: ./backend/aps-service
    ports:
      - "3001:3001"
    environment:
      APS_CLIENT_ID: ${APS_CLIENT_ID}
      APS_CLIENT_SECRET: ${APS_CLIENT_SECRET}

  frontend:
    build: ./pointcloud-frontend
    ports:
      - "80:80"
```

### Azure Deployment

1. **Azure Container Apps** for microservices
2. **Azure Cosmos DB (Gremlin)** or **Neo4j Aura** for graph
3. **Azure OpenAI** for GenAI
4. **Azure Storage** for point cloud files
5. **Azure App Service** for frontend

## 📖 Documentation

- **[bSDD Integration Guide](docs/BSDD_INTEGRATION.md)** - Complete bSDD setup, API usage, and knowledge graph
- **[GraphQL API Guide](docs/GRAPHQL_API_GUIDE.md)** - Comprehensive GraphQL queries, mutations, and examples
- **[Component Architecture](docs/COMPONENT_ARCHITECTURE.md)** - Detailed component diagrams, data flows, and interactions 🆕
- **[bSDD UI/UX Analysis](docs/BSDD_UI_UX_ANALYSIS.md)** - Official bSDD interface patterns and design system
- **[Task Tracker](docs/TASK_TRACKER.md)** - Project roadmap, 56 tasks, sprint planning
- **[bSDD API Reference](docs/BSDD_API_REFERENCE.md)** - Quick reference for bSDD REST and GraphQL endpoints
- **[Module Integration](docs/MODULE_INTEGRATION.md)** - Architecture deep dive and component integration
- **[API Documentation](http://localhost:8001/docs)** - Interactive Swagger API docs (when running)
- **[GraphiQL Playground](http://localhost:8001/api/graphql)** - Interactive GraphQL query builder (when running)

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

- **buildingSMART International** for bSDD
- **Autodesk** for APS/Forge platform
- **Neo4j** for graph database
- **Microsoft** for Azure OpenAI
- **PyTorch community** for PointNet implementation

## 📞 Support

- **Issues**: https://github.com/dparitosh/BIMTwinOps/issues
- **Email**: support@bimtwinops.com
- **bSDD Forums**: https://forums.buildingsmart.org/

---

**BIMTwinOps** - Enterprise Digital Twin Operations Platform  
*Bridging BIM, Point Clouds, and Standardized Building Data with AI*

🏗️ Built with ♥ for the AEC industry
- `GET http://127.0.0.1:3001/aps/oauth/callback`
- `GET http://127.0.0.1:3001/aps/oauth/status`
- `GET http://127.0.0.1:3001/aps/oauth/token`
- `POST http://127.0.0.1:3001/aps/oauth/logout`

ACC Docs (3-legged) endpoints:

- `GET http://127.0.0.1:3001/acc/hubs`
- `GET http://127.0.0.1:3001/acc/projects?hubId=...`
- `GET http://127.0.0.1:3001/acc/top-folders?hubId=...&projectId=...`
- `GET http://127.0.0.1:3001/acc/folder-contents?projectId=...&folderId=...`
- `GET http://127.0.0.1:3001/acc/item-versions?projectId=...&itemId=...`
- `GET http://127.0.0.1:3001/acc/version?projectId=...&versionId=...`

OSS + Model Derivative (2-legged) endpoints:

- `POST http://127.0.0.1:3001/oss/upload` (multipart form field `file`, optional `bucketKey`, `objectKey`)
- `POST http://127.0.0.1:3001/md/translate` (json: `{ "urn": "...", "force": false }`)
- `GET  http://127.0.0.1:3001/md/manifest?urn=...`

If you want the frontend to call a different URL, set `VITE_APS_API_URL` when running Vite.
