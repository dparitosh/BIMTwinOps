# BIMTwinOps Quick Setup Guide

Complete setup guide for BIMTwinOps - Digital Twin Point Cloud Platform.

---

## Prerequisites

| Software | Version | Check Command | Download |
|----------|---------|---------------|----------|
| Python | 3.10+ | `python --version` | https://www.python.org/downloads/ |
| Node.js | 18+ | `node --version` | https://nodejs.org/ |
| Git | Any | `git --version` | https://git-scm.com/ |
| Java | 11+ | `java -version` | https://adoptium.net/ (for BaseX) |

### Optional (for full features)

| Software | Purpose | Download |
|----------|---------|----------|
| Neo4j | Knowledge graph database | https://neo4j.com/download/ |
| Ollama | Local LLM (GenAI features) | https://ollama.ai/ |
| BaseX | XML/XQuery database for IFC/bSDD | https://basex.org/download/ |

---

## Quick Start

```powershell
# 1. Clone repository
git clone https://github.com/dparitosh/BIMTwinOps.git
cd BIMTwinOps

# 2. Bootstrap (one-time setup)
.\bootstrap.ps1

# 3. Configure Environment (Optional but recommended)
# Edit backend/.env with your Neo4j credentials

# 4. Initialize Database (Required if using Neo4j)
# Ensure your virtual environment is active or use the executable path
& .venv\Scripts\python backend/scripts/init_neo4j_schema.py --seed

# 5. Start all services
.\start-all.ps1
```

Open http://localhost:5173 in your browser.

---

## What Bootstrap Does

1. ✅ Creates Python virtual environment (`.venv/`)
2. ✅ Installs Python dependencies (`pip install -r requirements.txt`)
3. ✅ Installs PointNet dependencies
4. ✅ Installs Node.js dependencies (`npm install`)
5. ✅ Creates default `.env` files

---

## Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:5173 | React + Vite app |
| Backend API | http://localhost:8008 | FastAPI server |
| API Docs | http://localhost:8008/docs | Swagger UI |
| GraphQL | http://localhost:8008/api/graphql | GraphQL playground |
| APS Service | http://localhost:3001 | Autodesk Platform Services |
| BaseX Admin | http://localhost:8080/dba | BaseX database admin |

---

## External Services Setup

### Neo4j Setup (Knowledge Graph)

1. **Download** Neo4j Desktop from https://neo4j.com/download/
2. **Create** a new database (e.g., `bimtwinops`)
3. **Set password** and note it
4. **Configure** `backend/.env`:
   ```env
   NEO4J_URI=bolt://localhost:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=your_password
   ```

### Ollama Setup (Local LLM)

1. **Download** from https://ollama.ai/
2. **Install** and run:
   ```powershell
   ollama serve
   ollama pull llama3
   ```
3. **Configure** `backend/.env`:
   ```env
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3
   ```

### BaseX Setup (XML/XQuery Database)

BaseX is used for IFC/bSDD XML document storage and XQuery-based search.

#### Option 1: Automatic Installation (Recommended)

```powershell
# Run the BaseX installation script
.\scripts\start-basex.ps1
```

This will:
- Check for Java 11+ (required)
- Download BaseX 11.8 if not installed
- Extract to `D:\BaseX` (configurable)
- Start the BaseX HTTP server on port 8080

#### Option 2: Manual Installation

1. **Install Java 11+** (required):
   - Download from https://adoptium.net/
   - Verify: `java -version`

2. **Download BaseX**:
   - Download from https://basex.org/download/
   - Get the ZIP version (e.g., `BaseX118.zip`)

3. **Extract and Configure**:
   ```powershell
   # Extract to D:\BaseX (or your preferred location)
   Expand-Archive -Path BaseX118.zip -DestinationPath D:\BaseX
   
   # Set environment variable (optional)
   [Environment]::SetEnvironmentVariable("BASEX_HOME", "D:\BaseX", "User")
   ```

4. **Start BaseX HTTP Server**:
   ```powershell
   cd D:\BaseX\bin
   .\basexhttp.bat -p 8080
   ```

5. **Configure Backend** (`backend/.env`):
   ```env
   BASEX_HOST=localhost
   BASEX_PORT=8080
   BASEX_USER=admin
   BASEX_PASSWORD=admin
   ```

6. **Access Admin Interface**:
   - Open http://localhost:8080/dba
   - Default credentials: `admin` / `admin`

#### BaseX Scripts Reference

| Script | Purpose |
|--------|---------|
| `scripts/start-basex.ps1` | Start BaseX server (auto-downloads if needed) |
| `scripts/stop-basex.ps1` | Stop BaseX server |

---

## Scripts Reference

### Start Scripts

| Script | Purpose |
|--------|---------|
| `start-all.ps1` | Start backend + frontend + APS (shows diagnostics) |
| `start-backend.ps1` | Start backend only |
| `start-frontend.ps1` | Start frontend only |
| `start-aps.ps1` | Start APS OAuth service only |
| `bootstrap.ps1` | One-time setup |

