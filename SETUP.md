# BIMTwinOps Quick Setup Guide

This guide will get you up and running with BIMTwinOps in under 5 minutes.

## Prerequisites

| Software | Version | Check Command |
|----------|---------|---------------|
| Python | 3.10+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Git | Any | `git --version` |

### Optional (for full features)

| Software | Version | Purpose |
|----------|---------|---------|
| Neo4j | 5.x | Knowledge graph database |
| Ollama | Latest | Local LLM for GenAI features |

---

## Quick Start (3 commands)

```powershell
# 1. Clone or download
git clone https://github.com/dparitosh/BIMTwinOps.git
cd BIMTwinOps

# 2. Run bootstrap (one-time setup)
.\bootstrap.ps1

# 3. Start all services
.\start-all.ps1
```

That's it! Open http://localhost:5173 in your browser.

---

## What Bootstrap Does

1. Creates Python virtual environment (`.venv/`)
2. Installs Python dependencies (`pip install -r requirements.txt`)
3. Installs Node.js dependencies (`npm install`)
4. Creates default `.env` files

---

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | React + Vite app |
| Backend API | http://localhost:8000 | FastAPI server |
| API Docs | http://localhost:8000/docs | Swagger UI |
| GraphQL | http://localhost:8000/api/graphql | GraphQL playground |

---

## Configuration

### Backend (`backend/.env`)

```env
# Required
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# Neo4j (optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Azure OpenAI (optional)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Ollama (optional, for local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### APS Service (`backend/aps-service/.env`)

```env
APS_CLIENT_ID=your_autodesk_client_id
APS_CLIENT_SECRET=your_autodesk_client_secret
APS_SERVICE_PORT=3001
```

### Frontend (`pointcloud-frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_APS_SERVICE_URL=http://localhost:3001
```

---

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `bootstrap.ps1` | One-time setup (venv, npm install, .env) |
| `start-all.ps1` | Start backend + frontend |
| `start-backend.ps1` | Start backend only |
| `start-frontend.ps1` | Start frontend only |
| `start-all.bat` | Windows batch version |
| `start-backend.bat` | Windows batch version |
| `start-frontend.bat` | Windows batch version |

### Bootstrap Options

```powershell
# Skip frontend setup
.\bootstrap.ps1 -SkipFrontend

# Skip backend setup
.\bootstrap.ps1 -SkipBackend

# Run diagnostics after setup
.\bootstrap.ps1 -RunDiagnostics
```

### Backend Options

```powershell
# Enable hot-reload for development
.\start-backend.ps1 -Reload
```

---

## Troubleshooting

### Problem: "python is not recognized"

**Fix:** Install Python 3.10+ and add to PATH:
- Download from https://www.python.org/downloads/
- During installation, check "Add Python to PATH"

### Problem: "node is not recognized"

**Fix:** Install Node.js 18+:
- Download from https://nodejs.org/
- Use the LTS version

### Problem: Virtual environment fails to create

**Fix:**
```powershell
# Delete existing venv and retry
Remove-Item -Recurse -Force .venv
.\bootstrap.ps1
```

### Problem: Port already in use

**Fix:**
```powershell
# Find what's using the port
Get-NetTCPConnection -LocalPort 8000 -State Listen

# Kill the process
Stop-Process -Id <PID> -Force
```

Or change the port in `backend/.env`:
```env
BACKEND_PORT=8001
```

### Problem: Neo4j connection failed

**Fix:**
1. Make sure Neo4j is running
2. Check credentials in `backend/.env`
3. Neo4j is optional - the app works without it

### Problem: Script execution disabled

**Fix:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Reset Everything

If something is broken and you want to start fresh:

```powershell
cd BIMTwinOps

# Remove virtual environment
Remove-Item -Recurse -Force .venv -ErrorAction SilentlyContinue

# Remove node modules
Remove-Item -Recurse -Force pointcloud-frontend\node_modules -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force backend\aps-service\node_modules -ErrorAction SilentlyContinue

# Run bootstrap again
.\bootstrap.ps1
```

---

## Quick Reference

| Action | Command |
|--------|---------|
| Start everything | `.\start-all.ps1` |
| Start backend only | `.\start-backend.ps1` |
| Start frontend only | `.\start-frontend.ps1` |
| Run setup | `.\bootstrap.ps1` |
| View API docs | http://localhost:8000/docs |
| Open app | http://localhost:5173 |

---

## Next Steps

1. **Configure Neo4j** (optional): Add credentials to `backend/.env`
2. **Configure APS** (optional): Add Autodesk credentials to `backend/aps-service/.env`
3. **Upload a point cloud**: Use the Point Cloud tab to upload `.npy` files
4. **Try the AI chat**: Ask questions about your building data
