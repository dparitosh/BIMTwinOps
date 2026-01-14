import React from "react";

export default function Loader({ text = "Loading..." }) {
  return (
    <div className="flex items-center gap-4 p-4 rounded-lg" style={{ background: 'var(--bg-primary)' }}>
      <div style={{
        width: 36, height: 36, borderRadius: 18,
        border: "4px solid var(--border-light)",
        borderTopColor: "var(--tcs-blue)",
        animation: "spin 1s linear infinite"
      }} />
      <div className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>{text}</div>

      <style>{`@keyframes spin { from {transform: rotate(0deg)} to {transform: rotate(360deg)} }`}</style>
    </div>
  );
}
