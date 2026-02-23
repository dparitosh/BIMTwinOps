/**
 * OpenApiTab.jsx — API & Agents Management Dashboard
 *
 * Provides:
 *  1. System health overview (Backend, Neo4j, Ollama, APS)
 *  2. Agent roster with descriptions & status
 *  3. Quick-test panel for key endpoints
 *  4. Collapsible Swagger UI embed
 *  5. GraphQL playground link
 */
import React, { useState, useEffect, useCallback } from "react";
import ApiResponseViewer from "./ApiResponseViewer";

const API_URL = import.meta.env.VITE_BACKEND_API_URL || "http://127.0.0.1:8008";
const APS_URL = import.meta.env.VITE_APS_API_URL || "http://127.0.0.1:3001";
const OLLAMA_URL = import.meta.env.VITE_OLLAMA_URL || "http://localhost:11434";
const NEO4J_URI = import.meta.env.VITE_NEO4J_URI || "bolt://localhost:7687";

// ── Agent Registry ──────────────────────────────────────────────────────
const AGENTS = [
  { id: "orchestrator", name: "Agent Orchestrator", description: "LangGraph state machine that routes queries to specialist agents", module: "agent_orchestrator.py", icon: "[CORE]" },
  { id: "query",    name: "Query Agent",       description: "Generates Cypher queries and searches the Knowledge Graph",          module: "query_agent.py",    icon: "[?]" },
  { id: "action",   name: "Action Agent",      description: "Executes write operations on the Knowledge Graph with HITL",        module: "action_agent.py",   icon: "[*]" },
  { id: "planning", name: "Planning Agent",    description: "Breaks complex tasks into multi-step execution plans",              module: "planning_agent.py", icon: "[LIST]" },
  { id: "executor", name: "Executor Agent",    description: "Executes approved action plans against backend services",            module: "executor_agent.py", icon: "[>>]" },
  { id: "compliance", name: "Compliance Agent", description: "Validates IFC models against bSDD standards & regulations",         module: "compliance_agent.py", icon: "[OK]" },
];

// ── Endpoint Groups ─────────────────────────────────────────────────────
const ENDPOINT_GROUPS = [
  {
    name: "Core",
    endpoints: [
      { method: "GET",  path: "/health/neo4j",     desc: "Neo4j health check" },
      { method: "POST", path: "/chat",             desc: "Chat with scene (Cypher + LLM)" },
      { method: "POST", path: "/upload",           desc: "Upload point cloud for segmentation" },
    ]
  },
  {
    name: "Knowledge Graph",
    endpoints: [
      { method: "GET",  path: "/api/kg/bsdd/dictionaries", desc: "List bSDD dictionaries" },
      { method: "POST", path: "/api/kg/bsdd/search",       desc: "Search bSDD classes" },
      { method: "GET",  path: "/api/kg/graph/stats",        desc: "Graph statistics" },
      { method: "POST", path: "/api/kg/check-compliance",   desc: "Check IFC compliance" },
      { method: "POST", path: "/api/kg/import/json",        desc: "Import JSON to KG" },
    ]
  },
  {
    name: "AI & Generative UI",
    endpoints: [
      { method: "POST", path: "/api/ui/generate",          desc: "Generate UI components via AI" },
      { method: "GET",  path: "/api/ui/stream/{threadId}",  desc: "SSE stream for agent updates" },
      { method: "POST", path: "/api/kg/ai/semantic-search", desc: "Semantic search (embeddings)" },
      { method: "POST", path: "/api/kg/ai/chat",           desc: "KG-powered AI chat" },
    ]
  },
  {
    name: "Scheduling",
    endpoints: [
      { method: "GET",  path: "/api/schedules/tasks",         desc: "List schedule tasks" },
      { method: "POST", path: "/api/schedules/tasks",         desc: "Create a schedule task" },
      { method: "PATCH",path: "/api/schedules/tasks/{id}",    desc: "Update a task" },
      { method: "DELETE",path: "/api/schedules/tasks/{id}",   desc: "Delete a task" },
    ]
  },
  {
    name: "Approvals (HITL)",
    endpoints: [
      { method: "GET",  path: "/api/approvals/pending",      desc: "List pending approvals" },
      { method: "POST", path: "/api/approvals/{id}/approve",  desc: "Approve an action" },
      { method: "POST", path: "/api/approvals/{id}/reject",   desc: "Reject an action" },
    ]
  },
  {
    name: "GraphQL",
    endpoints: [
      { method: "GET",  path: "/api/graphql",                desc: "GraphiQL interactive playground" },
    ]
  },
];

