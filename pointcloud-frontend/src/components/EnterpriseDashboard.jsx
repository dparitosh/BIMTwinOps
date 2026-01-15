/**
 * EnterpriseDashboard.jsx
 * Enterprise-grade dashboard for SMART BIM Digital Twin Platform
 * TCS Corporate Branding
 */
import React, { useState, useEffect, useRef } from "react";
import ApsViewerExtended, { AVAILABLE_EXTENSIONS } from "./ApsViewerExtended";

// Dashboard widgets configuration
const DASHBOARD_WIDGETS = [
  { id: "model-stats", title: "Model Statistics", icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" },
  { id: "recent-activity", title: "Recent Activity", icon: "M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" },
  { id: "project-health", title: "Project Health", icon: "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" },
  { id: "team-members", title: "Team Members", icon: "M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" },
];

export default function EnterpriseDashboard({ 
  apsBaseUrl, 
  viewerUrn, 
  viewerAuth,
  onUrnChange 
}) {
  const viewerRef = useRef(null);
  const [enabledExtensions, setEnabledExtensions] = useState([]);
  const [selectedElements, setSelectedElements] = useState([]);
  const [modelStats, setModelStats] = useState(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activePanel, setActivePanel] = useState("extensions");

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

  // Handle selection change from viewer
  const handleSelectionChanged = (dbIds) => {
    setSelectedElements(dbIds);
  };

  // Handle model loaded
  const handleModelLoaded = (model) => {
    if (!model) return;
    
    // Get model statistics
    const instanceTree = model.getInstanceTree();
    if (instanceTree) {
      const stats = {
        nodeCount: instanceTree.nodeAccess.numNodes,
        rootId: instanceTree.getRootId(),
        name: model.getDocumentNode()?.name() || "Unknown",
      };
      setModelStats(stats);
    }
  };

  // Group extensions by category
  const extensionsByCategory = AVAILABLE_EXTENSIONS.reduce((acc, ext) => {
    if (!acc[ext.category]) acc[ext.category] = [];
    acc[ext.category].push(ext);
    return acc;
  }, {});

  return (
    <div className="enterprise-dashboard" style={{ display: 'flex', height: '100%', gap: 16 }}>
      {/* Main Viewer Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        {/* Toolbar */}
        <div className="dashboard-toolbar" style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '12px 16px',
          background: 'var(--surface)',
          borderRadius: 12,
          marginBottom: 12,
          border: '1px solid var(--border-light)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
              <path d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
            </svg>
            <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
              {modelStats?.name || "No Model Loaded"}
            </span>
          </div>

          {/* Quick Stats */}
          {modelStats && (
            <div style={{ display: 'flex', gap: 16 }}>
              <div className="stat-badge" style={statBadgeStyle}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>Elements</span>
                <span style={{ fontWeight: 600, color: 'var(--tcs-blue)' }}>{modelStats.nodeCount?.toLocaleString()}</span>
              </div>
              <div className="stat-badge" style={statBadgeStyle}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>Selected</span>
                <span style={{ fontWeight: 600, color: 'var(--tcs-orange)' }}>{selectedElements.length}</span>
              </div>
              <div className="stat-badge" style={statBadgeStyle}>
                <span style={{ color: 'var(--text-secondary)', fontSize: 11 }}>Extensions</span>
                <span style={{ fontWeight: 600, color: '#10b981' }}>{enabledExtensions.length}</span>
              </div>
            </div>
          )}

          {/* Sidebar Toggle */}
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              padding: 8,
              borderRadius: 8,
              background: sidebarOpen ? 'var(--tcs-blue)' : 'var(--bg-tertiary)',
              border: 'none',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke={sidebarOpen ? 'white' : 'var(--text-secondary)'} strokeWidth="2">
              <path d="M4 6h16M4 12h16M4 18h7" />
            </svg>
          </button>
        </div>

        {/* Viewer Container */}
        <div style={{ flex: 1, borderRadius: 12, overflow: 'hidden', background: '#1a1a2e' }}>
          <ApsViewerExtended
            ref={viewerRef}
            apsBaseUrl={apsBaseUrl}
            urn={viewerUrn}
            auth={viewerAuth}
            enabledExtensions={enabledExtensions}
            onSelectionChanged={handleSelectionChanged}
            onModelLoaded={handleModelLoaded}
            style={{ height: '100%' }}
          />
        </div>
      </div>

      {/* Right Sidebar */}
      {sidebarOpen && (
        <div className="dashboard-sidebar" style={{
          width: 320,
          display: 'flex',
          flexDirection: 'column',
          gap: 12
        }}>
          {/* Panel Tabs */}
          <div style={{
            display: 'flex',
            gap: 4,
            padding: 4,
            background: 'var(--surface)',
            borderRadius: 10,
            border: '1px solid var(--border-light)'
          }}>
            {[
              { id: 'extensions', label: 'Extensions', icon: 'M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10' },
              { id: 'properties', label: 'Properties', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
              { id: 'analytics', label: 'Analytics', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActivePanel(tab.id)}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: 'none',
                  cursor: 'pointer',
                  background: activePanel === tab.id ? 'var(--tcs-blue)' : 'transparent',
                  color: activePanel === tab.id ? 'white' : 'var(--text-secondary)',
                  fontWeight: 500,
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  transition: 'all 0.2s'
                }}
              >
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d={tab.icon} />
                </svg>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Extensions Panel */}
          {activePanel === 'extensions' && (
            <div className="panel-content" style={{
              flex: 1,
              background: 'var(--surface)',
              borderRadius: 12,
              border: '1px solid var(--border-light)',
              overflow: 'auto',
              padding: 16
            }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-primary)' }}>
                Viewer Extensions
              </h3>
              
              {Object.entries(extensionsByCategory).map(([category, extensions]) => (
                <div key={category} style={{ marginBottom: 20 }}>
                  <div style={{
                    fontSize: 11,
                    fontWeight: 600,
                    color: 'var(--text-secondary)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                    marginBottom: 8
                  }}>
                    {category}
                  </div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                    {extensions.map(ext => (
                      <button
                        key={ext.id}
                        onClick={() => toggleExtension(ext.id)}
                        disabled={!viewerUrn}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          padding: 10,
                          borderRadius: 8,
                          border: '1px solid',
                          borderColor: enabledExtensions.includes(ext.id) ? 'var(--tcs-blue)' : 'var(--border-light)',
                          background: enabledExtensions.includes(ext.id) ? 'rgba(0, 120, 215, 0.1)' : 'var(--bg-tertiary)',
                          cursor: viewerUrn ? 'pointer' : 'not-allowed',
                          opacity: viewerUrn ? 1 : 0.5,
                          transition: 'all 0.2s',
                          textAlign: 'left',
                          width: '100%'
                        }}
                      >
                        <div style={{
                          width: 32,
                          height: 32,
                          borderRadius: 6,
                          background: enabledExtensions.includes(ext.id) ? 'var(--tcs-blue)' : 'var(--bg-secondary)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0
                        }}>
                          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke={enabledExtensions.includes(ext.id) ? 'white' : 'var(--text-secondary)'} strokeWidth="2">
                            <path d={ext.icon} />
                          </svg>
                        </div>
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)' }}>{ext.name}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {ext.description}
                          </div>
                        </div>
                        <div style={{
                          width: 18,
                          height: 18,
                          borderRadius: 4,
                          background: enabledExtensions.includes(ext.id) ? 'var(--tcs-blue)' : 'var(--border-light)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}>
                          {enabledExtensions.includes(ext.id) && (
                            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="white" strokeWidth="3">
                              <path d="M5 13l4 4L19 7" />
                            </svg>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Properties Panel */}
          {activePanel === 'properties' && (
            <div className="panel-content" style={{
              flex: 1,
              background: 'var(--surface)',
              borderRadius: 12,
              border: '1px solid var(--border-light)',
              overflow: 'auto',
              padding: 16
            }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-primary)' }}>
                Element Properties
              </h3>
              
              {selectedElements.length === 0 ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
                  <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 12px', opacity: 0.5 }}>
                    <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                  </svg>
                  <div>Select elements in the viewer to see properties</div>
                </div>
              ) : (
                <div>
                  <div style={{
                    padding: 12,
                    background: 'var(--bg-tertiary)',
                    borderRadius: 8,
                    marginBottom: 12
                  }}>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 4 }}>Selected Elements</div>
                    <div style={{ fontWeight: 600, color: 'var(--tcs-blue)' }}>{selectedElements.length} item(s)</div>
                  </div>
                  
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                    Use the <strong>Custom Properties Extension</strong> to add custom properties to elements.
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Analytics Panel */}
          {activePanel === 'analytics' && (
            <div className="panel-content" style={{
              flex: 1,
              background: 'var(--surface)',
              borderRadius: 12,
              border: '1px solid var(--border-light)',
              overflow: 'auto',
              padding: 16
            }}>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--text-primary)' }}>
                Model Analytics
              </h3>
              
              {!modelStats ? (
                <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-secondary)' }}>
                  <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 12px', opacity: 0.5 }}>
                    <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <div>Load a model to view analytics</div>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  {/* Stats Cards */}
                  <div style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: 12
                  }}>
                    <div style={analyticsCardStyle}>
                      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--tcs-blue)' }}>
                        {modelStats.nodeCount?.toLocaleString()}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Total Elements</div>
                    </div>
                    <div style={analyticsCardStyle}>
                      <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--tcs-orange)' }}>
                        {enabledExtensions.length}
                      </div>
                      <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Active Extensions</div>
                    </div>
                  </div>
                  
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
                    Use the <strong>XLS Extension</strong> to export detailed model analytics to Excel.
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const statBadgeStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '6px 12px',
  background: 'var(--bg-tertiary)',
  borderRadius: 8,
  minWidth: 70
};

const analyticsCardStyle = {
  padding: 16,
  background: 'var(--bg-tertiary)',
  borderRadius: 10,
  textAlign: 'center'
};
