import express from 'express';
import cors from 'cors';
import path from 'node:path';
import fs from 'node:fs';

import { ResponseType } from '@aps_sdk/authentication';
import { createProxyMiddleware } from 'http-proxy-middleware';

import { getConfig, getOptionalReturnTo, requiredEnv } from './config.js';
import { createStore, newId } from './store.js';
import { parseCookies, setCookie } from './utils.js';
import { parseScopes } from './apsScopes.js';
import { createTokenService } from './tokens.js';
import { createAccDocsApi } from './accDocs.js';
import { createOssMdApi, createUploadMiddleware } from './ossMd.js';

const config = getConfig();
const store = await createStore({ type: config.APS_STORE, redisUrl: config.REDIS_URL });
const tokens = createTokenService({ config, store });

const upload = createUploadMiddleware();

const app = express();
app.use(express.json({ limit: '2mb' }));

const API_PREFIXES = [
  '/health',
  '/aps',
  '/acc',
  '/oss',
  '/md',
  '/urn'
];

function isApiPath(urlPath) {
  return API_PREFIXES.some((p) => urlPath === p || urlPath.startsWith(`${p}/`));
}

// -------------------- Frontend (single entrypoint on :3001) --------------------
// This must be registered BEFORE API routes so that SPA routes work.
if (config.FRONTEND_MODE === 'proxy') {
  // Proxy everything except API routes to Vite dev server.
  // IMPORTANT: createProxyMiddleware must be created ONCE.
  // Creating it per request leaks EventEmitter listeners (MaxListenersExceededWarning).
  const viteProxy = createProxyMiddleware({
    target: config.FRONTEND_DEV_URL,
    changeOrigin: true,
    ws: true,
    logLevel: 'silent',
    on: {
      error: (err, _req, res) => {
        // Vite dev server is not reachable
        if (res.headersSent) return;
        res.writeHead(502, { 'Content-Type': 'text/html; charset=utf-8' });
        res.end(
          `<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Frontend not running</title>
    <style>
      body { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial; background:#0b1020; color:#e5e7eb; margin:0; padding:24px; }
      .card { max-width: 760px; margin: 0 auto; background: rgba(17,24,39,0.65); border: 1px solid rgba(148,163,184,0.25); border-radius: 12px; padding: 16px; }
      code { background: rgba(2,6,23,0.7); padding: 2px 6px; border-radius: 6px; }
      .muted { opacity: 0.85; }
    </style>
  </head>
  <body>
    <div class="card">
      <h2>Frontend dev server not reachable</h2>
      <p class="muted">APS service is running, but it is configured to proxy the UI from <code>${config.FRONTEND_DEV_URL}</code>.</p>
      <p>Start Vite:</p>
      <pre><code>cd pointcloud-frontend
npm run dev</code></pre>
      <p>Then reload this page: <code>http://127.0.0.1:${config.APS_SERVICE_PORT}/</code></p>
      <p class="muted">Proxy error: ${String(err?.message || err)}</p>
    </div>
  </body>
</html>`
        );
      }
    }
  });

  app.use((req, res, next) => {
    if (isApiPath(req.path)) return next();
    return viteProxy(req, res, next);
  });
} else if (config.FRONTEND_MODE === 'static') {
  const distDir = path.resolve(process.cwd(), config.FRONTEND_DIST_DIR);
  if (fs.existsSync(distDir)) {
    app.use(express.static(distDir));
    // SPA fallback
    app.get('*', (req, res, next) => {
      if (isApiPath(req.path)) return next();
      return res.sendFile(path.join(distDir, 'index.html'));
    });
  } else {
    console.warn(`FRONTEND_MODE=static but dist dir not found: ${distDir}`);
  }
}

const allowedOrigins = config.APS_CORS_ORIGINS;
app.use(cors({
  origin: (origin, cb) => {
    // allow non-browser clients with no Origin header
    if (!origin) return cb(null, true);
    if (allowedOrigins.includes(origin)) return cb(null, true);
    return cb(new Error(`CORS blocked origin: ${origin}`));
  },
  credentials: true
}));

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'aps-service', store: store.kind, bucket: config.APS_BUCKET_KEY });
});

