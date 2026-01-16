<#
.SYNOPSIS
  BIMTwinOps - One-time bootstrap script

.DESCRIPTION
  Sets up the development environment:
  1. Creates Python virtual environment (.venv)
  2. Installs Python dependencies
  3. Installs Node.js dependencies (frontend + APS service)
  4. Creates default .env files if missing

.EXAMPLE
  .\bootstrap.ps1
  .\bootstrap.ps1 -SkipFrontend
  .\bootstrap.ps1 -SkipBackend

.NOTES
  Run ONCE after cloning. Then use start-all.ps1 to run services.
  Requires: Python 3.10+, Node.js 18+
#>

Param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend
)

$ErrorActionPreference = 'Stop'

function Assert-Command($name, $hint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: Missing required command: $name" -ForegroundColor Red
    Write-Host $hint -ForegroundColor Yellow
    exit 1
  }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  BIMTwinOps Bootstrap (Windows)" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check prerequisites
Assert-Command python "Install Python 3.10+ from https://www.python.org/downloads/"
Assert-Command node "Install Node.js 18+ from https://nodejs.org/"
Assert-Command npm "Install Node.js 18+ from https://nodejs.org/"

$root = $PSScriptRoot

# ============================================================================
# [1/3] Backend Setup
# ============================================================================
if (-not $SkipBackend) {
  Write-Host "[1/3] Setting up Python backend..." -ForegroundColor Cyan
  
  $venvDir = [IO.Path]::Combine($root, '.venv')
  $venvActivate = [IO.Path]::Combine($venvDir, 'Scripts', 'Activate.ps1')
  $venvPython = [IO.Path]::Combine($venvDir, 'Scripts', 'python.exe')
  
  # Create venv if not exists
  if (-not (Test-Path $venvPython)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvDir
  } else {
    Write-Host "  Virtual environment exists" -ForegroundColor Green
  }
  
  # Activate and install
  & $venvActivate
  Write-Host "  Installing Python dependencies..." -ForegroundColor Yellow
  python -m pip install --upgrade pip --quiet
  
  # Install API requirements
  $apiReq = [IO.Path]::Combine($root, 'backend', 'api', 'requirements.txt')
  if (Test-Path $apiReq) {
    python -m pip install -r $apiReq --quiet
  }
  
  # Install PointNet requirements
  $pointnetReq = [IO.Path]::Combine($root, 'backend', 'pointnet_s3dis', 'requirements.txt')
  if (Test-Path $pointnetReq) {
    Write-Host "  Installing PointNet dependencies..." -ForegroundColor Yellow
    python -m pip install -r $pointnetReq --quiet
  }
  
  # Create backend .env if not exists
  $backendEnv = [IO.Path]::Combine($root, 'backend', '.env')
  if (-not (Test-Path $backendEnv)) {
    @"
# BIMTwinOps Backend Configuration
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# Neo4j (optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=

# Azure OpenAI (optional)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Ollama (optional)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
"@ | Out-File -FilePath $backendEnv -Encoding UTF8
    Write-Host "  Created backend/.env" -ForegroundColor Green
  }
  
  Write-Host "[OK] Backend setup complete" -ForegroundColor Green
  Write-Host ""
}

# ============================================================================
# [2/3] Frontend Setup
# ============================================================================
if (-not $SkipFrontend) {
  Write-Host "[2/3] Setting up Node.js frontend..." -ForegroundColor Cyan
  
  $frontendDir = [IO.Path]::Combine($root, 'pointcloud-frontend')
  Push-Location $frontendDir
  try {
    Write-Host "  Installing npm dependencies..." -ForegroundColor Yellow
    npm install --silent
    
    # Create .env if not exists
    $frontendEnv = [IO.Path]::Combine($frontendDir, '.env')
    if (-not (Test-Path $frontendEnv)) {
      @"
VITE_API_BASE_URL=http://localhost:8000
VITE_APS_SERVICE_URL=http://localhost:3001
"@ | Out-File -FilePath $frontendEnv -Encoding UTF8
      Write-Host "  Created pointcloud-frontend/.env" -ForegroundColor Green
    }
  } finally {
    Pop-Location
  }
  
  Write-Host "[OK] Frontend setup complete" -ForegroundColor Green
  Write-Host ""
}

# ============================================================================
# [3/3] APS Service Setup (optional)
# ============================================================================
$apsDir = [IO.Path]::Combine($root, 'backend', 'aps-service')
if ((Test-Path $apsDir) -and (-not $SkipFrontend)) {
  Write-Host "[3/3] Setting up APS service..." -ForegroundColor Cyan
  
  Push-Location $apsDir
  try {
    Write-Host "  Installing npm dependencies..." -ForegroundColor Yellow
    npm install --silent
    
    # Create .env if not exists
    $apsEnv = [IO.Path]::Combine($apsDir, '.env')
    if (-not (Test-Path $apsEnv)) {
      @"
APS_CLIENT_ID=your_autodesk_client_id
APS_CLIENT_SECRET=your_autodesk_client_secret
APS_SERVICE_PORT=3001
"@ | Out-File -FilePath $apsEnv -Encoding UTF8
      Write-Host "  Created aps-service/.env" -ForegroundColor Green
    }
  } finally {
    Pop-Location
  }
  
  Write-Host "[OK] APS service setup complete" -ForegroundColor Green
  Write-Host ""
}

# ============================================================================
# Done
# ============================================================================
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Bootstrap Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Edit backend/.env with your credentials (optional)" -ForegroundColor White
Write-Host "  2. Run: .\start-all.ps1" -ForegroundColor White
Write-Host ""
