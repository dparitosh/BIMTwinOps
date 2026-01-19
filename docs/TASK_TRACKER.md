# SMART BIM - Task Tracker

**Project**: bSDD Knowledge Graph Integration + Intelligent App Architecture  
**Architecture Standard**: 2026 Intelligent App (MCP + LangGraph + Agentic)  
**Last Updated**: January 16, 2026  
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

### In Progress
- 🔄 HITL / Executor: approval queue + endpoints implemented; remaining: LangGraph/GenUI integration.

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

- [ ] **P0.1.1** - Set up MCP Host (Orchestrator)
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

- [ ] **P0.4.2** - Create Generative UI Components
  - [ ] Create `<TaskList />` component (rendered by agent)
  - [ ] Create `<PropertyRecommendation />` component
  - [ ] Create `<ApprovalGate />` component (HITL)
  - [ ] Create `<GraphVisualization />` component
  - [ ] Add component registry for agent selection
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P0.4.3** - Implement Agent Response Renderer
  - [ ] Create `renderAgentResponse()` utility
  - [ ] Parse agent output (text + component metadata)
  - [ ] Dynamically render React components
  - [ ] Add fallback to plain text
  - **Status**: ⏳ Pending
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

- [ ] **P1.1.1** - Add `BSDDClassProperty` node type
  - [ ] Define schema in `knowledge_graph_schema.py`
  - [ ] Add constraints and indexes
  - [ ] Update documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P1.1.2** - Add `BSDDAllowedValue` node type
  - [ ] Define schema in `knowledge_graph_schema.py`
  - [ ] Add constraints and indexes
  - [ ] Update documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P1.1.3** - Add `BSDDClassRelation` node type
  - [ ] Define schema in `knowledge_graph_schema.py`
  - [ ] Add constraints and indexes
  - [ ] Update documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P1.1.4** - Add `BSDDPropertyRelation` node type
  - [ ] Define schema in `knowledge_graph_schema.py`
  - [ ] Add constraints and indexes
  - [ ] Update documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

### P1.2: Expand Existing Node Properties
**Estimated Time**: 10 hours  
**Dependencies**: P1.1  
**Assignee**: TBD

- [ ] **P1.2.1** - Update `BSDDDictionary` node properties
  - [ ] Add `organizationCode: str`
  - [ ] Add `license: str`
  - [ ] Add `licenseUrl: str`
  - [ ] Add `status: str` (Preview/Active/Inactive)
  - [ ] Add `releaseDate: datetime`
  - [ ] Add `qualityAssuranceProcedure: str`
  - [ ] Add `qualityAssuranceProcedureUrl: str`
  - [ ] Add `moreInfoUrl: str`
  - [ ] Add `changeRequestEmailAddress: str`
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P1.2.2** - Update `BSDDClass` node properties
  - [ ] Add `classType: str` (Class/Material/GroupOfProperties/AlternativeUse)
  - [ ] Add `parentClassCode: str`
  - [ ] Add `relatedIfcEntityNames: List[str]`
  - [ ] Add `synonyms: List[str]`
  - [ ] Add `status: str` (Active/Inactive)
  - [ ] Add `referenceCode: str`
  - [ ] Add `countriesOfUse: List[str]`
  - [ ] Add `countryOfOrigin: str`
  - [ ] Add `activationDateUtc: datetime`
  - [ ] Add `deActivationDateUtc: datetime`
  - [ ] Add `versionDateUtc: datetime`
  - [ ] Add `versionNumber: int`
  - [ ] Add `visualRepresentationUri: str`
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P1.2.3** - Update `BSDDProperty` node properties
  - [ ] Add `dataType: str` (Boolean/Character/Integer/Real/String/Time)
  - [ ] Add `units: List[str]`
  - [ ] Add `propertyValueKind: str` (Single/Range/List/Complex/ComplexList)
  - [ ] Add `minInclusive: float`
  - [ ] Add `maxInclusive: float`
  - [ ] Add `minExclusive: float`
  - [ ] Add `maxExclusive: float`
  - [ ] Add `pattern: str` (regex)
  - [ ] Add `dimension: str` (physical quantity)
  - [ ] Add `dimensionLength: int`
  - [ ] Add `dimensionMass: int`
  - [ ] Add `dimensionTime: int`
  - [ ] Add `dimensionElectricCurrent: int`
  - [ ] Add `dimensionThermodynamicTemperature: int`
  - [ ] Add `dimensionAmountOfSubstance: int`
  - [ ] Add `dimensionLuminousIntensity: int`
  - [ ] Add `physicalQuantity: str`
  - [ ] Add `methodOfMeasurement: str`
  - [ ] Add `textFormat: str`
  - [ ] Add `isDynamic: bool`
  - [ ] Add `dynamicParameterPropertyCodes: List[str]`
  - [ ] Add `connectedPropertyCodes: List[str]`
  - **Status**: ⏳ Pending
  - **Time**: 3h

### P1.3: Add New Relationships
**Estimated Time**: 6 hours  
**Dependencies**: P1.1, P1.2  
**Assignee**: TBD

