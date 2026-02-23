import React from 'react';

/**
 * SaveStatusIndicator - Floating status indicator for auto-save
 * 
 * Shows current save status:
 * - Saving... (in progress)
 * - Unsaved changes (dirty state)
 * - All changes saved (clean state with timestamp)
 * 
 * Props:
 * - isDirty: boolean - Has unsaved changes
 * - isSaving: boolean - Save in progress
 * - lastSaved: Date | string | null - Last save timestamp
 * - onSaveNow: () => void - Manual save callback
 */
export default function SaveStatusIndicator({ isDirty, isSaving, lastSaved, onSaveNow }) {
  // Don't show indicator if never been dirty and no saves
  if (!isDirty && !lastSaved) return null;
  
  const statusConfig = isSaving 
    ? { 
        bg: '#2563eb', // blue - saving
        icon: 'spinner',
        text: 'Saving...'
      }
    : isDirty 
    ? { 
        bg: '#ff9800', // orange - unsaved
        icon: 'warning',
        text: 'Unsaved changes'
      }
    : { 
        bg: '#4caf50', // green - saved
        icon: 'check',
        text: 'All changes saved'
      };

  return (
    <div style={{
      position: 'fixed',
      bottom: 24,
      right: 24,
      padding: '12px 20px',
      background: statusConfig.bg,
      color: 'white',
      borderRadius: 8,
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      fontSize: '14px',
      fontWeight: 500,
      zIndex: 1000,
      maxWidth: '320px',
      animation: 'slideInFromRight 0.3s ease-out'
    }}>
      {/* Icon */}
      <div style={{ flexShrink: 0 }}>
        {isSaving ? (
          <svg 
            viewBox="0 0 24 24" 
            width="20" 
            height="20" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2"
            style={{ animation: 'spin 1s linear infinite' }}
          >
            <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
          </svg>
        ) : isDirty ? (
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
          </svg>
        ) : (
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2.5">
            <path d="M20 6L9 17l-5-5"/>
          </svg>
        )}
      </div>

      {/* Status Text */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600 }}>{statusConfig.text}</div>
        {lastSaved && !isDirty && (
          <div style={{ 
            fontSize: '12px', 
            opacity: 0.9,
            marginTop: 2
          }}>
            {formatTimestamp(lastSaved)}
          </div>
        )}
      </div>

      {/* Save Now Button (only when dirty) */}
      {isDirty && !isSaving && (
        <button 
          onClick={onSaveNow}
          style={{
            background: 'rgba(255, 255, 255, 0.2)',
            color: 'white',
            border: '1px solid rgba(255, 255, 255, 0.3)',
            padding: '6px 14px',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: '13px',
            fontWeight: 600,
            flexShrink: 0,
            transition: 'all 0.2s',
            backdropFilter: 'blur(4px)'
          }}
          onMouseEnter={(e) => {
            e.target.style.background = 'rgba(255, 255, 255, 0.3)';
            e.target.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.target.style.background = 'rgba(255, 255, 255, 0.2)';
            e.target.style.transform = 'translateY(0)';
          }}
        >
          Save Now
        </button>
      )}
    </div>
  );
}

function formatTimestamp(timestamp) {
  try {
    const date = timestamp instanceof Date ? timestamp : new Date(timestamp);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000); // seconds

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

// Add keyframe animations to CSS (inject into document head)
if (typeof document !== 'undefined') {
  const style = document.createElement('style');
  style.textContent = `
    @keyframes slideInFromRight {
      from {
        transform: translateX(100px);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }

    @keyframes spin {
      from {
        transform: rotate(0deg);
      }
      to {
        transform: rotate(360deg);
      }
    }
  `;
  document.head.appendChild(style);
}
