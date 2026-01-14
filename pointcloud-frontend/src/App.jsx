// src/App.jsx
import React, { useState, useEffect, useRef } from "react";
import FileUpload from "./components/FileUpload";
import PointCloudViewer from "./components/PointCloudViewer";
import GraphViewer from "./components/GraphViewer";
import AnnotationPanel from "./components/AnnotationPanel";
import Loader from "./components/Loader";
import AccBrowser from "./components/AccBrowser";
import OssUploadTranslate from "./components/OssUploadTranslate";
import ApsViewer from "./components/ApsViewer";
import "./ChatStyles.css";

const APS_API_URL =
  import.meta.env.VITE_APS_API_URL
  || (String(window.location.port) === "3001" ? window.location.origin : "http://127.0.0.1:3001");

/**
 Expected backend JSON contract for /upload:
 {
   scene_id: "Area_5_office_1_point",
   points: [[x,y,z], ...],
   labels: [0,1,2,...],
   segments: [{ segment_key: 0, semantic_name: "wall", centroid: [...], num_points: 123 }, ...],
   edges: [{ from:0, to:1, distance:1.2 }, ...]
 }
*/

// Tab options for the main viewer area
const VIEWER_TABS = [
  { id: "aps", label: "APS Viewer" },
  { id: "pointcloud", label: "PointCloud" },
];

