// src/components/GraphViewer.jsx
import React, { useRef, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceManyBody, forceCollide } from "d3-force";
import { getColorForLabel } from "./PointCloudViewer";

/**
 GraphViewer - uniform node sizes + configurable link strategy
 Props:
  - sceneId
  - segments: [{ segment_key, semantic_name, centroid, num_points }, ...]
  - edges (optional) - if provided will be used instead of generated links
  - onNodeClick(nodeId)
  - selectedSegmentId
    - uniformRadius (px) default 10
    - backgroundColor (css color) default "#eaf2ff" (light blue hue)
  - connectMode: "complete" | "knn" (default "complete")
  - knn: integer when connectMode="knn" (default 3)
*/

function euclidean(a = [0,0,0], b = [0,0,0]) {
  const dx = (a[0]||0) - (b[0]||0);
  const dy = (a[1]||0) - (b[1]||0);
  const dz = (a[2]||0) - (b[2]||0);
  return Math.sqrt(dx*dx + dy*dy + dz*dz);
}

function buildCompleteLinks(nodes) {
  const links = [];
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i+1; j < nodes.length; j++) {
      links.push({ source: nodes[i].id, target: nodes[j].id, distance: euclidean(nodes[i].centroid, nodes[j].centroid) });
    }
  }
  return links;
}

function buildKnnLinks(nodes, k = 3) {
  const links = [];
  for (let i = 0; i < nodes.length; i++) {
    const distances = nodes.map((n, idx) => ({ idx, dist: euclidean(nodes[i].centroid, n.centroid) }));
    distances.sort((a,b) => a.dist - b.dist);
    // skip first entry (distance 0 to itself)
    for (let r = 1; r <= Math.min(k, distances.length-1); r++) {
      const j = distances[r].idx;
      // add only once in canonical order
      if (i < j) links.push({ source: nodes[i].id, target: nodes[j].id, distance: distances[r].dist });
      else links.push({ source: nodes[j].id, target: nodes[i].id, distance: distances[r].dist });
    }
  }
  // deduplicate links by source+target
  const seen = new Set();
  const uniq = [];
  for (const l of links) {
    const key = `${l.source}--${l.target}`;
    if (!seen.has(key)) { seen.add(key); uniq.push(l); }
  }
  return uniq;
}

