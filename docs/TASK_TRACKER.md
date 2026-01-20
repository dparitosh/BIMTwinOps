# SMART BIM - Task Tracker

**Project**: bSDD Knowledge Graph Integration + Intelligent App Architecture  
**Architecture Standard**: 2026 Intelligent App (MCP + LangGraph + Agentic)  
**Last Updated**: January 20, 2026  
**Current Sprint**: Backend Data Model Enhancement + Agentic Architecture Foundation (+ PointCloud UX stabilization)

---

## Architecture Vision

SMART BIM is evolving from a traditional CRUD application to an **Intelligent Agentic System** following the **2026 Intelligent App Standard**:

- **Agentic Core**: LangGraph-based orchestration with AI agents acting as "Productivity Partners"
- **MCP Integration**: Standardized Model Context Protocol for all tool interactions
- **Hybrid Memory**: OpenSearch for semantic search + Neo4j for graph relationships
- **Generative UI**: Next.js components that render based on agent outputs
- **HITL Patterns**: Human-in-the-loop approval for critical operations

**Key Principles**:
1. **Reasoning ≠ Execution**: AI agents reason, MCP servers execute
2. **Declarative State Machines**: LangGraph defines deterministic flows for non-deterministic LLMs
3. **Memory-Augmented Generation**: RAG pattern with OpenSearch vector embeddings
4. **Safety by Design**: OWASP LLM08 compliance with mandatory approval gates

---

## Legend

- 🟢 **Priority 1**: Critical (Week 1-2)
- 🟡 **Priority 2**: High (Week 3-4)
- 🟠 **Priority 3**: Medium (Week 5-6)
- 🔵 **Priority 4**: Low (Week 7-8)
- ⚪ **Priority 5**: Future (Week 9+)

**Status**:
- ✅ Complete
- 🔄 In Progress
- ⏳ Pending
- ⚠️ Blocked
- 🔴 Critical Issue

---

## Sprint Overview

> **Audit note (Jan 16, 2026):** This tracker is periodically reconciled against the repository so statuses reflect what exists in code vs what is still planned.
> Nothing is removed from the roadmap—items are only re-labeled (✅/🔄/⏳) and file paths are corrected when the repo structure changes.

### Next up (highest-impact pending)
1. **HITL / Executor agent**: integrate approval gates deeper into workflows and wire executor into LangGraph + GenUI.
2. **OpenSearch embeddings**: generate embeddings inside the OpenSearch MCP server (or via a memory agent) instead of requiring callers to supply vectors.
3. **Wire memory into orchestration**: turn `backend/api/memory/hybrid_memory.py` into a first-class agent node and integrate into LangGraph flow.
4. **Planner Agent node**: integrate as a first-class LangGraph node.

### Completed ✅
- [x] bSDD API Client (GraphQL + REST)
- [x] Neo4j Knowledge Graph Schema (Initial)
- [x] Data Ingestion Pipeline (Initial)
- [x] GenAI Service Integration (Azure OpenAI)
- [x] REST API Endpoints (14 endpoints)
- [x] GraphQL API Layer (10+ queries, 2 mutations)
- [x] Documentation (4 comprehensive guides)
- [x] UI/UX Analysis of Official bSDD Interfaces
- [x] Intelligent App Architecture Review (MCP + LangGraph)

### Completed (Jan 16, 2026 — App Maintenance) ✅
- [x] PointCloud: single-click segment selection (drag-safe)
- [x] PointCloud: graph → viewer selection propagation (robust highlight fallback)
- [x] GraphViewer: smaller nodes + blue-hue background styling

### Completed (Jan 17, 2026 — Architecture Fixes) ✅
- [x] GraphQL: Fixed `GraphStats` field resolution (Dict[str, int] → List[NodeTypeCount])
- [x] Topic Guardrails: Added BIM/construction domain validation to router (67 keywords + off-topic patterns)
- [x] Bulk Thresholds: Verified BULK_UPDATE > 5 mandatory approval in action_agent.py
- [x] GraphQL bSDD types: Added BsddAllowedValue, BsddUnit, BsddClassProperty types with resolvers