- [ ] **P1.3.1** - Add `HAS_PARENT_CLASS` relationship
  - [ ] Define relationship (Class → Class)
  - [ ] Add to schema
  - [ ] Create migration script
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.3.2** - Add `HAS_CLASS_PROPERTY` relationship
  - [ ] Define relationship (Class → ClassProperty)
  - [ ] Add to schema
  - [ ] Create migration script
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.3.3** - Add `REFERENCES_PROPERTY` relationship
  - [ ] Define relationship (ClassProperty → Property)
  - [ ] Add to schema
  - [ ] Create migration script
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.3.4** - Add `HAS_ALLOWED_VALUE` relationship
  - [ ] Define relationship (Property/ClassProperty → AllowedValue)
  - [ ] Add to schema
  - [ ] Create migration script
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.3.5** - Add `HAS_CLASS_RELATION` relationship
  - [ ] Define relationship (Class → ClassRelation → Class)
  - [ ] Add to schema
  - [ ] Create migration script
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.3.6** - Add `HAS_PROPERTY_RELATION` relationship
  - [ ] Define relationship (Property → PropertyRelation → Property)
  - [ ] Add to schema
  - [ ] Create migration script
  - **Status**: ⏳ Pending
  - **Time**: 1h

### P1.4: Update Data Ingestion Pipeline
**Estimated Time**: 8 hours  
**Dependencies**: P1.1, P1.2, P1.3  
**Assignee**: TBD

- [ ] **P1.4.1** - Update `bsdd_ingestion.py` for new node types
  - [ ] Add ClassProperty ingestion logic
  - [ ] Add AllowedValue ingestion logic
  - [ ] Add ClassRelation ingestion logic
  - [ ] Add PropertyRelation ingestion logic
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P1.4.2** - Update relationship creation logic
  - [ ] Update existing relationships
  - [ ] Add new relationship creation
  - [ ] Handle circular dependencies
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P1.4.3** - Add error handling and validation
  - [ ] Validate required fields
  - [ ] Validate data types
  - [ ] Validate relationships
  - **Status**: ⏳ Pending
  - **Time**: 2h

### P1.5: BaseX Integration (Native Windows)
**Estimated Time**: 10 hours  
**Dependencies**: None  
**Assignee**: TBD

