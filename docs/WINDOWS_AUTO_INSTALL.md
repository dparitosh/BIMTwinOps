# Windows Auto Installation (PowerShell)

This repo includes PowerShell scripts that **prompt you for configuration (with examples)**, generate the required `.env` files, install dependencies, and optionally start the dev services.

> ✅ Recommended on Windows: run these scripts from an elevated PowerShell *only if* you need admin rights for external tools. For normal installs, regular PowerShell is fine.

---

## Quick start (interactive)

From the repo root (`d:\SMART_BIM`):

- Run the full installer:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1`

It will:
1) Prompt for config and write:
   - `backend\.env`
   - `backend\aps-service\.env` *(optional; APS service also reads `backend\.env`)*
   - `pointcloud-frontend\.env`
2) Create a Python venv in `./.venv` and install Python packages
3) Run `npm install` in:
   - `pointcloud-frontend/`
   - `backend/aps-service/`

---

## Example prompts (what you’ll see)

The wizard shows an **example** and a **default** (press Enter to accept). For secrets, it tells you whether it will keep an existing value.

Typical entries:

- Neo4j
  - `Neo4j URI (NEO4J_URI) - example: neo4j://127.0.0.1:7687 [default: neo4j://127.0.0.1:7687]`
  - `Neo4j password (NEO4J_PASSWORD) - example: <your-neo4j-password> (Enter to keep <kept>)`

- Local LLM (Ollama)
  - `LLM provider (ollama|gemini|azure) (LLM_PROVIDER) - example: ollama [default: ollama]`
  - `Ollama base URL (OLLAMA_BASE_URL) - example: http://localhost:11434 [default: http://localhost:11434]`
  - `Ollama chat model tag (OLLAMA_MODEL) - example: llama3.2:1b [default: llama3.2:1b]`

- APS (Autodesk Platform Services)
  - `APS Client ID (APS_CLIENT_ID) - example: <your-aps-client-id> [optional]`
  - `APS Client Secret (APS_CLIENT_SECRET) - example: <your-aps-client-secret> (Enter to keep <empty>)`
  - `APS OAuth callback URL (3-legged) (APS_CALLBACK_URL) - example: http://127.0.0.1:3001/aps/oauth/callback [default: http://127.0.0.1:3001/aps/oauth/callback]`

---

## Common modes

### Non-interactive (CI / repeatable)

- Use defaults / existing values without prompting:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -NonInteractive`

### Skip heavy PointNet/PyTorch install

PointNet dependencies include PyTorch, which can be large.

- Skip PointNet:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -SkipPointNet`

You can later install it with:
- `powershell -ExecutionPolicy Bypass -File .\scripts\bootstrap.ps1` *(without `-SkipPointNet`)*

### Start services automatically

- Configure + install + start everything:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\install.ps1 -Start -All`

---

## Where config lives

- Backend & APS service (central): `backend\.env`
  - Used by `backend/api/main.py`
  - Read by APS service via `backend/aps-service/src/config.js` (loads `backend\.env`)

- APS service override (optional): `backend\aps-service\.env`

- Frontend: `pointcloud-frontend\.env`
  - `VITE_BACKEND_API_URL`
  - `VITE_APS_API_URL`

> Note: never commit real secrets. `.env` files should stay local.

---

## Troubleshooting

### Port conflicts (ERR_CONNECTION_REFUSED / WinError 10048)

If you see errors like:

- Browser: `net::ERR_CONNECTION_REFUSED` (frontend can’t reach the API)
- API log: `WinError 10048` / “error while attempting to bind … only one usage of each socket address”

…then the configured port is already used by another process.

What to do:

1) Re-run the wizard (it will suggest a free port by default):
  - `powershell -ExecutionPolicy Bypass -File .\scripts\configure.ps1`
2) Restart services:
  - `powershell -ExecutionPolicy Bypass -File .\scripts\stop-services.ps1 -All -Force`
  - `powershell -ExecutionPolicy Bypass -File .\scripts\start-services.ps1 -All`

Important: the Vite frontend reads `VITE_*` variables at startup, so **you must restart the frontend** after changing `pointcloud-frontend\.env`.

### PointNet weights missing (upload returns 500)

PointNet’s Python dependencies can be installed, but the trained weights file is not always present:

- Expected path: `backend\pointnet_s3dis\best_pointnet_s3dis.pth`

If the weights are missing:

- The API will still accept uploads, but segmentation may run in a **fallback** mode (single segment) so you can continue using the viewer.

To enable real semantic segmentation, place the weights file at the expected path.

### “Python not found” / “npm not found”

- Install prerequisites:
  - Python 3.9+ (recommended 3.10+)
  - Node.js 18+

Then rerun `scripts\install.ps1`.

### Neo4j / Redis / Ollama

The scripts **do not** start external dependencies for you.

- Neo4j: start Neo4j Desktop or a local server
- Redis (optional): only required if `APS_STORE=redis`
- Ollama (optional): install and run `ollama serve`

### Check service logs

The start/stop scripts store PID + logs in:
- `.\.pids\`

Look at:
- `.\.pids\frontend.out.log`
- `.\.pids\aps-service.out.log`
- `.\.pids\api.out.log`