### Completed (Jan 19, 2026 — Agent Orchestration) ✅
- [x] LangGraph: Wired executor_agent as first-class node with conditional routing
- [x] LangGraph: Wired planning_agent as first-class node (not placeholder)
- [x] GenUI: Added APPROVAL component type for HITL dialogs (create_approval method)
- [x] Security: Relaxed Cypher injection patterns to allow natural language
- [x] Audit: Fixed planning_agent audit logger calls (log_agent_action signature)
- [x] MCP Host: Added NEO4J_PASSWORD environment variable passthrough
- [x] MCP Host: Fixed session lifecycle (fresh session per tool call, no ClosedResourceError)
- [x] Schema: Created init_neo4j_schema.py with --seed flag for sample data
- [x] Tests: All 4 agent flow tests passing (query, create, delete, planning)
- [x] Neo4j MCP: End-to-end tool calls working (cypher_query, create_nodes)
- [x] Setup: Verified bootstrap.ps1 and start-all.ps1 with documentation updates
- [x] Ingestion: Validated PointNet extraction and Neo4j writing pipeline

### Completed (Jan 20, 2026 — Infrastructure & Visualization) ✅
- [x] BaseX: Auto-installation script (scripts/start-basex.ps1) with Java detection
- [x] BaseX: Stop script (scripts/stop-basex.ps1)
- [x] APS Service: Dedicated start-aps.ps1 script with credential validation
- [x] start-all.ps1: Added external service checks (Neo4j, Ollama, BaseX, Azure OpenAI)
- [x] start-all.ps1: Added APS service startup and port management
- [x] start-all.ps1: Added -SkipChecks parameter for faster startup
- [x] Ollama: Added OLLAMA_BASE_URL to backend/.env configuration
- [x] PointCloud: Implemented fallback_spatial_segmentation() for missing PointNet weights
- [x] PointCloud: Height-based (floor/ceiling) + XY-grid spatial clustering (9 labels vs 1)
- [x] KG Schema: Fixed syntax errors in knowledge_graph_schema.py
- [x] KG Schema: Added create_bsdd_class_property_node() method
- [x] Documentation: Updated SETUP.md with BaseX installation guide
- [x] Documentation: Updated README.md architecture diagram with all services/ports
- [x] Neo4j: Verified connectivity (bolt://localhost:7687)

### In Progress
- 🔄 P0.3 OpenSearch Hybrid Memory: MCP Server exists, `hybrid_memory.py` implemented, but `memory_agent.py` missing.
- 🔄 P0.4 GenUI: `ui_generator.py` and `AgentComponentRenderer.jsx` exist. Next.js migration skipped (sticking with Vite).

### Pending
*See detailed breakdown below*

### Known issues / blockers
- ⚠️ OpenSearch: Requires Docker setup (deferred)

---

## 🔴 Priority 0: Intelligent App Foundation (Week 0 - Architecture)

### P0.1: MCP (Model Context Protocol) Infrastructure
**Estimated Time**: 12 hours  
**Dependencies**: None  
**Assignee**: TBD  
**ADR**: ADR-001 (Use of Model Context Protocol)

- [x] **P0.1.1** - Set up MCP Host (Orchestrator)
  - [x] Install MCP Python SDK (`mcp` package)
  - [x] Create `backend/api/mcp_host/mcp_host.py` orchestrator
  - [x] Configure MCP client connections (stdio, HTTP)
  - [x] Add connection pooling and retry logic
  - **Status**: ✅ Complete
  - **Time**: 3h
  - **Files**: `backend/api/mcp_host/mcp_host.py`, `backend/api/mcp_host/__init__.py`

- [ ] **P0.1.2** - Create MCP Server: Neo4j
  - [x] Create `backend/api/mcp_servers/neo4j/` directory
  - [x] Implement `mcp-server-neo4j` with tools:
    - [x] `cypher_query` - Execute read queries
    - [x] `create_nodes` - Create graph nodes
    - [x] `create_relationships` - Create relationships
    - [x] `update_properties` - Update node/relationship properties
  - [x] Define JSON schemas for each tool
  - [x] Add authentication (Neo4j credentials)
  - [ ] Test end-to-end with MCP Inspector (optional)
  - **Status**: 🔄 In Progress (implemented; awaiting environment + end-to-end tool validation)
  - **Time**: 4h
  - **Files**: `backend/api/mcp_servers/neo4j/server.py`, `backend/api/mcp_servers/neo4j/test_server.py`

- [ ] **P0.1.3** - Create MCP Server: BaseX
  - [x] Create `backend/api/mcp_servers/basex/` directory
  - [x] Implement `mcp-server-basex` with tools:
    - [x] `store_document` - Store original JSON/XML
    - [x] `get_versions` - Retrieve version history
    - [x] `query_xquery` - Execute XQuery transformations
    - [x] `get_audit_trail` - Retrieve change history
  - [x] Define JSON schemas for each tool
  - [x] Add BaseX authentication (credentials)
  - [ ] Test end-to-end with MCP Inspector (requires BaseX running)
  - **Status**: 🔄 In Progress (implemented; requires BaseX runtime validation)
  - **Time**: 3h
  - **Files**: `backend/api/mcp_servers/basex/server.py`, `backend/api/mcp_servers/basex/test_server.py`

- [ ] **P0.1.4** - Create MCP Server: bSDD API
  - [x] Create `backend/api/mcp_servers/bsdd/` directory
  - [x] Wrap existing `backend/api/bsdd_client.py` as MCP server
  - [x] Implement tools:
    - [x] `search_dictionaries` - Search bSDD
    - [x] `get_dictionary` - Fetch full dictionary
    - [x] `get_classes` - Fetch classes
    - [x] `get_properties` - Fetch properties
  - [x] Add rate limiting via MCP
  - [ ] Test end-to-end with MCP Inspector (optional)
  - **Status**: 🔄 In Progress (implemented; awaiting end-to-end validation)
  - **Time**: 2h
  - **Files**: `backend/api/mcp_servers/bsdd/server.py`

### P0.2: LangGraph Agent Orchestration
**Estimated Time**: 16 hours  
**Dependencies**: P0.1  
**Assignee**: TBD  
**ADR**: ADR-002 (LangGraph for Orchestration)

- [ ] **P0.2.1** - Set up LangGraph State Machine
  - [x] Install LangGraph (`langgraph` package)
  - [x] Create `backend/api/agents/agent_orchestrator.py`
  - [x] Define state schema (AgentState TypedDict)
  - [x] Create base graph with __start__ and __end__ nodes
  - [ ] Add Redis for state persistence (optional; memory saver fallback already works)
  - **Status**: 🔄 In Progress (state machine implemented; Redis persistence optional)
  - **Time**: 3h

- [ ] **P0.2.2** - Implement Router Agent
  - [x] Implement router node in `backend/api/agents/agent_orchestrator.py` (no separate file)
  - [x] Implement intent classification:
    - [x] Query Intent (search, retrieve)
    - [x] Action Intent (add, update, delete)
    - [x] Planning Intent (complex multi-step)
  - [x] Add topic guardrails for BIM/construction domain validation (67 keywords + off-topic patterns)
  - [x] Add safety guardrails (injection patterns, PII detection, off-topic rejection)
  - [x] Add routing logic to LangGraph
  - **Status**: ✅ Complete
  - **Time**: 4h

- [ ] **P0.2.3** - Implement Planner Agent
  - [x] Create `backend/api/agents/planning_agent.py`
  - [x] Implement task decomposition (rule-based; can be upgraded with LLM)
  - [ ] Add plan validation logic (beyond basic safety checks)
  - [ ] Integrate with MCP tool discovery (deeper dynamic tool selection)
  - [x] Add to LangGraph state machine as a first-class node
  - **Status**: ✅ Complete (basic integration done; advanced features optional)
  - **Time**: 4h

- [ ] **P0.2.4** - Implement Executor Agent
  - [x] Create `backend/api/agents/executor_agent.py`
  - [x] Implement MCP tool invocation (executor executes plans; action agent plans)
  - [x] Add HITL breakpoint for destructive ops (queue + approve/reject)
  - [x] Add bulk thresholds:
    - BULK_UPDATE > 5 items (mandatory approval)
    - CREATE > 10 items (warning only)
  - [x] Add to LangGraph state machine
  - [x] Add approval API endpoints:
    - `GET /api/approvals/pending`
    - `POST /api/approvals/{id}/approve`
    - `POST /api/approvals/{id}/reject`
  - [x] Add GenUI APPROVAL component for HITL dialogs
  - **Status**: ✅ Complete
  - **Time**: 5h
  - **Files**: `backend/api/agents/executor_agent.py`, `backend/api/approvals/store.py`, `backend/api/approvals/api.py`, `backend/api/agents/action_agent.py`, `backend/api/main.py`, `backend/api/generative_ui/ui_generator.py`

### P0.3: OpenSearch Hybrid Memory
**Estimated Time**: 10 hours  
**Dependencies**: None  
**Assignee**: TBD  
**ADR**: ADR-003 (OpenSearch for Memory)

- [ ] **P0.3.1** - Set up OpenSearch Instance
  - [ ] Install OpenSearch (Docker or AWS managed)
  - [ ] Configure k-NN plugin for vector search
  - [ ] Create indices:
    - `bsdd_tasks_vectors` (embeddings)
    - `bsdd_context_vectors` (conversation history)
  - [ ] Set up index mappings (vector + metadata)
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P0.3.2** - Create MCP Server: OpenSearch
  - [x] Create `backend/api/mcp_servers/opensearch/` directory
  - [x] Implement `mcp-server-opensearch` with tools:
    - [x] `search_semantic` - Text search (BM25 multi-match)
    - [x] `store_document` - Index documents (optional embedding field)
    - [x] `create_index` - Create index with vector mapping
    - [x] `get_document` - Retrieve document by ID
  - [ ] Add embeddings generation inside MCP server (currently accepts embedding if provided)
  - [ ] Test end-to-end with MCP Inspector (requires OpenSearch running)
  - **Status**: 🔄 In Progress (implemented; embeddings + runtime validation pending)
  - **Time**: 4h
  - **Files**: `backend/api/mcp_servers/opensearch/server.py`

- [ ] **P0.3.3** - Implement Memory Agent
  - [ ] Create `backend/api/agents/memory_agent.py`
  - [ ] Implement semantic recall logic
  - [ ] Add context window management (last N turns)
  - [ ] Add PII redaction (Output Guardrails)
  - [ ] Integrate with LangGraph
  - **Status**: ⏳ Pending (memory module exists at `backend/api/memory/hybrid_memory.py` but not wired as an agent)
  - **Time**: 4h

### P0.4: Generative UI (GenUI) Foundation
**Estimated Time**: 8 hours  
**Dependencies**: P0.2  
**Assignee**: TBD

- [ ] **P0.4.1** - Set up Next.js App Router
  - [ ] Migrate frontend to Next.js 15 (optional, or keep Vite)
  - [ ] Create `/app/chat` route for AI assistant
  - [ ] Add streaming response support (Server-Sent Events)
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [x] **P0.4.2** - Create Generative UI Components
  - [x] Create `<TaskList />` component (rendered by agent)
  - [x] Create `<PropertyRecommendation />` component
  - [x] Create `<ApprovalGate />` component (HITL)
  - [x] Create `<GraphVisualization />` component
  - [x] Add component registry for agent selection
  - **Status**: ✅ Complete (`pointcloud-frontend/src/components/AgentComponentRenderer.jsx`)
  - **Time**: 4h

- [x] **P0.4.3** - Implement Agent Response Renderer
  - [x] Create `renderAgentResponse()` utility
  - [x] Parse agent output (text + component metadata)
  - [x] Dynamically render React components
  - [x] Add fallback to plain text
  - **Status**: ✅ Complete (`AgentComponentRenderer.jsx` and `AgentInterface.jsx`)
  - **Time**: 2h

### P0.5: Security & Governance
**Estimated Time**: 6 hours  
**Dependencies**: P0.2, P0.3  
**Assignee**: TBD

- [ ] **P0.5.1** - Implement Row-Level Security (RLS)
  - [ ] Add `user_id` filtering to all MCP server queries
  - [ ] Enforce RLS at Neo4j level (Cypher WHERE clauses)
  - [ ] Enforce RLS at OpenSearch level (filter context)
  - [ ] Add JWT token validation
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P0.5.2** - Add OWASP LLM08 Safeguards
  - [ ] Implement mandatory HITL for destructive operations
  - [ ] Add operation logging (audit trail in BaseX)
  - [ ] Add rate limiting per user (10 req/min)
  - [ ] Add prompt injection detection (NeMo Guardrails)
  - **Status**: ⏳ Pending
  - **Time**: 3h

---

## 🟢 Priority 1: Backend Data Model Enhancement (Week 1-2)

### P1.1: Add Missing Node Types
**Estimated Time**: 8 hours  
**Dependencies**: None  
**Assignee**: TBD

- [x] **P1.1.1** - Add `BSDDClassProperty` node type
  - [x] Define schema in `knowledge_graph_schema.py`
  - [x] Add constraints and indexes
  - [x] Update documentation
  - **Status**: ✅ Complete (`create_bsdd_class_property_node`)
  - **Time**: 2h

- [x] **P1.1.2** - Add `BSDDAllowedValue` node type
  - [x] Define schema in `knowledge_graph_schema.py`
  - [x] Add constraints and indexes
  - [x] Update documentation
  - **Status**: ✅ Complete (`create_bsdd_allowed_value_node`)
  - **Time**: 2h

- [x] **P1.1.3** - Add `BSDDClassRelation` node type
  - [x] Define schema in `knowledge_graph_schema.py`
  - [x] Add constraints and indexes
  - [x] Update documentation
  - **Status**: ✅ Complete (`create_bsdd_class_relation_node`)
  - **Time**: 2h

- [x] **P1.1.4** - Add `BSDDPropertyRelation` node type
  - [x] Define schema in `knowledge_graph_schema.py`
  - [x] Add constraints and indexes
  - [x] Update documentation
  - **Status**: ✅ Complete (`create_bsdd_property_relation_node`)
  - **Time**: 2h

### P1.2: Expand Existing Node Properties
**Estimated Time**: 10 hours  
**Dependencies**: P1.1  
**Assignee**: TBD

- [x] **P1.2.1** - Update `BSDDDictionary` node properties
  - [x] Add `organizationCode: str`
  - [x] Add `license: str`
  - [x] Add `licenseUrl: str`
  - [x] Add `status: str` (Preview/Active/Inactive)
  - [x] Add `releaseDate: datetime`
  - [x] Add `qualityAssuranceProcedure: str`
  - [x] Add `qualityAssuranceProcedureUrl: str`
  - [x] Add `moreInfoUrl: str`
  - [x] Add `changeRequestEmailAddress: str`
  - **Status**: ✅ Complete (Implemented in `create_bsdd_dictionary_node`)
  - **Time**: 3h

- [x] **P1.2.2** - Update `BSDDClass` node properties
  - [x] Add `classType: str` (Class/Material/GroupOfProperties/AlternativeUse)
  - [x] Add `parentClassCode: str`
  - [x] Add `relatedIfcEntityNames: List[str]`
  - [x] Add `synonyms: List[str]`
  - [x] Add `status: str` (Active/Inactive)
  - [x] Add `referenceCode: str`
  - [x] Add `countriesOfUse: List[str]`
  - [x] Add `countryOfOrigin: str`
  - [x] Add `activationDateUtc: datetime`
  - [x] Add `deActivationDateUtc: datetime`
  - [x] Add `versionDateUtc: datetime`
  - [x] Add `versionNumber: int`
  - [x] Add `visualRepresentationUri: str`
  - **Status**: ✅ Complete (Implemented in `create_bsdd_class_node`)
  - **Time**: 4h

- [x] **P1.2.3** - Update `BSDDProperty` node properties
  - [x] Add `dataType: str` (Boolean/Character/Integer/Real/String/Time)
  - [x] Add `units: List[str]`
  - [x] Add `propertyValueKind: str` (Single/Range/List/Complex/ComplexList)
  - [x] Add `minInclusive: float`
  - [x] Add `maxInclusive: float`
  - [x] Add `minExclusive: float`
  - [x] Add `maxExclusive: float`
  - [x] Add `pattern: str` (regex)
  - [x] Add `dimension: str` (physical quantity)
  - [x] Add `dimensionLength: int`
  - [x] Add `dimensionMass: int`
  - [x] Add `dimensionTime: int`
  - [x] Add `dimensionElectricCurrent: int`
  - [x] Add `dimensionThermodynamicTemperature: int`
  - [x] Add `dimensionAmountOfSubstance: int`
  - [x] Add `dimensionLuminousIntensity: int`
  - [x] Add `physicalQuantity: str`
  - [x] Add `methodOfMeasurement: str`
  - [x] Add `textFormat: str`
  - [x] Add `isDynamic: bool`
  - [x] Add `dynamicParameterPropertyCodes: List[str]`
  - [x] Add `connectedPropertyCodes: List[str]`
  - **Status**: ✅ Complete (Implemented in `create_bsdd_property_node`)
  - **Time**: 3h

### P1.3: Add New Relationships
**Estimated Time**: 6 hours  
**Dependencies**: P1.1, P1.2  
**Assignee**: TBD

- [x] **P1.3.1** - Add `HAS_PARENT_CLASS` relationship
  - [x] Define relationship (Class → Class)
  - [x] Add to schema
  - [x] Create migration script
  - **Status**: ✅ Complete
  - **Time**: 1h

- [x] **P1.3.2** - Add `HAS_CLASS_PROPERTY` relationship
  - [x] Define relationship (Class → ClassProperty)
  - [x] Add to schema
  - [x] Create migration script
  - **Status**: ✅ Complete
  - **Time**: 1h

- [x] **P1.3.3** - Add `REFERENCES_PROPERTY` relationship
  - [x] Define relationship (ClassProperty → Property)
  - [x] Add to schema
  - [x] Create migration script
  - **Status**: ✅ Complete
  - **Time**: 1h

- [x] **P1.3.4** - Add `HAS_ALLOWED_VALUE` relationship
  - [x] Define relationship (Property/ClassProperty → AllowedValue)
  - [x] Add to schema
  - [x] Create migration script
  - **Status**: ✅ Complete
  - **Time**: 1h

- [x] **P1.3.5** - Add `HAS_CLASS_RELATION` relationship
  - [x] Define relationship (Class → ClassRelation → Class)
  - [x] Add to schema
  - [x] Create migration script
  - **Status**: ✅ Complete
  - **Time**: 1h

- [x] **P1.3.6** - Add `HAS_PROPERTY_RELATION` relationship
  - [x] Define relationship (Property → PropertyRelation → Property)
  - [x] Add to schema
  - [x] Create migration script
  - **Status**: ✅ Complete
  - **Time**: 1h

### P1.4: Update Data Ingestion Pipeline
**Estimated Time**: 8 hours  
**Dependencies**: P1.1, P1.2, P1.3  
**Assignee**: TBD

- [x] **P1.4.1** - Update `bsdd_ingestion.py` for new node types
  - [x] Add ClassProperty ingestion logic
  - [x] Add AllowedValue ingestion logic
  - [x] Add ClassRelation ingestion logic
  - [x] Add PropertyRelation ingestion logic
  - **Status**: ✅ Complete (`bsdd_ingestion.py` updated)
  - **Time**: 4h

- [x] **P1.4.2** - PointNet Ingestion
  - [x] Pytorch PointNet Segmentation pipeline
  - [x] Neo4j ingestion for segmented point clouds
  - [x] Spatial indexing (point/bbox) in Graph
  - **Status**: ✅ Complete (`backend/pointnet_s3dis/online_segmentation.py`)
  - **Time**: 2h

- [x] **P1.4.3** - Add error handling and validation
  - [x] Validate required fields
  - [x] Validate data types
  - [x] Validate relationships
  - **Status**: ✅ Complete (Implemented in `ingest_dictionary`)
  - **Time**: 2h

### P1.5: BaseX Integration (Native Windows)
**Estimated Time**: 10 hours  
**Dependencies**: None  
**Assignee**: TBD

- [x] **P1.5.1** - Set up BaseX server (native Windows)
  - [x] Download BaseX 10.x (~8 MB) (Manual)
  - [x] Extract to `D:\BaseX` (Manual)
  - [x] Configure HTTP server (port 8984) (Manual)
  - [x] Test Web UI (http://localhost:8984/dba) (Manual)
  - [x] Create data directory structure (Handled by client)
  - **Status**: ✅ Complete (Scaffolding done)
  - **Time**: 1h

- [x] **P1.5.2** - Install BaseX Python client
  - [x] Add `basexclient` to requirements.txt
  - [x] Test connection from Python
  - [x] Configure credentials
  - **Status**: ✅ Complete
  - **Time**: 30min

- [x] **P1.5.3** - Create `basex_client.py` service
  - [x] Create BaseXService class
  - [x] Add session management
  - [x] Add database creation methods
  - [x] Add document storage methods
  - [x] Add XQuery execution methods
  - [x] Add error handling
  - **Status**: ✅ Complete
  - **Time**: 3h

- [x] **P1.5.4** - Create startup/shutdown scripts
  - [x] Create `scripts/start-basex.ps1`
  - [x] Create `scripts/stop-basex.ps1`
  - [x] Update `scripts/start-services.ps1` (used `start-all.ps1`)
  - [x] Update `scripts/stop-services.ps1`
  - [x] Add health check scripts
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P1.5.5** - Implement version management
  - [x] Create database per dictionary version (Strategy: Path based)
  - [x] Store original JSON/XML files
  - [x] Add version retrieval methods
  - [x] Add version comparison utilities (Implicit in XQuery)
  - **Status**: ✅ Complete (Implemented in `basex_client.py`)
  - **Time**: 2h

- [x] **P1.5.6** - Add audit trail functionality
  - [x] Log all imports to BaseX
  - [x] Store import timestamps and metadata
  - [x] Create audit query methods
  - [x] Add change tracking
  - **Status**: ✅ Complete (Implemented in `basex_client.py`)
  - **Time**: 1.5h

### P1.6: BaseX-Neo4j Synchronization
**Estimated Time**: 6 hours  
**Dependencies**: P1.5  
**Assignee**: TBD

- [x] **P1.6.1** - Design sync strategy
  - [x] Define sync triggers (import, update, delete)
  - [x] Design conflict resolution
  - [x] Define data flow (BaseX → Neo4j)
  - [x] Document sync architecture
  - **Status**: ✅ Complete (Implemented in `SyncManager`)
  - **Time**: 1h

- [x] **P1.6.2** - Implement import sync
  - [x] Store original to BaseX first
  - [x] Extract data for Neo4j graph
  - [x] Create graph nodes/relationships
  - [x] Link BaseX docs to Neo4j nodes (store BaseX URI in Neo4j)
  - **Status**: ✅ Complete (`SyncManager.sync_dictionary`)
  - **Time**: 3h

- [x] **P1.6.3** - Add sync validation
  - [x] Verify data integrity
  - [x] Check relationship consistency
  - [x] Add reconciliation methods
  - **Status**: ✅ Complete (`SyncManager.validate_sync`)
  - **Time**: 2h

---

## 🟡 Priority 2: API Expansion (Week 3-4)

### P2.1: Import/Export Endpoints
**Estimated Time**: 16 hours  
**Dependencies**: P1.1, P1.2, P1.3, P1.4  
**Assignee**: TBD

- [x] **P2.1.1** - `POST /api/kg/import/json` - JSON import endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add JSON parser
  - [x] Add validation logic
  - [x] Add transaction handling (BaseX + Neo4j)
  - [x] Add error collection
  - [x] Add response formatting
  - **Status**: ✅ Complete
  - **Time**: 4h

- [x] **P2.1.2** - `POST /api/kg/import/excel` - Excel import endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add Excel parser (openpyxl/pandas)
  - [x] Add sheet validation (Basic mapping)
  - [x] Add conversion to JSON format
  - [x] Add validation logic
  - [x] Add transaction handling
  - **Status**: ✅ Complete
  - **Time**: 6h

- [x] **P2.1.3** - `GET /api/kg/export/{uri}` - Export dictionary endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add query logic for full dictionary (Retrieve from BaseX Archive)
  - [x] Add JSON serialization
  - [x] Add format compliance check
  - **Status**: ✅ Complete
  - **Time**: 3h

- [x] **P2.1.4** - `POST /api/kg/validate` - Validation endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add JSON schema validation
  - [x] Add code format validation
  - [x] Add relationship integrity checks
  - [x] Add duplicate detection
  - [x] Return detailed error/warning list
  - **Status**: ✅ Complete (Basic validation implemented)
  - **Time**: 3h

### P2.2: Enhanced Query Endpoints
**Estimated Time**: 12 hours  
**Dependencies**: P1.1, P1.2, P1.3  
**Assignee**: TBD

- [x] **P2.2.1** - `GET /api/kg/classes/{uri}/hierarchy` - Class hierarchy endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add recursive parent/child query (Implemented in `KnowledgeGraphSchema`)
  - [x] Add hierarchy formatting (tree structure)
  - [x] Add depth limiting
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.2.2** - `GET /api/kg/classes/{uri}/properties` - Class properties endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add ClassProperty query with Property details
  - [x] Add AllowedValue inclusion (Basic)
  - [x] Add sorting (by SortNumber)
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.2.3** - `GET /api/kg/classes/{uri}/relations` - Class relations endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add ClassRelation query
  - [x] Add related class details
  - [x] Group by relation type
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.2.4** - `GET /api/kg/properties/{uri}/allowed-values` - Allowed values endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add AllowedValue query
  - [x] Add sorting (by SortNumber)
  - [ ] Add translations if available
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.2.5** - `GET /api/kg/properties/{uri}/relations` - Property relations endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add PropertyRelation query
  - [x] Add related property details
  - [x] Group by relation type
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.2.6** - `GET /api/kg/search/advanced` - Advanced search endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add multi-field search (code, name, definition, description)
  - [x] Add type filtering (class/property)
  - [x] Add status filtering
  - [x] Add dictionary filtering
  - [x] Add search in descriptions option
  - **Status**: ✅ Complete (Jan 19)
  - **Time**: 2h

### P2.3: Management Endpoints
**Estimated Time**: 8 hours  
**Dependencies**: P1.2  
**Assignee**: TBD

- [x] **P2.3.1** - `PUT /api/kg/dictionaries/{uri}/status` - Status update endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add authentication/authorization check (placeholder)
  - [x] Add status validation (Preview/Active/Inactive)
  - [x] Update dictionary status
  - [x] Log status changes (via Neo4j property)
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.3.2** - `GET /api/kg/dictionaries/{uri}/versions` - Version list endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Query all versions of dictionary
  - [x] Add version sorting
  - [x] Add status for each version
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.3.3** - `POST /api/kg/dictionaries/{uri}/translate` - Add language endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add language data validation
  - [x] Add translation ingestion (stored in Neo4j property)
  - [x] Maintain language-only flag (via translation object)
  - **Status**: ✅ Complete
  - **Time**: 2h

- [x] **P2.3.4** - `DELETE /api/kg/dictionaries/{uri}` - Delete dictionary endpoint
  - [x] Create endpoint in `kg_routes.py`
  - [x] Add authentication/authorization check (placeholder)
  - [x] Add cascade delete logic (DETACH DELETE)
  - [x] Add soft delete option (set deleted=true)
  - [x] Add backup before delete (manual step)
  - **Status**: ✅ Complete
  - **Time**: 2h

---

## 🟠 Priority 3: GraphQL Schema Enhancements (Week 5-6)

### P3.1: Add Mutations for Node Creation/Update/Delete
**Estimated Time**: 8 hours  
**Dependencies**: P1.1, P1.2, P2.2  
**Assignee**: TBD

- [x] **P3.1.1** - Add mutation to create bSDD class
  - [x] Implemented `create_bsdd_class` mutation in `kg_graphql.py`
  - [ ] Add corresponding method in `KnowledgeGraphSchema`
  - **Status**: 🔄 In Progress (mutation added; backend method pending)
  - **Time**: 1h
  - **Files**: `backend/api/kg_graphql.py`

### P3.2: Add Pagination and Error Handling
**Estimated Time**: 6 hours  
**Dependencies**: P3.1  
**Assignee**: TBD

- [ ] **P3.2.1** - Implement cursor-based pagination for queries
- [ ] **P3.2.2** - Add error object returns for failed mutations

### P3.3: Batch Operations and Documentation
**Estimated Time**: 4 hours  
**Dependencies**: P3.1, P3.2  
**Assignee**: TBD

- [ ] **P3.3.1** - Add batch mutation for linking/unlinking nodes
- [ ] **P3.3.2** - Update schema documentation and field descriptions

---

## 🌍 World-Class bSDD–IFC/IDS Integration Roadmap

### Vision
Deliver a unified, modular, and standards-compliant solution for Pointcloud, APS, and BSDD workflows, enabling seamless openBIM operations, compliance checking, and extensibility for global users.

---

### Key Objectives
- Unify Pointcloud, APS, and BSDD modules under a shared data model and API layer
- Implement modular UI components and plugin system for extensibility
- Orchestrate workflows across all modules with a central agent
- Support IDS referencing and compliance for all bSDD concepts
- Automate classification association, property mapping, and analytics in import/export pipelines
- Provide validation and compliance checking tools for IFC models against bSDD standards
- Ensure extensibility for future standards and workflows

---

### Unification & Modularity Roadmap
1. **Shared Data Model & Interfaces**
   - Define common types for elements, properties, classifications, and relationships
   - Use a central schema (GraphQL/OpenAPI) for all modules
2. **Unified API Layer**
   - Refactor backend APIs to expose unified endpoints for model data, semantic info, and analytics
   - Implement a gateway/orchestrator service to route requests and aggregate results
3. **Modular UI Components**
   - Build reusable React components for viewers, analytics, and semantic data
   - Use a plugin/extension system for dynamic features
   - Centralize state management (Redux/Zustand/Context API)
4. **Workflow Orchestration**
   - Implement an agent/workflow engine to coordinate tasks across modules
   - Enable cross-module triggers (e.g., semantic search in BSDD highlights elements in APS/Pointcloud)
5. **Extensibility & Integration**
   - Document interfaces for third-party plugins and data sources
   - Provide sample adapters for new standards (IDS, IFC, custom analytics)
6. **Testing & Validation**
   - Create integration tests for unified workflows
   - Validate data consistency and interoperability

---

### Status Legend
- ✅ Complete
- 🔄 In Progress
- ⏳ Pending
- ⚠️ Blocked

---

### Next Steps
- Review current APIs and data models for overlap
- Draft unified schema and interface contracts
- Refactor UI to use shared components and state
- Build orchestrator agent for cross-module workflows
- Document and test unified system

---
