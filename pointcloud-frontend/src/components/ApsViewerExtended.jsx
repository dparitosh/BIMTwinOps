/**
 * ApsViewerExtended.jsx
 * Enterprise-grade APS Viewer with extension support
 */
import React, {
  useEffect,
  useMemo,
  useRef,
  useState,
  forwardRef,
  useImperativeHandle
} from "react";

/* ===================== CONSTANTS ===================== */

const VIEWER_CSS_ID = "aps-viewer-css";
const VIEWER_JS_ID = "aps-viewer-js";

/* ===================== EXTENSIONS ===================== */

export const AVAILABLE_EXTENSIONS = [
  { id: "PhasingExtension", jsFiles: ["/extensions/PhasingExtension/contents/main.js"] },
  { id: "CustomPropertiesExtension", jsFiles: ["/extensions/CustomPropertiesExtension/contents/main.js"] },
  { id: "XLSExtension", jsFiles: ["/extensions/XLSExtension/contents/main.js"], cssFiles: ["/extensions/XLSExtension/contents/main.css"] },
  { id: "DrawToolExtension", jsFiles: ["/extensions/DrawToolExtension/contents/main.js"], cssFiles: ["/extensions/DrawToolExtension/contents/main.css"] },
  { id: "IconMarkupExtension", jsFiles: ["/extensions/IconMarkupExtension/contents/main.js"], cssFiles: ["/extensions/IconMarkupExtension/contents/main.css"] },
  { id: "GoogleMapsLocator", jsFiles: ["/extensions/GoogleMapsLocator/contents/main.js"], cssFiles: ["/extensions/GoogleMapsLocator/contents/main.css"] },
  { id: "TurnTableExtension", jsFiles: ["/extensions/CameraRotation/contents/main.js"] },
  { id: "TransformExtension", jsFiles: ["/extensions/TransformationExtension/contents/main.js"], cssFiles: ["/extensions/TransformationExtension/contents/main.css"] },
  { id: "NestedViewerExtension", jsFiles: ["/extensions/NestedViewerExtension/contents/main.js"], cssFiles: ["/extensions/NestedViewerExtension/contents/main.css"] },
  { id: "Edit2dExtension", jsFiles: ["/extensions/Edit2dExtension/contents/main.js"] },
  { id: "BoundingBoxExtension", jsFiles: ["/extensions/BoundingBoxExtension/contents/main.js"] },
];

/* ===================== SDK LOADER ===================== */

function loadApsViewerSdk() {
  if (window.Autodesk?.Viewing) return Promise.resolve();

  if (!document.getElementById(VIEWER_CSS_ID)) {
    const css = document.createElement("link");
    css.id = VIEWER_CSS_ID;
    css.rel = "stylesheet";
    css.href = "https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/style.min.css";
    document.head.appendChild(css);
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.id = VIEWER_JS_ID;
    script.src = "https://developer.api.autodesk.com/modelderivative/v2/viewers/7.*/viewer3D.min.js";
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

/* ===================== TOKEN ===================== */

async function fetchViewerToken({ apsBaseUrl, auth }) {
  const url = auth === "user"
    ? `${apsBaseUrl}/aps/oauth/token`
    : `${apsBaseUrl}/aps/token`;

  const res = await fetch(url);
  const json = await res.json();

  return {
    accessToken: json.access_token,
    expiresIn: json.expires_in || 300
  };
}

/* ===================== EXTENSION LOADER ===================== */

async function loadExtensionFiles(ext) {
  for (const css of ext.cssFiles || []) {
    if (!document.querySelector(`link[href="${css}"]`)) {
      const link = document.createElement("link");
      link.rel = "stylesheet";
      link.href = css;
      document.head.appendChild(link);
    }
  }

  for (const js of ext.jsFiles || []) {
    if (!document.querySelector(`script[src="${js}"]`)) {
      await new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = js;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      });
    }
  }
}

/* ===================== COMPONENT ===================== */

const ApsViewerExtended = forwardRef(function ApsViewerExtended(
  { apsBaseUrl, urn, auth = "app", enabledExtensions = [], onModelLoaded, onSelectionChanged },
  ref
) {
  const containerRef = useRef(null);
  const viewerRef = useRef(null);
  const viewerInitializedRef = useRef(false);

  const [sdkReady, setSdkReady] = useState(false);
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState(null);

  const urnKey = useMemo(() => (urn ? String(urn).trim() : ""), [urn]);

  /* ===================== EXPOSE VIEWER ===================== */

  useImperativeHandle(ref, () => ({
    getViewer: () => viewerRef.current
  }));

  /* ===================== LOAD SDK ===================== */

  useEffect(() => {
    loadApsViewerSdk()
      .then(() => setSdkReady(true))
      .catch(e => setError(String(e)));
  }, []);

  /* ===================== INIT VIEWER (ONCE) ===================== */

  useEffect(() => {
    if (!sdkReady || viewerInitializedRef.current || !containerRef.current) return;

    const initViewer = async () => {
      const getAccessToken = async (cb) => {
        const { accessToken, expiresIn } = await fetchViewerToken({ apsBaseUrl, auth });
        cb(accessToken, expiresIn);
      };

      window.Autodesk.Viewing.Initializer(
        { env: "AutodeskProduction2", api: "derivativeV2", getAccessToken },
        () => {
          const viewer = new window.Autodesk.Viewing.GuiViewer3D(containerRef.current);
          viewer.start();
          viewerRef.current = viewer;
          viewerInitializedRef.current = true;

          viewer.addEventListener(
            window.Autodesk.Viewing.SELECTION_CHANGED_EVENT,
            e => onSelectionChanged?.(e.dbIdArray || [])
          );
        }
      );
    };

    initViewer();
  }, [sdkReady, apsBaseUrl, auth, onSelectionChanged]);

  /* ===================== LOAD MODEL ===================== */

  useEffect(() => {
    if (!viewerRef.current || !urnKey) return;

    console.log("[Viewer] Loading URN:", urnKey);
    setStatus("loading");

    window.Autodesk.Viewing.Document.load(
      `urn:${urnKey}`,
      async (doc) => {
        const defaultViewable = doc.getRoot().getDefaultGeometry();
        if (!defaultViewable) {
          setError("No default geometry found");
          return;
        }

        await viewerRef.current.loadDocumentNode(doc, defaultViewable);
        viewerRef.current.resize();
        viewerRef.current.fitToView();

        for (const extId of enabledExtensions) {
          const ext = AVAILABLE_EXTENSIONS.find(e => e.id === extId);
          if (ext) {
            await loadExtensionFiles(ext);
            await viewerRef.current.loadExtension(extId);
          }
        }

        setStatus("ready");
        onModelLoaded?.(viewerRef.current.model);
      },
      (code, msg) => {
        setError(`Document load failed (${code}): ${msg}`);
      }
    );
  }, [urnKey]);

  /* ===================== UI ===================== */

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
      {status !== "ready" && (
        <div style={overlayStyle}>
          <div style={overlayCardStyle}>
            <div>Loading Viewer…</div>
            {error && <div style={{ color: "red" }}>{error}</div>}
          </div>
        </div>
      )}
    </div>
  );
});

/* ===================== STYLES ===================== */

const overlayStyle = {
  position: "absolute",
  inset: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  pointerEvents: "none"
};

const overlayCardStyle = {
  background: "#111827",
  color: "#fff",
  padding: 16,
  borderRadius: 8
};

export default ApsViewerExtended;
