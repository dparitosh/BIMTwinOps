/**
 * BimPropertiesPanel.jsx
 * Displays detailed properties for selected BIM elements from APS Viewer
 */
import React, { useState, useEffect, useCallback } from 'react';

export default function BimPropertiesPanel({ viewer, selectedElements }) {
  const [properties, setProperties] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState(new Set(['Identity Data']));

  const fetchProperties = useCallback(async () => {
    if (!viewer || !selectedElements || selectedElements.length === 0) return;

    setLoading(true);
    try {
      const dbId = selectedElements[0]; // Show properties for first selected element
      const model = viewer.model;

      // Get element properties
      model.getProperties(dbId, (result) => {
        if (result && result.properties) {
          // Group properties by category
          const grouped = result.properties.reduce((acc, prop) => {
            const category = prop.displayCategory || 'Other';
            if (!acc[category]) acc[category] = [];
            acc[category].push(prop);
            return acc;
          }, {});

          setProperties({
            name: result.name || `Element ${dbId}`,
            dbId: dbId,
            externalId: result.externalId,
            grouped: grouped
          });
        }
        setLoading(false);
      }, (error) => {
        console.error('[Properties] Failed to fetch:', error);
        setLoading(false);
      });

    } catch (err) {
      console.error('[Properties] Error:', err);
      setLoading(false);
    }
  }, [viewer, selectedElements]);

  useEffect(() => {
    if (!viewer || !selectedElements || selectedElements.length === 0) {
      return;
    }

    // Schedule to avoid synchronous setState (via fetchProperties) inside effect body
    const id = requestAnimationFrame(() => fetchProperties());
    return () => cancelAnimationFrame(id);
  }, [viewer, selectedElements, fetchProperties]);

  const toggleCategory = (category) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(category)) {
        next.delete(category);
      } else {
        next.add(category);
      }
      return next;
    });
  };

  if (!selectedElements || selectedElements.length === 0) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        padding: 24,
        color: 'var(--text-secondary)',
        textAlign: 'center'
      }}>
        <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginBottom: 16, opacity: 0.5 }}>
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <path d="M9 3v18M3 9h18M3 15h18" />
        </svg>
        <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 6 }}>No Selection</div>
        <div style={{ fontSize: 12 }}>Click on an element in the viewer to see its properties</div>
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: 14, fontWeight: 600 }}>Loading properties...</div>
        </div>
      </div>
    );
  }

  if (!properties || !properties.grouped) {
    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        color: 'var(--text-secondary)'
      }}>
        <div style={{ fontSize: 13 }}>No properties available</div>
      </div>
    );
  }

  return (
    <div style={{ 
      display: 'flex', 
      flexDirection: 'column', 
      height: '100%',
      overflow: 'hidden'
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px',
        borderBottom: '1px solid var(--border-light)',
        background: 'var(--surface)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M9 3v18M3 9h18M3 15h18" />
          </svg>
          <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>
            Properties
          </span>
        </div>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--tcs-blue)', marginBottom: 2 }}>
          {properties.name}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'monospace' }}>
          DB ID: {properties.dbId}
          {properties.externalId && ` • External ID: ${properties.externalId}`}
        </div>
        {selectedElements.length > 1 && (
          <div style={{ 
            fontSize: 11, 
            color: 'var(--tcs-orange)', 
            marginTop: 6,
            padding: '4px 8px',
            background: 'var(--tcs-orange)18',
            borderRadius: 4,
            display: 'inline-block'
          }}>
            +{selectedElements.length - 1} more selected
          </div>
        )}
      </div>

      {/* Properties list */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {Object.entries(properties.grouped).map(([category, props]) => {
          const isExpanded = expandedCategories.has(category);
          
          return (
            <div key={category} style={{ borderBottom: '1px solid var(--border-light)' }}>
              {/* Category header */}
              <button
                onClick={() => toggleCategory(category)}
                style={{
                  width: '100%',
                  padding: '10px 16px',
                  background: 'var(--bg-secondary)',
                  border: 'none',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-tertiary)'}
                onMouseLeave={e => e.currentTarget.style.background = 'var(--bg-secondary)'}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <svg 
                    viewBox="0 0 24 24" 
                    width="14" 
                    height="14" 
                    fill="none" 
                    stroke="var(--text-secondary)" 
                    strokeWidth="2"
                    style={{ 
                      transform: isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
                      transition: 'transform 0.2s'
                    }}
                  >
                    <path d="M9 6l6 6-6 6" />
                  </svg>
                  <span style={{ 
                    fontSize: 13, 
                    fontWeight: 600, 
                    color: 'var(--text-primary)' 
                  }}>
                    {category}
                  </span>
                </div>
                <span style={{ 
                  fontSize: 11, 
                  color: 'var(--text-secondary)',
                  padding: '2px 8px',
                  borderRadius: 10,
                  background: 'var(--bg-tertiary)'
                }}>
                  {props.length}
                </span>
              </button>

              {/* Category properties */}
              {isExpanded && (
                <div style={{ padding: '8px 0' }}>
                  {props.map((prop, idx) => (
                    <div 
                      key={idx}
                      style={{
                        padding: '6px 16px',
                        display: 'flex',
                        justifyContent: 'space-between',
                        gap: 12,
                        fontSize: 12,
                        borderLeft: '3px solid transparent',
                        transition: 'all 0.15s'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.background = 'var(--bg-secondary)';
                        e.currentTarget.style.borderLeftColor = 'var(--tcs-blue)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.borderLeftColor = 'transparent';
                      }}
                    >
                      <span style={{ 
                        color: 'var(--text-secondary)', 
                        flex: '0 0 45%',
                        wordBreak: 'break-word'
                      }}>
                        {prop.displayName}
                      </span>
                      <span style={{ 
                        color: 'var(--text-primary)', 
                        fontWeight: 500,
                        flex: '1 1 55%',
                        textAlign: 'right',
                        wordBreak: 'break-word',
                        fontFamily: typeof prop.displayValue === 'number' ? 'monospace' : 'inherit'
                      }}>
                        {formatPropertyValue(prop.displayValue, prop.units)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer stats */}
      <div style={{
        padding: '8px 16px',
        borderTop: '1px solid var(--border-light)',
        background: 'var(--bg-secondary)',
        fontSize: 11,
        color: 'var(--text-secondary)',
        display: 'flex',
        justifyContent: 'space-between'
      }}>
        <span>
          {Object.keys(properties.grouped).length} categories
        </span>
        <span>
          {Object.values(properties.grouped).reduce((sum, props) => sum + props.length, 0)} properties
        </span>
      </div>
    </div>
  );
}

// Helper to format property values with units
function formatPropertyValue(value, units) {
  if (value === null || value === undefined) return '—';
  
  // Handle boolean
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  
  // Handle numbers with units
  if (typeof value === 'number') {
    const formatted = value.toLocaleString(undefined, { maximumFractionDigits: 3 });
    return units ? `${formatted} ${units}` : formatted;
  }
  
  // Handle strings (truncate if too long)
  if (typeof value === 'string') {
    return value.length > 50 ? `${value.substring(0, 47)}...` : value;
  }
  
  return String(value);
}
