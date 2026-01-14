import React from "react";

export default function AnnotationPanel({ selected, sceneData }) {
  if (!selected) {
    return (
      <div>
        <h3 className="text-lg font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Annotations</h3>
        <div className="p-4 rounded-lg text-center" style={{ background: 'var(--bg-primary)' }}>
          <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="var(--text-muted)" strokeWidth="1.5" className="mx-auto mb-2">
            <path d="M8 9l4-4 4 4M16 15l-4 4-4-4"/>
          </svg>
          <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Click a point or graph node to view details</p>
        </div>
      </div>
    );
  }

  const { segmentId, label, pointIndex } = selected;
  const seg = (sceneData?.segments || []).find(s => `${sceneData.scene_id}_sem_${s.segment_key}` === segmentId);

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Annotations</h3>

      <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-light)' }}>
        <div className="text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Selected Segment</div>
        <div className="text-sm break-words font-bold" style={{ color: 'var(--tcs-blue)' }}>{segmentId ?? `label:${label}`}</div>
        <div className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>Point index: {pointIndex ?? "n/a"}</div>
      </div>

      {seg ? (
        <div className="text-sm p-3 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border-light)' }}>
          <div className="flex items-center gap-2 mb-2">
            <span className="tcs-badge">{seg.semantic_name}</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
            <div>
              <span className="font-medium">Points:</span>
              <span className="ml-1" style={{ color: 'var(--text-primary)' }}>{seg.num_points}</span>
            </div>
          </div>
          <div className="mt-3 pt-2" style={{ borderTop: '1px solid var(--border-light)' }}>
            <div className="text-xs font-medium mb-1" style={{ color: 'var(--text-secondary)' }}>Centroid</div>
            <pre className="text-xs p-2 rounded overflow-auto" style={{ background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>{JSON.stringify(seg.centroid, null, 2)}</pre>
          </div>
        </div>
      ) : (
        <div className="text-sm p-3 rounded-lg text-center" style={{ background: 'var(--bg-primary)', color: 'var(--text-muted)' }}>
          Segment metadata not available
        </div>
      )}
    </div>
  );
}
