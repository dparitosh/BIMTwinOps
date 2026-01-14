// src/components/GraphViewer.jsx
import React, { useRef, useEffect, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { forceManyBody, forceCollide } from "d3-force";

/**
 GraphViewer - uniform node sizes + configurable link strategy
 Props:
  - sceneId
  - segments: [{ segment_key, semantic_name, centroid, num_points }, ...]
  - edges (optional) - if provided will be used instead of generated links
  - onNodeClick(nodeId)
  - selectedSegmentId
  - uniformRadius (px) default 12
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
  selectedSegmentId = null,
  uniformRadius = 12,
  connectMode = "complete", // "complete" or "knn"
  knn = 3,
}) {
  const fgRef = useRef();
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });

  useEffect(() => {
    // defensive
    if (!Array.isArray(segments)) {
      console.error("GraphViewer: segments must be an array");
      setGraphData({ nodes: [], links: [] });
      return;
    }

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

    // if explicit edges provided, prefer them (coerced to full ids)
    let links = [];
    if (Array.isArray(edges) && edges.length) {
      links = edges.map(e => ({
        source: `${sceneId}_sem_${e.from}`,
        target: `${sceneId}_sem_${e.to}`,
        distance: e.distance ?? 0,
      })).filter(l => nodes.find(n => n.id === l.source) && nodes.find(n => n.id === l.target));
    } else {
      // generate links by strategy
      if (connectMode === "knn") {
        links = buildKnnLinks(nodes, Math.max(1, Math.floor(knn)));
      } else {
        // default complete
        links = buildCompleteLinks(nodes);
      }
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

  return (
    <div style={{ width: "100%", height: "100%", borderRadius: 8, overflow: 'hidden' }}>
      <ForceGraph2D
        ref={fgRef}
        graphData={graphData}
        backgroundColor="#f8fafc"
        nodeLabel={(node) => `${node.label} — ${node.num_points ?? 0} pts`}
        linkColor={() => "#cbd5e1"}
        linkWidth={1}
        onNodeClick={(node) => onNodeClick?.(node.id)}
        nodeCanvasObject={(node, ctx, globalScale) => {
          const r = node.id === selectedSegmentId ? uniformRadius * 1.8 : uniformRadius;
          ctx.beginPath();
          ctx.arc(node.x, node.y, r, 0, 2 * Math.PI, false);
          // TCS colors: selected = orange, default = blue
          ctx.fillStyle = node.id === selectedSegmentId ? "#FF6600" : "#0076CE";
          ctx.fill();

          // draw label
          const fontSize = Math.max(10, 12 / Math.max(globalScale, 0.4));
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = "#1e293b";
          ctx.fillText(node.label, node.x + r + 6, node.y + fontSize/2 - 2);
        }}
        nodePointerAreaPaint={(node, color, ctx) => {
          ctx.fillStyle = color;
          ctx.beginPath();
          ctx.arc(node.x, node.y, uniformRadius + 6, 0, Math.PI * 2);
          ctx.fill();
        }}
      />
    </div>
  );
}
