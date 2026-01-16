<#
.SYNOPSIS
  BIMTwinOps bootstrap script - One-time setup

.DESCRIPTION
  This script:
  1. Creates Python virtual environment
  2. Installs Python dependencies
  3. Installs Node.js dependencies (frontend + APS service)
  4. Creates default .env files

.EXAMPLE
  .\bootstrap.ps1
  .\bootstrap.ps1 -SkipFrontend
  .\bootstrap.ps1 -RunDiagnostics

.NOTES
  Run this ONCE after cloning. Then use start-all.ps1 to run services.
#>

Param(
  [switch]$SkipFrontend,
  [switch]$SkipBackend,
  [switch]$RunDiagnostics
)

$ErrorActionPreference = 'Stop'

function Assert-Command($name, $hint) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    Write-Host "Missing required command: $name" -ForegroundColor Red
    Write-Host $hint -ForegroundColor Yellow
    exit 1
  }
}

Write-Host "BIMTwinOps bootstrap (Windows)" -ForegroundColor Green
Write-Host ""

Assert-Command python "Install Python 3.10+ and ensure it's on PATH."
Assert-Command node "Install Node.js 18+ (includes npm)."
Assert-Command npm "Install Node.js 18+ (includes npm)."

$root = $PSScriptRoot

# ============================================================================
# Backend Setup
# ============================================================================
if (-not $SkipBackend) {
  Write-Host "[1/3] Backend: venv + dependencies" -ForegroundColor Cyan
  
  $backendDir = [IO.Path]::Combine($root, 'backend')
  $venvDir = [IO.Path]::Combine($root, '.venv')
  $venvActivate = [IO.Path]::Combine($venvDir, 'Scripts', 'Activate.ps1')
  $venvPython = [IO.Path]::Combine($venvDir, 'Scripts', 'python.exe')
  
  # Create venv if not exists
  if (-not (Test-Path $venvPython)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv $venvDir
  }
  
  # Activate venv
  & $venvActivate
  
  # Upgrade pip and install dependencies
  Write-Host "Installing Python dependencies..." -ForegroundColor Yellow
  python -m pip install --upgrade pip
  
  $apiReq = [IO.Path]::Combine($backendDir, 'api', 'requirements.txt')
  if (Test-Path $apiReq) {
    python -m pip install -r $apiReq
  }
  
  $pointnetReq = [IO.Path]::Combine($backendDir, 'pointnet_s3dis', 'requirements.txt')
  if (Test-Path $pointnetReq) {
    Write-Host "Installing PointNet dependencies..." -ForegroundColor Yellow
    python -m pip install -r $pointnetReq
  }
  
  # Create backend .env if not exists
  $backendEnv = [IO.Path]::Combine($backendDir, '.env')
  $backendEnvExample = [IO.Path]::Combine($backendDir, '.env.example')
  if (-not (Test-Path $backendEnv)) {
    if (Test-Path $backendEnvExample) {
      Copy-Item $backendEnvExample $backendEnv
      Write-Host "Created backend/.env from example" -ForegroundColor Green
    } else {
      @"
# Backend Configuration
BACKEND_HOST=127.0.0.1
BACKEND_PORT=8000

# Neo4j (optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# Azure OpenAI (optional)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_API_KEY=
AZURE_OPENAI_DEPLOYMENT=
"@ | Out-File -FilePath $backendEnv -Encoding UTF8
      Write-Host "Created backend/.env with defaults" -ForegroundColor Green
    }
  }
  
  Write-Host "[OK] Backend setup complete" -ForegroundColor Green
}

# ============================================================================
# Frontend Setup
# ============================================================================
if (-not $SkipFrontend) {
  Write-Host "[2/3] Frontend: npm install" -ForegroundColor Cyan
  
  # Frontend
  $frontendDir = [IO.Path]::Combine($root, 'pointcloud-frontend')
  Push-Location $frontendDir
  try {
    npm install
    
    # Create .env if not exists
    $frontendEnv = [IO.Path]::Combine($frontendDir, '.env')
    if (-not (Test-Path $frontendEnv)) {
      @"
VITE_API_BASE_URL=http://localhost:8000
VITE_APS_SERVICE_URL=http://localhost:3001
"@ | Out-File -FilePath $frontendEnv -Encoding UTF8
      Write-Host "Created pointcloud-frontend/.env" -ForegroundColor Green
    }
  } finally {
    Pop-Location
  }
  
  # APS Service
  $apsDir = [IO.Path]::Combine($root, 'backend', 'aps-service')
  if (Test-Path $apsDir) {
    Write-Host "Installing APS service dependencies..." -ForegroundColor Yellow
    Push-Location $apsDir
    try {
      npm install
      
      # Create .env if not exists
      $apsEnv = [IO.Path]::Combine($apsDir, '.env')
      $apsEnvExample = [IO.Path]::Combine($apsDir, '.env.example')
      if (-not (Test-Path $apsEnv)) {
        if (Test-Path $apsEnvExample) {
          Copy-Item $apsEnvExample $apsEnv
          Write-Host "Created aps-service/.env from example" -ForegroundColor Green
        } else {
          @"
APS_CLIENT_ID=your_client_id
APS_CLIENT_SECRET=your_client_secret
APS_SERVICE_PORT=3001
"@ | Out-File -FilePath $apsEnv -Encoding UTF8
          Write-Host "Created aps-service/.env with defaults" -ForegroundColor Green
        }
      }
    } finally {
      Pop-Location
    }
  }
  
  Write-Host "[OK] Frontend setup complete" -ForegroundColor Green
}

# ============================================================================
# Diagnostics (optional)
# ============================================================================
if ($RunDiagnostics) {
  Write-Host "[3/3] Running diagnostics..." -ForegroundColor Cyan
  
  $diagScript = [IO.Path]::Combine($root, 'diagnostics', 'diagnose-all.ps1')
  if (Test-Path $diagScript) {
    & $diagScript
  } else {
    Write-Host "Diagnostics script not found" -ForegroundColor Yellow
  }
}

# ============================================================================
# Done
# ============================================================================
Write-Host ""
Write-Host "Bootstrap complete." -ForegroundColor Green
Write-Host "Next: .\start-all.ps1" -ForegroundColor Cyan
