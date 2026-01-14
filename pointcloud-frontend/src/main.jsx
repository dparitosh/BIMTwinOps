import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

try {
	const rootEl = document.getElementById("root");
	if (!rootEl) throw new Error("Missing #root element");
	createRoot(rootEl).render(<App />);
} catch (e) {
	const msg = e?.stack || e?.message || String(e);
	document.body.innerHTML = `<pre style="white-space:pre-wrap;padding:12px;font-family:ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;color:#111;background:#fff;">UI bootstrap error:\n\n${msg}</pre>`;
}
