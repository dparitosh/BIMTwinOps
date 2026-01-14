import React, { useEffect, useMemo, useRef, useState } from "react";

const VIEWER_CSS_ID = "aps-viewer-css";
const VIEWER_JS_ID = "aps-viewer-js";

function loadApsViewerSdk() {
  if (window.Autodesk?.Viewing) return Promise.resolve();

  const existing = document.getElementById(VIEWER_JS_ID);
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", (e) => reject(e));
    });
  }

  // The stylesheet is also included in index.html for consistent global styling.
  if (!document.getElementById(VIEWER_CSS_ID)) {
    const link = document.createElement("link");
    link.id = VIEWER_CSS_ID;
    link.rel = "stylesheet";
    link.href = "https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/style.min.css";
    document.head.appendChild(link);
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = VIEWER_JS_ID;
    script.src = "https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/viewer3D.min.js";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = (e) => reject(e);
    document.head.appendChild(script);
  });
}

async function fetchViewerToken({ apsBaseUrl, auth }) {
  const url = auth === "user" ? `${apsBaseUrl}/aps/oauth/token` : `${apsBaseUrl}/aps/token`;
  const res = await fetch(url, {
    method: "GET",
    credentials: auth === "user" ? "include" : "omit",
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(txt || `Token request failed (${res.status})`);
  }
  const json = await res.json();

  const accessToken = json.access_token || (json.authorization ? String(json.authorization).replace(/^Bearer\s+/i, "") : null);
  const expiresIn = Number.isFinite(json.expires_in) ? json.expires_in : 300;
  if (!accessToken) throw new Error("Token endpoint did not return access_token");
  return { accessToken, expiresIn };
}

export default function ApsViewer({ apsBaseUrl, urn, auth = "app", className = "", style = {} }) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);

  const [sdkReady, setSdkReady] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("idle");

  const urnKey = useMemo(() => (urn ? String(urn).trim() : ""), [urn]);

  useEffect(() => {
    let cancelled = false;
    setError(null);

    loadApsViewerSdk()
      .then(() => {
        if (cancelled) return;
        setSdkReady(true);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e?.message || String(e));
      });

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!sdkReady) return;
    if (!containerRef.current) return;
    if (!urnKey) return;

    let cancelled = false;

    const init = async () => {
      setStatus("initializing");
      setError(null);

      try {
        const getAccessToken = async (onTokenReady) => {
          try {
            const { accessToken, expiresIn } = await fetchViewerToken({ apsBaseUrl, auth });
            onTokenReady(accessToken, expiresIn);
          } catch (e) {
            // Viewer swallows many errors; surface it.
            setError(e?.message || String(e));
          }
        };

        await new Promise((resolve) => {
          window.Autodesk.Viewing.Initializer(
            {
              env: "AutodeskProduction2",
              api: "derivativeV2",
              getAccessToken,
            },
            () => resolve()
          );
        });

        if (cancelled) return;

        if (!viewerRef.current) {
          const viewer = new window.Autodesk.Viewing.GuiViewer3D(containerRef.current);
          const started = viewer.start();
          if (!started) throw new Error("Viewer failed to start");
          viewerRef.current = viewer;
        }

        setStatus("loading-document");

        const documentId = `urn:${urnKey}`;
        window.Autodesk.Viewing.Document.load(
          documentId,
          (doc) => {
            if (cancelled) return;

            const viewables = doc.getRoot().search({ type: "geometry" });
            const defaultViewable = viewables?.[0];
            if (!defaultViewable) {
              setError("No viewable geometry found in this derivative.");
              setStatus("error");
              return;
            }

            setStatus("loading-model");
            viewerRef.current
              .loadDocumentNode(doc, defaultViewable)
              .then(() => {
                if (cancelled) return;
                setStatus("ready");
              })
              .catch((e) => {
                if (cancelled) return;
                setError(e?.message || String(e));
                setStatus("error");
              });
          },
          (errCode, errMsg) => {
            if (cancelled) return;
            setError(`Document load failed (${errCode}): ${errMsg || ""}`.trim());
            setStatus("error");
          }
        );
      } catch (e) {
        if (cancelled) return;
        setError(e?.message || String(e));
        setStatus("error");
      }
    };

    init();

    return () => {
      cancelled = true;
    };
  }, [sdkReady, urnKey, apsBaseUrl, auth]);

  useEffect(() => {
    return () => {
      try {
        viewerRef.current?.finish?.();
      } catch {
        // ignore
      }
      viewerRef.current = null;
    };
  }, []);

  return (
    <div className={className} style={{ position: "relative", width: "100%", height: "100%", background: '#f8fafc', ...style }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />

      {!urnKey && (
        <div style={overlayStyle}>
          <div style={overlayCardStyle}>
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="var(--tcs-blue)" strokeWidth="1.5" style={{ margin: '0 auto 12px' }}>
              <path d="M2 20h20M4 20V10l8-6 8 6v10M9 20v-5h6v5"/>
            </svg>
            <div style={{ color: 'var(--text-secondary)', textAlign: 'center' }}>Select a model from ACC or upload a file to view</div>
          </div>
        </div>
      )}

      {urnKey && status !== "ready" && (
        <div style={overlayStyle}>
          <div style={overlayCardStyle}>
            <div style={{ fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>Loading Viewer</div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ width: 16, height: 16, borderRadius: '50%', border: '2px solid var(--border-light)', borderTopColor: 'var(--tcs-blue)', animation: 'spin 1s linear infinite' }} />
              {status}
            </div>
            {error && <div style={{ marginTop: 10, color: '#dc2626', fontSize: 13, padding: '8px', background: 'rgba(239, 68, 68, 0.1)', borderRadius: 6 }}>{error}</div>}
          </div>
        </div>
      )}

      {urnKey && status === "ready" && error && (
        <div style={{ ...overlayStyle, alignItems: "flex-start", paddingTop: 16 }}>
          <div style={{ ...overlayCardStyle, borderColor: 'rgba(239, 68, 68, 0.5)', background: 'rgba(239, 68, 68, 0.1)' }}>
            <span style={{ color: '#dc2626' }}>{error}</span>
          </div>
        </div>
      )}
    </div>
  );
}

const overlayStyle = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  pointerEvents: "none",
};

const overlayCardStyle = {
  pointerEvents: "none",
  background: "var(--surface)",
  border: "1px solid var(--border-light)",
  borderRadius: 12,
  padding: 20,
  maxWidth: 420,
  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
};
