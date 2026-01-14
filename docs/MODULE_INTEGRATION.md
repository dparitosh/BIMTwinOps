# Module Integration Documentation

This document describes how external modules are integrated into the SMART_BIM project.

## Integrated Modules

### 1. digitaltwin_pointcloud (Base Project)

**Source:** https://github.com/bhupesh-varma/digitaltwin_pointcloud

**Integration Type:** Direct code integration (forked/enhanced)

**Components Integrated:**

| Component | Source Path | Local Path | Status |
|-----------|------------|------------|--------|
| FastAPI Backend | `backend/api/main.py` | `backend/api/main.py` | ✅ Enhanced |
| PointCloud Viewer | `pointcloud-frontend/src/components/PointCloudViewer.jsx` | Same | ✅ Enhanced with TCS styling |
| Graph Viewer | `pointcloud-frontend/src/components/GraphViewer.jsx` | Same | ✅ Enhanced with TCS styling |
| Annotation Panel | `pointcloud-frontend/src/components/AnnotationPanel.jsx` | Same | ✅ Enhanced with TCS styling |
| File Upload | `pointcloud-frontend/src/components/FileUpload.jsx` | Same | ✅ Enhanced with TCS styling |
| Loader | `pointcloud-frontend/src/components/Loader.jsx` | Same | ✅ Enhanced with TCS styling |
| Chat Modal | `pointcloud-frontend/src/App.jsx` | Same | ✅ Enhanced with TCS styling |
| kNN Script | `backend/scripts/compute_knn_near.py` | Same | ✅ Unchanged |

**Enhancements Made:**

1. **TCS Corporate Branding**
   - Applied TCS color scheme (#0076CE Blue, #1A3D6D Navy, #FF6600 Orange)
   - Light background theme with professional styling
   - SVG icons instead of emojis

2. **Neo4j Configuration**
   - Added `NEO4J_DATABASE` environment variable support
   - Default database: `smartbim`

3. **Health Endpoints**
   - Added `/health/neo4j` endpoint for connectivity checks

---

### 2. pointnet_s3dis (Git Submodule)

**Source:** https://github.com/bhupesh-varma/pointnet_s3dis

**Integration Type:** Git submodule

**Local Path:** `backend/pointnet_s3dis/`

**Key Files:**

| File | Purpose |
|------|---------|
| `online_segmentation.py` | Main inference entry point (`process_uploaded_array`) |
| `src/models/pointnet.py` | PyTorch PointNet architecture |
| `src/data/dataset.py` | S3DIS dataset loader |
| `best_pointnet_s3dis.pth` | Trained model weights |

**API Usage:**

```python
from pointnet_s3dis.online_segmentation import process_uploaded_array

# Called from FastAPI /upload endpoint
result = process_uploaded_array(np_array, scene_id="my_scene")
# Returns: { scene_id, points, labels, segments, edges }
```

**Submodule Commands:**

```bash
# Initialize submodule after clone
git submodule update --init --recursive

# Update to latest version
git submodule update --remote backend/pointnet_s3dis
```

---

### 3. Autodesk Platform Services (APS SDK)

**Source:** https://github.com/autodesk-platform-services (npm packages)

**Integration Type:** npm packages

**Packages Used:**

```json
{
  "@aps_sdk/authentication": "^1.x",
  "@aps_sdk/data-management": "^1.x",
  "@aps_sdk/oss": "^1.x",
  "@aps_sdk/model-derivative": "^1.x"
}
```

**Local Path:** `backend/aps-service/`

**Features:**

| Feature | Endpoint | Auth Type |
|---------|----------|-----------|
| Token Generation | `/aps/token` | 2-legged |
| User Login | `/aps/oauth/login` | 3-legged |
| OAuth Callback | `/aps/oauth/callback` | 3-legged |
| ACC Hubs | `/acc/hubs` | 3-legged |
| ACC Projects | `/acc/projects` | 3-legged |
| ACC Folders | `/acc/folder-contents` | 3-legged |
| OSS Upload | `/oss/upload` | 2-legged |
| Model Translate | `/md/translate` | 2-legged |
| Manifest Status | `/md/manifest` | 2-legged |

---

## New Components Added

These components were **not** in the original `digitaltwin_pointcloud` repo:

| Component | Path | Purpose |
|-----------|------|---------|
| `AccBrowser.jsx` | `pointcloud-frontend/src/components/` | Browse ACC Docs (hubs, projects, folders) |
| `ApsViewer.jsx` | `pointcloud-frontend/src/components/` | Autodesk Forge Viewer integration |
| `OssUploadTranslate.jsx` | `pointcloud-frontend/src/components/` | Upload to OSS + translate models |

---

## Configuration Files

### Backend Environment (`backend/.env`)

```env
# Neo4j
NEO4J_URI=neo4j://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
NEO4J_DATABASE=smartbim

# Gemini LLM
GOOGLE_API_KEY=your_google_api_key
```

### APS Service Environment (`backend/aps-service/.env`)

```env
# APS Credentials
APS_CLIENT_ID=your_client_id
APS_CLIENT_SECRET=your_client_secret
APS_CALLBACK_URL=http://127.0.0.1:3001/aps/oauth/callback

# Frontend proxy mode
FRONTEND_MODE=proxy
FRONTEND_DEV_URL=http://localhost:5173
```

---

## Dependency Graph

```
SMART_BIM
├── digitaltwin_pointcloud (base code - enhanced)
│   ├── FastAPI backend
│   ├── React frontend
│   └── Neo4j integration
├── pointnet_s3dis (git submodule)
│   ├── PyTorch PointNet model
│   └── S3DIS dataset support
└── APS SDK (npm packages)
    ├── Authentication
    ├── Data Management
    ├── OSS
    └── Model Derivative
```

---

## Updating Modules

### Update pointnet_s3dis submodule

```bash
cd backend/pointnet_s3dis
git pull origin main
cd ../..
git add backend/pointnet_s3dis
git commit -m "Update pointnet_s3dis submodule"
```

### Update APS SDK packages

```bash
cd backend/aps-service
npm update @aps_sdk/authentication @aps_sdk/data-management @aps_sdk/oss @aps_sdk/model-derivative
```

### Sync with upstream digitaltwin_pointcloud

```bash
# Add upstream remote (one-time)
git remote add upstream https://github.com/bhupesh-varma/digitaltwin_pointcloud.git

# Fetch and merge changes
git fetch upstream
git merge upstream/main --allow-unrelated-histories
```

---

## License

- **digitaltwin_pointcloud**: See original repo license
- **pointnet_s3dis**: MIT License
- **APS SDK**: Autodesk Platform Services Terms
