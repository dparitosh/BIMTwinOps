/**
 * ModernBimViewer.jsx
 * Professional BIM Viewer with modern UX - Forge Viewer style
 * 
 * Features:
 * - Floating toolbars overlay on viewer
 * - Collapsible side panels
 * - Quick access buttons
 * - Streamlined upload workflow
 * - Context-aware UI
 */

import React, { useState, useRef, useCallback, useMemo } from "react";
import ApsViewerExtended from "./ApsViewerExtended";
import OssUploadTranslate from "./OssUploadTranslate";

export default function ModernBimViewer({ apsBaseUrl, viewerUrn, setViewerUrn, viewerAuth, setViewerAuth, onUrnReady }) {
  const viewerRef = useRef(null);
  
  // UI State
  const [uploadDrawerOpen, setUploadDrawerOpen] = useState(!viewerUrn); // Auto-open if no model
  const [toolsDrawerOpen, setToolsDrawerOpen] = useState(false);
  const [propertiesDrawerOpen, setPropertiesDrawerOpen] = useState(false);
  
  // Model State
  const [enabledExtensions, setEnabledExtensions] = useState([]);
  const [selectedElements, setSelectedElements] = useState([]);
  const [modelStats, setModelStats] = useState(null);
  const [selectedTool, setSelectedTool] = useState(null);

  // Toggle extension
  const toggleExtension = async (extId) => {
    const viewer = viewerRef.current?.getViewer();
    if (!viewer) return;
    if (enabledExtensions.includes(extId)) {
      setEnabledExtensions(prev => prev.filter(e => e !== extId));
      viewer.unloadExtension(extId);
    } else {
      setEnabledExtensions(prev => [...prev, extId]);
      await viewer.loadExtension(extId);
    }
  };

  // Model loaded handler
  const handleModelLoaded = useCallback((model) => {
    if (!model) return;
    const instanceTree = model.getInstanceTree();
    if (instanceTree) {
      setModelStats({
        nodeCount: instanceTree.nodeAccess.numNodes,
        rootId: instanceTree.getRootId(),
        name: model.getDocumentNode()?.name() || "Unknown",
      });
      setUploadDrawerOpen(false); // Auto-close upload drawer
    }
  }, []);

  // Selection changed handler
  const handleSelectionChanged = useCallback((dbIds) => {
    setSelectedElements(dbIds);
    if (dbIds && dbIds.length > 0 && !propertiesDrawerOpen) {
      setPropertiesDrawerOpen(true); // Auto-open properties on first selection
    }
  }, [propertiesDrawerOpen]);

  // Tool library data (static, memoized to avoid re-creating JSX on every render)
  const toolCategories = useMemo(() => getToolCategories(), []);

  return (
    <div style={{ position: 'relative', width: '100%', height: 'calc(100vh - 180px)', minHeight: '600px', background: 'var(--bg-primary)', borderRadius: '12px', overflow: 'hidden' }}>
      
      {/* ==== VIEWER CANVAS (Full Screen) ==== */}
      <div style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
        <ApsViewerExtended 
          ref={viewerRef}
          apsBaseUrl={apsBaseUrl} 
          urn={viewerUrn} 
          auth={viewerAuth}
          onModelLoaded={handleModelLoaded}
          onSelectionChanged={handleSelectionChanged}
          style={{ width: '100%', height: '100%' }}
        />
        
        {/* Watermark / No Model State */}
        {!viewerUrn && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            textAlign: 'center',
            pointerEvents: 'none',
            opacity: 0.3
          }}>
            <svg viewBox="0 0 24 24" width="80" height="80" fill="none" stroke="currentColor" strokeWidth="1">
              <path d="M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4"/>
              <path d="M18 20V10h3v10"/>
            </svg>
            <div style={{ marginTop: '16px', fontSize: '18px', fontWeight: 600, color: 'var(--text-secondary)' }}>
              No Model Loaded
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-muted)', marginTop: '8px' }}>
              Click the upload button to get started
            </div>
          </div>
        )}
      </div>

      {/* ==== TOP BAR (Floating Overlay) ==== */}
      <div style={{
        position: 'absolute',
        top: '16px',
        left: '16px',
        right: '16px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        zIndex: 100,
        pointerEvents: 'none'
      }}>
        
        {/* Left: Model Info Card */}
        <div style={{
          background: 'rgba(17, 24, 39, 0.95)',
          backdropFilter: 'blur(12px)',
          borderRadius: '12px',
          padding: '12px 16px',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
          pointerEvents: 'auto',
          maxWidth: '400px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '40px',
              height: '40px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0
            }}>
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" strokeWidth="2">
                <path d="M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4"/>
              </svg>
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              {modelStats ? (
                <>
                  <div style={{ 
                    fontSize: '14px', 
                    fontWeight: 700, 
                    color: 'white',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis'
                  }}>
                    {modelStats.name}
                  </div>
                  <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.6)', marginTop: '2px' }}>
                    {modelStats.nodeCount?.toLocaleString()} elements
                    {selectedElements.length > 0 && ` • ${selectedElements.length} selected`}
                  </div>
                </>
              ) : (
                <>
                  <div style={{ fontSize: '14px', fontWeight: 700, color: 'white' }}>
                    BIM Viewer
                  </div>
                  <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.6)', marginTop: '2px' }}>
                    Professional 3D Model Viewer
                  </div>
                </>
              )}
            </div>
            {viewerUrn && (
              <div style={{
                padding: '6px 10px',
                borderRadius: '6px',
                background: 'rgba(16, 185, 129, 0.2)',
                border: '1px solid rgba(16, 185, 129, 0.4)',
                fontSize: '11px',
                fontWeight: 600,
                color: '#10b981',
                flexShrink: 0
              }}>
                LOADED
              </div>
            )}
          </div>
        </div>

        {/* Right: Action Buttons */}
        <div style={{ display: 'flex', gap: '8px', pointerEvents: 'auto' }}>
          {/* Upload Button */}
          <button
            onClick={() => setUploadDrawerOpen(!uploadDrawerOpen)}
            style={{
              background: uploadDrawerOpen ? 'var(--tcs-blue)' : 'rgba(17, 24, 39, 0.95)',
              backdropFilter: 'blur(12px)',
              border: uploadDrawerOpen ? '1px solid var(--tcs-blue)' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '10px',
              padding: '12px 16px',
              color: 'white',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            Upload Model
          </button>

          {/* Tools Button */}
          <button
            onClick={() => setToolsDrawerOpen(!toolsDrawerOpen)}
            style={{
              background: toolsDrawerOpen ? 'var(--tcs-blue)' : 'rgba(17, 24, 39, 0.95)',
              backdropFilter: 'blur(12px)',
              border: toolsDrawerOpen ? '1px solid var(--tcs-blue)' : '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '10px',
              padding: '12px',
              color: 'white',
              cursor: 'pointer',
              boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)',
              position: 'relative',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
            </svg>
            {enabledExtensions.length > 0 && (
              <div style={{
                position: 'absolute',
                top: '-6px',
                right: '-6px',
                background: 'var(--tcs-orange)',
                borderRadius: '50%',
                width: '20px',
                height: '20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '10px',
                fontWeight: 700,
                border: '2px solid rgba(17, 24, 39, 0.95)'
              }}>
                {enabledExtensions.length}
              </div>
            )}
          </button>

          {/* Properties Button (only show when model loaded) */}
          {modelStats && (
            <button
              onClick={() => setPropertiesDrawerOpen(!propertiesDrawerOpen)}
              style={{
                background: propertiesDrawerOpen ? 'var(--tcs-blue)' : 'rgba(17, 24, 39, 0.95)',
                backdropFilter: 'blur(12px)',
                border: propertiesDrawerOpen ? '1px solid var(--tcs-blue)' : '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '10px',
                padding: '12px',
                color: 'white',
                cursor: 'pointer',
                boxShadow: '0 4px 16px rgba(0, 0, 0, 0.3)',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 7h18M3 12h18M3 17h18"/>
              </svg>
            </button>
          )}
        </div>
      </div>

      {/* ==== UPLOAD DRAWER (Right Side) ==== */}
      {uploadDrawerOpen && (
        <div style={{
          position: 'absolute',
          top: 0,
          right: 0,
          width: '420px',
          height: '100%',
          background: 'rgba(17, 24, 39, 0.98)',
          backdropFilter: 'blur(20px)',
          borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
          boxShadow: '-10px 0 40px rgba(0, 0, 0, 0.5)',
          zIndex: 200,
          overflowY: 'auto',
          animation: 'slideInRight 0.3s ease'
        }}>
          {/* Drawer Header */}
          <div style={{ 
            padding: '24px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
            position: 'sticky',
            top: 0,
            background: 'rgba(17, 24, 39, 0.98)',
            backdropFilter: 'blur(20px)',
            zIndex: 1
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'white' }}>
                Upload Model
              </h3>
              <button
                onClick={() => setUploadDrawerOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'rgba(255, 255, 255, 0.6)',
                  cursor: 'pointer',
                  padding: '4px',
                  borderRadius: '6px',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
                  e.currentTarget.style.color = 'white';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'none';
                  e.currentTarget.style.color = 'rgba(255, 255, 255, 0.6)';
                }}
              >
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12"/>
                </svg>
              </button>
            </div>
            <p style={{ margin: 0, fontSize: '13px', color: 'rgba(255, 255, 255, 0.6)' }}>
              Upload IFC, RVT, DWG, or other CAD/BIM files for 3D viewing
            </p>
          </div>

          {/* Drawer Content */}
          <div style={{ padding: '24px' }}>
            {/* Quick Upload Component */}
            <OssUploadTranslate 
              apsBaseUrl={apsBaseUrl} 
              onUrnReady={(data) => {
                onUrnReady(data);
                setUploadDrawerOpen(false);
              }} 
            />

            {/* Divider */}
            <div style={{ 
              margin: '32px 0', 
              height: '1px', 
              background: 'rgba(255, 255, 255, 0.1)',
              position: 'relative'
            }}>
              <span style={{
                position: 'absolute',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                background: 'rgba(17, 24, 39, 0.98)',
                padding: '0 12px',
                fontSize: '12px',
                color: 'rgba(255, 255, 255, 0.4)',
                fontWeight: 600
              }}>
                OR
              </span>
            </div>

            {/* Manual URN Entry */}
            <div style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <label style={{ display: 'block', marginBottom: '12px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'white', marginBottom: '8px' }}>
                  Paste Model URN
                </div>
                <input
                  type="text"
                  value={viewerUrn}
                  onChange={(e) => setViewerUrn(e.target.value)}
                  placeholder="urn:adsk.objects:os.object:bucket/file.ifc"
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '6px',
                    color: 'white',
                    fontSize: '13px',
                    outline: 'none',
                    transition: 'all 0.2s'
                  }}
                  onFocus={(e) => e.target.style.borderColor = 'var(--tcs-blue)'}
                  onBlur={(e) => e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'}
                />
              </label>

              <label style={{ display: 'block', marginTop: '16px' }}>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'white', marginBottom: '8px' }}>
                  Authentication Type
                </div>
                <select
                  value={viewerAuth}
                  onChange={(e) => setViewerAuth(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '10px 12px',
                    background: 'rgba(255, 255, 255, 0.05)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    borderRadius: '6px',
                    color: 'white',
                    fontSize: '13px',
                    outline: 'none',
                    cursor: 'pointer'
                  }}
                >
                  <option value="app">2-Legged (Server-to-Server)</option>
                  <option value="user">3-Legged (User Login)</option>
                </select>
              </label>
            </div>

            {/* Info Box */}
            <div style={{
              marginTop: '24px',
              padding: '12px',
              background: 'rgba(59, 130, 246, 0.1)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '8px',
              fontSize: '12px',
              color: 'rgba(255, 255, 255, 0.7)',
              lineHeight: '1.6'
            }}>
              <strong style={{ color: '#60a5fa' }}>💡 Quick Tip:</strong> For files under 100MB, use Quick Upload. 
              For larger models or cloud projects, use the URN method.
            </div>
          </div>
        </div>
      )}

      {/* ==== TOOLS DRAWER (Right Side) ==== */}
      {toolsDrawerOpen && (
        <ToolsDrawer 
          isOpen={toolsDrawerOpen}
          onClose={() => setToolsDrawerOpen(false)}
          toolCategories={toolCategories}
          enabledExtensions={enabledExtensions}
          toggleExtension={toggleExtension}
          selectedTool={selectedTool}
          setSelectedTool={setSelectedTool}
        />
      )}

      {/* ==== PROPERTIES DRAWER (Right Side) ==== */}
      {propertiesDrawerOpen && modelStats && (
        <PropertiesDrawer 
          isOpen={propertiesDrawerOpen}
          onClose={() => setPropertiesDrawerOpen(false)}
          selectedElements={selectedElements}
          modelStats={modelStats}
        />
      )}

      {/* Add CSS animation */}
      <style>{`
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
}

/* ========== TOOLS DRAWER COMPONENT ========== */
function ToolsDrawer({ isOpen, onClose, toolCategories, enabledExtensions, toggleExtension, selectedTool, setSelectedTool }) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      right: 0,
      width: '420px',
      height: '100%',
      background: 'rgba(17, 24, 39, 0.98)',
      backdropFilter: 'blur(20px)',
      borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
      boxShadow: '-10px 0 40px rgba(0, 0, 0, 0.5)',
      zIndex: 200,
      overflowY: 'auto',
      animation: 'slideInRight 0.3s ease'
    }}>
      {/* Header */}
      <div style={{ 
        padding: '24px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        position: 'sticky',
        top: 0,
        background: 'rgba(17, 24, 39, 0.98)',
        backdropFilter: 'blur(20px)',
        zIndex: 1
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'white' }}>
            Tools & Extensions
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'rgba(255, 255, 255, 0.6)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.color = 'white';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'none';
              e.currentTarget.style.color = 'rgba(255, 255, 255, 0.6)';
            }}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
       <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          fontSize: '13px',
          color: 'rgba(255, 255, 255, 0.6)'
        }}>
          <div style={{
            padding: '4px 10px',
            background: enabledExtensions.length > 0 ? 'var(--tcs-blue)' : 'rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            fontSize: '12px',
            fontWeight: 600,
            color: 'white'
          }}>
            {enabledExtensions.length} Active
          </div>
          <span>Click any tool to learn more</span>
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: '24px' }}>
        {selectedTool ? (
          // Tool Detail View
          <ToolDetailView 
            tool={selectedTool}
            isEnabled={enabledExtensions.includes(selectedTool.id)}
            onToggle={() => toggleExtension(selectedTool.id)}
            onBack={() => setSelectedTool(null)}
          />
        ) : (
          // Tool Library View
          <>
            {toolCategories.map((category, idx) => (
              <div key={idx} style={{ marginBottom: '32px' }}>
                {/* Category Header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginBottom: '16px',
                  paddingBottom: '12px',
                  borderBottom: '2px solid rgba(255, 255, 255, 0.1)'
                }}>
                  <div style={{ color: 'var(--tcs-blue)' }}>
                    {category.icon}
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '15px', fontWeight: 700, color: 'white' }}>
                      {category.category}
                    </div>
                    <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.5)', marginTop: '2px' }}>
                      {category.description}
                    </div>
                  </div>
                </div>

                {/* Tools Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '10px' }}>
                  {category.tools.map(tool => {
                    const isEnabled = enabledExtensions.includes(tool.id);
                    return (
                      <button
                        key={tool.id}
                        onClick={() => setSelectedTool(tool)}
                        style={{
                          background: isEnabled ? 'rgba(37, 99, 235, 0.2)' : 'rgba(255, 255, 255, 0.03)',
                          border: isEnabled ? '1px solid var(--tcs-blue)' : '1px solid rgba(255, 255, 255, 0.1)',
                          borderRadius: '10px',
                          padding: '14px',
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          textAlign: 'left',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '12px'
                        }}
                        onMouseEnter={(e) => {
                          if (!isEnabled) {
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)';
                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          if (!isEnabled) {
                            e.currentTarget.style.background = 'rgba(255, 255, 255, 0.03)';
                            e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)';
                          }
                        }}
                      >
                        <div style={{
                          width: '36px',
                          height: '36px',
                          borderRadius: '8px',
                          background: isEnabled ? 'var(--tcs-blue)' : 'rgba(255, 255, 255, 0.1)',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          flexShrink: 0,
                          color: 'white'
                        }}>
                          {tool.icon}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ fontSize: '14px', fontWeight: 600, color: 'white' }}>
                            {tool.name}
                          </div>
                          {isEnabled && (
                            <div style={{ fontSize: '11px', color: 'var(--tcs-blue)', marginTop: '2px', fontWeight: 600 }}>
                              ✓ ENABLED
                            </div>
                          )}
                        </div>
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="rgba(255, 255, 255, 0.4)" strokeWidth="2">
                          <path d="M9 5l7 7-7 7"/>
                        </svg>
                      </button>
                    );
                  })}
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}

/* ========== TOOL DETAIL VIEW ========== */
function ToolDetailView({ tool, isEnabled, onToggle, onBack }) {
  return (
    <div>
      {/* Back Button */}
      <button
        onClick={onBack}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--tcs-blue)',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: 600,
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          marginBottom: '20px',
          padding: '8px 0'
        }}
      >
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M19 12H5m7 7l-7-7 7-7"/>
        </svg>
        Back to Tools
      </button>

      {/* Tool Header Card */}
      <div style={{
        background: 'linear-gradient(135deg, var(--tcs-blue), var(--tcs-navy))',
        borderRadius: '12px',
        padding: '20px',
        marginBottom: '24px'
      }}>
        <div style={{ display: 'flex', alignItems: 'start', gap: '14px', marginBottom: '16px' }}>
          <div style={{
            width: '48px',
            height: '48px',
            borderRadius: '10px',
            background: 'rgba(255, 255, 255, 0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            flexShrink: 0
          }}>
            {tool.icon}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'white', marginBottom: '4px' }}>
              {tool.name}
            </div>
            <div style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.8)' }}>
              {tool.category}
            </div>
          </div>
        </div>
        
        {/* Toggle Button */}
        <button
          onClick={onToggle}
          style={{
            width: '100%',
            padding: '12px',
            background: isEnabled ? 'rgba(255, 255, 255, 0.2)' : 'white',
            border: 'none',
            borderRadius: '8px',
            color: isEnabled ? 'white' : 'var(--tcs-blue)',
            fontSize: '14px',
            fontWeight: 700,
            cursor: 'pointer',
            transition: 'all 0.2s'
          }}
        >
          {isEnabled ? '✓ Tool Enabled - Click to Disable' : 'Enable This Tool'}
        </button>
      </div>

      {/* About */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'white', marginBottom: '10px' }}>
          About This Tool
        </div>
        <div style={{
          background: 'rgba(255, 255, 255, 0.03)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          borderRadius: '8px',
          padding: '14px',
          fontSize: '13px',
          lineHeight: '1.7',
          color: 'rgba(255, 255, 255, 0.8)'
        }}>
          {tool.fullDescription}
        </div>
      </div>

      {/* Use Cases */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'white', marginBottom: '10px' }}>
          Common Use Cases
        </div>
        <div style={{ display: 'grid', gap: '10px' }}>
          {tool.useCases?.map((useCase, idx) => (
            <div key={idx} style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'start',
              gap: '10px'
            }}>
              <div style={{ color: 'var(--tcs-blue)', fontSize: '18px', flexShrink: 0 }}>→</div>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: 'white', marginBottom: '2px' }}>
                  {useCase.title}
                </div>
                <div style={{ fontSize: '12px', color: 'rgba(255, 255, 255, 0.6)' }}>
                  {useCase.description}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* How to Use */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 700, color: 'white', marginBottom: '10px' }}>
          How to Use
        </div>
        <div style={{ display: 'grid', gap: '10px' }}>
          {tool.steps?.map((step, idx) => (
            <div key={idx} style={{
              background: 'rgba(255, 255, 255, 0.03)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              borderRadius: '8px',
              padding: '12px 14px',
              display: 'flex',
              alignItems: 'start',
              gap: '12px'
            }}>
              <div style={{
                width: '24px',
                height: '24px',
                borderRadius: '50%',
                background: 'var(--tcs-blue)',
                color: 'white',
                fontSize: '12px',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0
              }}>
                {idx + 1}
              </div>
              <div style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.8)', lineHeight: '1.6', paddingTop: '2px' }}>
                {step}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Pro Tips */}
      {tool.tips && (
        <div style={{
          background: 'rgba(251, 146, 60, 0.1)',
          border: '1px solid rgba(251, 146, 60, 0.3)',
          borderRadius: '8px',
          padding: '14px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="var(--tcs-orange)">
              <path d="M12 2a7 7 0 015 11.9V17a3 3 0 01-3 3H10a3 3 0 01-3-3v-3.1A7 7 0 0112 2zm0 2a5 5 0 00-3.54 8.54l.54.5V17a1 1 0 001 1h4a1 1 0 001-1v-3.96l.54-.5A5 5 0 0012 4z"/>
            </svg>
            <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--tcs-orange)' }}>
              Pro Tips
            </div>
          </div>
          <div style={{ fontSize: '12px', color: 'rgba(251, 146, 60, 0.9)', lineHeight: '1.6' }}>
            {tool.tips}
          </div>
        </div>
      )}
    </div>
  );
}

/* ========== PROPERTIES DRAWER ========== */
function PropertiesDrawer({ isOpen, onClose, selectedElements, modelStats }) {
  if (!isOpen) return null;

  return (
    <div style={{
      position: 'absolute',
      top: 0,
      right: 0,
      width: '380px',
      height: '100%',
      background: 'rgba(17, 24, 39, 0.98)',
      backdropFilter: 'blur(20px)',
      borderLeft: '1px solid rgba(255, 255, 255, 0.1)',
      boxShadow: '-10px 0 40px rgba(0, 0, 0, 0.5)',
      zIndex: 200,
      overflowY: 'auto',
      animation: 'slideInRight 0.3s ease'
    }}>
      {/* Header */}
      <div style={{ 
        padding: '24px',
        borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        position: 'sticky',
        top: 0,
        background: 'rgba(17, 24, 39, 0.98)',
        backdropFilter: 'blur(20px)',
        zIndex: 1
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: 'white' }}>
            Properties
          </h3>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              color: 'rgba(255, 255, 255, 0.6)',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '6px',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)';
              e.currentTarget.style.color = 'white';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'none';
              e.currentTarget.style.color = 'rgba(255, 255, 255, 0.6)';
            }}
          >
            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M18 6L6 18M6 6l12 12"/>
            </svg>
          </button>
        </div>
        <div style={{ fontSize: '13px', color: 'rgba(255, 255, 255, 0.6)' }}>
          {selectedElements.length > 0 
            ? `${selectedElements.length} element${selectedElements.length > 1 ? 's' : ''} selected`
            : 'Select elements to view properties'}
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: '24px' }}>
        {selectedElements.length > 0 ? (
          <div style={{
            background: 'rgba(59, 130, 246, 0.1)',
            border: '1px solid rgba(59, 130, 246, 0.3)',
            borderRadius: '8px',
            padding: '14px',
            fontSize: '13px',
            color: 'rgba(255, 255, 255, 0.8)',
            textAlign: 'center'
          }}>
            <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="var(--tcs-blue)" strokeWidth="2" style={{ margin: '0 auto 12px' }}>
              <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>
            <div style={{ fontWeight: 600, marginBottom: '6px' }}>
              Properties Panel
            </div>
            <div style={{ fontSize: '12px', opacity: 0.8 }}>
              Element properties will be displayed here. This panel integrates with the Autodesk Viewer's property panel system.
            </div>
          </div>
        ) : (
          <div style={{
            textAlign: 'center',
            padding: '40px 20px',
            color: 'rgba(255, 255, 255, 0.4)'
          }}>
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: '0 auto 16px', opacity: 0.3 }}>
              <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/>
            </svg>
            <div style={{ fontSize: '14px', marginBottom: '8px' }}>
              No Selection
            </div>
            <div style={{ fontSize: '12px' }}>
              Click on elements in the 3D viewer to inspect their properties
            </div>
          </div>
        )}

        {/* Model Stats */}
        <div style={{ marginTop: '24px' }}>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'white', marginBottom: '12px' }}>
            Model Information
          </div>
          <div style={{
            background: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '8px',
            padding: '14px',
            fontSize: '13px'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <span style={{ color: 'rgba(255, 255, 255, 0.6)' }}>Model Name:</span>
              <span style={{ color: 'white', fontWeight: 600 }}>{modelStats.name}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px', paddingBottom: '10px', borderBottom: '1px solid rgba(255, 255, 255, 0.1)' }}>
              <span style={{ color: 'rgba(255, 255, 255, 0.6)' }}>Total Elements:</span>
              <span style={{ color: 'white', fontWeight: 600 }}>{modelStats.nodeCount?.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'rgba(255, 255, 255, 0.6)' }}>Root ID:</span>
              <span style={{ color: 'white', fontWeight: 600 }}>{modelStats.rootId}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ========== TOOL CATEGORIES DATA ========== */
function getToolCategories() {
  return [
    {
      category: 'Review & Markup',
      icon: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>,
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
            'Enable the tool from the tools panel',
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
      icon: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 3v18h18"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/></svg>,
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
      icon: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>,
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
      icon: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M7 7h10v10H7z"/><path d="M10 10l5 3-5 3V10z"/></svg>,
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
      icon: <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>,
      description: 'Advanced coordination tools',
      tools: [
        { 
          id: 'TransformExtension', 
          name: 'Move Elements', 
          icon: <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14.7 6.3a1 1 0 000 1.4l1.6 1.6a1 1 0 001.4 0l3.77-3.77a6 6 0 01-7.94 7.94l-6.91 6.91a2.12 2.12 0 01-3-3l6.91-6.91a6 6 0 017.94-7.94l-3.76 3.76z"/></svg>,
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
  ];
}
