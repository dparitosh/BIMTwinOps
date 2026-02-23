// src/App.jsx
import React, { useState, useEffect, useCallback, Component } from "react";
import FileUpload from "./components/FileUpload";
import PointCloudViewer from "./components/PointCloudViewer";
import GraphViewer from "./components/GraphViewer";
import AnnotationPanel from "./components/AnnotationPanel";
import Loader from "./components/Loader";
import ModernBimViewer from "./components/ModernBimViewer";
import AgentInterface from "./components/AgentInterface";
import SaveStatusIndicator from "./components/SaveStatusIndicator";
// Enterprise Pages
import ProjectScheduling from "./components/ProjectScheduling";
import ModelAnalytics from "./components/ModelAnalytics";
import RevitIntegration from "./components/RevitIntegration";
import { enrichBatch, checkPointCloudHealth } from "./api";
// Layout Components
import { Header } from "./components/layout/Header";
import { Sidebar } from "./components/layout/Sidebar";
import { MainContent } from "./components/layout/MainContent";
// Context Providers
import { AgentProvider } from "./contexts/AgentContext";
import { WorkspaceProvider } from "./contexts/WorkspaceContext";
// Point Cloud Sync Hook
import { usePointCloudSync } from "./hooks/usePointCloudSync";

// Error Boundary for graceful crash recovery
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 32, textAlign: "center" }}>
          <h2 style={{ color: "#ef4444", marginBottom: 12 }}>Something went wrong</h2>
          <p style={{ color: "#6b7280", marginBottom: 16 }}>{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{ padding: "8px 20px", borderRadius: 8, border: "none", background: "var(--tcs-blue, #2563eb)", color: "#fff", cursor: "pointer" }}
          >
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const APS_API_URL =
  import.meta.env.VITE_APS_API_URL
  || (import.meta.env.DEV ? "" : "http://127.0.0.1:3001");

// In dev mode, prefer relative URLs so Vite proxy handles routing.
// In production or if VITE_BACKEND_API_URL is explicitly set, use the full URL.
const BACKEND_API_URL =
  import.meta.env.VITE_BACKEND_API_URL || (import.meta.env.DEV ? "" : "http://127.0.0.1:8008");

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

import OpenApiTab from "./components/OpenApiTab";

