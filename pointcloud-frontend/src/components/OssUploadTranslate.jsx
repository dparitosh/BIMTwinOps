import React, { useState } from "react";

function jsonOrText(res) {
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

export default function OssUploadTranslate({ apsBaseUrl, onUrnReady }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [urn, setUrn] = useState("");

  const uploadAndTranslate = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);

    try {
      const fd = new FormData();
      fd.append("file", file);

      const up = await fetch(`${apsBaseUrl}/oss/upload`, { method: "POST", body: fd });
      if (!up.ok) {
        const body = await jsonOrText(up);
        throw new Error(typeof body === "string" ? body : (body?.error || `Upload failed (${up.status})`));
      }
      const upJson = await up.json();
      const urnValue = upJson?.urn;
      if (!urnValue) throw new Error("Upload did not return urn");
      setUrn(urnValue);

      const tr = await fetch(`${apsBaseUrl}/md/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urn: urnValue, auth: "app", force: false }),
      });
      if (!tr.ok) {
        const body = await jsonOrText(tr);
        throw new Error(typeof body === "string" ? body : (body?.error || `Translate failed (${tr.status})`));
      }

      for (let i = 0; i < 60; i++) {
        const mf = await fetch(`${apsBaseUrl}/md/manifest?urn=${encodeURIComponent(urnValue)}&auth=app`);
        if (!mf.ok) {
          const body = await jsonOrText(mf);
          throw new Error(typeof body === "string" ? body : (body?.error || `Manifest failed (${mf.status})`));
        }
        const manifest = await mf.json();
        const st = String(manifest?.status || "").toLowerCase();
        if (st === "success") {
          onUrnReady?.({ urn: urnValue, auth: "app" });
          setBusy(false);
          return;
        }
        if (st === "failed" || st === "timeout") {
          throw new Error(`Translation failed: ${manifest?.status || "failed"}`);
        }
        await new Promise((r) => setTimeout(r, 3000));
      }
      throw new Error("Translation is still in progress. Check again later.");
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="flex items-center gap-2">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="var(--tcs-orange)" strokeWidth="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
        </svg>
        <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>Local Upload → OSS</span>
      </div>
      
      {error && (
        <div className="px-3 py-2 rounded-lg text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#dc2626' }}>
          {error}
        </div>
      )}

      <div className="p-3 rounded-lg" style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-light)' }}>
        <label className="flex flex-col gap-2">
          <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Select CAD/BIM File</span>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            disabled={busy}
            className="tcs-input text-sm"
            style={{ padding: '8px' }}
          />
        </label>
      </div>

      <button
        onClick={uploadAndTranslate}
        disabled={!file || busy}
        className={file && !busy ? "tcs-btn-primary w-full flex items-center justify-center gap-2" : "tcs-btn-secondary w-full opacity-60"}
      >
        {busy ? (
          <>
            <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid rgba(255,255,255,0.3)', borderTopColor: 'white', animation: 'spin 1s linear infinite' }} />
            Processing…
          </>
        ) : (
          <>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"/>
            </svg>
            Upload + Translate + Open
          </>
        )}
      </button>

      {urn && (
        <div className="p-2 rounded-lg text-xs" style={{ background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)', wordBreak: "break-all" }}>
          <span style={{ color: 'var(--text-secondary)' }}>URN: </span>
          <span style={{ color: '#10b981' }}>{urn}</span>
        </div>
      )}
    </div>
  );
}
