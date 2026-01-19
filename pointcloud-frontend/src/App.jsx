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
import ApsViewerExtended, { AVAILABLE_EXTENSIONS } from "./components/ApsViewerExtended";
import AgentInterface from "./components/AgentInterface";
// Enterprise Pages
import EnterpriseDashboard from "./components/EnterpriseDashboard";
import ProjectScheduling from "./components/ProjectScheduling";
import ModelAnalytics from "./components/ModelAnalytics";
import "./ChatStyles.css";

const APS_API_URL =
  import.meta.env.VITE_APS_API_URL
  || (String(window.location.port) === "3001" ? window.location.origin : "http://127.0.0.1:3001");

// In dev mode, prefer relative URLs so Vite proxy handles routing.
// In production or if VITE_BACKEND_API_URL is explicitly set, use the full URL.
const BACKEND_API_URL =
  import.meta.env.VITE_BACKEND_API_URL || (import.meta.env.DEV ? "" : "http://127.0.0.1:8000");

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
  { id: "agent", label: "AI Assistant", icon: "M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" },
  { id: "bim", label: "BIM Viewer", icon: "M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4M18 20V10h3v10" },
  { id: "scheduling", label: "Scheduling", icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" },
  { id: "analytics", label: "Analytics", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { id: "pointcloud", label: "PointCloud", icon: "M12 12m-3 0a3 3 0 106 0 3 3 0 10-6 0M6 6m-2 0a2 2 0 104 0 2 2 0 10-4 0M18 6m-2 0a2 2 0 104 0 2 2 0 10-4 0M6 18m-2 0a2 2 0 104 0 2 2 0 10-4 0M18 18m-2 0a2 2 0 104 0 2 2 0 10-4 0" },
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
  const [activeTab, setActiveTab] = useState("agent");

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
      const res = await fetch(`${BACKEND_API_URL}/upload`, { method: "POST", body: fd });
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
    console.log('[App] handlePointClick called:', { pointIndex, label, segmentId });
    setSelected({ pointIndex, label, segmentId });
    console.log('[App] Selected state will be updated to:', { pointIndex, label, segmentId });
    // optionally: query backend/neo4j for metadata on segmentId
  };

  // Debug: Log selected state changes
  useEffect(() => {
    console.log('[App] ✅ Selected state changed:', selected);
    console.log('[App] ✅ selectedSegmentId prop for PointCloudViewer:', selected?.segmentId);
  }, [selected]);

  // graph node click handler - receives nodeId (string)
  const handleGraphClick = (nodeId) => {
    console.log('[App] Graph node clicked:', nodeId);
    // nodeId expected like `${scene_id}_sem_${segment_key}`
    const parts = String(nodeId).split("_sem_");
    const labelStr = parts.length === 2 ? parts[1] : null;
    const label = labelStr ? Number(labelStr) : null;
    
    console.log('[App] Parsed label from graph click:', { nodeId, label, labelStr });
    
    // find first point index of that label (stable mapping)
    let firstIndex = null;
    if (sceneData && Array.isArray(sceneData.labels) && label !== null) {
      firstIndex = sceneData.labels.indexOf(label);
      if (firstIndex === -1) {
        // Try string version
        firstIndex = sceneData.labels.indexOf(String(label));
      }
      if (firstIndex === -1) firstIndex = null;
    }
    
    console.log('[App] Setting selected state:', { segmentId: nodeId, label, firstIndex });
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
              <h1 className="text-xl font-bold">BIMTwinOps</h1>
              <p className="text-xs opacity-75">Enterprise Digital Twin Operations Platform</p>
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
              padding: '12px 16px',
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
              gap: 8,
              fontSize: 13
            }}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <path d={tab.icon} />
            </svg>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main Viewer Panel */}
      <div className="glass p-4" style={{ minHeight: "75vh" }}>
        {activeTab === "agent" && (
          <AgentInterface />
        )}

        {activeTab === "bim" && (
          <UnifiedBimViewer
            apsBaseUrl={APS_API_URL}
            viewerUrn={viewerUrn}
            setViewerUrn={setViewerUrn}
            viewerAuth={viewerAuth}
            setViewerAuth={setViewerAuth}
            onUrnReady={handleUrnReady}
          />
        )}

        {activeTab === "scheduling" && (
          <ProjectScheduling
            apsBaseUrl={APS_API_URL}
            viewerUrn={viewerUrn}
            viewerAuth={viewerAuth}
          />
        )}

        {activeTab === "analytics" && (
          <ModelAnalytics
            apsBaseUrl={APS_API_URL}
            viewerUrn={viewerUrn}
            viewerAuth={viewerAuth}
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

/* ---------------- Unified BIM Viewer (merged Dashboard + APS) ---------------- */
function UnifiedBimViewer({ apsBaseUrl, viewerUrn, setViewerUrn, viewerAuth, setViewerAuth, onUrnReady }) {
  const viewerRef = useRef(null);
  const [leftPanelOpen, setLeftPanelOpen] = useState(true);
  const [rightPanelOpen, setRightPanelOpen] = useState(true);
  const [activeLeftTab, setActiveLeftTab] = useState("files"); // "files" or "upload"
  const [activeRightTab, setActiveRightTab] = useState("extensions"); // "extensions" or "stats"
  const [enabledExtensions, setEnabledExtensions] = useState([]);
  const [selectedElements, setSelectedElements] = useState([]);
  const [modelStats, setModelStats] = useState(null);
  const [selectedTool, setSelectedTool] = useState(null); // For tool detail navigation

  // Handle extension toggle
  const toggleExtension = async (extId) => {
    if (enabledExtensions.includes(extId)) {
      setEnabledExtensions(prev => prev.filter(e => e !== extId));
      viewerRef.current?.unloadExtension(extId);
    } else {
      setEnabledExtensions(prev => [...prev, extId]);
      await viewerRef.current?.loadExtension(extId);
    }
  };

  // Handle model loaded
  const handleModelLoaded = (model) => {
    if (!model) return;
    const instanceTree = model.getInstanceTree();
    if (instanceTree) {
      setModelStats({
        nodeCount: instanceTree.nodeAccess.numNodes,
        rootId: instanceTree.getRootId(),
        name: model.getDocumentNode()?.name() || "Unknown",
      });
    }
  };

  // Handle selection change
  const handleSelectionChanged = (dbIds) => {
    setSelectedElements(dbIds);
  };

  return (
    <>
      {/* Header with stats and controls */}
      <div className="flex items-center justify-between mb-4 pb-3" style={{ borderBottom: '2px solid var(--border-light)' }}>
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl" style={{ background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))' }}>
            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="white" strokeWidth="2">
              <path d="M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4"/>
              <path d="M18 20V10h3v10"/>
            </svg>
          </div>
          <div>
            <div className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>BIM Viewer</div>
            <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
              {modelStats ? `${modelStats.name} • ${modelStats.nodeCount?.toLocaleString()} elements` : "Load a model to get started"}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {viewerUrn && (
            <span className="tcs-badge" style={{ background: 'var(--success)', color: 'white', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 6L9 17l-5-5"/>
              </svg>
              Model Loaded
            </span>
          )}
          <button 
            onClick={() => setLeftPanelOpen(!leftPanelOpen)}
            className="tcs-btn"
            style={{ padding: '8px 12px', background: leftPanelOpen ? 'var(--tcs-blue)' : 'var(--surface)' }}
            aria-label="Toggle file panel"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M3 7h18M3 12h18M3 17h18"/>
            </svg>
          </button>
          <button 
            onClick={() => setRightPanelOpen(!rightPanelOpen)}
            className="tcs-btn"
            style={{ padding: '8px 12px', background: rightPanelOpen ? 'var(--tcs-blue)' : 'var(--surface)' }}
            aria-label="Toggle tools panel"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
            </svg>
          </button>
        </div>
      </div>

      {/* Main layout with collapsible panels */}
      <div className="flex gap-4" style={{ height: "calc(100vh - 280px)", minHeight: "500px" }}>
        {/* Left Panel: File Management */}
        {leftPanelOpen && (
          <div className="glass p-4" style={{ width: '360px', minWidth: '320px', display: 'flex', flexDirection: 'column' }}>
            {/* Tab switcher */}
            <div className="flex gap-1 mb-4 p-1 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
              <button
                onClick={() => setActiveLeftTab("files")}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '6px',
                  background: activeLeftTab === "files" ? 'var(--tcs-blue)' : 'transparent',
                  color: activeLeftTab === "files" ? 'white' : 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 600
                }}
              >
                Files
              </button>
              <button
                onClick={() => setActiveLeftTab("upload")}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '6px',
                  background: activeLeftTab === "upload" ? 'var(--tcs-blue)' : 'transparent',
                  color: activeLeftTab === "upload" ? 'white' : 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 600
                }}
              >
                Upload
              </button>
            </div>

            {/* Panel content */}
            <div className="flex-1 overflow-auto">
              {activeLeftTab === "files" ? (
                <>
                  <AccBrowser apsBaseUrl={apsBaseUrl} onUrnReady={onUrnReady} />
                  <div className="my-4" style={{ height: 1, background: 'var(--border-light)' }} />
                  <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
                    <div className="font-semibold mb-3" style={{ color: 'var(--text-primary)', fontSize: '14px' }}>Manual URN</div>
                    <input
                      value={viewerUrn}
                      onChange={(e) => setViewerUrn(e.target.value)}
                      placeholder="Paste URN (base64url)"
                      className="tcs-input"
                      style={{ width: '100%', fontSize: '13px' }}
                    />
                    <div className="mt-3">
                      <label className="flex flex-col gap-2">
                        <span className="font-medium" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Auth Type</span>
                        <select
                          value={viewerAuth}
                          onChange={(e) => setViewerAuth(e.target.value)}
                          className="tcs-select"
                          style={{ fontSize: '13px' }}
                        >
                          <option value="app">2-legged (App)</option>
                          <option value="user">3-legged (User)</option>
                        </select>
                      </label>
                    </div>
                  </div>
                </>
              ) : (
                <OssUploadTranslate apsBaseUrl={apsBaseUrl} onUrnReady={onUrnReady} />
              )}
            </div>
          </div>
        )}

        {/* Center: Viewer */}
        <div className="flex-1 glass overflow-hidden" style={{ minWidth: '400px', height: '100%' }}>
          <ApsViewerExtended 
            ref={viewerRef}
            apsBaseUrl={apsBaseUrl} 
            urn={viewerUrn} 
            auth={viewerAuth}
            onModelLoaded={handleModelLoaded}
            onSelectionChanged={handleSelectionChanged}
            style={{ width: '100%', height: '100%' }}
          />
        </div>

        {/* Right Panel: Extensions & Stats */}
        {rightPanelOpen && (
          <div className="glass p-4" style={{ width: '340px', minWidth: '300px', display: 'flex', flexDirection: 'column' }}>
            {/* Tab switcher */}
            <div className="flex gap-1 mb-4 p-1 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
              <button
                onClick={() => setActiveRightTab("extensions")}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '6px',
                  background: activeRightTab === "extensions" ? 'var(--tcs-blue)' : 'transparent',
                  color: activeRightTab === "extensions" ? 'white' : 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 600
                }}
              >
                Tools
              </button>
              <button
                onClick={() => setActiveRightTab("stats")}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '6px',
                  background: activeRightTab === "stats" ? 'var(--tcs-blue)' : 'transparent',
                  color: activeRightTab === "stats" ? 'white' : 'var(--text-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '13px',
                  fontWeight: 600
                }}
              >
                Info
              </button>
            </div>

            {/* Panel content */}
            <div className="flex-1 overflow-auto">
              {activeRightTab === "extensions" ? (
                <div>
                  {/* Tool Detail Page */}
                  {selectedTool ? (
                    <div>
                      {/* Breadcrumb Navigation */}
                      <div className="mb-4">
                        <button
                          onClick={() => setSelectedTool(null)}
                          className="flex items-center gap-2 p-2 rounded hover:bg-gray-100 transition-colors"
                          style={{ border: 'none', background: 'none', cursor: 'pointer', color: 'var(--tcs-blue)', fontSize: '13px', fontWeight: 600 }}
                        >
                          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M19 12H5m7 7l-7-7 7-7"/>
                          </svg>
                          Back to Tool Library
                        </button>
                      </div>

                      {/* Tool Header */}
                      <div className="mb-4 p-4 rounded-lg" style={{ background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))', color: 'white' }}>
                        <div className="flex items-start gap-3 mb-3">
                          <div className="p-2 rounded-lg" style={{ background: 'rgba(255,255,255,0.2)' }}>
                            {selectedTool.icon}
                          </div>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: '18px', fontWeight: 700, marginBottom: '4px' }}>{selectedTool.name}</div>
                            <div style={{ fontSize: '13px', opacity: 0.9 }}>{selectedTool.category}</div>
                          </div>
                        </div>
                        {/* Enable/Disable Button */}
                        <button
                          onClick={() => toggleExtension(selectedTool.id)}
                          className="w-full p-3 rounded-lg font-semibold transition-all"
                          style={{
                            background: enabledExtensions.includes(selectedTool.id) ? 'rgba(255,255,255,0.2)' : 'white',
                            color: enabledExtensions.includes(selectedTool.id) ? 'white' : 'var(--tcs-blue)',
                            border: 'none',
                            cursor: 'pointer',
                            fontSize: '14px'
                          }}
                        >
                          {enabledExtensions.includes(selectedTool.id) ? '✓ Tool Enabled' : 'Enable This Tool'}
                        </button>
                      </div>

                      {/* Tool Description */}
                      <div className="mb-4">
                        <div className="font-semibold mb-2" style={{ fontSize: '14px', color: 'var(--text-primary)' }}>About This Tool</div>
                        <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)', fontSize: '13px', lineHeight: '1.6', color: 'var(--text-secondary)' }}>
                          {selectedTool.fullDescription}
                        </div>
                      </div>

                      {/* Use Cases */}
                      <div className="mb-4">
                        <div className="font-semibold mb-2" style={{ fontSize: '14px', color: 'var(--text-primary)' }}>Common Use Cases</div>
                        <div className="space-y-2">
                          {selectedTool.useCases.map((useCase, idx) => (
                            <div key={idx} className="flex items-start gap-2 p-3 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
                              <div style={{ color: 'var(--tcs-blue)', fontSize: '18px', marginTop: '2px' }}>→</div>
                              <div>
                                <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>{useCase.title}</div>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{useCase.description}</div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* How to Use */}
                      <div className="mb-4">
                        <div className="font-semibold mb-2" style={{ fontSize: '14px', color: 'var(--text-primary)' }}>How to Use</div>
                        <div className="space-y-2">
                          {selectedTool.steps.map((step, idx) => (
                            <div key={idx} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
                              <div className="flex items-center justify-center" style={{ width: '24px', height: '24px', borderRadius: '50%', background: 'var(--tcs-blue)', color: 'white', fontSize: '12px', fontWeight: 700, flexShrink: 0 }}>
                                {idx + 1}
                              </div>
                              <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: '1.5' }}>{step}</div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Tips */}
                      {selectedTool.tips && (
                        <div className="p-3 rounded-lg" style={{ background: '#FFF4E6', border: '2px solid var(--tcs-orange)' }}>
                          <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--tcs-orange)' }}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                              <path d="M12 2a7 7 0 015 11.9V17a3 3 0 01-3 3H10a3 3 0 01-3-3v-3.1A7 7 0 0112 2zm0 2a5 5 0 00-3.54 8.54l.54.5V17a1 1 0 001 1h4a1 1 0 001-1v-3.96l.54-.5A5 5 0 0012 4z"/>
                            </svg>
                            <div className="font-semibold" style={{ fontSize: '13px' }}>Pro Tips</div>
                          </div>
                          <div style={{ fontSize: '12px', color: '#8B4513', lineHeight: '1.5' }}>{selectedTool.tips}</div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Tool Library Dashboard */
                    <div>
                      {/* Header */}
                      <div className="mb-4">
                        <div className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '16px', marginBottom: '4px' }}>Tool Library</div>
                        <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Click any tool to learn more and enable</div>
                        <div className="mt-2 flex items-center gap-2">
                          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Active:</div>
                          <span className="px-2 py-1 rounded" style={{ background: enabledExtensions.length > 0 ? 'var(--tcs-blue)' : 'var(--bg-primary)', color: enabledExtensions.length > 0 ? 'white' : 'var(--text-secondary)', fontSize: '12px', fontWeight: 600 }}>
                            {enabledExtensions.length} tool{enabledExtensions.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>

                      {/* Tool Categories - Tree Structure */}
                      {[
                        {
                          category: 'Review & Markup',
                          categoryIcon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
                          description: 'Annotate and document issues',
                          tools: [
                            { 
                              id: 'DrawToolExtension', 
                              name: 'Draw & Redline', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
                              category: 'Review & Markup',
                              fullDescription: 'Add 2D markup annotations, redlines, and callouts directly on your model views. Perfect for design reviews, coordination meetings, and documenting issues.',
                              useCases: [
                                { title: 'Design Reviews', description: 'Mark up design issues during review meetings' },
                                { title: 'RFI Documentation', description: 'Annotate areas that need clarification' },
                                { title: 'Clash Resolution', description: 'Draw attention to coordination conflicts' }
                              ],
                              steps: [
                                'Enable the tool from this page',
                                'Select the drawing tool from the viewer toolbar',
                                'Click and drag to draw markup on the model',
                                'Add text notes to your markups',
                                'Save or export your annotated views'
                              ],
                              tips: 'Use different colors for different issue types (red=critical, yellow=review, blue=info)'
                            },
                            { 
                              id: 'IconMarkupExtension', 
                              name: 'Issue Markers', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><circle cx="12" cy="10" r="3"/></svg>,
                              category: 'Review & Markup',
                              fullDescription: 'Place 3D icon markers directly on model elements to tag issues, defects, or items requiring attention. Each marker can include notes, photos, and status.',
                              useCases: [
                                { title: 'Site Inspections', description: 'Tag defects found during inspections' },
                                { title: 'Safety Issues', description: 'Mark potential safety hazards' },
                                { title: 'Quality Control', description: 'Track quality issues by location' }
                              ],
                              steps: [
                                'Enable the tool',
                                'Select the issue marker icon',
                                'Click on any model element to place a marker',
                                'Fill in issue details (type, priority, description)',
                                'Export issue list for tracking'
                              ],
                              tips: 'Color-coded markers help teams quickly identify priority levels'
                            },
                          ]
                        },
                        {
                          category: 'Data & Reports',
                          categoryIcon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>,
                          description: 'Extract and analyze model data',
                          tools: [
                            { 
                              id: 'XLSExtension', 
                              name: 'Excel Export', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 17H7A5 5 0 017 7h2m6 0h2a5 5 0 110 10h-2"/><path d="M9 12h6"/></svg>,
                              category: 'Data & Reports',
                              fullDescription: 'Export element properties and metadata to Excel spreadsheets. Perfect for quantity takeoffs, cost estimation, and custom reporting.',
                              useCases: [
                                { title: 'Quantity Takeoffs', description: 'Export all walls, doors, windows for material estimation' },
                                { title: 'Cost Analysis', description: 'Export element data with cost properties for budgeting' },
                                { title: 'Equipment Lists', description: 'Generate equipment schedules and specifications' }
                              ],
                              steps: [
                                'Select elements you want to export (or select all)',
                                'Enable the Excel Export tool',
                                'Click the export button in the toolbar',
                                'Choose which properties to include',
                                'Download the Excel file'
                              ],
                              tips: 'Filter elements before export to create category-specific reports (e.g., only structural elements)'
                            },
                            { 
                              id: 'CustomPropertiesExtension', 
                              name: 'Custom Properties', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20.59 13.41l-7.17 7.17a2 2 0 01-2.83 0L2 12V2h10l8.59 8.59a2 2 0 010 2.82z"/><line x1="7" y1="7" x2="7.01" y2="7"/></svg>,
                              category: 'Data & Reports',
                              fullDescription: 'Add custom metadata and properties to model elements. Extend beyond standard IFC properties to track project-specific data like costs, suppliers, or installation status.',
                              useCases: [
                                { title: 'Cost Tracking', description: 'Add cost data to elements for budget tracking' },
                                { title: 'Supplier Info', description: 'Link elements to supplier and product information' },
                                { title: 'Installation Status', description: 'Track construction progress per element' }
                              ],
                              steps: [
                                'Select elements to add properties to',
                                'Enable the Custom Properties tool',
                                'Define new property fields (name, type, value)',
                                'Fill in values for selected elements',
                                'Properties are saved with the model'
                              ],
                              tips: 'Create property templates for consistent data entry across your project'
                            },
                          ]
                        },
                        {
                          category: 'Planning & Scheduling',
                          categoryIcon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
                          description: 'Construction sequencing and timeline',
                          tools: [
                            { 
                              id: 'PhasingExtension', 
                              name: 'Timeline Gantt', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
                              category: 'Planning & Scheduling',
                              fullDescription: 'Link model elements to construction schedule phases. Visualize what gets built when, and play through your construction sequence as a 4D animation.',
                              useCases: [
                                { title: '4D Scheduling', description: 'Visualize construction sequence over time' },
                                { title: 'Logistics Planning', description: 'Plan site access and staging areas by phase' },
                                { title: 'Progress Tracking', description: 'Compare actual vs planned construction progress' }
                              ],
                              steps: [
                                'Import or create construction schedule (Gantt chart)',
                                'Enable the Timeline tool',
                                'Link model elements to schedule tasks',
                                'Use timeline slider to show/hide elements by date',
                                'Play animation to see construction sequence'
                              ],
                              tips: 'Color-code phases (foundation=brown, structure=gray, MEP=blue) for clearer visualization'
                            },
                          ]
                        },
                        {
                          category: 'Presentation',
                          categoryIcon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 7h10v10H7z"/><path d="M10 10l5 3-5 3V10z"/></svg>,
                          description: 'Client demos and stakeholder meetings',
                          tools: [
                            { 
                              id: 'TurnTableExtension', 
                              name: 'Auto-Rotate Camera', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/></svg>,
                              category: 'Presentation',
                              fullDescription: 'Automatically rotate the camera around your model for impressive presentations and marketing videos. Adjust speed and direction for perfect showcase.',
                              useCases: [
                                { title: 'Client Presentations', description: 'Auto-rotating showcase for stakeholder meetings' },
                                { title: 'Marketing Videos', description: 'Record rotating views for promotional content' },
                                { title: 'Design Reviews', description: 'Show all angles without manual navigation' }
                              ],
                              steps: [
                                'Enable the Auto-Rotate tool',
                                'Set camera focus point and distance',
                                'Adjust rotation speed and direction',
                                'Start rotation and record if needed'
                              ],
                              tips: 'Combine with exploded view for dramatic architectural reveals'
                            },
                            { 
                              id: 'GoogleMapsLocator', 
                              name: 'Site Context', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0118 0z"/><path d="M15 10a3 3 0 11-6 0 3 3 0 016 0z"/></svg>,
                              category: 'Presentation',
                              fullDescription: 'Display building location on Google Maps with nearby streets, landmarks, and utilities. Show project context and site access.',
                              useCases: [
                                { title: 'Site Analysis', description: 'Show building context with nearby infrastructure' },
                                { title: 'Logistics Planning', description: 'Plan delivery routes and site access' },
                                { title: 'Stakeholder Updates', description: 'Show project location to remote teams' }
                              ],
                              steps: [
                                'Enable Site Context tool',
                                'Map automatically shows building location',
                                'Zoom in/out to show context at different scales',
                                'Toggle between map and satellite view'
                              ],
                              tips: 'Use satellite view to show actual site conditions and access points'
                            },
                          ]
                        },
                        {
                          category: 'Analysis & Editing',
                          categoryIcon: <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>,
                          description: 'Advanced coordination tools',
                          tools: [
                            { 
                              id: 'TransformExtension', 
                              name: 'Move Elements', 
                              emoji: '🔧',
                              category: 'Analysis & Editing',
                              fullDescription: 'Move, rotate, and scale model elements for clash testing and coordination studies. Test alternative layouts without modifying the original design.',
                              useCases: [
                                { title: 'Clash Resolution', description: 'Move pipes or ducts to resolve conflicts' },
                                { title: 'Layout Studies', description: 'Test furniture and equipment arrangements' },
                                { title: 'What-If Scenarios', description: 'Explore design alternatives' }
                              ],
                              steps: [
                                'Select elements to transform',
                                'Enable the Move tool',
                                'Use transform gizmo to move/rotate/scale',
                                'Test for clashes in new position',
                                'Save or discard changes'
                              ],
                              tips: 'Use snap settings to align elements precisely to grid or other elements'
                            },
                            { 
                              id: 'BoundingBoxExtension', 
                              name: 'Element Bounds', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>,
                              category: 'Analysis & Editing',
                              fullDescription: 'Visualize 3D bounding boxes around elements to understand space requirements and clearances. Essential for space planning and clash detection.',
                              useCases: [
                                { title: 'Space Planning', description: 'Verify clearances and access zones' },
                                { title: 'Equipment Sizing', description: 'Check if equipment fits in allocated space' },
                                { title: 'Clash Detection', description: 'Visualize potential interference zones' }
                              ],
                              steps: [
                                'Select elements to analyze',
                                'Enable Bounding Box tool',
                                'Colored boxes show element extents',
                                'Check dimensions and clearances'
                              ],
                              tips: 'Use transparency to see both bounding box and actual element geometry'
                            },
                            { 
                              id: 'Edit2dExtension', 
                              name: 'Draw 2D Shapes', 
                              icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/></svg>,
                              category: 'Analysis & Editing',
                              fullDescription: 'Draw 2D polygons and shapes on floor plans for space analysis, area calculations, or zone definitions.',
                              useCases: [
                                { title: 'Area Calculations', description: 'Draw zones to calculate square footage' },
                                { title: 'Space Planning', description: 'Sketch proposed layouts and furniture' },
                                { title: 'Safety Zones', description: 'Define exclusion or restricted areas' }
                              ],
                              steps: [
                                'Switch to 2D view (floor plan)',
                                'Enable 2D Drawing tool',
                                'Click to create polygon vertices',
                                'Tool shows area and perimeter',
                                'Save shapes as markup layers'
                              ],
                              tips: 'Use color coding for different zone types (work area, storage, circulation)'
                            },
                          ]
                        },
                      ].map((group, idx) => (
                        <div key={idx} className="mb-4">
                          {/* Category Header */}
                          <div className="mb-2 p-2 rounded-lg flex items-center gap-2" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-light)' }}>
                            <div style={{ color: 'var(--tcs-blue)' }}>{group.categoryIcon}</div>
                            <div style={{ flex: 1 }}>
                              <div className="font-semibold" style={{ fontSize: '13px', color: 'var(--text-primary)' }}>{group.category}</div>
                              <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{group.description}</div>
                            </div>
                          </div>
                          
                          {/* Tool List - Row Layout */}
                          <div className="space-y-2 pl-3">
                            {group.tools.map(tool => (
                              <button
                                key={tool.id}
                                onClick={() => setSelectedTool(tool)}
                                className="w-full text-left flex items-center gap-3 p-2 rounded-lg transition-all hover:bg-gray-50"
                                style={{
                                  background: enabledExtensions.includes(tool.id) ? 'var(--tcs-blue)' : 'var(--surface)',
                                  border: enabledExtensions.includes(tool.id) ? '1px solid var(--tcs-blue)' : '1px solid var(--border-light)',
                                  cursor: 'pointer',
                                  color: enabledExtensions.includes(tool.id) ? 'white' : 'var(--text-primary)'
                                }}
                              >
                                <div className="p-2 rounded" style={{ background: enabledExtensions.includes(tool.id) ? 'rgba(255,255,255,0.2)' : 'var(--bg-primary)', flexShrink: 0 }}>
                                  {tool.icon}
                                </div>
                                <div style={{ flex: 1 }}>
                                  <div style={{ fontSize: '13px', fontWeight: 600 }}>{tool.name}</div>
                                </div>
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" style={{ opacity: 0.5, flexShrink: 0 }}>
                                  <path d="M9 5l7 7-7 7"/>
                                </svg>
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div>
                  <div className="mb-3">
                    <div className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '15px' }}>Model Insights</div>
                  </div>
                  {modelStats ? (
                    <div className="space-y-4">
                      {/* Model Overview Card */}
                      <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-light)' }}>
                        <div className="flex items-center gap-2 mb-2">
                          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
                            <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                          </svg>
                          <div className="font-semibold" style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>Model Name</div>
                        </div>
                        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', wordBreak: 'break-word' }}>{modelStats.name}</div>
                      </div>

                      {/* Key Metrics */}
                      <div className="grid grid-cols-2 gap-3">
                        <div className="p-3 rounded-lg text-center" style={{ background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))', color: 'white' }}>
                          <div style={{ fontSize: '24px', fontWeight: 700 }}>{modelStats.nodeCount?.toLocaleString()}</div>
                          <div style={{ fontSize: '11px', opacity: 0.9 }}>Total Elements</div>
                        </div>
                        <div className="p-3 rounded-lg text-center" style={{ background: selectedElements.length > 0 ? 'var(--tcs-orange)' : 'var(--bg-primary)', color: selectedElements.length > 0 ? 'white' : 'var(--text-primary)', border: selectedElements.length === 0 ? '1px solid var(--border-light)' : 'none' }}>
                          <div style={{ fontSize: '24px', fontWeight: 700 }}>{selectedElements.length}</div>
                          <div style={{ fontSize: '11px', opacity: selectedElements.length > 0 ? 0.9 : 0.6 }}>Selected</div>
                        </div>
                      </div>

                      {/* Health Status */}
                      <div className="p-3 rounded-lg" style={{ background: 'var(--success)', color: 'white' }}>
                        <div className="flex items-center gap-2 mb-1">
                          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                            <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                          </svg>
                          <div className="font-semibold" style={{ fontSize: '13px' }}>Model Loaded Successfully</div>
                        </div>
                        <div style={{ fontSize: '12px', opacity: 0.9 }}>All geometry rendered • Ready for review</div>
                      </div>

                      {/* Active Tools */}
                      {enabledExtensions.length > 0 && (
                        <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-light)' }}>
                          <div className="font-semibold mb-2" style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Active Tools</div>
                          <div className="flex flex-wrap gap-1">
                            {enabledExtensions.map(extId => {
                              const ext = AVAILABLE_EXTENSIONS.find(e => e.id === extId);
                              if (!ext) return null;
                              return (
                                <span key={extId} className="px-2 py-1 rounded" style={{ background: 'var(--tcs-blue)', color: 'white', fontSize: '11px', fontWeight: 600 }}>
                                  {ext.name}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Quick Actions */}
                      <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-light)' }}>
                        <div className="font-semibold mb-2" style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Next Steps</div>
                        <div className="space-y-2">
                          {selectedElements.length === 0 && (
                            <div className="flex items-start gap-2" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                              <span style={{ color: 'var(--tcs-blue)' }}>1.</span>
                              <span>Click elements in the viewer to inspect properties</span>
                            </div>
                          )}
                          {enabledExtensions.length === 0 && (
                            <div className="flex items-start gap-2" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                              <span style={{ color: 'var(--tcs-blue)' }}>2.</span>
                              <span>Enable tools from the "Tools" tab for markup & analysis</span>
                            </div>
                          )}
                          {selectedElements.length > 0 && enabledExtensions.includes('XLSExtension') && (
                            <div className="flex items-start gap-2" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                              <span style={{ color: 'var(--success)' }}>✓</span>
                              <span>Ready to export selected elements to Excel</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                      <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 opacity-40">
                        <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                      </svg>
                      <div style={{ fontSize: '13px' }}>Load a model to see details</div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </>
  );
}

/* ---------------- PointCloud Panel (submodule) ---------------- */
function PointCloudPanel({ sceneData, selected, loading, onUpload, onPointClick, onGraphClick }) {
  const [graphExpanded, setGraphExpanded] = useState(false);
  const [hoveredNode, setHoveredNode] = useState(null);

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

      {/* Diagonal Layout: Full-height Scene Hierarchy (left) + PointCloud (top-right) + Graph (bottom-right) */}
      <div className="flex gap-4" style={{ height: "calc(75vh - 120px)", minHeight: '600px' }}>
        {/* Left: Full-height Scene Hierarchy Panel */}
        <div className="glass p-4 flex flex-col" style={{ width: '320px', minWidth: '280px', maxWidth: '360px', flexShrink: 0, overflow: 'hidden' }}>
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <AnnotationPanel 
              selected={selected} 
              sceneData={sceneData} 
              onSegmentSelect={(segId, segment) => {
                console.log('[App] Segment selected from annotation:', { segId, segment_key: segment.segment_key });
                onPointClick({
                  segmentId: segId,
                  label: segment.segment_key, // Use segment_key which matches the numeric label
                  pointIndex: null
                });
              }}
            />
          </div>
        </div>

        {/* Right: Stacked PointCloud Viewer (top) + Graph + Info (bottom) */}
        <div className="flex-1 flex flex-col gap-4">
          {/* Top: PointCloud Viewer */}
          <div className="glass p-4" style={{ height: graphExpanded ? "50%" : "70%", minHeight: '300px', transition: "height 0.3s ease", display: 'flex', flexDirection: 'column' }}>
            {sceneData ? (
              <div style={{ flex: 1, minHeight: 0, minWidth: 0, position: 'relative', overflow: 'hidden' }}>
                {/* Debug logging - will be visible in render but won't affect UI */}
                {console.log('[App] Rendering PointCloudViewer with selectedSegmentId:', selected?.segmentId) || null}
                <PointCloudViewer
                  data={sceneData}
                  selectedSegmentId={selected?.segmentId}
                  onSegmentClick={onPointClick}
                />
              </div>
            ) : (
              <div className="h-full flex items-center justify-center" style={{ color: 'var(--text-muted)' }}>
                <div className="text-center" style={{ maxWidth: '400px', padding: '24px' }}>
                  <div style={{ width: '64px', height: '64px', margin: '0 auto 16px', borderRadius: '12px', background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="white" strokeWidth="2">
                      <circle cx="12" cy="12" r="3"/>
                      <circle cx="6" cy="6" r="2"/>
                      <circle cx="18" cy="6" r="2"/>
                      <circle cx="6" cy="18" r="2"/>
                      <circle cx="18" cy="18" r="2"/>
                    </svg>
                  </div>
                  <div style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>Get Started with Your Digital Twin</div>
                  <div style={{ fontSize: '14px', color: 'var(--text-secondary)', marginBottom: '16px' }}>Upload .npy or .txt point cloud file for automatic semantic segmentation</div>
                  <div style={{ fontSize: '13px', color: 'var(--text-muted)', padding: '12px', background: 'var(--bg-primary)', borderRadius: '8px' }}>
                    <div>✓ 13 semantic classes</div>
                    <div>✓ Interactive 3D visualization</div>
                    <div>✓ Spatial relationship graph</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Bottom: Mini Graph + Info Panel */}
          {sceneData && (
            <div className="flex gap-4" style={{ height: graphExpanded ? "50%" : "30%", minHeight: '220px', transition: "height 0.3s ease" }}>
              {/* Mini Graph Viewer */}
              <div className="glass p-4" style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
                <div className="flex items-center justify-between mb-3" style={{ flexShrink: 0 }}>
                  <div className="flex items-center gap-2">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
                      <circle cx="12" cy="12" r="2"/><circle cx="19" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><path d="M13 11l4-4M11 13l-4 4"/>
                    </svg>
                    <span className="font-semibold" style={{ color: 'var(--text-primary)', fontSize: '14px' }}>Graph Network</span>
                  </div>
                  <button
                    onClick={() => setGraphExpanded(!graphExpanded)}
                    className="tcs-btn"
                    style={{
                      padding: '6px 12px',
                      borderRadius: '6px',
                      background: 'var(--tcs-blue)',
                      color: 'white',
                      border: 'none',
                      cursor: 'pointer',
                      fontSize: '13px',
                      fontWeight: 600,
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px'
                    }}
                    aria-label={graphExpanded ? 'Collapse graph' : 'Expand graph'}
                  >
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                      {graphExpanded ? (
                        <path d="M19 9l-7 7-7-7"/>
                      ) : (
                        <path d="M5 15l7-7 7 7"/>
                      )}
                    </svg>
                    {graphExpanded ? 'Collapse' : 'Expand'}
                  </button>
                </div>
                <div style={{ flex: 1, minHeight: 0, minWidth: 0, position: 'relative', overflow: 'hidden' }}>
                  <GraphViewer
                    sceneId={sceneData.scene_id}
                    segments={sceneData.segments}
                    edges={sceneData.edges}
                    onNodeClick={onGraphClick}
                    selectedSegmentId={selected?.segmentId ?? null}
                    uniformRadius={10}
                    onNodeHover={(node) => setHoveredNode(node)}
                  />
                </div>
              </div>

              {/* Info Panel */}
              <div className="glass p-4" style={{ width: '288px', minWidth: '260px', maxWidth: '320px', flexShrink: 0, overflowY: 'auto' }}>
                <div className="font-semibold mb-3 pb-2" style={{ borderBottom: '1px solid var(--border-light)', color: 'var(--text-primary)', fontSize: '14px' }}>
                  Node Details
                </div>
                {hoveredNode || selected ? (
                  <div className="space-y-3">
                    {(hoveredNode || selected) && (
                      <>
                      <div>
                        <div className="font-medium mb-2" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Node ID</div>
                        <div className="px-3 py-2 rounded" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)', fontFamily: 'monospace', fontSize: '12px', wordBreak: 'break-all' }}>
                          {hoveredNode?.id || selected?.segmentId}
                        </div>
                      </div>
                      <div>
                        <div className="font-medium mb-2" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Label</div>
                        <div className="px-3 py-2 rounded flex items-center gap-2" style={{ background: 'var(--tcs-blue)', color: 'white', fontSize: '13px', fontWeight: 600 }}>
                          <svg viewBox="0 0 8 8" width="8" height="8" fill="currentColor">
                            <circle cx="4" cy="4" r="4"/>
                          </svg>
                          {hoveredNode?.label || selected?.label || 'N/A'}
                        </div>
                      </div>
                      <div>
                        <div className="font-medium mb-2" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Properties</div>
                        <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: '13px' }}>
                          <tbody>
                            {hoveredNode?.segment_key && (
                              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                                <td className="py-1" style={{ color: 'var(--text-secondary)' }}>Segment Key</td>
                                <td className="py-1 text-right" style={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                                  {hoveredNode.segment_key}
                                </td>
                              </tr>
                            )}
                            {sceneData?.segments && (
                              <tr style={{ borderBottom: '1px solid var(--border-light)' }}>
                                <td className="py-1" style={{ color: 'var(--text-secondary)' }}>Total Nodes</td>
                                <td className="py-1 text-right" style={{ color: 'var(--text-primary)' }}>
                                  {sceneData.segments.length}
                                </td>
                              </tr>
                            )}
                            {sceneData?.edges && (
                              <tr>
                                <td className="py-1" style={{ color: 'var(--text-secondary)' }}>Total Edges</td>
                                <td className="py-1 text-right" style={{ color: 'var(--text-primary)' }}>
                                  {sceneData.edges.length}
                                </td>
                              </tr>
                            )}
                          </tbody>
                        </table>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                  <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 opacity-40">
                    <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
                  </svg>
                  <div style={{ fontSize: '13px', lineHeight: '1.5' }}>Hover over a graph node<br/>or select a segment<br/>to view details</div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>    </div>    </>
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

      const res = await fetch(`${BACKEND_API_URL}/chat`, {
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
