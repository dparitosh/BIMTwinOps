import React from 'react';

export function MainContent({ children, loading = false }) {
  return (
    <main 
      style={{
        flex: 1,
        overflow: 'auto',
        background: 'var(--bg-secondary)',
        position: 'relative',
      }}
    >
      {loading && (
        <div 
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'rgba(255, 255, 255, 0.8)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div 
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '12px',
            }}
          >
            <div 
              style={{
                width: '40px',
                height: '40px',
                border: '4px solid var(--border-light)',
                borderTop: '4px solid var(--tcs-blue, #2563eb)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
              }}
            />
            <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
              Loading...
            </span>
          </div>
        </div>
      )}
      
      <div 
        style={{
          height: '100%',
          width: '100%',
        }}
      >
        {children}
      </div>

      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </main>
  );
}
