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
┌─────────────────────────────────────────────────────┐
│          BIMTwinOps Frontend (React + Vite)         │
│  ┌──────────┐ ┌───────────┐ ┌──────────────────┐   │
│  │APS Viewer│ │Point Cloud│ │Knowledge Graph   │   │
│  │40+ Ext.  │ │PointNet AI│ │Browser + AI Chat │   │
│  └──────────┘ └───────────┘ └──────────────────┘   │
└───────────────────────┬─────────────────────────────┘
                        │ REST API
┌───────────────────────┴─────────────────────────────┐
│               Backend Services Layer                │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐  │
│  │FastAPI   │ │APS Node  │ │Knowledge Graph API │  │
│  │Python    │ │Service   │ │bSDD + GenAI        │  │
│  └──────────┘ └──────────┘ └────────────────────┘  │
└───────────┬──────────────┬──────────────┬──────────┘
            │              │              │
      ┌─────▼─────┐  ┌─────▼──────┐  ┌───▼────────┐
      │  Neo4j    │  │   APS      │  │  bSDD      │
      │Knowledge  │  │  Cloud     │  │ GraphQL    │
      │  Graph    │  │  Services  │  │   API      │
      └─────┬─────┘  └────────────┘  └────────────┘
            │ sync           │
      ┌─────▼─────┐    ┌─────▼──────┐
      │  BaseX    │    │Azure OpenAI│
      │Document DB│    │   GPT-4o   │
      │(Native Win)│   └────────────┘
      └───────────┘
```

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
│   ├── pointnet_s3dis/              # PointNet S3DIS (submodule)
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
    ├── start-services.ps1           # Start all services (Windows)
    └── stop-services.ps1            # Stop all services

```

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+** with PyTorch
- **Node.js 18+**
- **Neo4j 5.x** (desktop or cloud)
- **BaseX 10.x** (~8 MB, native Windows, no Docker) - XML/JSON document database
- **Java 11+** (for BaseX runtime)
- **Ollama** (optional, recommended for local GenAI features)
- **Azure OpenAI** account (optional, for Azure-hosted GenAI features)
- **Autodesk Platform Services** credentials (optional)

### 1. Clone Repository

```powershell
git clone --recurse-submodules https://github.com/dparitosh/BIMTwinOps.git
cd BIMTwinOps
```

### Windows: auto-install (recommended)

This repo includes an interactive installer that:
- prompts for configuration (with examples)
- generates `.env` files
- installs Python/Node dependencies

Run from repo root:

- `powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1`

Docs: see `docs/WINDOWS_AUTO_INSTALL.md`.

Notes:

- If a port is already in use (common on dev machines), re-run `scripts/configure.ps1` to pick a free port and restart services.
- The Vite frontend reads `VITE_*` variables at startup, so restart the frontend after changing `pointcloud-frontend/.env`.
- PointNet model weights are not always bundled; when missing, point cloud upload can run in a fallback mode.

### Start/Stop everything on Windows (recommended)

This repo includes convenience scripts that start the dev services in the background and track their PIDs/logs in a local `.pids/` folder.

From the repo root:

- Start all services (Frontend + APS service + API): `powershell -ExecutionPolicy Bypass -File .\scripts\start-services.ps1 -All`
- Stop all services: `powershell -ExecutionPolicy Bypass -File .\scripts\stop-services.ps1 -All -Force`

Notes:

- The scripts start:
  - Frontend: Vite dev server (default port **5173**)
  - APS service: Node dev server (default port **3001**)
  - API: FastAPI via Uvicorn (default port **8000**, or `BACKEND_PORT` from `backend/.env`)
- They **do not** automatically start external dependencies (Neo4j/BaseX/OpenSearch). Start those separately.
- Logs are written to `.pids/*.out.log` and `.pids/*.err.log`.

### 2. Setup Backend (Python + Knowledge Graph)

```powershell
cd backend

# Install dependencies
pip install -r api\requirements.txt
pip install -r pointnet_s3dis\requirements.txt

# Configure environment
copy .env.example .env
# Edit backend\.env with your credentials:
#   - NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
#   - GOOGLE_API_KEY (optional)
#   - LLM_PROVIDER (optional, default: ollama)
#   - OLLAMA_BASE_URL / OLLAMA_MODEL (optional)
#   - BACKEND_PORT (optional, default 8000)

# Initialize knowledge graph schema
python api\knowledge_graph_schema.py

# (Optional) Ingest bSDD data
python api\bsdd_ingestion.py

# Start FastAPI server (default: 8000)
python -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Setup APS Service (Node.js)

```powershell
cd backend\aps-service

# Install dependencies
npm install

# Configure environment
copy .env.example .env
# Edit .env with Autodesk credentials

# Start APS service
npm run dev
```

### 4. Setup Frontend (React)

- `APS_CLIENT_ID`
- `APS_CLIENT_SECRET`
- (optional) `APS_SCOPES`

For 3-legged (ACC/Docs), also set:

- `APS_CALLBACK_URL` (must match your APS app callback URL, e.g. `http://127.0.0.1:3001/aps/oauth/callback`)
- (optional) `APS_OAUTH_SCOPES` (default: `data:read viewables:read`)
- (optional) `APS_CORS_ORIGINS` (default allows Vite dev server)

For demo scalability, Redis can be used to store sessions/tokens:

- `APS_STORE=redis`
- `REDIS_URL=redis://127.0.0.1:6379`

### Run

From `backend/aps-service`:

`npm install`

`npm run dev`

The service will be available at:

- `GET http://127.0.0.1:3001/` (serves the React UI when `FRONTEND_MODE=proxy|static`)
- `GET http://127.0.0.1:3001/health`
- `GET http://127.0.0.1:3001/aps/token`

### Recommended dev topology (single entrypoint)

Run both processes:

1) Start the React dev server:

`cd pointcloud-frontend`

`npm run dev`

2) Start APS service as the entrypoint (proxies UI at `/`):

Create `backend/aps-service/.env` with:

- `FRONTEND_MODE=proxy`
- `FRONTEND_DEV_URL=http://localhost:5173`

Then run:

`cd backend/aps-service`

`npm run dev`

Open the app at `http://127.0.0.1:3001/` (not `:5173`).

### Static mode (single process)

1) Build frontend:

`cd pointcloud-frontend`

`npm run build`

2) Set in `backend/aps-service/.env`:

- `FRONTEND_MODE=static`
- `FRONTEND_DIST_DIR=../../pointcloud-frontend/dist`

3) Start APS service and open `http://127.0.0.1:3001/`.

3-legged OAuth endpoints:

```powershell
cd pointcloud-frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Start All Services (Windows)

Use the convenience scripts:

```powershell
# Start all services
.\scripts\start-services.ps1

# Start specific services
.\scripts\start-services.ps1 -Api      # Backend only
.\scripts\start-services.ps1 -Aps      # APS service only
.\scripts\start-services.ps1 -Frontend  # Frontend only

# Stop all services
.\scripts\stop-services.ps1 -Force
```

### 6. Access the Platform

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8001
- **APS Service**: http://localhost:3001
- **API Docs (Swagger)**: http://localhost:8001/docs
- **GraphQL API**: http://localhost:8001/api/graphql
- **GraphiQL Playground**: http://localhost:8001/api/graphql (interactive UI)
- **Knowledge Graph Health**: http://localhost:8001/api/kg/health

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
