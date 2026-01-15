/**
 * ProjectScheduling.jsx
 * Enterprise-grade project scheduling page with Gantt chart integration
 * Integrates with PhasingExtension from APS Extensions
 */
import React, { useState, useEffect, useRef } from "react";
import ApsViewerExtended from "./ApsViewerExtended";

// Mock schedule data (in production, this would come from a backend/database)
const SAMPLE_SCHEDULE_DATA = [
  { id: 1, name: "Foundation", start: "2026-01-01", end: "2026-02-15", progress: 100, status: "completed", dbIds: [1, 2, 3] },
  { id: 2, name: "Structural Steel", start: "2026-02-01", end: "2026-04-30", progress: 75, status: "in-progress", dbIds: [4, 5, 6, 7] },
  { id: 3, name: "MEP Rough-In", start: "2026-03-15", end: "2026-05-30", progress: 50, status: "in-progress", dbIds: [8, 9, 10] },
  { id: 4, name: "Exterior Envelope", start: "2026-04-01", end: "2026-07-15", progress: 25, status: "in-progress", dbIds: [11, 12, 13] },
  { id: 5, name: "Interior Finishes", start: "2026-06-01", end: "2026-09-30", progress: 0, status: "not-started", dbIds: [14, 15, 16] },
  { id: 6, name: "Final MEP", start: "2026-08-01", end: "2026-10-15", progress: 0, status: "not-started", dbIds: [17, 18] },
  { id: 7, name: "Commissioning", start: "2026-10-01", end: "2026-11-30", progress: 0, status: "not-started", dbIds: [19, 20] },
];

const STATUS_COLORS = {
  "completed": "#10b981",
  "in-progress": "var(--tcs-blue)",
  "not-started": "var(--text-secondary)",
  "delayed": "#ef4444"
};