export default function GraphViewer({
  sceneId = "scene",
  segments = [],
  edges = [],
  onNodeClick = () => {},
  onNodeHover = () => {},
  selectedSegmentId = null,
  uniformRadius = 10,
  backgroundColor = "#eaf2ff",
  connectMode = "complete", // "complete" or "knn"
  knn = 3,
}) {
  const fgRef = useRef();
  const containerRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Measure container dimensions
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        if (width > 0 && height > 0) {
          setDimensions({ width, height });
        }
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    
    // Also update after a short delay to ensure layout is complete
    const timer = setTimeout(updateDimensions, 100);
    
    return () => {
      window.removeEventListener('resize', updateDimensions);
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    // defensive
    if (!Array.isArray(segments)) {
      console.error("GraphViewer: segments must be an array");
      setGraphData({ nodes: [], links: [] });
      return;
    }

    console.log("GraphViewer: Processing", segments.length, "segments");

    // build nodes (stable ids)
    const nodes = segments.map((s) => {
      const key = s.segment_key ?? s.semantic_id ?? s.id ?? Math.random().toString(36).slice(2,7);
      return {
        id: `${sceneId}_sem_${key}`,
        key,
        label: s.semantic_name ?? `seg_${key}`,
        centroid: Array.isArray(s.centroid) ? s.centroid : [0,0,0],
        num_points: Number(s.num_points ?? s.numPoints ?? 0),
      };
    });

    console.log("GraphViewer: Created", nodes.length, "nodes");

    // if explicit edges provided, prefer them (coerced to full ids)
    let links = [];
    if (Array.isArray(edges) && edges.length) {
      links = edges.map(e => ({
        source: `${sceneId}_sem_${e.from}`,
        target: `${sceneId}_sem_${e.to}`,
        distance: e.distance ?? 0,
      })).filter(l => nodes.find(n => n.id === l.source) && nodes.find(n => n.id === l.target));
      console.log("GraphViewer: Using provided edges:", links.length);
    } else {
      // generate links by strategy
      if (connectMode === "knn") {
        links = buildKnnLinks(nodes, Math.max(1, Math.floor(knn)));
      } else {
        // default complete
        links = buildCompleteLinks(nodes);
      }
      console.log("GraphViewer: Generated links:", links.length);
    }

    setGraphData({ nodes, links });
  }, [sceneId, segments, edges, connectMode, knn]);

  // apply d3 forces (charge + collide) so nodes don't overlap
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg || !fg.d3Force) return;

    // repulsion to spread nodes
    fg.d3Force("charge", forceManyBody().strength(-80));
    // collision radius uses uniformRadius + padding
    fg.d3Force("collide", forceCollide().radius(() => uniformRadius + 6).strength(0.9));

    // reheating layout
    try { fg.d3ReheatSimulation(); }
    catch(e) { fg.pauseSimulation(); setTimeout(() => fg.resumeSimulation(), 50); }
  }, [graphData, uniformRadius]);

  // Graph control handlers
  const handleZoomIn = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() * 1.3, 200);
    }
  };

  const handleZoomOut = () => {
    if (fgRef.current) {
      fgRef.current.zoom(fgRef.current.zoom() / 1.3, 200);
    }
  };

  const handleFitView = () => {
    if (fgRef.current) {
      fgRef.current.zoomToFit(400, 40);
    }
  };

  const handleCenterView = () => {
    if (fgRef.current) {
      fgRef.current.centerAt(0, 0, 200);
      fgRef.current.zoom(1, 200);
    }
  };

  return (
    <div ref={containerRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}>
      {graphData.nodes.length === 0 ? (
        <div style={{ 
          width: "100%", 
          height: "100%", 
          display: "flex", 
          alignItems: "center", 
          justifyContent: "center",
          background: "#f8fafc",
          borderRadius: 8
        }}>
          <div style={{ textAlign: "center", color: "#64748b" }}>
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: "0 auto 12px" }}>
              <circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>
            </svg>
            <div>No segments to display</div>
          </div>
        </div>
      ) : (
        <ForceGraph2D
          ref={fgRef}
          graphData={graphData}
          width={dimensions.width}
          height={dimensions.height}
          backgroundColor={backgroundColor}
          nodeLabel={(node) => `${node.label} — ${node.num_points ?? 0} pts`}
          linkColor={() => "rgba(30, 64, 175, 0.22)"}
          linkWidth={1}
          onNodeClick={(node) => onNodeClick?.(node.id)}
          onNodeHover={(node) => {
            if (node) {
              onNodeHover?.({
                id: node.id,
                label: node.label,
                segment_key: node.key,
                num_points: node.num_points,
              });
            } else {
              onNodeHover?.(null);
            }
          }}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const r = node.id === selectedSegmentId ? uniformRadius * 1.6 : uniformRadius;
            ctx.beginPath();
            ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
            
            // Use semantic color matching point cloud, with orange border if selected
            const semanticColor = getColorForLabel(node.key);
            ctx.fillStyle = semanticColor;
            ctx.fill();
            
            // Add orange ring for selected node
            if (node.id === selectedSegmentId) {
              ctx.beginPath();
              ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
              ctx.strokeStyle = "#FF6600";
              ctx.lineWidth = 3;
              ctx.stroke();
            }

            // draw label (stroke + fill) for readability on a blue-hue background
            const fontSize = Math.max(10, 12 / Math.max(globalScale, 0.4));
            ctx.font = `${fontSize}px Sans-Serif`;
            const tx = node.x + r + 6;
            const ty = node.y + fontSize / 2 - 2;
            ctx.lineWidth = 3;
            ctx.strokeStyle = "rgba(255, 255, 255, 0.75)";
            ctx.strokeText(node.label, tx, ty);
            ctx.fillStyle = "rgba(15, 23, 42, 0.95)"; // slate-900-ish
            ctx.fillText(node.label, tx, ty);
          }}
          nodePointerAreaPaint={(node, color, ctx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, uniformRadius + 5, 0, Math.PI * 2);
            ctx.fill();
          }}
        />
      )}

      {/* Corporate-Grade Graph Controls */}
      {graphData.nodes.length > 0 && (
        <div style={{
          position: 'absolute',
          top: '12px',
          right: '12px',
          display: 'flex',
          flexDirection: 'column',
          gap: '1px',
          zIndex: 10,
          background: 'white',
          borderRadius: '8px',
          border: '1px solid rgba(0, 118, 206, 0.2)',
          boxShadow: '0 4px 12px rgba(0, 61, 121, 0.15)',
          overflow: 'hidden'
        }}>
          <button
            onClick={handleZoomIn}
            title="Zoom In"
            style={{
              width: '40px',
              height: '40px',
              border: 'none',
              background: 'white',
              color: 'var(--tcs-blue)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>

          <button
            onClick={handleZoomOut}
            title="Zoom Out"
            style={{
              width: '40px',
              height: '40px',
              border: 'none',
              background: 'white',
              color: 'var(--tcs-blue)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/><line x1="8" y1="11" x2="14" y2="11"/>
            </svg>
          </button>

          <button
            onClick={handleFitView}
            title="Fit to View"
            style={{
              width: '40px',
              height: '40px',
              border: 'none',
              background: 'white',
              color: 'var(--tcs-blue)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s',
              borderBottom: '1px solid rgba(0, 118, 206, 0.1)'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
            </svg>
          </button>

          <button
            onClick={handleCenterView}
            title="Center View"
            style={{
              width: '40px',
              height: '40px',
              border: 'none',
              background: 'white',
              color: 'var(--tcs-blue)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--tcs-blue)'; e.currentTarget.style.color = 'white'; }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'white'; e.currentTarget.style.color = 'var(--tcs-blue)'; }}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2.5">
              <circle cx="12" cy="12" r="3"/><circle cx="12" cy="12" r="10"/>
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}