// ── Health Check helpers ────────────────────────────────────────────────
async function checkHealth(url, timeout = 5000) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeout);
  try {
    const res = await fetch(url, { signal: ctrl.signal });
    clearTimeout(timer);
    if (!res.ok) return { ok: false, status: res.status, ms: 0 };
    const t0 = performance.now();
    const data = await res.json().catch(() => ({}));
    return { ok: true, status: res.status, data, ms: Math.round(performance.now() - t0) };
  } catch (e) {
    clearTimeout(timer);
    return { ok: false, error: e.message, ms: 0 };
  }
}

// ── Quick-test helper ───────────────────────────────────────────────────
async function quickTest(method, path, body = null) {
  const url = `${API_URL}${path}`;
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body && method !== "GET") opts.body = JSON.stringify(body);
  const t0 = performance.now();
  const res = await fetch(url, opts);
  const elapsed = Math.round(performance.now() - t0);
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = text; }
  return { status: res.status, ok: res.ok, ms: elapsed, data };
}

// =====================================================================
// Component
// =====================================================================
export default function OpenApiTab() {
  const [healthResults, setHealthResults] = useState({});
  const [healthLoading, setHealthLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("health");
  const [testResult, setTestResult] = useState(null);
  const [testLoading, setTestLoading] = useState(false);


  // ── Health checks ──
  const runHealthChecks = useCallback(async () => {
    setHealthLoading(true);
    const [backend, neo4j, aps, ollama] = await Promise.all([
      checkHealth(`${API_URL}/docs`),
      checkHealth(`${API_URL}/health/neo4j`),
      checkHealth(`${APS_URL}/aps/config`),
      checkHealth(`${OLLAMA_URL}/api/version`),
    ]);
    setHealthResults({ backend, neo4j, aps, ollama });
    setHealthLoading(false);
  }, []);

  useEffect(() => { runHealthChecks(); }, [runHealthChecks]);

  // ── Quick test ──
  const handleQuickTest = async (method, path) => {
    setTestLoading(true);
    setTestResult(null);
    try {
      const body = method === "POST" ? getDefaultBody(path) : null;
      const result = await quickTest(method, path, body);
      setTestResult({ method, path, body, ...result });
    } catch (err) {
      setTestResult({ method, path, ok: false, error: err.message, ms: 0 });
    } finally {
      setTestLoading(false);
    }
  };

  // ── Sections ──
  const sections = [
    { id: "health",    label: "System Health",   icon: "[HEALTH]" },
    { id: "agents",    label: "Agents",          icon: "[AGENT]" },
    { id: "endpoints", label: "Endpoints",       icon: "[API]" },
    { id: "swagger",   label: "Swagger UI",      icon: "[DOCS]" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", gap: 12 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 16px", background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border-light)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 24 }}>[API]</span>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)", margin: 0 }}>API & Agent Dashboard</h2>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0 }}>
              System health, agents, endpoints &bull; {ENDPOINT_GROUPS.reduce((s, g) => s + g.endpoints.length, 0)} endpoints &bull; {AGENTS.length} agents
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: 4, padding: 4, background: "var(--bg-tertiary)", borderRadius: 8 }}>
          {sections.map(s => (
            <button key={s.id} onClick={() => setActiveSection(s.id)}
              style={{ padding: "6px 14px", borderRadius: 6, border: "none", cursor: "pointer", background: activeSection === s.id ? "var(--tcs-blue)" : "transparent", color: activeSection === s.id ? "white" : "var(--text-secondary)", fontWeight: 500, fontSize: 12, display: "flex", alignItems: "center", gap: 4 }}>
              <span>{s.icon}</span> {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Section Content */}
      <div style={{ flex: 1, overflow: "auto" }}>
        {activeSection === "health" && <HealthSection results={healthResults} loading={healthLoading} onRefresh={runHealthChecks} />}
        {activeSection === "agents" && <AgentsSection />}
        {activeSection === "endpoints" && <EndpointsSection onTest={handleQuickTest} testResult={testResult} testLoading={testLoading} onClearResult={() => setTestResult(null)} />}
        {activeSection === "swagger" && <SwaggerSection />}
      </div>
    </div>
  );
}

// =====================================================================
// Sub-sections
// =====================================================================

function HealthSection({ results, loading, onRefresh }) {
  const services = [
    { key: "backend", label: "Backend API", url: `${API_URL}`, icon: "[API]", desc: "FastAPI server (port 8000)" },
    { key: "neo4j",   label: "Neo4j KG",    url: NEO4J_URI,     icon: "[DB]", desc: "Knowledge Graph database" },
    { key: "ollama",  label: "Ollama LLM",   url: OLLAMA_URL,    icon: "[AI]", desc: "Local AI model server" },
    { key: "aps",     label: "APS Service",  url: `${APS_URL}`,               icon: "[APS]", desc: "Autodesk Platform Services" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Service Health</h3>
        <button onClick={onRefresh} disabled={loading}
          style={{ padding: "6px 14px", borderRadius: 6, border: "1px solid var(--border-light)", background: "transparent", color: "var(--text-secondary)", cursor: "pointer", fontSize: 12 }}>
          {loading ? "Checking..." : "Refresh"}
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {services.map(svc => {
          const r = results[svc.key];
          const ok = r?.ok;
          const statusColor = loading ? "#f59e0b" : ok ? "#10b981" : "#ef4444";
          const statusText = loading ? "Checking..." : ok ? "Online" : "Offline";

          return (
            <div key={svc.key} style={{ padding: 16, background: "var(--surface)", borderRadius: 12, border: `1px solid ${statusColor}30`, display: "flex", alignItems: "flex-start", gap: 14 }}>
              <span style={{ fontSize: 28 }}>{svc.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)" }}>{svc.label}</span>
                  <span style={{ fontSize: 11, fontWeight: 700, padding: "2px 10px", borderRadius: 10, background: `${statusColor}18`, color: statusColor }}>{statusText}</span>
                </div>
                <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: "4px 0 0" }}>{svc.desc}</p>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", marginTop: 6, fontFamily: "monospace" }}>{svc.url}</div>
                {r && ok && r.data && (
                  <pre style={{ fontSize: 11, color: "#6b7280", margin: "6px 0 0", background: "var(--bg-tertiary)", padding: "6px 10px", borderRadius: 6, overflowX: "auto", maxHeight: 80 }}>
                    {JSON.stringify(r.data, null, 2).slice(0, 200)}
                  </pre>
                )}
                {r && !ok && r.error && (
                  <div style={{ fontSize: 11, color: "#ef4444", marginTop: 6 }}>{r.error}</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick stats */}
      <div style={{ display: "flex", gap: 12 }}>
        {[
          { label: "Total Endpoints",  value: ENDPOINT_GROUPS.reduce((s, g) => s + g.endpoints.length, 0), color: "#3b82f6" },
          { label: "AI Agents",        value: AGENTS.length,                                                 color: "#8b5cf6" },
          { label: "Services Online",  value: Object.values(results).filter(r => r?.ok).length,             color: "#10b981" },
          { label: "Services Total",   value: services.length,                                               color: "#6b7280" },
        ].map(s => (
          <div key={s.label} style={{ flex: 1, padding: "12px 16px", background: "var(--surface)", borderRadius: 10, border: "1px solid var(--border-light)" }}>
            <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
            <div style={{ fontSize: 11, color: "var(--text-secondary)" }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function AgentsSection() {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Agent Roster</h3>
      <p style={{ margin: 0, fontSize: 12, color: "var(--text-secondary)" }}>
        BIMTwinOps uses a LangGraph-based multi-agent architecture. The Orchestrator routes requests to specialist agents based on intent classification.
      </p>

      {/* Architecture diagram */}
      <div style={{ padding: 16, background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border-light)" }}>
        <div style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)", marginBottom: 10 }}>Architecture Flow</div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 6, flexWrap: "wrap", fontSize: 12, color: "var(--text-secondary)" }}>
          <FlowBox label="User Query" color="#3b82f6" />
          <Arrow />
          <FlowBox label="[CORE] Orchestrator" color="#8b5cf6" />
          <Arrow />
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <FlowBox label="[?] Query" color="#10b981" small />
            <FlowBox label="[*] Action" color="#f59e0b" small />
            <FlowBox label="[LIST] Planning" color="#6366f1" small />
          </div>
          <Arrow />
          <FlowBox label="[>>] Executor" color="#ec4899" />
          <Arrow />
          <FlowBox label="[OK] HITL Approval" color="#10b981" />
        </div>
      </div>

      {/* Agent cards */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12 }}>
        {AGENTS.map(agent => (
          <div key={agent.id} style={{ padding: 16, background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border-light)", display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 24 }}>{agent.icon}</span>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{agent.name}</div>
                <div style={{ fontSize: 11, color: "var(--text-secondary)", fontFamily: "monospace" }}>{agent.module}</div>
              </div>
            </div>
            <p style={{ fontSize: 12, color: "var(--text-secondary)", margin: 0, lineHeight: 1.5 }}>{agent.description}</p>
            <div style={{ marginTop: "auto", display: "flex", alignItems: "center", gap: 6 }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981" }} />
              <span style={{ fontSize: 11, color: "#10b981", fontWeight: 600 }}>Loaded</span>
            </div>
          </div>
        ))}
      </div>

      {/* MCP / Tools info */}
      <div style={{ padding: 16, background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border-light)" }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)", marginBottom: 8 }}>MCP Tool Servers</div>
        <div style={{ display: "flex", gap: 12 }}>
          {[
            { name: "Neo4j MCP", desc: "Cypher queries, schema ops, node CRUD", icon: "[DB]" },
            { name: "bSDD MCP",  desc: "Dictionary search, class lookup, IFC mapping", icon: "[DOCS]" },
            { name: "BaseX MCP", desc: "XML/IFC document storage & XQuery", icon: "[XML]" },
            { name: "OpenSearch MCP", desc: "Full-text search & semantic embeddings", icon: "[?]" },
          ].map(t => (
            <div key={t.name} style={{ flex: 1, padding: "10px 12px", background: "var(--bg-tertiary)", borderRadius: 8, fontSize: 12 }}>
              <div style={{ fontWeight: 600, color: "var(--text-primary)" }}>{t.icon} {t.name}</div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11, marginTop: 4 }}>{t.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EndpointsSection({ onTest, testResult, testLoading, onClearResult }) {
  const [expandedGroup, setExpandedGroup] = useState(null);

  const methodColor = { GET: "#10b981", POST: "#3b82f6", PATCH: "#f59e0b", DELETE: "#ef4444", PUT: "#8b5cf6" };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>API Endpoints</h3>
        <a href={`${API_URL}/api/graphql`} target="_blank" rel="noopener noreferrer"
          style={{ fontSize: 12, color: "var(--tcs-blue)", textDecoration: "none", fontWeight: 600 }}>
          Open GraphiQL Playground &rarr;
        </a>
      </div>

      {ENDPOINT_GROUPS.map(group => (
        <div key={group.name} style={{ background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border-light)", overflow: "hidden" }}>
          <button onClick={() => setExpandedGroup(expandedGroup === group.name ? null : group.name)}
            style={{ width: "100%", padding: "12px 16px", border: "none", background: expandedGroup === group.name ? "var(--bg-tertiary)" : "transparent", cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center", textAlign: "left" }}>
            <span style={{ fontWeight: 600, fontSize: 13, color: "var(--text-primary)" }}>{group.name}</span>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{group.endpoints.length} endpoints</span>
              <span style={{ transform: expandedGroup === group.name ? "rotate(180deg)" : "none", transition: "transform 0.2s", fontSize: 12, color: "var(--text-secondary)" }}>▼</span>
            </div>
          </button>

          {expandedGroup === group.name && (
            <div style={{ borderTop: "1px solid var(--border-light)" }}>
              {group.endpoints.map((ep, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", padding: "10px 16px", borderBottom: i < group.endpoints.length - 1 ? "1px solid var(--border-light)" : "none", gap: 12 }}>
                  <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4, background: `${methodColor[ep.method]}18`, color: methodColor[ep.method], minWidth: 50, textAlign: "center" }}>{ep.method}</span>
                  <code style={{ fontFamily: "monospace", fontSize: 12, color: "var(--text-primary)", flex: 1 }}>{ep.path}</code>
                  <span style={{ fontSize: 11, color: "var(--text-secondary)", flex: 1 }}>{ep.desc}</span>
                  {!ep.path.includes("{") && (
                    <button onClick={() => onTest(ep.method, ep.path)} disabled={testLoading}
                      style={{ padding: "4px 12px", borderRadius: 4, border: "1px solid var(--border-light)", background: "transparent", cursor: "pointer", fontSize: 11, color: "var(--text-secondary)" }}>
                      Test
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* Test result */}
      {testResult && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: 16, background: "var(--surface)", borderRadius: 12, border: `1px solid ${testResult.ok ? "#10b981" : "#ef4444"}40` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontFamily: "monospace", fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 4, background: `${methodColor[testResult.method]}18`, color: methodColor[testResult.method] }}>{testResult.method}</span>
              <code style={{ fontSize: 12, color: "var(--text-primary)" }}>{testResult.path}</code>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span style={{ fontSize: 11, color: "var(--text-secondary)" }}>{testResult.ms}ms</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: testResult.ok ? "#10b981" : "#ef4444" }}>{testResult.status || "ERR"}</span>
              <button onClick={onClearResult} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-secondary)", fontSize: 16 }}>&times;</button>
            </div>
          </div>
          
          {/* Request body if POST/PUT/PATCH */}
          {testResult.body && (
            <ApiResponseViewer response={testResult.body} title="Request Body" />
          )}
          
          {/* Response data */}
          {testResult.data && (
            <ApiResponseViewer 
              response={testResult.data} 
              title={`Response (${testResult.status || 'ERR'})`} 
            />
          )}
          
          {/* Error message if failed */}
          {testResult.error && (
            <div style={{ 
              marginTop: 16, 
              padding: 16, 
              background: '#fee2e2', 
              border: '1px solid #ef4444', 
              borderRadius: 12,
              color: '#991b1b'
            }}>
              <div style={{ fontWeight: 600, marginBottom: 8 }}>Error</div>
              <div style={{ fontFamily: 'monospace', fontSize: 12 }}>{testResult.error}</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SwaggerSection() {
  // Lazy-load swagger-ui-react only when this section is active
  const [SwaggerUI, setSwaggerUI] = useState(null);

  useEffect(() => {
    import("swagger-ui-react").then(mod => setSwaggerUI(() => mod.default));
    // CSS should already be imported globally or handled by the build
    import("swagger-ui-react/swagger-ui.css");
  }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h3 style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--text-primary)" }}>Swagger / OpenAPI</h3>
        <a href={`${API_URL}/docs`} target="_blank" rel="noopener noreferrer"
          style={{ fontSize: 12, color: "var(--tcs-blue)", textDecoration: "none" }}>Open in new tab &rarr;</a>
      </div>
      <div style={{ background: "var(--surface)", borderRadius: 12, border: "1px solid var(--border-light)", padding: 16, minHeight: 400 }}>
        {SwaggerUI ? (
          <SwaggerUI url={`${API_URL}/openapi.json`} docExpansion="list" />
        ) : (
          <div style={{ padding: 40, textAlign: "center", color: "var(--text-secondary)" }}>Loading Swagger UI...</div>
        )}
      </div>
    </div>
  );
}

// ── Tiny helper components ──────────────────────────────────────────────
function FlowBox({ label, color, small }) {
  return (
    <div style={{
      padding: small ? "4px 10px" : "8px 14px",
      borderRadius: 8,
      background: `${color}18`,
      border: `1px solid ${color}40`,
      color,
      fontWeight: 600,
      fontSize: small ? 11 : 12,
      whiteSpace: "nowrap",
    }}>{label}</div>
  );
}

function Arrow() {
  return <span style={{ fontSize: 16, color: "var(--text-secondary)" }}>&rarr;</span>;
}

// ── Default POST bodies for quick-test ──────────────────────────────────
function getDefaultBody(path) {
  if (path.includes("/chat")) return { question: "How many segments are there?", scene_id: null };
  if (path.includes("/bsdd/search")) return { query: "wall", language: "en" };
  if (path.includes("/ui/generate")) return { user_input: "Show me building stats" };
  if (path.includes("/check-compliance")) return { ifc_entity: "IfcWall", properties: {} };
  if (path.includes("/import/json")) return { nodes: [], relationships: [] };
  if (path.includes("/schedules/tasks") && !path.includes("{")) return { name: "Test Task", start: "2026-03-01", end: "2026-03-15", progress: 0, status: "not-started" };
  return {};
}