// Non-sensitive config status (helps the UI show actionable messages instead of failing on click).
app.get('/aps/config', (_req, res) => {
  const missing = [];
  if (!config.APS_CLIENT_ID) missing.push('APS_CLIENT_ID');
  if (!config.APS_CLIENT_SECRET) missing.push('APS_CLIENT_SECRET');
  const twoLeggedConfigured = missing.length === 0;

  const oauthMissing = [...missing];
  if (!config.APS_CALLBACK_URL) oauthMissing.push('APS_CALLBACK_URL');
  const threeLeggedConfigured = oauthMissing.length === 0;

  res.json({
    twoLeggedConfigured,
    threeLeggedConfigured,
    missing,
    oauthMissing,
    frontendMode: config.FRONTEND_MODE,
    frontendDevUrl: config.FRONTEND_DEV_URL
  });
});

// 2-legged token endpoint (safe to call from your frontend; secrets stay server-side)
app.get('/aps/token', async (_req, res, next) => {
  try {
    if (!config.APS_CLIENT_ID || !config.APS_CLIENT_SECRET) {
      return res.status(503).json({ 
        error: 'APS credentials not configured', 
        message: 'Please set APS_CLIENT_ID and APS_CLIENT_SECRET in backend/.env',
        documentation: 'https://aps.autodesk.com/myapps'
      });
    }
    const token = await tokens.getTwoLeggedToken();
    res.setHeader('Cache-Control', 'no-store');
    res.json(token);
  } catch (e) {
    next(e);
  }
});

// -------------------- 3-legged OAuth (ACC/Docs) --------------------

app.get('/aps/oauth/login', async (req, res, next) => {
  try {
    // Check for required credentials first and return a helpful HTML error page
    const missingVars = [];
    if (!config.APS_CLIENT_ID) missingVars.push('APS_CLIENT_ID');
    if (!config.APS_CLIENT_SECRET) missingVars.push('APS_CLIENT_SECRET');
    if (!config.APS_CALLBACK_URL) missingVars.push('APS_CALLBACK_URL');

    if (missingVars.length > 0) {
      res.status(500).send(`
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>APS Configuration Required</title>
  <style>
    body { font-family: system-ui, -apple-system, sans-serif; background: #f5f7fa; color: #1e293b; margin: 0; padding: 24px; }
    .card { max-width: 600px; margin: 40px auto; background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    h2 { color: #0076CE; margin-top: 0; }
    code { background: #f1f5f9; padding: 2px 6px; border-radius: 4px; font-size: 14px; }
    pre { background: #f1f5f9; padding: 12px; border-radius: 8px; overflow-x: auto; }
    .error { color: #dc2626; }
    ul { margin: 12px 0; }
  </style>
</head>
<body>
  <div class="card">
    <h2>APS Configuration Required</h2>
    <p class="error">Missing environment variables:</p>
    <ul>
      ${missingVars.map(v => `<li><code>${v}</code></li>`).join('')}
    </ul>
    <p>To enable 3-legged OAuth (ACC Docs access):</p>
    <ol>
      <li>Create an APS app at <a href="https://aps.autodesk.com/myapps" target="_blank">aps.autodesk.com/myapps</a></li>
      <li>Copy your Client ID and Secret</li>
      <li>Set callback URL to: <code>http://127.0.0.1:3001/aps/oauth/callback</code></li>
      <li>Create a <code>.env</code> file in <code>backend/aps-service/</code>:</li>
    </ol>
    <pre>APS_CLIENT_ID="your-client-id"
APS_CLIENT_SECRET="your-client-secret"
APS_CALLBACK_URL="http://127.0.0.1:3001/aps/oauth/callback"</pre>
    <p>Then restart the APS service.</p>
  </div>
</body>
</html>
      `);
      return;
    }

    const clientId = config.APS_CLIENT_ID;
    const callbackUrl = config.APS_CALLBACK_URL;

    const cookies = parseCookies(req.headers.cookie);
    let sessionId = cookies.aps_session;
    if (!sessionId) {
      sessionId = newId();
      setCookie(res, 'aps_session', sessionId, { httpOnly: true, sameSite: 'Lax' });
    }

    const returnTo = getOptionalReturnTo(req.query.returnTo) || 'http://127.0.0.1:3001';
    const state = newId();
    const session = { state, returnTo };
    await store.set(`aps:sess:${sessionId}`, session, config.APS_SESSION_TTL_SECONDS);

    const scopes = parseScopes(config.APS_OAUTH_SCOPES);
    const { AuthenticationClient } = await import('@aps_sdk/authentication');
    const client = new AuthenticationClient();
    const url = client.authorize(clientId, ResponseType.Code, callbackUrl, scopes, { state });

    res.redirect(url);
  } catch (e) {
    next(e);
  }
});