export default function App() {
  const [sceneData, setSceneData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState(null); // { pointIndex, label, segmentId }
  const [sidebarOpen, setSidebarOpen] = useState(true); // Sidebar visibility

  const [apsStatus, setApsStatus] = useState({
    loading: true,
    twoLeggedConfigured: false,
    threeLeggedConfigured: false,
    missing: [],
    oauthMissing: [],
  });

  // Point Cloud Segment Synchronization
  const {
    segments: syncedSegments,
    isDirty,
    isSaving,
    lastSaved,
    error: syncError,
    updateSegment,
    saveNow,
    loadSegments,
    setSegments
  } = usePointCloudSync(sceneData?.scene_id, BACKEND_API_URL);

  // APS Viewer state
  const [viewerUrn, setViewerUrn] = useState("");
  const [viewerAuth, setViewerAuth] = useState("app");

  // Active viewer tab
  const [activeTab, setActiveTab] = useState("agent");

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
      
      // Initialize segment sync with uploaded data
      if (json.segments && json.segments.length > 0) {
        setSegments(json.segments.map(seg => ({
          segment_id: `seg_${seg.segment_key}`,
          semantic_class_id: seg.segment_key,
          semantic_label: seg.semantic_name,
          pointCount: seg.num_points,
          centroid: seg.centroid
        })));
      }
    } catch (err) {
      console.error("Upload error", err);
      alert("Upload failed — check console");
    } finally {
      setLoading(false);
    }
  };

  // Load segments from Neo4j when scene changes
  useEffect(() => {
    if (sceneData?.scene_id) {
      loadSegments().catch(() => {
        // Fallback to uploaded segments if Neo4j load fails
      });
    }
  }, [sceneData?.scene_id, loadSegments]);

  // pointcloud click handler
  const handlePointClick = ({ pointIndex, label, segmentId }) => {
    setSelected({ pointIndex, label, segmentId });
  };

  // graph node click handler - receives nodeId (string)
  const handleGraphClick = (nodeId) => {
    // nodeId expected like `${scene_id}_sem_${segment_key}`
    const parts = String(nodeId).split("_sem_");
    const labelStr = parts.length === 2 ? parts[1] : null;
    const label = labelStr ? Number(labelStr) : null;
    
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
    
    setSelected({ pointIndex: firstIndex, label, segmentId: nodeId });
  };

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
    <ErrorBoundary>
    <AgentProvider>
    <WorkspaceProvider>
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg-primary)' }}>
      {/* Header with backend health indicators */}
      <Header 
        backendUrl={BACKEND_API_URL}
        apsUrl={APS_API_URL}
        onMenuClick={() => setSidebarOpen(!sidebarOpen)}
        showMenuButton={true}
      />

      {/* Main layout: Sidebar + Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        {/* Sidebar Navigation */}
        <Sidebar 
          open={sidebarOpen}
          currentView={activeTab}
          onViewChange={setActiveTab}
          onClose={() => setSidebarOpen(false)}
        />

        {/* Main Content Area */}
        <MainContent loading={loading}>
          <div className="p-5" style={{ height: '100%', overflow: 'auto' }}>
            {/* Main Viewer Panel */}
            <div className="glass p-4" style={{ minHeight: "75vh" }}>
              {activeTab === "agent" && <AgentInterface />}
              {activeTab === "bim" && (
                <ModernBimViewer
                  apsBaseUrl={APS_API_URL}
                  viewerUrn={viewerUrn}
                  setViewerUrn={setViewerUrn}
                  viewerAuth={viewerAuth}
                  setViewerAuth={setViewerAuth}
                  onUrnReady={handleUrnReady}
                />
              )}
              {activeTab === "revit" && <RevitIntegration />}
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
                  onSegmentUpdate={(segmentId, updates) => {
                    updateSegment(segmentId, updates);
                  }}
                />
              )}
              {activeTab === "openapi" && <OpenApiTab />}
            </div>
          </div>
        </MainContent>
      </div>

      {/* Save Status Indicator - Floating bottom-right */}
      {sceneData?.scene_id && (
        <SaveStatusIndicator
          isDirty={isDirty}
          isSaving={isSaving}
          lastSaved={lastSaved}
          onSaveNow={saveNow}
        />
      )}

      {/* Sync Error Notification */}
      {syncError && (
        <div style={{
          position: 'fixed',
          top: 80,
          right: 24,
          padding: '12px 20px',
          background: '#ef4444',
          color: 'white',
          borderRadius: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
          zIndex: 1000,
          maxWidth: '400px'
        }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Sync Error</div>
          <div style={{ fontSize: '13px', opacity: 0.9 }}>{syncError}</div>
        </div>
      )}
    </div>
    </WorkspaceProvider>
    </AgentProvider>
    </ErrorBoundary>
  );
}

