/**
 * ApsViewerExtended.jsx
 * Enterprise-grade APS Viewer with extension support
 * Integrates with autodesk-platform-services/aps-extensions
 */
import React, { useEffect, useMemo, useRef, useState, useCallback, forwardRef, useImperativeHandle } from "react";

const VIEWER_CSS_ID = "aps-viewer-css";
const VIEWER_JS_ID = "aps-viewer-js";

// Available extensions configuration
const AVAILABLE_EXTENSIONS = [
  {
    id: "PhasingExtension",
    name: "Project Phasing",
    description: "Gantt chart integration with model elements for construction scheduling",
    icon: "M3 4h18M3 8h18M3 12h12M3 16h8",
    category: "Scheduling",
    cssFiles: [],
    jsFiles: ["/extensions/PhasingExtension/contents/main.js"],
  },
  {
    id: "CustomPropertiesExtension",
    name: "Custom Properties",
    description: "Add custom properties to model elements in the Properties panel",
    icon: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
    category: "Properties",
    cssFiles: [],
    jsFiles: ["/extensions/CustomPropertiesExtension/contents/main.js"],
  },
  {
    id: "XLSExtension",
    name: "Excel Export",
    description: "Export model metadata to Excel spreadsheet",
    icon: "M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    category: "Export",
    cssFiles: ["/extensions/XLSExtension/contents/main.css"],
    jsFiles: ["/extensions/XLSExtension/contents/main.js"],
  },
  {
    id: "DrawToolExtension",
    name: "Draw Tools",
    description: "2D drawing and markup tools for annotations",
    icon: "M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z",
    category: "Markup",
    cssFiles: ["/extensions/DrawToolExtension/contents/main.css"],
    jsFiles: ["/extensions/DrawToolExtension/contents/main.js"],
  },
  {
    id: "IconMarkupExtension",
    name: "Icon Markup",
    description: "Place icon markers on model elements with custom labels",
    icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z M15 11a3 3 0 11-6 0 3 3 0 016 0z",
    category: "Markup",
    cssFiles: ["/extensions/IconMarkupExtension/contents/main.css"],
    jsFiles: ["/extensions/IconMarkupExtension/contents/main.js"],
  },
  {
    id: "GoogleMapsLocator",
    name: "Google Maps",
    description: "Display building location on Google Maps mini-map",
    icon: "M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2 2 2 0 012 2v2.945M8 3.935V5.5A2.5 2.5 0 0010.5 8h.5a2 2 0 012 2 2 2 0 104 0 2 2 0 012-2h1.064M15 20.488V18a2 2 0 012-2h3.064M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
    category: "Location",
    cssFiles: ["/extensions/GoogleMapsLocator/contents/main.css"],
    jsFiles: ["/extensions/GoogleMapsLocator/contents/main.js"],
  },
  {
    id: "TurnTableExtension",
    name: "Camera Rotation",
    description: "Auto-rotate camera around model for presentations",
    icon: "M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15",
    category: "View",
    cssFiles: ["/extensions/CameraRotation/contents/main.css"],
    jsFiles: ["/extensions/CameraRotation/contents/main.js"],
  },
  {
    id: "TransformExtension",
    name: "Transform Tool",
    description: "Move, rotate and scale model elements",
    icon: "M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4",
    category: "Editing",
    cssFiles: ["/extensions/TransformationExtension/contents/main.css"],
    jsFiles: ["/extensions/TransformationExtension/contents/main.js"],
  },
  {
    id: "NestedViewerExtension",
    name: "Nested Viewer",
    description: "Open linked models in a nested viewer panel",
    icon: "M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z",
    category: "View",
    cssFiles: ["/extensions/NestedViewerExtension/contents/main.css"],
    jsFiles: ["/extensions/NestedViewerExtension/contents/main.js"],
  },
  {
    id: "Edit2dExtension",
    name: "Edit 2D",
    description: "2D polygon and shape drawing tools",
    icon: "M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z",
    category: "Markup",
    cssFiles: [],
    jsFiles: ["/extensions/Edit2dExtension/contents/main.js"],
  },
  {
    id: "BoundingBoxExtension",
    name: "Bounding Box",
    description: "Display bounding boxes around selected elements",
    icon: "M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4",
    category: "View",
    cssFiles: [],
    jsFiles: ["/extensions/BoundingBoxExtension/contents/main.js"],
  },
];