app.get('/aps/oauth/callback', async (req, res, next) => {
  try {
    const clientId = requiredEnv('APS_CLIENT_ID', config.APS_CLIENT_ID);
    requiredEnv('APS_CLIENT_SECRET', config.APS_CLIENT_SECRET);
    const callbackUrl = requiredEnv('APS_CALLBACK_URL', config.APS_CALLBACK_URL);

    const cookies = parseCookies(req.headers.cookie);
    const sessionId = cookies.aps_session;
    if (!sessionId) {
      const err = new Error('Missing session cookie (aps_session)');
      err.status = 400;
      throw err;
    }

    const session = await store.get(`aps:sess:${sessionId}`);
    if (!session) {
      const err = new Error('OAuth session expired. Start again at /aps/oauth/login');
      err.status = 400;
      throw err;
    }

    const code = typeof req.query.code === 'string' ? req.query.code : '';
    const state = typeof req.query.state === 'string' ? req.query.state : '';

    if (!code) {
      const err = new Error('Missing OAuth code');
      err.status = 400;
      throw err;
    }
    if (!state || state !== session.state) {
      const err = new Error('Invalid OAuth state');
      err.status = 400;
      throw err;
    }

    const threeLegged = await tokens.exchangeThreeLeggedCode({ code });
    const updated = { ...session, threeLegged };
    await store.set(`aps:sess:${sessionId}`, updated, config.APS_SESSION_TTL_SECONDS);

    res.redirect(updated.returnTo || 'http://localhost:5173');
  } catch (e) {
    next(e);
  }
});

app.get('/aps/oauth/status', async (req, res, next) => {
  try {
    const cookies = parseCookies(req.headers.cookie);
    const sessionId = cookies.aps_session;
    if (!sessionId) return res.json({ logged_in: false, expires_at: null });
    const session = await store.get(`aps:sess:${sessionId}`);
    const t = session?.threeLegged;
    res.json({
      logged_in: Boolean(t?.access_token),
      expires_at: t?.expires_at || null
    });
  } catch (e) {
    next(e);
  }
});

async function requireSession(req) {
  const cookies = parseCookies(req.headers.cookie);
  const sessionId = cookies.aps_session;
  if (!sessionId) {
    const err = new Error('Not logged in. Start OAuth at /aps/oauth/login');
    err.status = 401;
    throw err;
  }
  const session = await store.get(`aps:sess:${sessionId}`);
  if (!session) {
    const err = new Error('Session expired. Start OAuth at /aps/oauth/login');
    err.status = 401;
    throw err;
  }
  return { sessionId, session };
}

