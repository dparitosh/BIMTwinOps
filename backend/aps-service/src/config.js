import 'dotenv/config';

function splitList(value) {
  return String(value || '')
    .split(/[\s,]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function getConfig() {
  const APS_SERVICE_PORT = Number.parseInt(process.env.APS_SERVICE_PORT || '3001', 10);

  const APS_CLIENT_ID = process.env.APS_CLIENT_ID;
  const APS_CLIENT_SECRET = process.env.APS_CLIENT_SECRET;

  const APS_SCOPES = process.env.APS_SCOPES || 'data:read';

  // 3-legged OAuth (ACC/Docs)
  const APS_CALLBACK_URL = process.env.APS_CALLBACK_URL;
  const APS_OAUTH_SCOPES = process.env.APS_OAUTH_SCOPES || 'data:read viewables:read';

  // CORS
  const APS_CORS_ORIGINS = splitList(
    process.env.APS_CORS_ORIGINS
      || 'http://localhost:5173 http://127.0.0.1:5173 http://localhost:3001 http://127.0.0.1:3001'
  );

  // Cache/session store
  // If REDIS_URL is set, Redis is used by default (demo-friendly).
  const REDIS_URL = process.env.REDIS_URL || '';
  const APS_STORE = (process.env.APS_STORE || (REDIS_URL ? 'redis' : 'memory')).toLowerCase();
  const APS_SESSION_TTL_SECONDS = Number.parseInt(process.env.APS_SESSION_TTL_SECONDS || String(60 * 60 * 24), 10); // 1 day
  const APS_TOKEN_TTL_SECONDS = Number.parseInt(process.env.APS_TOKEN_TTL_SECONDS || String(60 * 60), 10); // 1 hour

  // OSS/MD defaults
  const APS_OSS_REGION = (process.env.APS_OSS_REGION || 'US').toUpperCase();
  const APS_BUCKET_KEY = process.env.APS_BUCKET_KEY || 'smartbim-demo-bucket';

  // Frontend integration (serve React app from the APS service)
  // proxy: forwards non-API requests to Vite dev server
  // static: serves built assets from pointcloud-frontend/dist
  const FRONTEND_MODE = (process.env.FRONTEND_MODE || 'proxy').toLowerCase();
  const FRONTEND_DEV_URL = process.env.FRONTEND_DEV_URL || 'http://localhost:5173';
  const FRONTEND_DIST_DIR = process.env.FRONTEND_DIST_DIR || '../../pointcloud-frontend/dist';

  return {
    APS_SERVICE_PORT,
    APS_CLIENT_ID,
    APS_CLIENT_SECRET,
    APS_SCOPES,
    APS_CALLBACK_URL,
    APS_OAUTH_SCOPES,
    APS_CORS_ORIGINS,
    APS_STORE,
    REDIS_URL,
    APS_SESSION_TTL_SECONDS,
    APS_TOKEN_TTL_SECONDS,
    APS_OSS_REGION,
    APS_BUCKET_KEY,
    FRONTEND_MODE,
    FRONTEND_DEV_URL,
    FRONTEND_DIST_DIR
  };
}

export function requiredEnv(name, value) {
  if (!value) {
    const err = new Error(`Missing required env var: ${name}`);
    err.status = 500;
    throw err;
  }
  return value;
}

export function getOptionalReturnTo(value) {
  if (typeof value !== 'string') return null;
  const v = value.trim();
  return v ? v : null;
}