function loadApsViewerSdk() {
  if (window.Autodesk?.Viewing) return Promise.resolve();

  const existing = document.getElementById(VIEWER_JS_ID);
  if (existing) {
    return new Promise((resolve, reject) => {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", (e) => reject(e));
    });
  }

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

// Load extension files dynamically
async function loadExtensionFiles(extension) {
  const loadCSS = (href) => {
    return new Promise((resolve) => {
      if (document.querySelector(`link[href="${href}"]`)) {
        resolve();
        return;
      }
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = href;
      link.onload = () => resolve();
      link.onerror = () => resolve(); // Don't fail if CSS is missing
      document.head.appendChild(link);
    });
  };

  const loadJS = (src) => {
    return new Promise((resolve, reject) => {
      if (document.querySelector(`script[src="${src}"]`)) {
        resolve();
        return;
      }
      const script = document.createElement("script");
      script.src = src;
      script.onload = () => resolve();
      script.onerror = (e) => reject(e);
      document.head.appendChild(script);
    });
  };

  // Load CSS files first
  await Promise.all((extension.cssFiles || []).map(loadCSS));
  // Load JS files sequentially (order matters)
  for (const js of extension.jsFiles || []) {
    await loadJS(js);
  }
}

const ApsViewerExtended = forwardRef(function ApsViewerExtended(
  { apsBaseUrl, urn, auth = "app", className = "", style = {}, enabledExtensions = [], onExtensionLoaded, onSelectionChanged, onModelLoaded },
  ref
) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);

  const [sdkReady, setSdkReady] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState("idle");
  const [loadedExtensions, setLoadedExtensions] = useState([]);

  const urnKey = useMemo(() => (urn ? String(urn).trim() : ""), [urn]);

  // Expose viewer instance and methods via ref
  useImperativeHandle(ref, () => ({
    getViewer: () => viewerRef.current,
    loadExtension: async (extId, options = {}) => {
      const viewer = viewerRef.current;
      if (!viewer) return null;
      
      const extConfig = AVAILABLE_EXTENSIONS.find(e => e.id === extId);
      if (extConfig) {
        await loadExtensionFiles(extConfig);
      }
      
      return viewer.loadExtension(extId, options);
    },
    unloadExtension: (extId) => {
      const viewer = viewerRef.current;
      if (!viewer) return;
      viewer.unloadExtension(extId);
    },
    getLoadedExtensions: () => loadedExtensions,
    isolate: (dbIds) => viewerRef.current?.isolate(dbIds),
    fitToView: (dbIds) => viewerRef.current?.fitToView(dbIds),
    select: (dbIds) => viewerRef.current?.select(dbIds),
    clearSelection: () => viewerRef.current?.clearSelection(),
    setThemingColor: (dbId, color, model) => viewerRef.current?.setThemingColor(dbId, color, model),
    clearThemingColors: (model) => viewerRef.current?.clearThemingColors(model),
    getProperties: (dbId, callback) => viewerRef.current?.getProperties(dbId, callback),
    search: (text, callback, errorCallback) => viewerRef.current?.search(text, callback, errorCallback),
  }), [loadedExtensions]);

  // Load SDK
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

  // Initialize viewer and load model
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
          const config = {
            extensions: [], // We'll load extensions manually
          };
          const viewer = new window.Autodesk.Viewing.GuiViewer3D(containerRef.current, config);
          const started = viewer.start();
          if (!started) throw new Error("Viewer failed to start");
          viewerRef.current = viewer;

          // Set up selection changed callback
          viewer.addEventListener(window.Autodesk.Viewing.SELECTION_CHANGED_EVENT, (e) => {
            onSelectionChanged?.(e.dbIdArray || []);
          });
        }

        setStatus("loading-document");

        const documentId = `urn:${urnKey}`;
        window.Autodesk.Viewing.Document.load(
          documentId,
          async (doc) => {
            if (cancelled) return;

            const viewables = doc.getRoot().search({ type: "geometry" });
            const defaultViewable = viewables?.[0];
            if (!defaultViewable) {
              setError("No viewable geometry found in this derivative.");
              setStatus("error");
              return;
            }

            setStatus("loading-model");
            try {
              await viewerRef.current.loadDocumentNode(doc, defaultViewable);
              if (cancelled) return;
              
              setStatus("loading-extensions");
              
              // Load enabled extensions
              const loaded = [];
              for (const extId of enabledExtensions) {
                try {
                  const extConfig = AVAILABLE_EXTENSIONS.find(e => e.id === extId);
                  if (extConfig) {
                    await loadExtensionFiles(extConfig);
                  }
                  await viewerRef.current.loadExtension(extId, extConfig?.options || {});
                  loaded.push(extId);
                  onExtensionLoaded?.(extId);
                } catch (e) {
                  console.warn(`Failed to load extension ${extId}:`, e);
                }
              }
              setLoadedExtensions(loaded);
              
              setStatus("ready");
              onModelLoaded?.(viewerRef.current.model);
            } catch (e) {
              if (cancelled) return;
              setError(e?.message || String(e));
              setStatus("error");
            }
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
  }, [sdkReady, urnKey, apsBaseUrl, auth, enabledExtensions, onExtensionLoaded, onSelectionChanged, onModelLoaded]);

  // Cleanup
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
    <div className={className} style={{ position: "relative", width: "100%", height: "100%", background: '#1a1a2e', ...style }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />

      {!urnKey && (
        <div style={overlayStyle}>
          <div style={overlayCardStyle}>
            <svg viewBox="0 0 24 24" width="48" height="48" fill="none" stroke="var(--tcs-blue)" strokeWidth="1.5" style={{ margin: '0 auto 12px', display: 'block' }}>
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
});

// Export the available extensions list for other components
export { AVAILABLE_EXTENSIONS };
export default ApsViewerExtended;

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
