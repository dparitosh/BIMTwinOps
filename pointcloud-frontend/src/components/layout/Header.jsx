import React, { useState, useEffect } from 'react';

export function Header({ 
  backendUrl, 
  apsUrl,
  onMenuClick,
  showMenuButton = true,
  title = "BIMTwinOps",
  subtitle = "Digital Twin Platform"
}) {
  const [backendStatus, setBackendStatus] = useState('checking');
  const [neo4jStatus, setNeo4jStatus] = useState('checking');
  const [apsStatus, setApsStatus] = useState('checking');

  useEffect(() => {
    const checkBackend = async () => {
      try {
        const response = await fetch(`${backendUrl}/health`, {
          signal: AbortSignal.timeout(3000),
        });
        if (response.ok) {
          const data = await response.json();
          setBackendStatus('connected');
          setNeo4jStatus(data.neo4j_connected ? 'connected' : 'disconnected');
        } else {
          setBackendStatus('disconnected');
        }
      } catch {
        setBackendStatus('disconnected');
      }
    };

    const checkAPS = async () => {
      try {
        const response = await fetch(`${apsUrl}/aps/config`, {
          signal: AbortSignal.timeout(3000),
        });
        if (response.ok) {
          setApsStatus('connected');
        } else {
          setApsStatus('disconnected');
        }
      } catch {
        setApsStatus('disconnected');
      }
    };

    checkBackend();
    checkAPS();
    const interval = setInterval(() => {
      checkBackend();
      checkAPS();
    }, 30000);
    return () => clearInterval(interval);
  }, [backendUrl, apsUrl]);

  const getStatusColor = (status) => {
    switch (status) {
      case 'connected': return '#10b981'; // green
      case 'disconnected': return '#ef4444'; // red
      case 'checking': return '#f59e0b'; // yellow
      default: return '#6b7280'; // gray
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'connected': return 'Connected';
      case 'disconnected': return 'Offline';
      case 'checking': return 'Checking...';
      default: return 'Unknown';
    }
  };

  return (
    <header 
      style={{
        height: '60px',
        borderBottom: '1px solid var(--border-light)',
        background: 'var(--bg-primary)',
        position: 'sticky',
        top: 0,
        zIndex: 50,
        boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
      }}
    >
      <div 
        style={{
          height: '100%',
          padding: '0 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Left side - Title and menu */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          {showMenuButton && (
            <button
              onClick={onMenuClick}
              style={{
                display: 'none',
                padding: '8px',
                background: 'transparent',
                border: 'none',
                cursor: 'pointer',
                borderRadius: '6px',
                color: 'var(--text-primary)',
              }}
              className="mobile-menu-btn"
            >
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div 
              style={{
                width: '36px',
                height: '36px',
                background: 'linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 700,
                fontSize: '16px',
              }}
            >
              BT
            </div>
            <div>
              <h1 
                style={{
                  fontSize: '16px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  margin: 0,
                  lineHeight: 1.2,
                }}
              >
                {title}
              </h1>
              <p 
                style={{
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  margin: 0,
                  lineHeight: 1.2,
                }}
              >
                {subtitle}
              </p>
            </div>
          </div>
        </div>

        {/* Right side - Status indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Backend API Status */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              background: 'var(--bg-secondary)',
              fontSize: '12px',
            }}
            title={`Backend API: ${getStatusText(backendStatus)}`}
          >
            <span style={{ color: 'var(--text-secondary)' }}>[API]</span>
            <div 
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: getStatusColor(backendStatus),
              }}
            />
          </div>

          {/* Neo4j Status */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              background: 'var(--bg-secondary)',
              fontSize: '12px',
            }}
            title={`Neo4j: ${getStatusText(neo4jStatus)}`}
          >
            <span style={{ color: 'var(--text-secondary)' }}>[DB]</span>
            <div 
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: getStatusColor(neo4jStatus),
              }}
            />
          </div>

          {/* APS Status */}
          <div 
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '6px 12px',
              borderRadius: '6px',
              background: 'var(--bg-secondary)',
              fontSize: '12px',
            }}
            title={`APS Service: ${getStatusText(apsStatus)}`}
          >
            <span style={{ color: 'var(--text-secondary)' }}>[APS]</span>
            <div 
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: getStatusColor(apsStatus),
              }}
            />
          </div>
        </div>
      </div>

      <style>{`
        @media (max-width: 1024px) {
          .mobile-menu-btn {
            display: block !important;
          }
        }
      `}</style>
    </header>
  );
}