- [ ] **P1.5.1** - Set up BaseX server (native Windows)
  - [ ] Download BaseX 10.x (~8 MB)
  - [ ] Extract to `D:\BaseX`
  - [ ] Configure HTTP server (port 8984)
  - [ ] Test Web UI (http://localhost:8984/dba)
  - [ ] Create data directory structure
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.5.2** - Install BaseX Python client
  - [ ] Add `basexclient` to requirements.txt
  - [ ] Test connection from Python
  - [ ] Configure credentials
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P1.5.3** - Create `basex_client.py` service
  - [ ] Create BaseXService class
  - [ ] Add session management
  - [ ] Add database creation methods
  - [ ] Add document storage methods
  - [ ] Add XQuery execution methods
  - [ ] Add error handling
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P1.5.4** - Create startup/shutdown scripts
  - [ ] Create `scripts/start-basex.ps1`
  - [ ] Create `scripts/stop-basex.ps1`
  - [ ] Update `scripts/start-services.ps1` to include BaseX
  - [ ] Update `scripts/stop-services.ps1` to include BaseX
  - [ ] Add health check scripts
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P1.5.5** - Implement version management
  - [ ] Create database per dictionary version
  - [ ] Store original JSON/XML files
  - [ ] Add version retrieval methods
  - [ ] Add version comparison utilities
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P1.5.6** - Add audit trail functionality
  - [ ] Log all imports to BaseX
  - [ ] Store import timestamps and metadata
  - [ ] Create audit query methods
  - [ ] Add change tracking
  - **Status**: ⏳ Pending
  - **Time**: 1.5h

### P1.6: BaseX-Neo4j Synchronization
**Estimated Time**: 6 hours  
**Dependencies**: P1.5  
**Assignee**: TBD

- [ ] **P1.6.1** - Design sync strategy
  - [ ] Define sync triggers (import, update, delete)
  - [ ] Design conflict resolution
  - [ ] Define data flow (BaseX → Neo4j)
  - [ ] Document sync architecture
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P1.6.2** - Implement import sync
  - [ ] Store original to BaseX first
  - [ ] Extract data for Neo4j graph
  - [ ] Create graph nodes/relationships
  - [ ] Link BaseX docs to Neo4j nodes (store BaseX URI in Neo4j)
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P1.6.3** - Add sync validation
  - [ ] Verify data integrity
  - [ ] Check relationship consistency
  - [ ] Add reconciliation methods
  - **Status**: ⏳ Pending
  - **Time**: 2h

---

## 🟡 Priority 2: API Expansion (Week 3-4)

### P2.1: Import/Export Endpoints
**Estimated Time**: 16 hours  
**Dependencies**: P1.1, P1.2, P1.3, P1.4  
**Assignee**: TBD

- [ ] **P2.1.1** - `POST /api/kg/import/json` - JSON import endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add JSON parser
  - [ ] Add validation logic
  - [ ] Add transaction handling
  - [ ] Add error collection
  - [ ] Add response formatting
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P2.1.2** - `POST /api/kg/import/excel` - Excel import endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add Excel parser (openpyxl/pandas)
  - [ ] Add sheet validation (7 sheets)
  - [ ] Add conversion to JSON format
  - [ ] Add validation logic
  - [ ] Add transaction handling
  - **Status**: ⏳ Pending
  - **Time**: 6h

- [ ] **P2.1.3** - `GET /api/kg/export/{uri}` - Export dictionary endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add query logic for full dictionary
  - [ ] Add JSON serialization
  - [ ] Add format compliance check
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P2.1.4** - `POST /api/kg/validate` - Validation endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add JSON schema validation
  - [ ] Add code format validation
  - [ ] Add relationship integrity checks
  - [ ] Add duplicate detection
  - [ ] Return detailed error/warning list
  - **Status**: ⏳ Pending
  - **Time**: 3h

### P2.2: Enhanced Query Endpoints
**Estimated Time**: 12 hours  
**Dependencies**: P1.1, P1.2, P1.3  
**Assignee**: TBD

- [ ] **P2.2.1** - `GET /api/kg/classes/{uri}/hierarchy` - Class hierarchy endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add recursive parent/child query
  - [ ] Add hierarchy formatting (tree structure)
  - [ ] Add depth limiting
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.2.2** - `GET /api/kg/classes/{uri}/properties` - Class properties endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add ClassProperty query with Property details
  - [ ] Add AllowedValue inclusion
  - [ ] Add sorting (by SortNumber)
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.2.3** - `GET /api/kg/classes/{uri}/relations` - Class relations endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add ClassRelation query
  - [ ] Add related class details
  - [ ] Group by relation type
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.2.4** - `GET /api/kg/properties/{uri}/allowed-values` - Allowed values endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add AllowedValue query
  - [ ] Add sorting (by SortNumber)
  - [ ] Add translations if available
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.2.5** - `GET /api/kg/properties/{uri}/relations` - Property relations endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add PropertyRelation query
  - [ ] Add related property details
  - [ ] Group by relation type
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.2.6** - `GET /api/kg/search/advanced` - Advanced search endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add multi-field search
  - [ ] Add type filtering
  - [ ] Add status filtering
  - [ ] Add dictionary filtering
  - [ ] Add search in descriptions option
  - **Status**: ⏳ Pending
  - **Time**: 2h

### P2.3: Management Endpoints
**Estimated Time**: 8 hours  
**Dependencies**: P1.2  
**Assignee**: TBD

- [ ] **P2.3.1** - `PUT /api/kg/dictionaries/{uri}/status` - Status update endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add authentication/authorization check
  - [ ] Add status validation (Preview/Active/Inactive)
  - [ ] Update dictionary status
  - [ ] Log status changes
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.3.2** - `GET /api/kg/dictionaries/{uri}/versions` - Version list endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Query all versions of dictionary
  - [ ] Add version sorting
  - [ ] Add status for each version
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.3.3** - `POST /api/kg/dictionaries/{uri}/translate` - Add language endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add language data validation
  - [ ] Add translation ingestion
  - [ ] Maintain language-only flag
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P2.3.4** - `DELETE /api/kg/dictionaries/{uri}` - Delete dictionary endpoint
  - [ ] Create endpoint in `kg_routes.py`
  - [ ] Add authentication/authorization check
  - [ ] Add cascade delete logic
  - [ ] Add soft delete option
  - [ ] Add backup before delete
  - **Status**: ⏳ Pending
  - **Time**: 2h

---

## 🟠 Priority 3: GraphQL Schema Enhancement (Week 5-6)

### P3.1: Add New GraphQL Types
**Estimated Time**: 10 hours  
**Dependencies**: P1.1, P1.2  
**Assignee**: TBD

- [x] **P3.1.1** - Add `BsddClassProperty` type
  - [x] Define type in `kg_graphql.py`
  - [x] Add field resolvers
  - [x] Add to Class.classProperties field
  - [ ] Add documentation
  - **Status**: ✅ Complete (Jan 17)
  - **Time**: 2h

- [x] **P3.1.2** - Add `BsddAllowedValue` type
  - [x] Define type in `kg_graphql.py`
  - [x] Add field resolvers
  - [x] Add to Property.allowedValues field
  - [x] Add query resolver `bsdd_allowed_values`
  - [ ] Add documentation
  - **Status**: ✅ Complete (Jan 17)
  - **Time**: 2h

- [ ] **P3.1.3** - Add `BsddClassRelation` type
  - [ ] Define type in `kg_graphql.py`
  - [ ] Add field resolvers
  - [ ] Add to Class.classRelations field
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P3.1.4** - Add `BsddPropertyRelation` type
  - [ ] Define type in `kg_graphql.py`
  - [ ] Add field resolvers
  - [ ] Add to Property.propertyRelations field
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P3.1.5** - Add `ImportResult` type
  - [ ] Define type in `kg_graphql.py`
  - [ ] Add success/errors/warnings fields
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P3.1.6** - Add `ValidationResult` type
  - [ ] Define type in `kg_graphql.py`
  - [ ] Add isValid/errors/warnings fields
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [x] **P3.1.7** - Add `BsddUnit` type
  - [x] Define type in `kg_graphql.py`
  - [x] Add field resolvers (uri, code, name, symbol)
  - [x] Add query resolver `bsdd_units`
  - [x] Add to Property.unit field
  - [ ] Add documentation
  - **Status**: ✅ Complete (Jan 17)
  - **Time**: 1h

- [x] **P3.1.8** - Add `NodeTypeCount` type (for GraphStats)
  - [x] Define type in `kg_graphql.py`
  - [x] Replace Dict[str, int] with List[NodeTypeCount] in GraphStats
  - **Status**: ✅ Complete (Jan 17)
  - **Time**: 30min

### P3.2: Add Enum Types
**Estimated Time**: 4 hours  
**Dependencies**: None  
**Assignee**: TBD

- [ ] **P3.2.1** - Add `ClassType` enum
  - [ ] Define enum (Class, Material, GroupOfProperties, AlternativeUse)
  - [ ] Add to BsddClass type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.2** - Add `DataType` enum
  - [ ] Define enum (Boolean, Character, Integer, Real, String, Time)
  - [ ] Add to BsddProperty type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.3** - Add `PropertyValueKind` enum
  - [ ] Define enum (Single, Range, List, Complex, ComplexList)
  - [ ] Add to BsddProperty type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.4** - Add `ClassRelationType` enum
  - [ ] Define enum (HasMaterial, HasReference, IsEqualTo, IsSimilarTo, IsParentOf, IsChildOf, HasPart, IsPartOf)
  - [ ] Add to BsddClassRelation type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.5** - Add `PropertyRelationType` enum
  - [ ] Define enum (HasReference, IsEqualTo, IsSimilarTo, IsParentOf, IsChildOf, HasPart)
  - [ ] Add to BsddPropertyRelation type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.6** - Add `DictionaryStatus` enum
  - [ ] Define enum (Preview, Active, Inactive)
  - [ ] Add to BsddDictionary type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.7** - Add `ResourceStatus` enum
  - [ ] Define enum (Active, Inactive)
  - [ ] Add to BsddClass and BsddProperty types
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

- [ ] **P3.2.8** - Add `PropertyType` enum
  - [ ] Define enum (Property, Dependency)
  - [ ] Add to BsddClassProperty type
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 30min

### P3.3: Add Mutation Operations
**Estimated Time**: 12 hours  
**Dependencies**: P2.1, P3.1  
**Assignee**: TBD

- [ ] **P3.3.1** - Add `importDictionary` mutation
  - [ ] Define mutation signature
  - [ ] Add JSON parsing logic
  - [ ] Add validation
  - [ ] Add ingestion logic
  - [ ] Return ImportResult
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P3.3.2** - Add `importDictionaryFromExcel` mutation
  - [ ] Define mutation signature (with Upload scalar)
  - [ ] Add Excel parsing logic
  - [ ] Add validation
  - [ ] Add ingestion logic
  - [ ] Return ImportResult
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P3.3.3** - Add `activateDictionary` mutation
  - [ ] Define mutation signature
  - [ ] Add authorization check
  - [ ] Update dictionary status
  - [ ] Return updated dictionary
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P3.3.4** - Add `deactivateDictionary` mutation
  - [ ] Define mutation signature
  - [ ] Add authorization check
  - [ ] Update dictionary status
  - [ ] Return updated dictionary
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P3.3.5** - Add `addLanguage` mutation
  - [ ] Define mutation signature
  - [ ] Add authorization check
  - [ ] Add translation ingestion
  - [ ] Return updated dictionary
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P3.3.6** - Add `validateDictionary` mutation
  - [ ] Define mutation signature
  - [ ] Add validation logic
  - [ ] Return ValidationResult
  - [ ] Add documentation
  - **Status**: ⏳ Pending
  - **Time**: 1h

### P3.4: Update Existing Types
**Estimated Time**: 6 hours  
**Dependencies**: P3.1, P3.2  
**Assignee**: TBD

- [ ] **P3.4.1** - Update `BsddDictionary` type
  - [ ] Add new fields (organizationCode, license, status, etc.)
  - [ ] Add classProperties field
  - [ ] Add versions field
  - [ ] Update resolvers
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P3.4.2** - Update `BsddClass` type
  - [ ] Add new fields (classType, parentClass, synonyms, status, etc.)
  - [ ] Add classProperties field
  - [ ] Add classRelations field
  - [ ] Add parentClass/childClasses navigation
  - [ ] Update resolvers
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P3.4.3** - Update `BsddProperty` type
  - [ ] Add new fields (dataType, units, propertyValueKind, etc.)
  - [ ] Add allowedValues field
  - [ ] Add propertyRelations field
  - [ ] Update resolvers
  - **Status**: ⏳ Pending
  - **Time**: 2h

---

## 🔵 Priority 4: Frontend Components (Week 7-8)

### P4.0: PointCloud UX Stabilization (Week 7-8)
**Estimated Time**: 4 hours  
**Dependencies**: None  
**Assignee**: TBD

- [x] **P4.0.1** - Sync selection across Viewer / Annotations / Graph
  - [x] PointCloudViewer: single-click selection (pointer events + drag threshold)
  - [x] GraphViewer: click node updates shared selection state
  - [x] AnnotationPanel: selection highlight and auto-expand category
  - **Status**: ✅ Complete
  - **Files**: `pointcloud-frontend/src/components/PointCloudViewer.jsx`, `pointcloud-frontend/src/components/GraphViewer.jsx`, `pointcloud-frontend/src/components/AnnotationPanel.jsx`, `pointcloud-frontend/src/App.jsx`

- [x] **P4.0.2** - Improve Graph styling (smaller nodes, blue background)
  - [x] Reduce node radius for readability
  - [x] Use blue-hue canvas background
  - [x] Ensure label readability on tinted background
  - **Status**: ✅ Complete
  - **Files**: `pointcloud-frontend/src/components/GraphViewer.jsx`, `pointcloud-frontend/src/App.jsx`

### P4.1: Search Components
**Estimated Time**: 16 hours  
**Dependencies**: P2.2  
**Assignee**: TBD

- [ ] **P4.1.1** - Create `SearchBar.jsx`
  - [ ] Implement search input with debouncing
  - [ ] Add autocomplete suggestions
  - [ ] Add example placeholders
  - [ ] Add clear button
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.1.2** - Create `SearchFilters.jsx`
  - [ ] Implement collapsible filter panel
  - [ ] Add filter state management
  - [ ] Add filter reset functionality
  - [ ] Add URL state synchronization
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P4.1.3** - Create `TypeFilter.jsx`
  - [ ] Implement icon-based type selection
  - [ ] Add 6 type icons (Property, Class, Material, Group, Dictionary, Organization)
  - [ ] Add multi-select support
  - [ ] Add styling/hover effects
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.1.4** - Create `SearchResults.jsx`
  - [ ] Implement results list/grid view
  - [ ] Add pagination
  - [ ] Add result highlighting
  - [ ] Add loading states
  - [ ] Add empty states
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P4.1.5** - Create `CheckboxFilter.jsx`
  - [ ] Implement reusable checkbox filter
  - [ ] Add group support
  - [ ] Add styling
  - **Status**: ⏳ Pending
  - **Time**: 2h

### P4.2: Dictionary Components
**Estimated Time**: 12 hours  
**Dependencies**: None  
**Assignee**: TBD

- [ ] **P4.2.1** - Create `DictionaryCard.jsx`
  - [ ] Implement card layout (logo, name, attribution)
  - [ ] Add stats display (class/property counts)
  - [ ] Add hover effects
  - [ ] Add click navigation
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.2.2** - Create `DictionaryGrid.jsx`
  - [ ] Implement responsive grid (3-4 columns desktop, 1-2 mobile)
  - [ ] Add overflow handling ("300+ more" button)
  - [ ] Add sorting options
  - [ ] Add filtering integration
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.2.3** - Create `DictionaryBrowser.jsx`
  - [ ] Implement browsing interface
  - [ ] Add "Browse all" functionality
  - [ ] Add search integration
  - [ ] Add category filtering
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.2.4** - Create `DictionaryDetail.jsx`
  - [ ] Implement detail view
  - [ ] Add metadata display
  - [ ] Add class/property lists
  - [ ] Add version information
  - [ ] Add export functionality
  - **Status**: ⏳ Pending
  - **Time**: 3h

### P4.3: Class Components
**Estimated Time**: 14 hours  
**Dependencies**: P2.2  
**Assignee**: TBD

- [ ] **P4.3.1** - Create `ClassCard.jsx`
  - [ ] Implement class display card
  - [ ] Add type badge
  - [ ] Add IFC entity display
  - [ ] Add property count
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P4.3.2** - Create `ClassHierarchy.jsx`
  - [ ] Implement tree view navigation
  - [ ] Add expand/collapse functionality
  - [ ] Add parent/child navigation
  - [ ] Add breadcrumb trail
  - [ ] Add search within hierarchy
  - **Status**: ⏳ Pending
  - **Time**: 5h

- [ ] **P4.3.3** - Create `ClassProperties.jsx`
  - [ ] Implement property list
  - [ ] Add sorting (by SortNumber)
  - [ ] Add property set grouping
  - [ ] Add required/optional indicators
  - [ ] Add value restrictions display
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P4.3.4** - Create `ClassRelations.jsx`
  - [ ] Implement relationship visualization
  - [ ] Group by relation type
  - [ ] Add navigation to related classes
  - [ ] Add visual indicators
  - **Status**: ⏳ Pending
  - **Time**: 3h

### P4.4: Property Components
**Estimated Time**: 10 hours  
**Dependencies**: P2.2  
**Assignee**: TBD

- [ ] **P4.4.1** - Create `PropertyCard.jsx`
  - [ ] Implement property display card
  - [ ] Add data type badge
  - [ ] Add unit display
  - [ ] Add example value
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P4.4.2** - Create `PropertyValue.jsx`
  - [ ] Implement value display with units
  - [ ] Add unit conversion UI
  - [ ] Add value validation
  - [ ] Add formatting options
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.4.3** - Create `AllowedValues.jsx`
  - [ ] Implement enumeration display
  - [ ] Add dropdown/list view toggle
  - [ ] Add search within values
  - [ ] Add descriptions
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.4.4** - Create `PropertyRelations.jsx`
  - [ ] Implement relationship display
  - [ ] Group by relation type
  - [ ] Add navigation to related properties
  - [ ] Add visual indicators
  - **Status**: ⏳ Pending
  - **Time**: 2h

### P4.5: Import Components
**Estimated Time**: 14 hours  
**Dependencies**: P2.1  
**Assignee**: TBD

- [ ] **P4.5.1** - Create `ImportForm.jsx`
  - [ ] Implement upload interface
  - [ ] Add file type selection (JSON/Excel)
  - [ ] Add drag-and-drop support
  - [ ] Add progress indicator
  - [ ] Add cancel functionality
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P4.5.2** - Create `JsonUpload.jsx`
  - [ ] Implement JSON file upload
  - [ ] Add file validation (size, format)
  - [ ] Add preview functionality
  - [ ] Add syntax highlighting
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.5.3** - Create `ExcelUpload.jsx`
  - [ ] Implement Excel file upload
  - [ ] Add file validation (size, format)
  - [ ] Add sheet preview
  - [ ] Add column mapping preview
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P4.5.4** - Create `ImportValidation.jsx`
  - [ ] Implement validation results display
  - [ ] Add error/warning categorization
  - [ ] Add fix suggestions
  - [ ] Add re-upload functionality
  - [ ] Add success/failure states
  - **Status**: ⏳ Pending
  - **Time**: 4h

### P4.6: Common Components
**Estimated Time**: 8 hours  
**Dependencies**: None  
**Assignee**: TBD

- [ ] **P4.6.1** - Create `IconFilter.jsx`
  - [ ] Implement reusable icon filter
  - [ ] Add icon support
  - [ ] Add selected state
  - [ ] Add tooltip
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P4.6.2** - Create `StatusBadge.jsx`
  - [ ] Implement status display (Preview/Active/Inactive)
  - [ ] Add color coding
  - [ ] Add icon support
  - [ ] Add tooltip
  - **Status**: ⏳ Pending
  - **Time**: 1h

- [ ] **P4.6.3** - Create `VersionDisplay.jsx`
  - [ ] Implement version information display
  - [ ] Add version comparison
  - [ ] Add "latest" indicator
  - [ ] Add changelog link
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P4.6.4** - Create `AuthGate.jsx`
  - [ ] Implement authentication wrapper
  - [ ] Add login redirect
  - [ ] Add role checking
  - [ ] Add loading state
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P4.6.5** - Create `UpdateCard.jsx`
  - [ ] Implement structured update display
  - [ ] Add sections (What/Why/When/How)
  - [ ] Add status emojis
  - [ ] Add author/date display
  - **Status**: ⏳ Pending
  - **Time**: 1h

---

## ⚪ Priority 5: Testing & Documentation (Week 9+)

### P5.1: Unit Tests
**Estimated Time**: 20 hours  
**Dependencies**: P1, P2, P3  
**Assignee**: TBD

- [ ] **P5.1.1** - Test backend data model
  - [ ] Test node creation
  - [ ] Test relationship creation
  - [ ] Test property validation
  - [ ] Test constraints
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P5.1.2** - Test REST API endpoints
  - [ ] Test all GET endpoints
  - [ ] Test all POST endpoints
  - [ ] Test all PUT endpoints
  - [ ] Test all DELETE endpoints
  - [ ] Test error handling
  - **Status**: ⏳ Pending
  - **Time**: 6h

- [ ] **P5.1.3** - Test GraphQL resolvers
  - [ ] Test all query resolvers
  - [ ] Test all mutation resolvers
  - [ ] Test field resolvers
  - [ ] Test error handling
  - **Status**: ⏳ Pending
  - **Time**: 6h

- [ ] **P5.1.4** - Test import pipeline
  - [ ] Test JSON parsing
  - [ ] Test Excel parsing
  - [ ] Test validation logic
  - [ ] Test error collection
  - **Status**: ⏳ Pending
  - **Time**: 4h

### P5.2: Integration Tests
**Estimated Time**: 16 hours  
**Dependencies**: P5.1  
**Assignee**: TBD

- [ ] **P5.2.1** - Test end-to-end import (JSON)
  - [ ] Test full dictionary import
  - [ ] Test partial dictionary import
  - [ ] Test language-only import
  - [ ] Test error scenarios
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P5.2.2** - Test end-to-end import (Excel)
  - [ ] Test full dictionary import
  - [ ] Test partial dictionary import
  - [ ] Test error scenarios
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P5.2.3** - Test knowledge graph queries
  - [ ] Test complex queries
  - [ ] Test relationship traversal
  - [ ] Test aggregations
  - [ ] Test performance
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P5.2.4** - Test bSDD API client
  - [ ] Test dictionary queries
  - [ ] Test class queries
  - [ ] Test property queries
  - [ ] Test search
  - **Status**: ⏳ Pending
  - **Time**: 4h

### P5.3: Data Validation Tests
**Estimated Time**: 12 hours  
**Dependencies**: P2.1  
**Assignee**: TBD

- [ ] **P5.3.1** - Test with official bSDD examples
  - [ ] Test IFC dictionary
  - [ ] Test "Fruit and vegetables" demo
  - [ ] Test CCI Construction
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P5.3.2** - Test with large datasets
  - [ ] Test dictionary with 1000+ classes
  - [ ] Test dictionary with complex relations
  - [ ] Test performance
  - **Status**: ⏳ Pending
  - **Time**: 4h

- [ ] **P5.3.3** - Test validation rules
  - [ ] Test code format validation
  - [ ] Test URI format validation
  - [ ] Test relationship integrity
  - [ ] Test duplicate detection
  - **Status**: ⏳ Pending
  - **Time**: 4h

### P5.4: Performance Testing
**Estimated Time**: 8 hours  
**Dependencies**: P5.2  
**Assignee**: TBD

- [ ] **P5.4.1** - Test import performance
  - [ ] Benchmark JSON import
  - [ ] Benchmark Excel import
  - [ ] Identify bottlenecks
  - [ ] Optimize
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P5.4.2** - Test query performance
  - [ ] Benchmark REST endpoints
  - [ ] Benchmark GraphQL queries
  - [ ] Identify slow queries
  - [ ] Add indexes
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P5.4.3** - Test API comparison
  - [ ] Compare REST vs GraphQL performance
  - [ ] Compare response sizes
  - [ ] Document recommendations
  - **Status**: ⏳ Pending
  - **Time**: 2h

### P5.5: Documentation Updates
**Estimated Time**: 10 hours  
**Dependencies**: All  
**Assignee**: TBD

- [ ] **P5.5.1** - Update README.md
  - [ ] Update features list
  - [ ] Update API endpoints
  - [ ] Update GraphQL examples
  - [ ] Update setup instructions
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P5.5.2** - Update BSDD_INTEGRATION.md
  - [ ] Update data model section
  - [ ] Update import process
  - [ ] Add new examples
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P5.5.3** - Update GRAPHQL_API_GUIDE.md
  - [ ] Add new types
  - [ ] Add new queries
  - [ ] Add new mutations
  - [ ] Update examples
  - **Status**: ⏳ Pending
  - **Time**: 2h

- [ ] **P5.5.4** - Create IMPORT_GUIDE.md
  - [ ] Document JSON import format
  - [ ] Document Excel import format
  - [ ] Add validation rules
  - [ ] Add troubleshooting
  - **Status**: ⏳ Pending
  - **Time**: 3h

- [ ] **P5.5.5** - Update API reference docs
  - [ ] Generate OpenAPI spec
  - [ ] Update endpoint descriptions
  - [ ] Add request/response examples
  - **Status**: ⏳ Pending
  - **Time**: 1h

---

## Sprint Metrics

### Overall Progress
```
Total Tasks: 71 (was 56, +15 Intelligent App tasks)
Completed: 9 (13%) [Including architecture review]
In Progress: 0 (0%)
Pending: 62 (87%)
Blocked: 0 (0%)

Estimated Total Time: 296 hours (~7.5 weeks with 1 developer)
  - Core bSDD Integration: 244 hours
  - Intelligent App Foundation: 52 hours (NEW)
```

### By Priority
```
Priority 0 (Week 0): 52 hours - 15 tasks (Intelligent App Foundation) **NEW**
Priority 1 (Week 1-2): 48 hours - 20 tasks (+ BaseX integration)
Priority 2 (Week 3-4): 36 hours - 13 tasks
Priority 3 (Week 5-6): 32 hours - 14 tasks
Priority 4 (Week 7-8): 74 hours - 26 tasks
Priority 5 (Week 9+): 54 hours - 17 tasks
```

### By Category
```
Intelligent App (MCP + LangGraph): 52 hours (18%) **NEW**
Backend: 80 hours (27%) [+ BaseX integration]
API: 48 hours (16%)
GraphQL: 32 hours (11%)
Frontend: 74 hours (25%)
Testing: 10 hours (3%)
```

### By Architecture Layer
```
Agentic Core (LangGraph + Agents): 22 hours (7%) **NEW**
MCP Infrastructure: 18 hours (6%) **NEW**
Hybrid Memory (OpenSearch): 10 hours (3%) **NEW**
Security & Governance: 6 hours (2%) **NEW**
Traditional Backend/Frontend: 240 hours (82%)
```

---

## Architectural Decision Records (ADRs)

### ADR-001: Use of Model Context Protocol (MCP)
- **Context**: Need to integrate with Neo4j, BaseX, bSDD API, and OpenSearch
- **Decision**: Implement standard **MCP Servers** for each integration rather than custom API wrappers
- **Rationale**: 
  - Decouples tool implementation from LLM orchestrator
  - Framework-agnostic (works with LangChain, AutoGen, or custom frameworks)
  - Allows local/remote execution for security
  - Standardized JSON-RPC protocol
- **Status**: ✅ Approved
- **Date**: January 15, 2026

### ADR-002: LangGraph for Orchestration
- **Context**: System handles sensitive operations (delete, bulk updates) and requires HITL
- **Decision**: Use **LangGraph** instead of purely autonomous loop (like AutoGen)
- **Rationale**:
  - Explicit state machine allows "breakpoint" nodes
  - Code physically halts and waits for user input before destructive operations
  - Satisfies OWASP LLM08 (Excessive Agency) requirements
  - Redis-backed state persistence
  - Deterministic handling of non-deterministic LLM outputs
- **Status**: ✅ Approved
- **Date**: January 15, 2026

### ADR-003: OpenSearch for Memory
- **Context**: Users need semantic search over tasks and conversation history
- **Decision**: Use **OpenSearch** (Managed) for vector storage alongside Neo4j
- **Rationale**:
  - Native MCP server implementation available
  - Superior hybrid search (vector + keyword + metadata)
  - k-NN plugin for similarity search
  - Better filtering by dates/tags than pure vector stores
  - Complements Neo4j (graph relationships vs. semantic similarity)
- **Status**: ✅ Approved
- **Date**: January 15, 2026

### ADR-004: Hybrid Database Architecture (BaseX + Neo4j)
- **Context**: Need both document storage with versioning and graph relationships
- **Decision**: Use **BaseX** for originals + **Neo4j** for graph
- **Rationale**:
  - BaseX: Document store, version management, audit trail
  - Neo4j: Graph traversal, semantic queries, real-time performance
  - Separation of concerns (originals vs. processed graph)
  - Independent scaling
- **Status**: ✅ Approved
- **Date**: January 14, 2026

### ADR-005: Generative UI (GenUI) over Static Components
- **Context**: Need dynamic, context-aware UI rendering based on agent outputs
- **Decision**: Use **Generative UI** pattern with React component registry
- **Rationale**:
  - Agents can choose optimal visualization (table, graph, chart)
  - Reduces frontend-backend coupling
  - Enables rich, interactive responses
  - Falls back to plain text if components unavailable
- **Status**: 🔄 Under Review
- **Date**: January 15, 2026

---

## Risk Register

### Critical Risk **NEW**
- **R0**: Agentic architecture adds complexity and potential failure modes
  - **Mitigation**: Start with simple state machine, add complexity incrementally, comprehensive error handling
  - **Owner**: Architecture lead

### High Risk
- **R1**: Large data model changes may break existing functionality
  - **Mitigation**: Comprehensive testing, backward compatibility checks
  - **Owner**: Backend lead

- **R2**: Excel parsing complexity may cause import failures
  - **Mitigation**: Robust error handling, detailed validation
  - **Owner**: API lead

- **R6**: LLM non-determinism may cause unpredictable agent behavior **NEW**
  - **Mitigation**: LangGraph state machines, strict output schemas, HITL gates
  - **Owner**: AI/ML lead

### Medium Risk
- **R3**: Frontend component library may not match official bSDD patterns
  - **Mitigation**: Regular UI/UX reviews, iterative refinement
  - **Owner**: Frontend lead

- **R4**: Performance issues with large dictionaries (1000+ classes)
  - **Mitigation**: Early performance testing, query optimization
  - **Owner**: Backend lead

- **R7**: MCP server failures may cascade to agent failures **NEW**
  - **Mitigation**: Circuit breakers, retry logic, fallback tools
  - **Owner**: Backend lead

### Low Risk
- **R5**: Documentation may become outdated
  - **Mitigation**: Update docs alongside code changes
  - **Owner**: All team members

---

## Dependencies

### External Dependencies
- Neo4j 5.25+ (graph database)
- **BaseX 10.x (XML/JSON database) - Native Windows, No Docker**
- **OpenSearch 2.x (vector + keyword search) - Docker or AWS** **NEW**
- Azure OpenAI GPT-4o (GenAI service + embeddings)
- bSDD API access (official service)
- Python 3.9+ with required packages
- Node.js 18+ for frontend
- Java 11+ (for BaseX runtime)
- **Redis 7.x (LangGraph state persistence)** **NEW**

### Python Packages (NEW)
- `langgraph` - Agent orchestration
- `mcp` - Model Context Protocol SDK
- `opensearch-py` - OpenSearch client
- `nemo-guardrails` - Safety guardrails **NEW**

### Internal Dependencies
- **P0 (Intelligent App) → All other priorities (foundation layer)**
- P1 (Backend) → P2 (API), P3 (GraphQL), P4 (Frontend)
- P2.1 (Import API) → P4.5 (Import UI)
- P2.2 (Query API) → P4.1-P4.4 (UI components)
- P3 (GraphQL) → P4 (Frontend)
- All → P5 (Testing)

---

## Notes

### Design Decisions
- Using dual import format (JSON + Excel) for flexibility
- Maintaining URI format compatibility with official bSDD
- Supporting "latest" version resolution
- Implementing soft delete for dictionaries
- **Hybrid database architecture**: BaseX (document store) + Neo4j (graph)
- **Native Windows deployment**: BaseX runs without Docker
- **BaseX as source of truth**: Original files stored, Neo4j for graph queries
- **Synchronization pattern**: BaseX → Neo4j unidirectional sync
- **Agentic architecture**: LangGraph-based orchestration with MCP tools **NEW**
- **HITL pattern**: Mandatory approval for destructive operations **NEW**
- **Hybrid memory**: OpenSearch (semantic) + Neo4j (graph) **NEW**

### Technical Debt
- Current schema lacks ClassProperty junction nodes
- Missing enumeration support (AllowedValues)
- No version management in current implementation
- Limited relationship types
- **No agent observability/monitoring yet** **NEW**
- **No prompt versioning system yet** **NEW**

### Future Enhancements
- Real-time collaboration on dictionary editing
- Visual schema designer
- Automated dictionary validation
- Dictionary comparison tool
- Bulk import from multiple sources
- Export to multiple formats (JSON, Excel, RDF, TTL)
- Integration with Revit, BlenderBIM, etc.
- **Multi-agent collaboration (agent swarms)** **NEW**
- **Custom agent training/fine-tuning** **NEW**
- **Offline mode with local LLMs** **NEW**
- **Agent performance analytics dashboard** **NEW**

---

## 2026 Intelligent App Compliance Checklist

### ✅ Architecture Standards
- [x] Reasoning ≠ Execution principle (LangGraph + MCP)
- [ ] Declarative state machines (LangGraph graphs defined)
- [ ] Memory-augmented generation (OpenSearch RAG)
- [ ] Safety by design (OWASP LLM08 compliance)

### ✅ MCP Integration
- [ ] MCP Host implemented (orchestrator)
- [ ] MCP Server: Neo4j (4 tools)
- [ ] MCP Server: BaseX (4 tools)
- [ ] MCP Server: bSDD API (4 tools)
- [ ] MCP Server: OpenSearch (3 tools)
- [ ] MCP Inspector tested all servers

### ✅ Agent System
- [ ] Router Agent (intent classification)
- [ ] Planner Agent (task decomposition)
- [ ] Executor Agent (tool invocation)
- [ ] Memory Agent (semantic recall)
- [ ] HITL gates for critical operations

### ✅ Security & Governance
- [ ] Row-level security (user_id filtering)
- [ ] JWT authentication
- [ ] Rate limiting (10 req/min per user)
- [ ] Prompt injection detection (NeMo Guardrails)
- [ ] Audit logging (BaseX trail)

### ✅ User Experience
- [ ] Generative UI components
- [ ] Streaming responses (SSE)
- [ ] Approval gates UI
- [ ] Natural language interface

---

**Last Updated**: January 15, 2026  
**Next Review**: Weekly sprint planning  
**Document Owner**: Project Manager + Architecture Lead
