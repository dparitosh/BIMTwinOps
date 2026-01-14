import React, { useCallback, useEffect, useState } from "react";

function jsonOrText(res) {
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function findStorageObjectId(versionDetails) {
  const data = versionDetails?.data || versionDetails?.data?.data;
  const rel = data?.relationships || {};

  // Most common shape: relationships.storage.data.id
  const storage = rel.storage?.data;
  if (typeof storage?.id === "string" && storage.id.startsWith("urn:")) return storage.id;

  // Sometimes storage is an array
  if (Array.isArray(storage)) {
    const hit = storage.find((x) => typeof x?.id === "string" && x.id.startsWith("urn:"));
    if (hit) return hit.id;
  }

  // Fallback: scan for any nested urn:adsk.objects... in relationships
  const raw = JSON.stringify(versionDetails);
  const m = raw.match(/urn:adsk\.objects:os\.object:[^"\s]+/);
  return m ? m[0] : null;
}

export default function AccBrowser({ apsBaseUrl, onUrnReady }) {
  const [status, setStatus] = useState({ logged_in: false, expires_at: null });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const [hubs, setHubs] = useState([]);
  const [projects, setProjects] = useState([]);
  const [folders, setFolders] = useState([]);

  const [hubId, setHubId] = useState("");
  const [projectId, setProjectId] = useState("");
  const [folderStack, setFolderStack] = useState([]); // [{id,name}]

  const apiFetch = async (path, options = {}) => {
    const res = await fetch(`${apsBaseUrl}${path}`,
      {
        ...options,
        credentials: "include",
        headers: {
          Accept: "application/json",
          ...(options.headers || {}),
        },
      }
    );

    if (!res.ok) {
      const body = await jsonOrText(res);
      throw new Error(typeof body === "string" ? body : (body?.error || `Request failed (${res.status})`));
    }
    return await res.json();
  };

  const login = () => {
    const returnTo = window.location.href;
    window.location.href = `${apsBaseUrl}/aps/oauth/login?returnTo=${encodeURIComponent(returnTo)}`;
  };

  const refreshStatus = useCallback(async () => {
    const res = await fetch(`${apsBaseUrl}/aps/oauth/status`, { credentials: "include" });
    if (!res.ok) return;
    const json = await res.json();
    setStatus(json);
  }, [apsBaseUrl]);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  const loadHubs = async () => {
    setBusy(true);
    setError(null);
    try {
      const resp = await apiFetch(`/acc/hubs`);
      const list = resp?.data || resp?.hubs || [];
      setHubs(list);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const loadProjects = async (hubIdValue) => {
    setBusy(true);
    setError(null);
    try {
      const resp = await apiFetch(`/acc/projects?hubId=${encodeURIComponent(hubIdValue)}`);
      const list = resp?.data || resp?.projects || [];
      setProjects(list);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const loadTopFolders = async (hubIdValue, projectIdValue) => {
    setBusy(true);
    setError(null);
    try {
      const resp = await apiFetch(`/acc/top-folders?hubId=${encodeURIComponent(hubIdValue)}&projectId=${encodeURIComponent(projectIdValue)}`);
      const list = resp?.data || resp?.folders || [];
      setFolders(list);
      setFolderStack([]);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const loadFolderContents = async (projectIdValue, folderIdValue) => {
    setBusy(true);
    setError(null);
    try {
      const resp = await apiFetch(`/acc/folder-contents?projectId=${encodeURIComponent(projectIdValue)}&folderId=${encodeURIComponent(folderIdValue)}`);
      const list = resp?.data || resp?.contents || [];
      setFolders(list);
    } catch (e) {
      setError(e?.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const pickHub = async (value) => {
    setHubId(value);
    setProjectId("");
    setFolderStack([]);
    setProjects([]);
    setFolders([]);
    if (value) await loadProjects(value);
  };

  const pickProject = async (value) => {
    setProjectId(value);
    setFolderStack([]);
    setFolders([]);
    if (hubId && value) await loadTopFolders(hubId, value);
  };

  const goIntoFolder = async (folder) => {
    const id = folder?.id;
    const name = folder?.attributes?.displayName || folder?.attributes?.name || folder?.id;
    if (!id) return;
    setFolderStack((s) => [...s, { id, name }]);
    await loadFolderContents(projectId, id);
  };

  const goUpTo = async (index) => {
    const next = folderStack.slice(0, index + 1);
    setFolderStack(next);
    const id = next[next.length - 1]?.id;
    if (id) await loadFolderContents(projectId, id);
    else if (hubId && projectId) await loadTopFolders(hubId, projectId);
  };

  const translateAndOpen = async (item) => {
    setBusy(true);
    setError(null);
    try {
      const itemId = item?.id;
      if (!itemId) throw new Error("Missing item id");

      const versions = await apiFetch(`/acc/item-versions?projectId=${encodeURIComponent(projectId)}&itemId=${encodeURIComponent(itemId)}`);
      const v = versions?.data?.[0];
      const versionId = v?.id;
      if (!versionId) throw new Error("No versions found for item");

      const version = await apiFetch(`/acc/version?projectId=${encodeURIComponent(projectId)}&versionId=${encodeURIComponent(versionId)}`);
      const objectId = findStorageObjectId(version);
      if (!objectId) throw new Error("Could not locate storage objectId for this version");

      const urnResp = await apiFetch(`/urn/from-object-id?objectId=${encodeURIComponent(objectId)}`);
      const urn = urnResp?.urn;
      if (!urn) throw new Error("Failed to compute URN");

      await apiFetch(`/md/translate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ urn, auth: "user", force: false }),
      });

      // Poll manifest until success/failed
      for (let i = 0; i < 60; i++) {
        const manifest = await apiFetch(`/md/manifest?urn=${encodeURIComponent(urn)}&auth=user`);
        const st = String(manifest?.status || "").toLowerCase();
        if (st === "success") {
          onUrnReady?.({ urn, auth: "user" });
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
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
        <div className="flex items-center gap-2">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="var(--tcs-blue)" strokeWidth="2">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
          </svg>
          <span style={{ fontWeight: 700, color: 'var(--text-primary)' }}>ACC Docs Browser</span>
        </div>
        <button
          onClick={status.logged_in ? loadHubs : login}
          className="tcs-btn-primary text-sm"
        >
          {status.logged_in ? "Load Hubs" : "Login"}
        </button>
      </div>

      <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: status.logged_in ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)', border: `1px solid ${status.logged_in ? 'rgba(16, 185, 129, 0.3)' : 'rgba(239, 68, 68, 0.3)'}` }}>
        <div style={{ width: 8, height: 8, borderRadius: '50%', background: status.logged_in ? '#10b981' : '#ef4444' }} />
        <span style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          {status.logged_in ? "Connected to Autodesk" : "Not logged in"}
        </span>
      </div>

      {error && (
        <div className="px-3 py-2 rounded-lg text-sm" style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', color: '#dc2626' }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 12 }}>
        <label style={labelStyle}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Hub</span>
          <select
            value={hubId}
            onChange={(e) => pickHub(e.target.value)}
            className="tcs-select"
            disabled={busy || hubs.length === 0}
          >
            <option value="">Select hub…</option>
            {hubs.map((h) => (
              <option key={h.id} value={h.id}>
                {h.attributes?.name || h.attributes?.displayName || h.id}
              </option>
            ))}
          </select>
        </label>

        <label style={labelStyle}>
          <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Project</span>
          <select
            value={projectId}
            onChange={(e) => pickProject(e.target.value)}
            className="tcs-select"
            disabled={busy || projects.length === 0}
          >
            <option value="">Select project…</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.attributes?.name || p.attributes?.displayName || p.id}
              </option>
            ))}
          </select>
        </label>
      </div>

      {projectId && (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text-secondary)' }}>Folder Navigation</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            <button
              onClick={() => loadTopFolders(hubId, projectId)}
              disabled={busy}
              className="tcs-btn-secondary text-xs"
            >
              / Root
            </button>
            {folderStack.map((f, idx) => (
              <button
                key={f.id}
                onClick={() => goUpTo(idx)}
                disabled={busy}
                className="tcs-btn-secondary text-xs"
              >
                {f.name}
              </button>
            ))}
          </div>

          <div className="rounded-lg overflow-hidden" style={{ maxHeight: 260, overflow: "auto", border: "1px solid var(--border-light)", background: 'var(--surface)' }}>
            {folders.map((x) => {
              const type = x?.type;
              const name = x?.attributes?.displayName || x?.attributes?.name || x?.id;
              const isFolder = type === "folders";
              const isItem = type === "items";

              return (
                <div
                  key={x.id}
                  className="flex items-center justify-between gap-2 px-3 py-2 hover:bg-gray-50 transition-colors"
                  style={{ borderBottom: "1px solid var(--border-light)" }}
                >
                  <div style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", color: 'var(--text-primary)' }}>
                    <span style={{ marginRight: 8, color: 'var(--text-muted)' }}>{isFolder ? "[D]" : isItem ? "[F]" : "-"}</span>
                    {name}
                  </div>

                  {isFolder && (
                    <button
                      onClick={() => goIntoFolder(x)}
                      disabled={busy}
                      className="tcs-btn-secondary text-xs"
                    >
                      Open
                    </button>
                  )}

                  {isItem && (
                    <button
                      onClick={() => translateAndOpen(x)}
                      disabled={busy}
                      className="tcs-btn-primary text-xs"
                      title="Translate latest version and open in Viewer"
                    >
                      View
                    </button>
                  )}
                </div>
              );
            })}

            {folders.length === 0 && (
              <div className="p-4 text-center" style={{ color: 'var(--text-muted)' }}>
                No entries found
              </div>
            )}
          </div>

          <div className="text-xs px-2" style={{ color: 'var(--text-muted)' }}>
            Tip: Click "View" on an item to translate (SVF2) and open.
          </div>
        </div>
      )}

      {busy && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg" style={{ background: 'rgba(0, 118, 206, 0.1)' }}>
          <div style={{ width: 14, height: 14, borderRadius: '50%', border: '2px solid var(--border-light)', borderTopColor: 'var(--tcs-blue)', animation: 'spin 1s linear infinite' }} />
          <span style={{ fontSize: 12, color: 'var(--tcs-blue)' }}>Working…</span>
        </div>
      )}

      <button
        onClick={refreshStatus}
        disabled={busy}
        className="tcs-btn-secondary text-xs w-full"
      >
        Refresh Login Status
      </button>
    </div>
  );
}

const labelStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 6,
  fontSize: 13,
};
