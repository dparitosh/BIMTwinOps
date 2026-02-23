import React from 'react';

const TAB_ITEMS = [
  { 
    id: "agent", 
    label: "AI Assistant", 
    icon: "M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z",
    description: "Agent orchestration"
  },
  { 
    id: "bim", 
    label: "BIM Viewer", 
    icon: "M2 20h20M4 20V8l4-4v6l4-4v6l4-4v8M8 20v-4h4v4M18 20V10h3v10",
    description: "View IFC files"
  },
  { 
    id: "revit", 
    label: "Revit Integration", 
    icon: "M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4",
    description: "Upload IFC files"
  },
  { 
    id: "scheduling", 
    label: "Scheduling", 
    icon: "M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z",
    description: "Project timeline"
  },
  { 
    id: "analytics", 
    label: "Analytics", 
    icon: "M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z",
    description: "Model analytics"
  },
  { 
    id: "pointcloud", 
    label: "Point Cloud", 
    icon: "M12 12m-3 0a3 3 0 106 0 3 3 0 10-6 0M6 6m-2 0a2 2 0 104 0 2 2 0 10-4 0M18 6m-2 0a2 2 0 104 0 2 2 0 10-4 0M6 18m-2 0a2 2 0 104 0 2 2 0 10-4 0M18 18m-2 0a2 2 0 104 0 2 2 0 10-4 0",
    description: "Point cloud viewer"
  },
  { 
    id: "openapi", 
    label: "API & Agents", 
    icon: "M12 2a10 10 0 100 20 10 10 0 000-20zm1 14.5v-5h-2v5h2zm0-7V7h-2v2.5h2z",
    description: "API testing"
  },
];

export function Sidebar({ open, currentView, onViewChange, onClose }) {
  return (
    <>
      <aside 
        style={{
          position: 'fixed',
          top: '60px',
          left: 0,
          bottom: 0,
          width: '240px',
          background: 'var(--bg-primary)',
          borderRight: '1px solid var(--border-light)',
          transition: 'transform 0.3s ease',
          transform: open ? 'translateX(0)' : 'translateX(-100%)',
          zIndex: 40,
          overflowY: 'auto',
        }}
        className="sidebar-desktop"
      >
        <nav style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {TAB_ITEMS.map((item) => {
            const isActive = currentView === item.id;
            
            return (
              <button
                key={item.id}
                onClick={() => {
                  onViewChange(item.id);
                  onClose?.();
                }}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  padding: '12px 16px',
                  borderRadius: '8px',
                  border: 'none',
                  background: isActive ? 'var(--tcs-blue, #2563eb)' : 'transparent',
                  color: isActive ? '#ffffff' : 'var(--text-primary)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '14px',
                  fontWeight: isActive ? 600 : 500,
                  transition: 'all 0.2s ease',
                  boxShadow: isActive ? '0 4px 6px -1px rgba(0, 0, 0, 0.1)' : 'none',
                }}
                onMouseEnter={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'var(--bg-secondary)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isActive) {
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <svg 
                  width="20" 
                  height="20" 
                  viewBox="0 0 24 24" 
                  fill={isActive ? 'white' : 'none'}
                  stroke={isActive ? 'white' : 'currentColor'}
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d={item.icon} />
                </svg>
                <div style={{ flex: 1 }}>
                  <div>{item.label}</div>
                  {!isActive && (
                    <div 
                      style={{ 
                        fontSize: '11px', 
                        color: 'var(--text-secondary)', 
                        marginTop: '2px',
                      }}
                    >
                      {item.description}
                    </div>
                  )}
                </div>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Mobile overlay */}
      {open && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0, 0, 0, 0.5)',
            zIndex: 30,
            display: 'none',
          }}
          className="sidebar-overlay"
        />
      )}

      <style>{`
        @media (min-width: 1024px) {
          .sidebar-desktop {
            position: static !important;
            transform: translateX(0) !important;
          }
        }

        @media (max-width: 1024px) {
          .sidebar-overlay {
            display: block !important;
          }
        }
      `}</style>
    </>
  );
}
