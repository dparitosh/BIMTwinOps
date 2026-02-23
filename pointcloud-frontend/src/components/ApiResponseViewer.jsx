/**
 * ApiResponseViewer.jsx
 * Enhanced JSON viewer for API responses with syntax highlighting and copy functionality
 */
import React, { useState } from 'react';

export default function ApiResponseViewer({ response, title = "Response" }) {
  const [copied, setCopied] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  if (!response) return null;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(JSON.stringify(response, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const responseSize = JSON.stringify(response).length;
  const formattedSize = responseSize < 1024 
    ? `${responseSize} B` 
    : `${(responseSize / 1024).toFixed(1)} KB`;

  return (
    <div style={{
      marginTop: 16,
      border: '1px solid var(--border-light)',
      borderRadius: 12,
      overflow: 'hidden',
      background: 'var(--surface)'
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-light)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
            <path d="M16 18l6-6-6-6M8 6l-6 6 6 6" />
          </svg>
          <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
            {title}
          </span>
          <span style={{
            fontSize: 10,
            padding: '2px 8px',
            borderRadius: 10,
            background: 'var(--tcs-blue)18',
            color: 'var(--tcs-blue)',
            fontFamily: 'monospace'
          }}>
            {formattedSize}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => setCollapsed(!collapsed)}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              borderRadius: 6,
              border: '1px solid var(--border-light)',
              background: 'transparent',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4
            }}
          >
            {collapsed ? 'Expand' : 'Collapse'}
          </button>
          <button
            onClick={handleCopy}
            disabled={copied}
            style={{
              padding: '4px 10px',
              fontSize: 11,
              borderRadius: 6,
              border: '1px solid var(--border-light)',
              background: copied ? 'var(--success)' : 'transparent',
              color: copied ? 'white' : 'var(--text-secondary)',
              cursor: copied ? 'default' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 4
            }}
          >
            {copied ? (
              <>
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
                Copied!
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="9" y="9" width="13" height="13" rx="2" />
                  <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
                </svg>
                Copy
              </>
            )}
          </button>
        </div>
      </div>

      {/* Response body */}
      {!collapsed && (
        <div style={{
          maxHeight: 400,
          overflow: 'auto',
          padding: 16,
          background: '#0f1419',
          fontFamily: 'monospace',
          fontSize: 12,
          lineHeight: 1.6
        }}>
          <JsonTree data={response} level={0} />
        </div>
      )}
    </div>
  );
}

// Recursive JSON tree component with syntax highlighting
function JsonTree({ data, level = 0 }) {
  const [collapsed, setCollapsed] = useState(level > 2); // Auto-collapse deep levels

  if (data === null) {
    return <span style={{ color: '#f59e0b' }}>null</span>;
  }

  if (data === undefined) {
    return <span style={{ color: '#9ca3af' }}>undefined</span>;
  }

  if (typeof data === 'boolean') {
    return <span style={{ color: '#a78bfa' }}>{String(data)}</span>;
  }

  if (typeof data === 'number') {
    return <span style={{ color: '#60a5fa' }}>{data}</span>;
  }

  if (typeof data === 'string') {
    // Truncate very long strings
    const displayStr = data.length > 100 ? `${data.substring(0, 97)}...` : data;
    return <span style={{ color: '#34d399' }}>"{displayStr}"</span>;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span style={{ color: '#9ca3af' }}>[]</span>;
    }

    return (
      <span>
        <span style={{ color: '#9ca3af' }}>[</span>
        {!collapsed && (
          <span>
            {data.map((item, idx) => (
              <div key={idx} style={{ marginLeft: 20 }}>
                <JsonTree data={item} level={level + 1} />
                {idx < data.length - 1 && <span style={{ color: '#9ca3af' }}>,</span>}
              </div>
            ))}
          </span>
        )}
        {collapsed && (
          <span
            onClick={() => setCollapsed(false)}
            style={{ color: '#6b7280', cursor: 'pointer', marginLeft: 8, marginRight: 8 }}
          >
            ... {data.length} items
          </span>
        )}
        <span style={{ color: '#9ca3af' }}>]</span>
      </span>
    );
  }

  if (typeof data === 'object') {
    const keys = Object.keys(data);
    
    if (keys.length === 0) {
      return <span style={{ color: '#9ca3af' }}>{'{}'}</span>;
    }

    return (
      <span>
        <span style={{ color: '#9ca3af' }}>{'{'}</span>
        {!collapsed && (
          <span>
            {keys.map((key, idx) => (
              <div key={key} style={{ marginLeft: 20 }}>
                <span style={{ color: '#fb923c' }}>"{key}"</span>
                <span style={{ color: '#9ca3af' }}>: </span>
                <JsonTree data={data[key]} level={level + 1} />
                {idx < keys.length - 1 && <span style={{ color: '#9ca3af' }}>,</span>}
              </div>
            ))}
          </span>
        )}
        {collapsed && (
          <span
            onClick={() => setCollapsed(false)}
            style={{ color: '#6b7280', cursor: 'pointer', marginLeft: 8, marginRight: 8 }}
          >
            ... {keys.length} keys
          </span>
        )}
        <span style={{ color: '#9ca3af' }}>{'}'}</span>
      </span>
    );
  }

  return <span>{String(data)}</span>;
}
