# SMART_BIM

**Integrated APS + PointCloud Digital Twin Platform**

This project integrates:
- **[digitaltwin_pointcloud](https://github.com/bhupesh-varma/digitaltwin_pointcloud)** - PointCloud Digital Twin with PointNet semantic segmentation
- **[pointnet_s3dis](https://github.com/bhupesh-varma/pointnet_s3dis)** - PointNet S3DIS for 3D scene semantic segmentation (git submodule)
- **[Autodesk Platform Services (APS)](https://github.com/autodesk-platform-services)** - Official APS SDK integration

## Architecture

```
SMART_BIM/
├── backend/
│   ├── api/                    # FastAPI backend (from digitaltwin_pointcloud)
│   │   └── main.py             # Endpoints: /upload, /chat, /health/neo4j
│   ├── pointnet_s3dis/         # Git submodule - PointNet S3DIS model
│   │   ├── src/models/         # PyTorch PointNet implementation
│   │   └── online_segmentation.py  # Inference + Neo4j writing
│   ├── aps-service/            # Node.js APS service (new integration)
│   │   └── src/server.js       # OAuth, ACC Docs, OSS, Model Derivative
│   └── scripts/                # kNN computation scripts
├── pointcloud-frontend/        # React + Vite frontend
│   └── src/
│       ├── App.jsx             # Main app with tabbed APS/PointCloud viewers
│       └── components/         # Viewer components
└── scripts/                    # Windows start/stop scripts
```

## Integrated Modules

### 1. PointNet S3DIS (Git Submodule)

The `backend/pointnet_s3dis` module provides:
- **Semantic Segmentation**: Classifies point cloud into 13 classes (ceiling, floor, wall, beam, column, window, door, chair, table, bookcase, sofa, board, clutter)
- **Online Inference**: `process_uploaded_array()` runs multi-pass PointNet inference
- **Neo4j Integration**: Writes segments with spatial properties (`centroid_point`, `bbox_min`, `bbox_max`)

### 2. Digital Twin PointCloud (Base Integration)

Core features from the digitaltwin_pointcloud repo:
- **FastAPI Backend**: Upload point clouds, chat with scene via Gemini LLM
- **React Frontend**: 3D viewer (Three.js), Graph viewer (Force-Graph), Annotation panel
- **Neo4j Graph**: Store scene segments and spatial relationships

### 3. APS Integration (Extended Feature)

New APS SDK integration providing:
- **2-Legged OAuth**: Token generation for OSS/Model Derivative
- **3-Legged OAuth**: User login for ACC Docs browsing
- **OSS Upload**: Upload files to Autodesk Object Storage
- **Model Derivative**: Translate models for Forge Viewer
- **Forge Viewer**: Display translated models in browser

## Windows: start/stop scripts

- Start all (frontend + APS service + FastAPI): `powershell -ExecutionPolicy Bypass -File .\scripts\start-services.ps1`
- Stop all: `powershell -ExecutionPolicy Bypass -File .\scripts\stop-services.ps1 -Force`
- Start only APS service: `powershell -ExecutionPolicy Bypass -File .\scripts\start-services.ps1 -Aps`
- Start only frontend: `powershell -ExecutionPolicy Bypass -File .\scripts\start-services.ps1 -Frontend`
- Start only API: `powershell -ExecutionPolicy Bypass -File .\scripts\start-services.ps1 -Api`

PIDs and logs are written to `.pids/`.

## Quick Start

### Prerequisites

- Python 3.9+ with PyTorch
- Node.js 18+
- Neo4j 5.x (with database named `smartbim`)
- (Optional) Autodesk Platform Services credentials

### 1. Clone with submodules

```bash
git clone --recurse-submodules https://github.com/your-org/SMART_BIM.git
cd SMART_BIM
```

### 2. Set up PointNet S3DIS

Follow the `backend/pointnet_s3dis` README to set up data.

### 3. Start the Python backend (FastAPI)

Create `backend/.env` based on `backend/.env.example` and set Neo4j + Gemini env vars.

```bash
cd backend
pip install -r api/requirements.txt
pip install -r pointnet_s3dis/requirements.txt
uvicorn api.main:app --reload --port 8000
```

### 4. Start the React frontend

```bash
cd pointcloud-frontend
npm install
npm run dev
```

### 5. (Optional) Start APS service

Create `backend/aps-service/.env` with your Autodesk credentials.

```bash
cd backend/aps-service
npm install
npm run dev
```

Open the app at `http://127.0.0.1:3001/` (APS proxy mode) or `http://localhost:5173` (Vite direct).

## APS Integration (Autodesk Platform Services)

This repo now includes an APS module using the official APS Node SDK (`@aps_sdk/authentication`).

All APS configuration is centralized in `backend/aps-service/.env`.

### Setup

1) Create `backend/aps-service/.env` based on `backend/aps-service/.env.example` and set:

- `APS_CLIENT_ID`
- `APS_CLIENT_SECRET`
- (optional) `APS_SCOPES`

For 3-legged (ACC/Docs), also set:

- `APS_CALLBACK_URL` (must match your APS app callback URL, e.g. `http://127.0.0.1:3001/aps/oauth/callback`)
- (optional) `APS_OAUTH_SCOPES` (default: `data:read viewables:read`)
- (optional) `APS_CORS_ORIGINS` (default allows Vite dev server)

For demo scalability, Redis can be used to store sessions/tokens:

- `APS_STORE=redis`
- `REDIS_URL=redis://127.0.0.1:6379`

### Run

From `backend/aps-service`:

`npm install`

`npm run dev`

The service will be available at:

- `GET http://127.0.0.1:3001/` (serves the React UI when `FRONTEND_MODE=proxy|static`)
- `GET http://127.0.0.1:3001/health`
- `GET http://127.0.0.1:3001/aps/token`

### Recommended dev topology (single entrypoint)

Run both processes:

1) Start the React dev server:

`cd pointcloud-frontend`

`npm run dev`

2) Start APS service as the entrypoint (proxies UI at `/`):