### Stop Scripts

| Script | Purpose |
|--------|---------|
| `stop-all.ps1` | Stop all services |
| `stop-backend.ps1` | Stop backend only |
| `stop-frontend.ps1` | Stop frontend only |

### Batch Versions (for cmd.exe)

| Script | Purpose |
|--------|---------|
| `start-all.bat` | Start all services |
| `start-backend.bat` | Start backend |
| `start-frontend.bat` | Start frontend |
| `stop-all.bat` | Stop all services |

---

## Configuration

### Backend (`backend/.env`)

```env
# Server Settings
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8008

# Neo4j (optional - for knowledge graph)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Azure OpenAI (optional - for GenAI features)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Ollama (optional - for local LLM)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

### Frontend (`pointcloud-frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8008
VITE_APS_SERVICE_URL=http://localhost:3001
```

### APS Service (`backend/aps-service/.env`)

```env
APS_CLIENT_ID=your_autodesk_client_id
APS_CLIENT_SECRET=your_autodesk_client_secret
APS_SERVICE_PORT=3001
```

---

## Script Options

### Bootstrap Options

```powershell
# Full setup
.\bootstrap.ps1

# Skip frontend setup
.\bootstrap.ps1 -SkipFrontend

# Skip backend setup
.\bootstrap.ps1 -SkipBackend
```

### Backend Options

```powershell
# Normal start
.\start-backend.ps1

# Enable hot-reload for development
.\start-backend.ps1 -Reload

# Skip connection checks (faster start)
.\start-backend.ps1 -SkipChecks
```

### Frontend Options

```powershell
# Normal start
.\start-frontend.ps1

# Skip connection checks
.\start-frontend.ps1 -SkipChecks
```

---

## Startup Output Example

When you run `.\start-all.ps1`, you'll see:

```
========================================
  BIMTwinOps - Starting All Services
========================================

--- Prerequisites ---
[OK] Python: Python 3.11.5
[OK] Node.js: v20.10.0
[OK] Virtual Environment: .venv
[OK] node_modules: Found

--- Configuration ---
  Backend:       http://127.0.0.1:8008
  Frontend:      http://localhost:5173
  Neo4j:         bolt://localhost:7687
  Ollama:        http://localhost:11434
  Azure OpenAI:  (not configured)

--- Port Check ---
[OK] Port 8008: Ready
[OK] Port 5173: Ready

--- Starting Services ---
Starting Backend Server...
Waiting for backend to start (5s)...
[OK] Backend: Running
Starting Frontend Server...

========================================
  Services Started!
========================================
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

### Problem: Port already in use

**Fix:** Stop existing processes:
```powershell
.\stop-all.ps1
```

Or manually:
```powershell
# Find what's using the port
Get-NetTCPConnection -LocalPort 8008 -State Listen

# Kill the process
Stop-Process -Id <PID> -Force
```

### Problem: Virtual environment fails

**Fix:** Delete and recreate:
```powershell
Remove-Item -Recurse -Force .venv
.\bootstrap.ps1
```

### Problem: Script execution disabled

**Fix:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problem: Neo4j connection failed

**Fix:**
1. Make sure Neo4j is running
2. Check credentials in `backend/.env`
3. Neo4j is **optional** - the app works without it

### Problem: Ollama not connecting

**Fix:**
1. Install Ollama from https://ollama.ai/
2. Run `ollama serve` to start the server
3. Pull a model: `ollama pull llama3`

### Problem: BaseX won't start / Java not found

**Fix:**
1. Install Java 11+ from https://adoptium.net/
2. Verify Java is in PATH: `java -version`
3. If using custom Java location, set JAVA_HOME:
   ```powershell
   $env:JAVA_HOME = "C:\Program Files\Eclipse Adoptium\jdk-11"
   ```

### Problem: BaseX port conflict (8080)

**Fix:** Change the port in `.env` and start script:
```env
BASEX_PORT=8984
```
Or start BaseX on a different port:
```powershell
cd D:\BaseX\bin
.\basexhttp.bat -p 8984
```

---

## Reset Everything

Start fresh if something is broken:

```powershell
cd BIMTwinOps

# Stop services
.\stop-all.ps1

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
| **Start everything** | `.\start-all.ps1` |
| **Stop everything** | `.\stop-all.ps1` |
| **Start backend only** | `.\start-backend.ps1` |
| **Stop backend only** | `.\stop-backend.ps1` |
| **Start frontend only** | `.\start-frontend.ps1` |
| **Stop frontend only** | `.\stop-frontend.ps1` |
| **Run full setup** | `.\bootstrap.ps1` |
| **View API docs** | http://localhost:8008/docs |
| **Open app** | http://localhost:5173 |

---

## Next Steps

1. **Upload a point cloud**: Use the Point Cloud tab to upload `.npy` files
2. **Configure Neo4j** (optional): Add credentials to `backend/.env`
3. **Configure Ollama** (optional): For local AI features
4. **Try the AI chat**: Ask questions about your building data
