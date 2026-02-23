# Backend Startup Guide

## ⚠️ Important: Correct Startup Method

The BIMTwinOps backend **must** be started using the correct module path to support Python relative imports.

## ✅ Correct Methods

### Option 1: Use Startup Script (Recommended)
```powershell
# From project root
.\scripts\start-services.ps1
```
This starts all services (Backend, Frontend, APS) with health checks.

### Option 2: Manual Startup
```powershell
# From project root
cd backend
..\\.venv\Scripts\python.exe -m uvicorn api.main:app --host 0.0.0.0 --port 8008 --reload
```

**Key Requirements**:
- **Working directory**: `backend/` (not `backend/api/`)
- **Module path**: `api.main:app` (not `main:app`)
- **Port**: `8008` (default)

## ❌ Common Mistakes

### Mistake 1: Running from `backend/api/`
```powershell
# ❌ WRONG - Will fail with ImportError
cd backend/api
python -m uvicorn main:app --host 0.0.0.0 --port 8008
```

**Error**:
```
ImportError attempted relative import with no known parent package
  File "D:\SMART_BIM\backend\api\main.py", line 25, in <module>
    from .config import cfg
```

**Why it fails**: When you run from `backend/api/`, Python treats `main.py` as `__main__`, not as a module within a package. This breaks relative imports like `from .config import cfg`.

### Mistake 2: Using `main:app` instead of `api.main:app`
```powershell
# ❌ WRONG - Will fail with ImportError
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8008
```

**Error**: Same as above - Python can't find the `main` module because it's in the `api` subdirectory.

## 📚 Technical Explanation

### Python Package Structure
```
backend/
├── api/                    # Python package
│   ├── __init__.py        # Makes 'api' a package
│   ├── main.py            # Main FastAPI app
│   ├── config.py          # Configuration
│   └── ...
└── pointnet_s3dis/        # Another package
```

### How Relative Imports Work

In [main.py](../backend/api/main.py), we use relative imports:
```python
from .config import cfg              # Relative import
from .kg_routes import router        # Relative import
from .generative_ui.api import ...   # Relative import
```

These imports require:
1. **Package context**: Python must recognize `api` as a package
2. **Working directory**: Must be a parent of `api/`, not inside it
3. **Module path**: Must specify the package path (`api.main:app`)

### When you run correctly:
```powershell
cd backend
python -m uvicorn api.main:app
```

Python's module resolution:
1. Working directory: `backend/`
2. Module path: `api.main:app`
3. Python imports: `api` package → `main.py` module → `app` variable
4. Relative imports work: `.config` resolves to `api.config`

### When you run incorrectly:
```powershell
cd backend/api
python -m uvicorn main:app
```

Python's module resolution:
1. Working directory: `backend/api/`
2. Module path: `main:app`
3. Python imports: `main.py` as `__main__` (not a package)
4. Relative imports fail: `.config` has no parent package

## 🔧 Service Management

### Start All Services
```powershell
.\scripts\start-services.ps1
```

Opens 3 PowerShell windows:
- **Backend** (port 8008): FastAPI with auto-reload
- **Frontend** (port 5173): Vite dev server
- **APS Service** (port 3001): Node.js OAuth proxy

### Stop All Services
```powershell
.\scripts\stop-services.ps1
```

Gracefully terminates all processes on ports 8008, 5173, 3001.

### Check Service Status
```powershell
# Check which services are running
Get-NetTCPConnection -LocalPort 8008,5173,3001 -State Listen

# Test backend health
curl http://localhost:8008/health

# Test backend API docs
Start-Process http://localhost:8008/docs
```

## 🌐 Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Backend Health | http://localhost:8008/health | Health check endpoint |
| API Docs (Swagger) | http://localhost:8008/docs | Interactive API documentation |
| GraphQL Playground | http://localhost:8008/api/graphql | GraphQL query interface |
| Frontend | http://localhost:5173 | React application |
| APS Service | http://localhost:3001 | Autodesk Platform Services |

## 📝 Troubleshooting

### Backend won't start
```powershell
# Check if port 8008 is already in use
Get-NetTCPConnection -LocalPort 8008 -ErrorAction SilentlyContinue

# Kill process on port 8008
$pid = (Get-NetTCPConnection -LocalPort 8008).OwningProcess
Stop-Process -Id $pid -Force

# Check Python environment
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\pip list | Select-String "fastapi|uvicorn"
```

### ImportError: attempted relative import
```powershell
# Verify you're in the correct directory
pwd  # Should be D:\SMART_BIM\backend

# Verify using correct module path
# ✅ python -m uvicorn api.main:app
# ❌ python -m uvicorn main:app
```

### Module not found errors
```powershell
# Reinstall dependencies
.\.venv\Scripts\activate
pip install -r api\requirements.txt

# Verify installation
pip list | Select-String "fastapi|uvicorn|neo4j"
```

## 🔄 Related Documentation

- [README.md](../README.md) - Main project documentation
- [GraphQL API Guide](GRAPHQL_API_GUIDE.md) - GraphQL endpoint usage
- [Component Architecture](COMPONENT_ARCHITECTURE.md) - System architecture