Create `backend/aps-service/.env` with:

- `FRONTEND_MODE=proxy`
- `FRONTEND_DEV_URL=http://localhost:5173`

Then run:

`cd backend/aps-service`

`npm run dev`

Open the app at `http://127.0.0.1:3001/` (not `:5173`).

### Static mode (single process)

1) Build frontend:

`cd pointcloud-frontend`

`npm run build`

2) Set in `backend/aps-service/.env`:

- `FRONTEND_MODE=static`
- `FRONTEND_DIST_DIR=../../pointcloud-frontend/dist`

3) Start APS service and open `http://127.0.0.1:3001/`.

3-legged OAuth endpoints:

- `GET http://127.0.0.1:3001/aps/oauth/login?returnTo=http://localhost:5173`
- `GET http://127.0.0.1:3001/aps/oauth/callback`
- `GET http://127.0.0.1:3001/aps/oauth/status`
- `GET http://127.0.0.1:3001/aps/oauth/token`
- `POST http://127.0.0.1:3001/aps/oauth/logout`

ACC Docs (3-legged) endpoints:

- `GET http://127.0.0.1:3001/acc/hubs`
- `GET http://127.0.0.1:3001/acc/projects?hubId=...`
- `GET http://127.0.0.1:3001/acc/top-folders?hubId=...&projectId=...`
- `GET http://127.0.0.1:3001/acc/folder-contents?projectId=...&folderId=...`
- `GET http://127.0.0.1:3001/acc/item-versions?projectId=...&itemId=...`
- `GET http://127.0.0.1:3001/acc/version?projectId=...&versionId=...`

OSS + Model Derivative (2-legged) endpoints:

- `POST http://127.0.0.1:3001/oss/upload` (multipart form field `file`, optional `bucketKey`, `objectKey`)
- `POST http://127.0.0.1:3001/md/translate` (json: `{ "urn": "...", "force": false }`)
- `GET  http://127.0.0.1:3001/md/manifest?urn=...`

If you want the frontend to call a different URL, set `VITE_APS_API_URL` when running Vite.