async function getUserAuthHeader(req) {
  const { sessionId, session } = await requireSession(req);
  const now = Date.now();
  const safetyWindowMs = 60_000;
  const t = session.threeLegged;
  if (!t?.access_token || !t?.expires_at) {
    const err = new Error('No 3-legged token in session. Start OAuth at /aps/oauth/login');
    err.status = 401;
    throw err;
  }
  if ((t.expires_at - safetyWindowMs) > now) {
    return `Bearer ${t.access_token}`;
  }
  if (!t.refresh_token) {
    const err = new Error('3-legged token expired and no refresh token available. Login again.');
    err.status = 401;
    throw err;
  }
  const refreshed = await tokens.refreshThreeLeggedToken({ refresh_token: t.refresh_token });
  const updated = { ...session, threeLegged: refreshed };
  await store.set(`aps:sess:${sessionId}`, updated, config.APS_SESSION_TTL_SECONDS);
  return `Bearer ${refreshed.access_token}`;
}

async function getAppAuthHeader() {
  const t = await tokens.getTwoLeggedToken();
  return `Bearer ${t.access_token}`;
}

app.get('/aps/oauth/token', async (req, res, next) => {
  try {
    const authHeader = await getUserAuthHeader(req);
    const cookies = parseCookies(req.headers.cookie);
    const sessionId = cookies.aps_session;
    const session = sessionId ? await store.get(`aps:sess:${sessionId}`) : null;
    const t = session?.threeLegged;

    res.setHeader('Cache-Control', 'no-store');
    res.json({
      authorization: authHeader,
      access_token: t?.access_token || null,
      token_type: t?.token_type || 'Bearer',
      // Viewer expects expires_in seconds; compute from expires_at (ms)
      expires_in: t?.expires_at ? Math.max(0, Math.floor((t.expires_at - Date.now()) / 1000)) : null
    });
  } catch (e) {
    next(e);
  }
});

app.post('/aps/oauth/logout', async (req, res, next) => {
  try {
    const cookies = parseCookies(req.headers.cookie);
    const sessionId = cookies.aps_session;
    if (sessionId) await store.del(`aps:sess:${sessionId}`);
    setCookie(res, 'aps_session', '', { httpOnly: true, sameSite: 'Lax', maxAge: 0 });
    res.json({ ok: true });
  } catch (e) {
    next(e);
  }
});

// -------------------- ACC Docs (3-legged) --------------------

app.get('/acc/hubs', async (req, res, next) => {
  try {
    const api = createAccDocsApi({ getUserAuthHeader: async () => await getUserAuthHeader(req) });
    res.json(await api.hubs());
  } catch (e) {
    next(e);
  }
});

app.get('/acc/projects', async (req, res, next) => {
  try {
    const hubId = String(req.query.hubId || '').trim();
    if (!hubId) return res.status(400).json({ error: 'hubId is required' });
    const api = createAccDocsApi({ getUserAuthHeader: async () => await getUserAuthHeader(req) });
    res.json(await api.projects(hubId));
  } catch (e) {
    next(e);
  }
});

app.get('/acc/top-folders', async (req, res, next) => {
  try {
    const hubId = String(req.query.hubId || '').trim();
    const projectId = String(req.query.projectId || '').trim();
    if (!hubId || !projectId) return res.status(400).json({ error: 'hubId and projectId are required' });
    const api = createAccDocsApi({ getUserAuthHeader: async () => await getUserAuthHeader(req) });
    res.json(await api.topFolders(hubId, projectId));
  } catch (e) {
    next(e);
  }
});

app.get('/acc/folder-contents', async (req, res, next) => {
  try {
    const projectId = String(req.query.projectId || '').trim();
    const folderId = String(req.query.folderId || '').trim();
    if (!projectId || !folderId) return res.status(400).json({ error: 'projectId and folderId are required' });
    const api = createAccDocsApi({ getUserAuthHeader: async () => await getUserAuthHeader(req) });
    res.json(await api.folderContents(projectId, folderId));
  } catch (e) {
    next(e);
  }
});

app.get('/acc/item-versions', async (req, res, next) => {
  try {
    const projectId = String(req.query.projectId || '').trim();
    const itemId = String(req.query.itemId || '').trim();
    if (!projectId || !itemId) return res.status(400).json({ error: 'projectId and itemId are required' });
    const api = createAccDocsApi({ getUserAuthHeader: async () => await getUserAuthHeader(req) });
    res.json(await api.itemVersions(projectId, itemId));
  } catch (e) {
    next(e);
  }
});