export default function ProjectScheduling({
  apsBaseUrl,
  viewerUrn,
  viewerAuth
}) {
  const viewerRef = useRef(null);
  const [scheduleData, setScheduleData] = useState(SAMPLE_SCHEDULE_DATA);
  const [selectedTask, setSelectedTask] = useState(null);
  const [viewMode, setViewMode] = useState("split"); // "split", "gantt", "model"
  const [highlightMode, setHighlightMode] = useState("status"); // "status", "progress", "none"

  // Calculate project timeline
  const projectStart = new Date(Math.min(...scheduleData.map(t => new Date(t.start))));
  const projectEnd = new Date(Math.max(...scheduleData.map(t => new Date(t.end))));
  const totalDays = Math.ceil((projectEnd - projectStart) / (1000 * 60 * 60 * 24));

  // Handle task selection
  const handleTaskClick = (task) => {
    setSelectedTask(task);
    
    // Highlight elements in viewer
    if (viewerRef.current && task.dbIds?.length > 0) {
      viewerRef.current.isolate(task.dbIds);
      viewerRef.current.fitToView(task.dbIds);
      
      // Apply color based on status
      const color = new window.Autodesk.Viewing.THREE.Vector4(
        ...hexToRgb(STATUS_COLORS[task.status] || "#666666"),
        1
      );
      task.dbIds.forEach(dbId => {
        viewerRef.current.setThemingColor(dbId, color);
      });
    }
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedTask(null);
    if (viewerRef.current) {
      viewerRef.current.isolate([]);
      viewerRef.current.clearThemingColors();
    }
  };

  // Apply highlighting to all elements based on mode
  const applyHighlighting = () => {
    if (!viewerRef.current || highlightMode === "none") {
      viewerRef.current?.clearThemingColors();
      return;
    }

    scheduleData.forEach(task => {
      let color;
      if (highlightMode === "status") {
        color = STATUS_COLORS[task.status];
      } else if (highlightMode === "progress") {
        const hue = (task.progress / 100) * 120; // 0 = red, 120 = green
        color = `hsl(${hue}, 70%, 50%)`;
      }

      if (color && task.dbIds) {
        const rgb = hexToRgb(color) || hslToRgb(color);
        if (rgb) {
          const threeColor = new window.Autodesk.Viewing.THREE.Vector4(...rgb, 1);
          task.dbIds.forEach(dbId => {
            viewerRef.current?.setThemingColor(dbId, threeColor);
          });
        }
      }
    });
  };

  useEffect(() => {
    applyHighlighting();
  }, [highlightMode, scheduleData]);

  // Calculate Gantt bar position
  const getBarStyle = (task) => {
    const start = new Date(task.start);
    const end = new Date(task.end);
    const startOffset = (start - projectStart) / (1000 * 60 * 60 * 24);
    const duration = (end - start) / (1000 * 60 * 60 * 24);
    
    return {
      left: `${(startOffset / totalDays) * 100}%`,
      width: `${(duration / totalDays) * 100}%`
    };
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 12 }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '12px 16px',
        background: 'var(--surface)',
        borderRadius: 12,
        border: '1px solid var(--border-light)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
            <path d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Project Schedule</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
              4D BIM Construction Sequencing
            </p>
          </div>
        </div>

        {/* View Mode Toggle */}
        <div style={{ display: 'flex', gap: 4, padding: 4, background: 'var(--bg-tertiary)', borderRadius: 8 }}>
          {[
            { id: 'split', icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z', label: 'Split' },
            { id: 'gantt', icon: 'M3 4h18M3 8h18M3 12h12M3 16h8', label: 'Gantt' },
            { id: 'model', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4', label: 'Model' }
          ].map(mode => (
            <button
              key={mode.id}
              onClick={() => setViewMode(mode.id)}
              style={{
                padding: '6px 12px',
                borderRadius: 6,
                border: 'none',
                cursor: 'pointer',
                background: viewMode === mode.id ? 'var(--tcs-blue)' : 'transparent',
                color: viewMode === mode.id ? 'white' : 'var(--text-secondary)',
                fontWeight: 500,
                fontSize: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2">
                <path d={mode.icon} />
              </svg>
              {mode.label}
            </button>
          ))}
        </div>

        {/* Highlight Mode */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>Color by:</span>
          <select
            value={highlightMode}
            onChange={(e) => setHighlightMode(e.target.value)}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              border: '1px solid var(--border-light)',
              background: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: 12
            }}
          >
            <option value="status">Status</option>
            <option value="progress">Progress</option>
            <option value="none">None</option>
          </select>
        </div>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        {/* Gantt Chart */}
        {(viewMode === 'split' || viewMode === 'gantt') && (
          <div style={{
            flex: viewMode === 'gantt' ? 1 : '0 0 50%',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--surface)',
            borderRadius: 12,
            border: '1px solid var(--border-light)',
            overflow: 'hidden'
          }}>
            {/* Timeline Header */}
            <div style={{
              display: 'flex',
              borderBottom: '1px solid var(--border-light)',
              background: 'var(--bg-tertiary)'
            }}>
              <div style={{ width: 200, padding: 12, fontWeight: 600, fontSize: 12, color: 'var(--text-secondary)', flexShrink: 0 }}>
                Task Name
              </div>
              <div style={{ flex: 1, padding: 12, display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-secondary)' }}>
                <span>{projectStart.toLocaleDateString()}</span>
                <span>{projectEnd.toLocaleDateString()}</span>
              </div>
            </div>

            {/* Tasks */}
            <div style={{ flex: 1, overflow: 'auto' }}>
              {scheduleData.map(task => (
                <div
                  key={task.id}
                  onClick={() => handleTaskClick(task)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    borderBottom: '1px solid var(--border-light)',
                    cursor: 'pointer',
                    background: selectedTask?.id === task.id ? 'rgba(0, 120, 215, 0.1)' : 'transparent',
                    transition: 'background 0.2s'
                  }}
                >
                  {/* Task Name */}
                  <div style={{ width: 200, padding: 12, flexShrink: 0 }}>
                    <div style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)' }}>{task.name}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{task.progress}% complete</div>
                  </div>

                  {/* Gantt Bar */}
                  <div style={{ flex: 1, padding: '12px 16px', position: 'relative', height: 40 }}>
                    <div style={{
                      position: 'absolute',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      height: 24,
                      borderRadius: 4,
                      background: 'var(--bg-tertiary)',
                      ...getBarStyle(task)
                    }}>
                      {/* Progress Fill */}
                      <div style={{
                        height: '100%',
                        width: `${task.progress}%`,
                        borderRadius: 4,
                        background: STATUS_COLORS[task.status],
                        transition: 'width 0.3s'
                      }} />
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Legend */}
            <div style={{
              display: 'flex',
              gap: 16,
              padding: 12,
              borderTop: '1px solid var(--border-light)',
              background: 'var(--bg-tertiary)'
            }}>
              {Object.entries(STATUS_COLORS).map(([status, color]) => (
                <div key={status} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 12, height: 12, borderRadius: 3, background: color }} />
                  <span style={{ fontSize: 11, color: 'var(--text-secondary)', textTransform: 'capitalize' }}>
                    {status.replace('-', ' ')}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 3D Viewer */}
        {(viewMode === 'split' || viewMode === 'model') && (
          <div style={{
            flex: viewMode === 'model' ? 1 : '0 0 50%',
            borderRadius: 12,
            overflow: 'hidden',
            background: '#1a1a2e'
          }}>
            <ApsViewerExtended
              ref={viewerRef}
              apsBaseUrl={apsBaseUrl}
              urn={viewerUrn}
              auth={viewerAuth}
              enabledExtensions={["PhasingExtension"]}
              style={{ height: '100%' }}
            />
          </div>
        )}
      </div>

      {/* Task Details Panel */}
      {selectedTask && (
        <div style={{
          padding: 16,
          background: 'var(--surface)',
          borderRadius: 12,
          border: '1px solid var(--border-light)',
          display: 'flex',
          alignItems: 'center',
          gap: 24
        }}>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <div style={{
                width: 12,
                height: 12,
                borderRadius: 3,
                background: STATUS_COLORS[selectedTask.status]
              }} />
              <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--text-primary)' }}>
                {selectedTask.name}
              </h3>
            </div>
            <div style={{ display: 'flex', gap: 24, fontSize: 13, color: 'var(--text-secondary)' }}>
              <span>Start: {new Date(selectedTask.start).toLocaleDateString()}</span>
              <span>End: {new Date(selectedTask.end).toLocaleDateString()}</span>
              <span>Elements: {selectedTask.dbIds?.length || 0}</span>
            </div>
          </div>

          {/* Progress Bar */}
          <div style={{ width: 200 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Progress</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-primary)' }}>{selectedTask.progress}%</span>
            </div>
            <div style={{ height: 8, borderRadius: 4, background: 'var(--bg-tertiary)' }}>
              <div style={{
                height: '100%',
                width: `${selectedTask.progress}%`,
                borderRadius: 4,
                background: STATUS_COLORS[selectedTask.status],
                transition: 'width 0.3s'
              }} />
            </div>
          </div>

          <button
            onClick={clearSelection}
            style={{
              padding: '8px 16px',
              borderRadius: 6,
              border: '1px solid var(--border-light)',
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: 12
            }}
          >
            Clear Selection
          </button>
        </div>
      )}
    </div>
  );
}

// Utility functions
function hexToRgb(hex) {
  if (!hex || typeof hex !== 'string') return null;
  if (hex.startsWith('var(')) return null;
  
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [
    parseInt(result[1], 16) / 255,
    parseInt(result[2], 16) / 255,
    parseInt(result[3], 16) / 255
  ] : null;
}

function hslToRgb(hsl) {
  if (!hsl || typeof hsl !== 'string' || !hsl.startsWith('hsl')) return null;
  
  const match = hsl.match(/hsl\((\d+),\s*(\d+)%,\s*(\d+)%\)/);
  if (!match) return null;
  
  let h = parseInt(match[1]) / 360;
  let s = parseInt(match[2]) / 100;
  let l = parseInt(match[3]) / 100;
  
  let r, g, b;
  if (s === 0) {
    r = g = b = l;
  } else {
    const hue2rgb = (p, q, t) => {
      if (t < 0) t += 1;
      if (t > 1) t -= 1;
      if (t < 1/6) return p + (q - p) * 6 * t;
      if (t < 1/2) return q;
      if (t < 2/3) return p + (q - p) * (2/3 - t) * 6;
      return p;
    };
    const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
    const p = 2 * l - q;
    r = hue2rgb(p, q, h + 1/3);
    g = hue2rgb(p, q, h);
    b = hue2rgb(p, q, h - 1/3);
  }
  
  return [r, g, b];
}
