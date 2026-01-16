import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
	const env = loadEnv(mode, process.cwd(), '');
	const backendUrl = env.VITE_BACKEND_API_URL || 'http://127.0.0.1:8000';
	const apsUrl = env.VITE_APS_API_URL || 'http://127.0.0.1:3001';

	return {
		plugins: [react(), tailwindcss()],
		server: {
			port: 5173,
			strictPort: true,
			proxy: {
				// Proxy /api requests to backend (FastAPI)
				'/api': {
					target: backendUrl,
					changeOrigin: true,
					rewrite: (path) => path.replace(/^\/api/, '')
				},
				// Proxy /upload directly to backend
				'/upload': {
					target: backendUrl,
					changeOrigin: true
				},
				// Proxy /aps requests to APS service
				'/aps': {
					target: apsUrl,
					changeOrigin: true
				}
			}
		}
	};
});
  