app.get('/acc/version', async (req, res, next) => {
  try {
    const projectId = String(req.query.projectId || '').trim();
    const versionId = String(req.query.versionId || '').trim();
    if (!projectId || !versionId) return res.status(400).json({ error: 'projectId and versionId are required' });
    const api = createAccDocsApi({ getUserAuthHeader: async () => await getUserAuthHeader(req) });
    res.json(await api.versionDetails(projectId, versionId));
  } catch (e) {
    next(e);
  }
});

// -------------------- OSS + Model Derivative (2-legged) --------------------

const ossmd = createOssMdApi({
  config,
  getAppAuthHeader,
  getUserAuthHeader: async () => {
    // request-scoped cookie/session lookup happens in route handlers
    throw new Error('getUserAuthHeader must be provided per-request');
  }
});

app.get('/urn/from-object-id', (req, res) => {
  const objectId = String(req.query.objectId || '').trim();
  if (!objectId) return res.status(400).json({ error: 'objectId is required' });
  return res.json({ objectId, urn: ossmd.urnFromObjectId(objectId) });
});

app.post('/oss/upload', upload.single('file'), async (req, res, next) => {
  try {
    if (!config.APS_CLIENT_ID || !config.APS_CLIENT_SECRET) {
      return res.status(503).json({ 
        error: 'APS credentials not configured', 
        message: 'Please set APS_CLIENT_ID and APS_CLIENT_SECRET in backend/.env',
        documentation: 'https://aps.autodesk.com/myapps'
      });
    }
    
    const bucketKey = String(req.body.bucketKey || config.APS_BUCKET_KEY).trim();
    if (!req.file?.buffer) return res.status(400).json({ error: 'file is required (multipart field name: file)' });

    const objectKey = String(req.body.objectKey || req.file.originalname || `upload-${Date.now()}`).trim();
    const uploadResp = await ossmd.uploadObject({ bucketKey, objectKey, buffer: req.file.buffer });

    // objectId returned by OSS upload response
    const objectId = uploadResp.objectId || uploadResp.object_id;
    const urn = objectId ? ossmd.urnFromObjectId(objectId) : null;

    res.json({ bucketKey, objectKey, objectId, urn, upload: uploadResp });
  } catch (e) {
    next(e);
  }
});

app.post('/md/translate', async (req, res, next) => {
  try {
    const urn = String(req.body?.urn || '').trim();
    if (!urn) return res.status(400).json({ error: 'urn is required' });
    const force = Boolean(req.body?.force);
    const auth = String(req.body?.auth || 'app').toLowerCase();
    const api = createOssMdApi({
      config,
      getAppAuthHeader,
      getUserAuthHeader: async () => await getUserAuthHeader(req)
    });
    const resp = await api.translate({ urn, force, auth });
    res.json(resp);
  } catch (e) {
    next(e);
  }
});

app.get('/md/manifest', async (req, res, next) => {
  try {
    const urn = String(req.query.urn || '').trim();
    if (!urn) return res.status(400).json({ error: 'urn is required' });
    const auth = String(req.query.auth || 'app').toLowerCase();
    const api = createOssMdApi({
      config,
      getAppAuthHeader,
      getUserAuthHeader: async () => await getUserAuthHeader(req)
    });
    const resp = await api.manifest({ urn, auth });
    res.json(resp);
  } catch (e) {
    next(e);
  }
});

app.use((err, _req, res, _next) => {
  const status = Number.isInteger(err?.status) ? err.status : 500;
  const message = err?.message || 'Internal error';
  res.status(status).json({ error: message });
});

app.listen(config.APS_SERVICE_PORT, () => {
  console.log(`APS service listening on http://127.0.0.1:${config.APS_SERVICE_PORT}`);
  console.log(`Store: ${store.kind}`);
});