export default function App() {
  const [sceneData, setSceneData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null); // { pointIndex, label, segmentId }

  const [apsStatus, setApsStatus] = useState({
    loading: true,
    twoLeggedConfigured: false,
    threeLeggedConfigured: false,
    missing: [],
    oauthMissing: [],
  });

  // APS Viewer state
  const [viewerUrn, setViewerUrn] = useState("");
  const [viewerAuth, setViewerAuth] = useState("app");

  // Active viewer tab
  const [activeTab, setActiveTab] = useState("aps");

  // Chat UI state
  const [chatOpen, setChatOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      try {
        const res = await fetch(`${APS_API_URL}/aps/config`, { headers: { Accept: "application/json" } });
        const json = await res.json();
        if (cancelled) return;
        setApsStatus({ loading: false, ...json });
      } catch {
        if (cancelled) return;
        setApsStatus((s) => ({ ...s, loading: false }));
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const handleUpload = async (file) => {
    setLoading(true);
    setSelected(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await fetch("http://localhost:8000/upload", { method: "POST", body: fd });
      if (!res.ok) throw new Error(`Upload failed (${res.status})`);
      const json = await res.json();
      // Defensive: ensure keys exist
      json.points = json.points || [];
      json.labels = json.labels || [];
      json.segments = json.segments || [];
      json.edges = json.edges || [];
      setSceneData(json);
    } catch (err) {
      console.error("Upload error", err);
      alert("Upload failed — check console");
    } finally {
      setLoading(false);
    }
  };

  // pointcloud click handler
  const handlePointClick = ({ pointIndex, label, segmentId }) => {
    setSelected({ pointIndex, label, segmentId });
    // optionally: query backend/neo4j for metadata on segmentId
  };

  // graph node click handler - receives nodeId (string)
  const handleGraphClick = (nodeId) => {
    // nodeId expected like `${scene_id}_sem_${segment_key}`
    const parts = String(nodeId).split("_sem_");
    const label = parts.length === 2 ? Number(parts[1]) : null;
    // find first point index of that label (stable mapping)
    let firstIndex = null;
    if (sceneData && Array.isArray(sceneData.labels)) {
      firstIndex = sceneData.labels.indexOf(label);
      if (firstIndex === -1) firstIndex = null;
    }
    setSelected({ pointIndex: firstIndex, label, segmentId: nodeId });
  };

  // Chat toggle
  const toggleChat = () => setChatOpen((s) => !s);

  const loginToAps = () => {
    if (!apsStatus.threeLeggedConfigured) {
      const missing = Array.isArray(apsStatus.oauthMissing) && apsStatus.oauthMissing.length
        ? apsStatus.oauthMissing.join(", ")
        : "APS_CLIENT_ID, APS_CLIENT_SECRET, APS_CALLBACK_URL";
      alert(`APS OAuth is not configured. Set ${missing} in backend/aps-service/.env, then restart the APS service.`);
      return;
    }
    const returnTo = window.location.href;
    window.location.href = `${APS_API_URL}/aps/oauth/login?returnTo=${encodeURIComponent(returnTo)}`;
  };

  const handleUrnReady = ({ urn, auth }) => {
    setViewerUrn(urn);
    setViewerAuth(auth || "app");
  };

  return (
    <div className="min-h-screen p-5" style={{ background: 'var(--bg-primary)' }}>
      {/* TCS Header */}
      <header className="tcs-header mb-5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex items-center justify-center w-10 h-10 rounded-lg" style={{ background: 'rgba(255,255,255,0.15)' }}>
              <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
              </svg>
            </div>
            <div>
              <h1 className="text-xl font-bold">SMART BIM</h1>
              <p className="text-xs opacity-75">APS + PointCloud Digital Twin Platform</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="tcs-badge flex items-center gap-2" style={{ background: 'rgba(255,255,255,0.15)', color: 'white' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: apsStatus.twoLeggedConfigured ? '#10b981' : '#ef4444' }} />
              {apsStatus.twoLeggedConfigured ? 'Connected' : 'Not Configured'}
            </span>
            <button
              onClick={loginToAps}
              disabled={!apsStatus.threeLeggedConfigured}
              className="tcs-btn tcs-btn-primary"
              style={{ background: apsStatus.threeLeggedConfigured ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.05)' }}
              title="Login to Autodesk Platform Services (3-legged OAuth)"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4M10 17l5-5-5-5M13.8 12H3"/>
              </svg>
              APS Login
            </button>
          </div>
        </div>
      </header>

      {/* Viewer Mode Tabs */}
      <div className="flex items-center gap-1 mb-4 p-1 rounded-xl" style={{ background: 'var(--surface)', border: '1px solid var(--border-light)' }}>
        {VIEWER_TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tcs-tab ${activeTab === tab.id ? 'active' : ''}`}
            style={{
              flex: 1,
              padding: '12px 24px',
              borderRadius: '10px',
              background: activeTab === tab.id ? 'var(--tcs-blue)' : 'transparent',
              color: activeTab === tab.id ? 'white' : 'var(--text-secondary)',
              fontWeight: 600,
              border: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8
            }}
          >
            {tab.id === 'aps' && (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4"/>
                <path d="M18 20V10h3v10"/>
                <circle cx="19.5" cy="6" r="2"/>
              </svg>
            )}
            {tab.id === 'pointcloud' && (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="2"/>
                <circle cx="6" cy="6" r="1.5"/>
                <circle cx="18" cy="6" r="1.5"/>
                <circle cx="6" cy="18" r="1.5"/>
                <circle cx="18" cy="18" r="1.5"/>
                <circle cx="12" cy="5" r="1"/>
                <circle cx="12" cy="19" r="1"/>
                <circle cx="5" cy="12" r="1"/>
                <circle cx="19" cy="12" r="1"/>
              </svg>
            )}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Viewer Panel */}
      <div className="glass p-4" style={{ minHeight: "75vh" }}>
        {activeTab === "aps" && (
          <ApsViewerPanel
            apsBaseUrl={APS_API_URL}
            viewerUrn={viewerUrn}
            setViewerUrn={setViewerUrn}
            viewerAuth={viewerAuth}
            setViewerAuth={setViewerAuth}
            onUrnReady={handleUrnReady}
          />
        )}

        {activeTab === "pointcloud" && (
          <PointCloudPanel
            sceneData={sceneData}
            selected={selected}
            loading={loading}
            onUpload={handleUpload}
            onPointClick={handlePointClick}
            onGraphClick={handleGraphClick}
          />
        )}
      </div>

      {/* Floating Chat Button */}
      <button className="chat-fab" onClick={toggleChat} title="Open scene assistant">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="white" strokeWidth="2">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
        </svg>
      </button>

      {/* Chat modal */}
      {chatOpen && (
        <ChatModal
          onClose={() => setChatOpen(false)}
          sceneId={sceneData?.scene_id ?? null}
          onHighlightSegment={(segmentId) => {
            const parts = String(segmentId).split("_sem_");
            const label = parts.length === 2 ? Number(parts[1]) : null;
            let firstIndex = null;
            if (sceneData && Array.isArray(sceneData.labels)) {
              firstIndex = sceneData.labels.indexOf(label);
              if (firstIndex === -1) firstIndex = null;
            }
            setSelected({ pointIndex: firstIndex, label, segmentId });
            setActiveTab("pointcloud"); // Switch to pointcloud tab to show highlight
          }}
        />
      )}
    </div>
  );
}

/* ---------------- APS Viewer Panel ---------------- */
function ApsViewerPanel({ apsBaseUrl, viewerUrn, setViewerUrn, viewerAuth, setViewerAuth, onUrnReady }) {
  return (
    <>
      <div className="flex items-center justify-between mb-4 pb-3" style={{ borderBottom: '1px solid var(--border-light)' }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg" style={{ background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))' }}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" strokeWidth="2">
              <path d="M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4"/>
              <path d="M18 20V10h3v10"/>
              <circle cx="19.5" cy="6" r="2"/>
            </svg>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>APS Model Viewer</div>
            <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>Autodesk Platform Services Integration</div>
          </div>
        </div>
        {viewerUrn && (
          <span className="tcs-badge flex items-center gap-2">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            URN Loaded
          </span>
        )}
      </div>

      <div className="flex gap-4" style={{ height: "calc(75vh - 80px)" }}>
        <div className="w-[400px] min-w-[320px] max-w-[480px] overflow-auto pr-2" style={{ borderRight: '1px solid var(--border-light)' }}>
          <div className="mb-4">
            <AccBrowser apsBaseUrl={apsBaseUrl} onUrnReady={onUrnReady} />
          </div>

          <div className="my-4" style={{ height: 1, background: 'var(--border-light)' }} />

          <OssUploadTranslate apsBaseUrl={apsBaseUrl} onUrnReady={onUrnReady} />

          <div className="my-4" style={{ height: 1, background: 'var(--border-light)' }} />

          <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
            <div className="font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Viewer Options</div>
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-2">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Token Source</span>
                <select
                  value={viewerAuth}
                  onChange={(e) => setViewerAuth(e.target.value)}
                  className="tcs-select"
                >
                  <option value="app">2-legged (Application)</option>
                  <option value="user">3-legged (User)</option>
                </select>
              </label>

              <label className="flex flex-col gap-2">
                <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Load URN Manually</span>
                <input
                  value={viewerUrn}
                  onChange={(e) => setViewerUrn(e.target.value)}
                  placeholder="Paste URN (base64url)"
                  className="tcs-input"
                />
              </label>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-hidden rounded-xl" style={{ border: '1px solid var(--border-light)', background: 'var(--bg-primary)' }}>
          <ApsViewer apsBaseUrl={apsBaseUrl} urn={viewerUrn} auth={viewerAuth} />
        </div>
      </div>
    </>
  );
}

/* ---------------- PointCloud Panel (submodule) ---------------- */
function PointCloudPanel({ sceneData, selected, loading, onUpload, onPointClick, onGraphClick }) {
  return (
    <>
      <div className="flex items-center justify-between mb-4 pb-3" style={{ borderBottom: '1px solid var(--border-light)' }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-lg" style={{ background: 'linear-gradient(135deg, var(--tcs-orange), #CC5200)' }}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" strokeWidth="2">
              <circle cx="12" cy="12" r="3"/>
              <circle cx="6" cy="6" r="2"/>
              <circle cx="18" cy="6" r="2"/>
              <circle cx="6" cy="18" r="2"/>
              <circle cx="18" cy="18" r="2"/>
            </svg>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>PointCloud Digital Twin</div>
            <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
              {sceneData ? `Scene: ${sceneData.scene_id}` : "Upload a .npy or .txt pointcloud file"}
            </div>
          </div>
        </div>
        {sceneData && (
          <span className="tcs-badge tcs-badge-success flex items-center gap-2">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 6L9 17l-5-5"/>
            </svg>
            Scene Loaded
          </span>
        )}
      </div>

      <div className="mb-4">
        <FileUpload onUpload={onUpload} />
      </div>

      {loading && (
        <div className="mb-4">
          <Loader text="Processing... this can take a few seconds" />
        </div>
      )}

      {/* Top row: pointcloud (left) + annotation (right) */}
      <div className="flex gap-4 mb-4" style={{ height: "45vh" }}>
        <div className="flex-1 glass p-3 overflow-hidden">
          {sceneData ? (
            <PointCloudViewer
              data={sceneData}
              selected={selected}
              onSegmentClick={onPointClick}
            />
          ) : (
            <div className="h-full flex items-center justify-center" style={{ color: 'var(--text-muted)' }}>
              <div className="text-center">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 opacity-50">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
                </svg>
                <div>Upload a pointcloud to preview</div>
              </div>
            </div>
          )}
        </div>

        <div className="w-72 glass p-3 overflow-auto">
          <AnnotationPanel selected={selected} sceneData={sceneData} />
        </div>
      </div>

      {/* Bottom row: graph viewer */}
      <div className="glass p-3" style={{ height: "20vh" }}>
        {sceneData ? (
          <GraphViewer
            sceneId={sceneData.scene_id}
            segments={sceneData.segments}
            edges={sceneData.edges}
            onNodeClick={onGraphClick}
            selectedSegmentId={selected?.segmentId ?? null}
          />
        ) : (
          <div className="h-full flex items-center justify-center" style={{ color: 'var(--text-muted)' }}>
            Graph will appear here after upload
          </div>
        )}
      </div>
    </>
  );
}

/* ---------------- ChatModal & helpers  ---------------- */
function ChatModal({ onClose, sceneId, onHighlightSegment }) {
  const [messages, setMessages] = useState([
    { id: "sys", from: "assistant", text: "Hi — ask me about this scene (e.g. 'Which objects are near the window?')." },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    const userMsg = { id: `u${Date.now()}`, from: "user", text: trimmed };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const payload = {
        question: trimmed,
        scene_id: sceneId,
      };

      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Server error");
      }

      const body = await res.json();
      // body: { llm_text, cypher, results, highlight_segment_id (optional) }
      const assistantMsg = {
      id: `a${Date.now()}`,
      from: "assistant",
  // prefer conversational_reply (friendly), then final_answer, then legacy llm_text
      text: body.conversational_reply || body.final_answer || body.llm_text || "No answer from LLM.",
      cypher: body.cypher,
      results: body.results,
  };


      setMessages((m) => [...m, assistantMsg]);

      // optional: if backend suggests a segment to highlight, invoke parent callback
      if (body.highlight_segment_id && typeof onHighlightSegment === "function") {
        onHighlightSegment(body.highlight_segment_id);
      }
    } catch (err) {
      setMessages((m) => [...m, { id: `err${Date.now()}`, from: "assistant", text: `Error: ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) === false) {
      e.preventDefault();
      sendMessage();
    }
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
      setInput((t) => t + "\n");
    }
  };

  return (
    <div className="chat-modal-backdrop" onMouseDown={onClose}>
      <div className="chat-modal" onMouseDown={(e) => e.stopPropagation()}>
        <div className="chat-header">
          <div>
            <div className="chat-title">Scene Assistant</div>
            <div className="chat-sub">Ask spatial questions about this scene</div>
          </div>
          <button className="chat-close" onClick={onClose}>
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div className="chat-body">
          {messages.map((m) => (
            <ChatMessage key={m.id} msg={m} />
          ))}
          {loading && <div className="chat-loading">Assistant is thinking…</div>}
          <div ref={bottomRef} />
        </div>

        <div className="chat-footer">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Ask: e.g. 'What objects are within 1m of the window?'"
            rows={2}
            className="chat-input"
            disabled={loading}
          />
          <div className="chat-actions">
            <button className="btn" onClick={sendMessage} disabled={loading || !input.trim()}>
              {loading ? "Thinking…" : "Send"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatMessage({ msg }) {
  if (!msg) return null;
  if (msg.from === "user") {
    return (
      <div className="message-row user">
        <div className="message-bubble user">{msg.text}</div>
      </div>
    );
  }

  return (
    <div className="message-row assistant">
      <div className="message-bubble assistant">
        <div dangerouslySetInnerHTML={{ __html: escapeHtml(msg.text).replace(/\n/g, "<br/>") }} />
        {msg.cypher && (
          <pre className="cypher-block"><code>{msg.cypher}</code></pre>
        )}
        {Array.isArray(msg.results) && msg.results.length > 0 && (
          <div className="results-block">
            <strong>Results:</strong>
            <pre className="results-pre">{JSON.stringify(msg.results, null, 2)}</pre>
          </div>
        )}
      </div>
    </div>
  );
}

/* small helper to escape HTML for safety */
function escapeHtml(s = "") {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
