/**
 * ModelAnalytics.jsx
 * Enterprise-grade analytics page for BIM model data
 * Includes element statistics, property analysis, and export capabilities
 */
import React, { useState, useEffect, useRef } from "react";
import ApsViewerExtended from "./ApsViewerExtended";

// Category colors for visualization
const CATEGORY_COLORS = {
  "Walls": "#3b82f6",
  "Floors": "#10b981",
  "Roofs": "#f59e0b",
  "Doors": "#ef4444",
  "Windows": "#8b5cf6",
  "Columns": "#ec4899",
  "Beams": "#06b6d4",
  "Furniture": "#84cc16",
  "Mechanical": "#f97316",
  "Electrical": "#eab308",
  "Plumbing": "#14b8a6",
  "Other": "#6b7280"
};

export default function ModelAnalytics({
  apsBaseUrl,
  viewerUrn,
  viewerAuth
}) {
  const viewerRef = useRef(null);
  const [modelData, setModelData] = useState(null);
  const [categoryStats, setCategoryStats] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeChart, setActiveChart] = useState("category"); // "category", "level", "material"

  // Analyze model when loaded
  const handleModelLoaded = async (model) => {
    if (!model || !viewerRef.current) return;
    
    setLoading(true);
    
    try {
      const viewer = viewerRef.current.getViewer();
      const instanceTree = model.getInstanceTree();
      
      if (!instanceTree) {
        setLoading(false);
        return;
      }

      // Get all leaf nodes
      const dbIds = [];
      instanceTree.enumNodeChildren(instanceTree.getRootId(), (dbId) => {
        if (instanceTree.getChildCount(dbId) === 0) {
          dbIds.push(dbId);
        }
      }, true);

      // Collect category statistics
      const categories = {};
      let processed = 0;

      const processNode = (dbId) => {
        return new Promise((resolve) => {
          viewer.getProperties(dbId, (props) => {
            const categoryProp = props.properties?.find(p => 
              p.displayName === "Category" || 
              p.attributeName === "Category" ||
              p.displayName === "Type"
            );
            
            const category = categoryProp?.displayValue || "Other";
            
            if (!categories[category]) {
              categories[category] = {
                name: category,
                count: 0,
                dbIds: [],
                color: CATEGORY_COLORS[category] || CATEGORY_COLORS["Other"]
              };
            }
            
            categories[category].count++;
            categories[category].dbIds.push(dbId);
            processed++;
            
            resolve();
          }, (err) => {
            categories["Other"] = categories["Other"] || { name: "Other", count: 0, dbIds: [], color: CATEGORY_COLORS["Other"] };
            categories["Other"].count++;
            categories["Other"].dbIds.push(dbId);
            processed++;
            resolve();
          });
        });
      };

      // Process in batches to avoid blocking
      const batchSize = 100;
      for (let i = 0; i < dbIds.length; i += batchSize) {
        const batch = dbIds.slice(i, i + batchSize);
        await Promise.all(batch.map(processNode));
      }

      // Sort by count
      const sortedCategories = Object.values(categories).sort((a, b) => b.count - a.count);
      
      setCategoryStats(sortedCategories);
      setModelData({
        totalElements: dbIds.length,
        categories: sortedCategories.length,
        processedAt: new Date().toISOString()
      });
    } catch (err) {
      console.error("Error analyzing model:", err);
    } finally {
      setLoading(false);
    }
  };

  // Handle category selection
  const handleCategoryClick = (category) => {
    setSelectedCategory(category);
    
    if (viewerRef.current && category?.dbIds?.length > 0) {
      viewerRef.current.isolate(category.dbIds);
      viewerRef.current.fitToView(category.dbIds);
      
      // Apply category color
      const rgb = hexToRgb(category.color);
      if (rgb) {
        const threeColor = new window.Autodesk.Viewing.THREE.Vector4(...rgb, 1);
        category.dbIds.forEach(dbId => {
          viewerRef.current.setThemingColor(dbId, threeColor);
        });
      }
    }
  };

  // Clear selection
  const clearSelection = () => {
    setSelectedCategory(null);
    if (viewerRef.current) {
      viewerRef.current.isolate([]);
      viewerRef.current.clearThemingColors();
    }
  };

  // Export to CSV
  const exportToCSV = () => {
    if (!categoryStats.length) return;
    
    const headers = ["Category", "Element Count", "Percentage"];
    const rows = categoryStats.map(cat => [
      cat.name,
      cat.count,
      ((cat.count / modelData.totalElements) * 100).toFixed(2) + "%"
    ]);
    
    const csv = [headers, ...rows].map(row => row.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement("a");
    a.href = url;
    a.download = "model-analytics.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  // Calculate max count for bar chart scaling
  const maxCount = Math.max(...categoryStats.map(c => c.count), 1);

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
            <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Model Analytics</h2>
            <p style={{ fontSize: 12, color: 'var(--text-secondary)', margin: 0 }}>
              Element statistics and property analysis
            </p>
          </div>
        </div>

        {/* Summary Stats */}
        {modelData && (
          <div style={{ display: 'flex', gap: 16 }}>
            <div style={summaryStatStyle}>
              <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--tcs-blue)' }}>
                {modelData.totalElements.toLocaleString()}
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Total Elements</span>
            </div>
            <div style={summaryStatStyle}>
              <span style={{ fontSize: 20, fontWeight: 700, color: 'var(--tcs-orange)' }}>
                {modelData.categories}
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Categories</span>
            </div>
          </div>
        )}

        {/* Export Button */}
        <button
          onClick={exportToCSV}
          disabled={!categoryStats.length}
          style={{
            padding: '8px 16px',
            borderRadius: 8,
            border: 'none',
            background: 'var(--tcs-blue)',
            color: 'white',
            fontWeight: 500,
            fontSize: 13,
            cursor: categoryStats.length ? 'pointer' : 'not-allowed',
            opacity: categoryStats.length ? 1 : 0.5,
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}
        >
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Main Content */}
      <div style={{ flex: 1, display: 'flex', gap: 12, minHeight: 0 }}>
        {/* Analytics Panel */}
        <div style={{
          width: 400,
          display: 'flex',
          flexDirection: 'column',
          gap: 12
        }}>
          {/* Chart Type Selector */}
          <div style={{
            display: 'flex',
            gap: 4,
            padding: 4,
            background: 'var(--surface)',
            borderRadius: 10,
            border: '1px solid var(--border-light)'
          }}>
            {[
              { id: 'category', label: 'By Category' },
              { id: 'level', label: 'By Level' },
              { id: 'material', label: 'By Material' }
            ].map(chart => (
              <button
                key={chart.id}
                onClick={() => setActiveChart(chart.id)}
                style={{
                  flex: 1,
                  padding: '8px 12px',
                  borderRadius: 8,
                  border: 'none',
                  cursor: 'pointer',
                  background: activeChart === chart.id ? 'var(--tcs-blue)' : 'transparent',
                  color: activeChart === chart.id ? 'white' : 'var(--text-secondary)',
                  fontWeight: 500,
                  fontSize: 12
                }}
              >
                {chart.label}
              </button>
            ))}
          </div>

          {/* Bar Chart */}
          <div style={{
            flex: 1,
            background: 'var(--surface)',
            borderRadius: 12,
            border: '1px solid var(--border-light)',
            overflow: 'auto',
            padding: 16
          }}>
            {loading ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{
                    width: 40,
                    height: 40,
                    border: '3px solid var(--border-light)',
                    borderTopColor: 'var(--tcs-blue)',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    margin: '0 auto 12px'
                  }} />
                  <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Analyzing model...</div>
                </div>
              </div>
            ) : categoryStats.length === 0 ? (
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', textAlign: 'center' }}>
                <div>
                  <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="var(--text-secondary)" strokeWidth="1.5" style={{ margin: '0 auto 12px', opacity: 0.5 }}>
                    <path d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 13 }}>Load a model to see analytics</div>
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {categoryStats.map((category, index) => (
                  <div
                    key={category.name}
                    onClick={() => handleCategoryClick(category)}
                    style={{
                      padding: 12,
                      borderRadius: 8,
                      border: '1px solid',
                      borderColor: selectedCategory?.name === category.name ? category.color : 'var(--border-light)',
                      background: selectedCategory?.name === category.name ? `${category.color}10` : 'var(--bg-tertiary)',
                      cursor: 'pointer',
                      transition: 'all 0.2s'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                      <span style={{ fontWeight: 500, fontSize: 13, color: 'var(--text-primary)' }}>
                        {category.name}
                      </span>
                      <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
                        {category.count.toLocaleString()} ({((category.count / modelData.totalElements) * 100).toFixed(1)}%)
                      </span>
                    </div>
                    <div style={{ height: 8, borderRadius: 4, background: 'var(--bg-secondary)', overflow: 'hidden' }}>
                      <div style={{
                        height: '100%',
                        width: `${(category.count / maxCount) * 100}%`,
                        background: category.color,
                        borderRadius: 4,
                        transition: 'width 0.3s'
                      }} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Selected Category Details */}
          {selectedCategory && (
            <div style={{
              padding: 16,
              background: 'var(--surface)',
              borderRadius: 12,
              border: `2px solid ${selectedCategory.color}`
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 16, height: 16, borderRadius: 4, background: selectedCategory.color }} />
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{selectedCategory.name}</span>
                </div>
                <button
                  onClick={clearSelection}
                  style={{
                    padding: '4px 8px',
                    borderRadius: 4,
                    border: '1px solid var(--border-light)',
                    background: 'transparent',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    fontSize: 11
                  }}
                >
                  Clear
                </button>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12 }}>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Elements</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: selectedCategory.color }}>
                    {selectedCategory.count.toLocaleString()}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Percentage</div>
                  <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {((selectedCategory.count / modelData.totalElements) * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 3D Viewer */}
        <div style={{
          flex: 1,
          borderRadius: 12,
          overflow: 'hidden',
          background: '#1a1a2e'
        }}>
          <ApsViewerExtended
            ref={viewerRef}
            apsBaseUrl={apsBaseUrl}
            urn={viewerUrn}
            auth={viewerAuth}
            enabledExtensions={["XLSExtension"]}
            onModelLoaded={handleModelLoaded}
            style={{ height: '100%' }}
          />
        </div>
      </div>
    </div>
  );
}

const summaryStatStyle = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '8px 16px',
  background: 'var(--bg-tertiary)',
  borderRadius: 8
};

function hexToRgb(hex) {
  if (!hex || typeof hex !== 'string') return null;
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? [
    parseInt(result[1], 16) / 255,
    parseInt(result[2], 16) / 255,
    parseInt(result[3], 16) / 255
  ] : null;
}
