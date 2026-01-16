import React, { useState, useEffect, useRef } from "react";

export default function AnnotationPanel({ selected, sceneData, onSegmentSelect }) {
  const [expandedCategories, setExpandedCategories] = useState({});
  const [sceneExpanded, setSceneExpanded] = useState(true);

  const toggleCategory = (category) => {
    setExpandedCategories(prev => ({ ...prev, [category]: !prev[category] }));
  };

  // Group segments by semantic_name
  const segmentsByCategory = {};
  (sceneData?.segments || []).forEach(seg => {
    const category = seg.semantic_name || 'unknown';
    if (!segmentsByCategory[category]) {
      segmentsByCategory[category] = [];
    }
    segmentsByCategory[category].push(seg);
  });

  const categories = Object.keys(segmentsByCategory).sort();
  const selectedSegId = selected?.segmentId;

  // Auto-expand category containing selected segment
  useEffect(() => {
    if (selectedSegId && sceneData) {
      console.log('[AnnotationPanel] Selected segment ID:', selectedSegId);
      
      // Find which category contains this segment
      for (const category of categories) {
        const segments = segmentsByCategory[category];
        const found = segments.some(seg => {
          const segId = `${sceneData.scene_id}_sem_${seg.segment_key}`;
          return segId === selectedSegId;
        });
        
        if (found) {
          console.log('[AnnotationPanel] Auto-expanding category:', category);
          setExpandedCategories(prev => ({ ...prev, [category]: true }));
          setSceneExpanded(true);
          break;
        }
      }
    }
  }, [selectedSegId]);

  if (!sceneData || categories.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--text-primary)', flexShrink: 0 }}>Scene Tree</h3>
        <div style={{ flex: 1, minHeight: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px', borderRadius: '8px', background: 'var(--bg-primary)', textAlign: 'center' }}>
          <div>
            <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" className="mx-auto mb-2">
              <path d="M8 9l4-4 4 4M16 15l-4 4-4-4"/>
            </svg>
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Upload a point cloud to view scene tree</p>
          </div>
        </div>
      </div>
    );
  }

  const { segmentId, label, pointIndex } = selected || {};
  const seg = (sceneData?.segments || []).find(s => `${sceneData.scene_id}_sem_${s.segment_key}` === segmentId);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        className="flex items-center justify-between mb-3 pb-3"
        style={{ flexShrink: 0, borderBottom: '2px solid var(--border-light)' }}
      >
        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Scene Hierarchy</h3>
        {sceneData?.segments && (
          <span className="px-2 py-1 rounded" style={{ background: 'var(--tcs-blue)', color: 'white', fontSize: '12px', fontWeight: 600 }}>
            {sceneData.segments.length}
          </span>
        )}
      </div>

      {/* Hierarchical Tree view */}
      <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', fontSize: '13px' }}>
        {/* Root: Scene */}
        <div>
          <div
            onClick={() => setSceneExpanded(!sceneExpanded)}
            className="flex items-center gap-2 p-2 rounded cursor-pointer mb-1"
            style={{ 
              background: 'var(--tcs-blue)',
              color: 'white',
              fontWeight: 600
            }}
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2"
              style={{ transform: sceneExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
              <path d="M9 6l6 6-6 6"/>
            </svg>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z"/>
            </svg>
            <span className="flex-1">{sceneData.scene_id}</span>
            <span className="text-xs px-2 py-0.5 rounded" style={{ background: 'rgba(255,255,255,0.2)' }}>
              {sceneData.segments.length} items
            </span>
          </div>

          {/* Level 2: Categories */}
          {sceneExpanded && (
            <div className="ml-4 space-y-0.5">
              {categories.map(category => {
                const segments = segmentsByCategory[category];
                const isExpanded = expandedCategories[category];
                const categoryId = `category_${category}`;
                
                return (
                  <div key={categoryId}>
                    {/* Category header */}
                    <div
                      onClick={() => toggleCategory(category)}
                      className="flex items-center gap-2 p-2 rounded cursor-pointer hover:bg-opacity-80"
                      style={{ 
                        background: 'var(--bg-primary)',
                        color: 'var(--text-primary)',
                        fontWeight: 500,
                        border: '1px solid var(--border-light)'
                      }}
                    >
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2"
                        style={{ transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}>
                        <path d="M9 6l6 6-6 6"/>
                      </svg>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" opacity="0.7">
                        <path d="M20 6h-8l-2-2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2z"/>
                      </svg>
                      <span className="flex-1">{category}</span>
                      <span className="text-xs px-1.5 py-0.5 rounded" style={{ background: 'var(--surface)', color: 'var(--text-secondary)' }}>
                        {segments.length}
                      </span>
                    </div>

                    {/* Level 3: Segments */}
                    {isExpanded && (
                      <div className="ml-6 mt-0.5 space-y-0.5">
                        {segments.map(segment => {
                          const segId = `${sceneData.scene_id}_sem_${segment.segment_key}`;
                          const isSelected = segId === selectedSegId;
                          
                          return (
                            <div
                              key={segId}
                              onClick={() => {
                                console.log('[AnnotationPanel] Clicking segment:', { segId, segment_key: segment.segment_key, segment });
                                onSegmentSelect && onSegmentSelect(segId, segment);
                              }}
                              className="flex items-center gap-2 p-1.5 pl-3 rounded cursor-pointer"
                              style={{
                                background: isSelected ? 'var(--tcs-orange)' : 'var(--surface)',
                                color: isSelected ? 'white' : 'var(--text-primary)',
                                border: `1px solid ${isSelected ? 'var(--tcs-orange)' : 'var(--border-light)'}`,
                                transition: 'all 0.15s',
                                position: 'relative'
                              }}
                            >
                              {/* Tree connector line */}
                              <div style={{
                                position: 'absolute',
                                left: '-12px',
                                top: '0',
                                bottom: '50%',
                                width: '12px',
                                borderLeft: '1px solid var(--border-light)',
                                borderBottom: '1px solid var(--border-light)'
                              }}></div>
                              
                              <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                                <circle cx="12" cy="12" r="3"/>
                              </svg>
                              <div className="flex-1 text-xs">
                                <div style={{ fontWeight: isSelected ? '600' : '400' }}>
                                  {category} #{segment.segment_key}
                                </div>
                                <div style={{ opacity: 0.7, fontSize: '11px' }}>
                                  {segment.num_points} points
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Selected segment details panel */}
      {seg && (
        <div style={{ flexShrink: 0, marginTop: '12px', paddingTop: '12px', borderTop: '1px solid var(--border-light)' }}>
          <div className="text-xs font-semibold mb-2" style={{ color: 'var(--text-secondary)' }}>
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" style={{ display: 'inline', marginRight: '4px' }}>
              <circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>
            </svg>
            SELECTED DETAILS
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>Category:</span>
              <span className="font-semibold" style={{ color: 'var(--tcs-blue)' }}>{seg.semantic_name}</span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>Segment:</span>
              <span style={{ color: 'var(--text-primary)' }}>#{seg.segment_key}</span>
            </div>
            <div className="flex justify-between">
              <span style={{ color: 'var(--text-secondary)' }}>Points:</span>
              <span style={{ color: 'var(--text-primary)' }}>{seg.num_points.toLocaleString()}</span>
            </div>
            {seg.centroid && (
              <div>
                <div style={{ color: 'var(--text-secondary)' }} className="mb-1">Centroid:</div>
                <div className="p-2 rounded text-xs" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)', fontFamily: 'monospace' }}>
                  [{seg.centroid.map(v => v.toFixed(2)).join(', ')}]
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