/* ---------------- PointCloud Panel (submodule) ---------------- */
function PointCloudPanel({ sceneData, selected, loading, onUpload, onPointClick, onGraphClick, onSegmentUpdate }) {
  const [graphExpanded, setGraphExpanded] = useState(false);
  const [hoveredNode, setHoveredNode] = useState(null);
  const [enriching, setEnriching] = useState(false);
  const [enrichmentData, setEnrichmentData] = useState(null);
  const [apiHealth, setApiHealth] = useState(null);

  // Check API health on mount
  useEffect(() => {
    checkPointCloudHealth()
      .then(health => {
        setApiHealth(health);
      })
      .catch(err => {
        setApiHealth({ status: 'error', error: err.message, neo4j_connected: false });
      });
  }, []);

  // Helper to get label name from ID
  const getLabelName = (labelId) => {
    const labelNames = [
      "ceiling", "floor", "wall", "beam", "column", "window", 
      "door", "chair", "table", "bookcase", "sofa", "board", "clutter"
    ];
    return labelNames[labelId] || `label_${labelId}`;
  };

  // Handle enrichment
  const handleEnrichScene = async () => {
    if (!sceneData) return;
    
    setEnriching(true);
    try {
      // Group points by semantic label
      const segmentMap = {};
      sceneData.points.forEach((point, idx) => {
        const label = sceneData.labels[idx];
        if (!segmentMap[label]) {
          segmentMap[label] = [];
        }
        segmentMap[label].push(point);
      });

      // Prepare batch payload (sample points for performance)
      const segments = Object.entries(segmentMap).map(([label, points], idx) => ({
        id: `seg_${idx}`,
        semantic_label: parseInt(label),
        points: points.slice(0, 100), // Sample for performance
      }));

      // Call enrichment API
      const result = await enrichBatch(segments);
      setEnrichmentData(result);
      
      alert(`Enriched ${result.enriched_count} segments with bSDD data!`);
    } catch (err) {
      alert(`Failed to enrich segments: ${err.message}`);
    } finally {
      setEnriching(false);
    }
  };

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
        {apiHealth && (
          <span
            className={`tcs-badge ${apiHealth.neo4j_connected ? 'tcs-badge-success' : 'tcs-badge-error'}`}
            title={`Neo4j: ${apiHealth.neo4j_connected ? 'Connected' : 'Disconnected'} | Semantic Classes: ${apiHealth.semantic_classes_loaded || 0}`}
            style={{ marginLeft: '8px' }}
          >
            {apiHealth.neo4j_connected ? '[OK]' : '[X]'} Knowledge Graph
          </span>
        )}
      </div>

      <div className="mb-4">
        <FileUpload onUpload={onUpload} />
      </div>

      {sceneData && (
        <div className="mb-4">
          <button
            onClick={handleEnrichScene}
            disabled={enriching}
            className="tcs-button tcs-button-primary w-full"
            style={{
              padding: '12px 20px',
              borderRadius: '8px',
              border: 'none',
              background: enriching ? 'var(--text-muted)' : 'var(--tcs-blue)',
              color: 'white',
              cursor: enriching ? 'not-allowed' : 'pointer',
              fontSize: '14px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'all 0.2s'
            }}
          >
            {enriching ? (
              <>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" style={{ animation: 'spin 1s linear infinite' }}>
                  <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                </svg>
                Enriching with bSDD...
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                </svg>
                Enrich with bSDD Standards
              </>
            )}
          </button>
        </div>
      )}

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
              onSegmentUpdate={onSegmentUpdate}
              onSegmentSelect={(segId, segment) => {
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
              <div className="glass p-4" style={{ width: '320px', minWidth: '280px', maxWidth: '380px', flexShrink: 0, overflowY: 'auto', maxHeight: '100%' }}>
                <div className="font-semibold mb-3 pb-2" style={{ borderBottom: '1px solid var(--border-light)', color: 'var(--text-primary)', fontSize: '14px' }}>
                  {enrichmentData ? 'Segment Details & bSDD' : 'Node Details'}
                </div>
                {hoveredNode || selected ? (
                  <div className="space-y-3">
                    {/* Basic Info */}
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
                        {hoveredNode?.label || getLabelName(selected?.label) || 'N/A'}
                      </div>
                    </div>

                    {/* bSDD Enrichment Data */}
                    {enrichmentData && enrichmentData.enriched_segments && selected && (() => {
                      const segmentEnrichment = enrichmentData.enriched_segments.find(
                        s => s.semantic_class === getLabelName(selected.label)
                      );
                      
                      if (!segmentEnrichment) return null;
                      
                      return (
                        <div className="border-t pt-4 space-y-4" style={{ borderColor: 'var(--border-color)' }}>
                          <h4 className="font-bold flex items-center gap-2" style={{ color: 'var(--tcs-blue)', fontSize: '14px' }}>
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                            </svg>
                            bSDD Standards
                          </h4>

                          {/* IFC Entities */}
                          {segmentEnrichment.ifc_entities && segmentEnrichment.ifc_entities.length > 0 && (
                            <div>
                              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                                IFC ENTITIES ({segmentEnrichment.ifc_entities.length})
                              </div>
                              <div className="flex flex-wrap gap-1">
                                {segmentEnrichment.ifc_entities.map((entity, idx) => (
                                  <span
                                    key={idx}
                                    className="px-2 py-1 rounded text-xs font-medium"
                                    style={{ background: 'var(--tcs-blue)', color: 'white' }}
                                  >
                                    {entity}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* bSDD Classes */}
                          {segmentEnrichment.bsdd_classes && segmentEnrichment.bsdd_classes.length > 0 && (
                            <div>
                              <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
                                CLASSIFICATIONS ({segmentEnrichment.bsdd_classes.length})
                              </div>
                              <div className="space-y-3">
                                {segmentEnrichment.bsdd_classes.slice(0, 3).map((bsddClass, idx) => (
                                  <div
                                    key={idx}
                                    className="p-3 rounded-lg"
                                    style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-color)' }}
                                  >
                                    <div className="font-semibold mb-1" style={{ fontSize: '13px', color: 'var(--text-primary)' }}>
                                      {bsddClass.name}
                                    </div>
                                    <div className="text-xs mb-2" style={{ color: 'var(--text-secondary)' }}>
                                      {bsddClass.code}
                                    </div>
                                    {bsddClass.definition && (
                                      <div className="text-xs" style={{ color: 'var(--text-muted)', lineHeight: '1.4' }}>
                                        {bsddClass.definition.substring(0, 120)}
                                        {bsddClass.definition.length > 120 && '...'}
                                      </div>
                                    )}
                                    
                                    {/* Properties Preview */}
                                    {bsddClass.properties && bsddClass.properties.length > 0 && (
                                      <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border-color)' }}>
                                        <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
                                          PROPERTIES ({bsddClass.properties.length})
                                        </div>
                                        <div className="space-y-1">
                                          {bsddClass.properties.slice(0, 2).map((prop, pIdx) => (
                                            <div key={pIdx} className="text-xs" style={{ color: 'var(--text-muted)' }}>
                                              • {prop.name} <span style={{ color: 'var(--tcs-blue)' }}>({prop.dataType})</span>
                                            </div>
                                          ))}
                                          {bsddClass.properties.length > 2 && (
                                            <div className="text-xs" style={{ color: 'var(--tcs-blue)', cursor: 'pointer' }}>
                                              +{bsddClass.properties.length - 2} more...
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    )}

                                    {/* Relations Preview */}
                                    {bsddClass.relations && bsddClass.relations.length > 0 && (
                                      <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border-color)' }}>
                                        <div className="text-xs font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
                                          RELATIONS ({bsddClass.relations.length})
                                        </div>
                                        <div className="flex flex-wrap gap-1">
                                          {bsddClass.relations.slice(0, 3).map((rel, rIdx) => (
                                            <span
                                              key={rIdx}
                                              className="px-2 py-1 rounded text-xs"
                                              style={{ background: 'var(--bg-secondary)', color: 'var(--text-secondary)' }}
                                            >
                                              {rel.relationType}
                                            </span>
                                          ))}
                                        </div>
                                      </div>
                                    )}
                                  </div>
                                ))}
                                {segmentEnrichment.bsdd_classes.length > 3 && (
                                  <div className="text-xs text-center" style={{ color: 'var(--tcs-blue)', cursor: 'pointer' }}>
                                    +{segmentEnrichment.bsdd_classes.length - 3} more classifications
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Confidence Score */}
                          {segmentEnrichment.confidence !== undefined && (
                            <div className="p-2 rounded" style={{ background: 'var(--bg-primary)' }}>
                              <div className="text-xs flex items-center justify-between">
                                <span style={{ color: 'var(--text-secondary)' }}>Confidence:</span>
                                <span style={{ color: 'var(--tcs-blue)', fontWeight: 600 }}>
                                  {(segmentEnrichment.confidence * 100).toFixed(0)}%
                                </span>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })()}

                    {/* Original Properties */}
                    {!enrichmentData && (
                      <div>
                        <div className="font-medium mb-2" style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>Properties</div>
                        <table className="w-full" style={{ borderCollapse: 'collapse', fontSize: '13px' }}>
                          <tbody>
                            {hoveredNode?.segment_key !== undefined && (
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
                    )}
                  </div>
                ) : (
                  <div className="text-center py-8" style={{ color: 'var(--text-muted)' }}>
                    <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5" className="mx-auto mb-3 opacity-40">
                      <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
                    </svg>
                    <div style={{ fontSize: '13px', lineHeight: '1.5' }}>
                      {enrichmentData ? 'Select a segment to view bSDD data' : 'Hover over a graph node or select a segment'}
                    </div>
                  </div>
                )}
            </div>
          </div>
        )}
      </div>    </div>    </>
  );
}