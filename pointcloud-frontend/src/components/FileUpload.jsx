import React from "react";

export default function FileUpload({ onUpload }) {
  const handleChange = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    onUpload(f);
  };

  return (
    <div className="flex items-center gap-4">
      <label className="cursor-pointer">
        <div className="tcs-btn-primary flex items-center gap-2">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
          </svg>
          Choose File
        </div>
        <input type="file" accept=".npy,.txt,.npz" onChange={handleChange} className="hidden" />
      </label>
      <div className="text-sm" style={{ color: 'var(--text-secondary)' }}>
        Supported: .npy (preferred) or .txt (xyz / xyzrgb)
      </div>
    </div>
  );
}
