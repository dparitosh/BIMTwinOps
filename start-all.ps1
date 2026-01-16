<#
.SYNOPSIS
  Start all BIMTwinOps services

.DESCRIPTION
  Checks prerequisites, displays configuration, and launches services

.EXAMPLE
  .\start-all.ps1

.NOTES
  Run bootstrap.ps1 first if this is a fresh clone
#>

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BIMTwinOps - Starting All Services" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# ============================================================================
# Prerequisites Check
# ============================================================================
Write-Host "--- Prerequisites ---" -ForegroundColor Cyan

# Python
if (Get-Command python -ErrorAction SilentlyContinue) {
  $pyVersion = python --version 2>&1
  Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green
} else {
  Write-Host "[X] Python: NOT FOUND" -ForegroundColor Red
  exit 1
}

# Node
if (Get-Command node -ErrorAction SilentlyContinue) {
  $nodeVersion = node --version
  Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green
} else {
  Write-Host "[X] Node.js: NOT FOUND" -ForegroundColor Red
  exit 1
}

# Virtual environment
$venvPython = [IO.Path]::Combine($root, '.venv', 'Scripts', 'python.exe')
if (Test-Path $venvPython) {
  Write-Host "[OK] Virtual Environment: .venv" -ForegroundColor Green
} else {
  Write-Host "[!] Virtual Environment: Not found (will be created)" -ForegroundColor Yellow
}

# node_modules
$nodeModules = [IO.Path]::Combine($root, 'pointcloud-frontend', 'node_modules')
if (Test-Path $nodeModules) {
  Write-Host "[OK] node_modules: Found" -ForegroundColor Green
} else {
  Write-Host "[!] node_modules: Not found (will be installed)" -ForegroundColor Yellow
}

# ============================================================================
# Configuration Display
# ============================================================================
Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Cyan

$backendEnv = [IO.Path]::Combine($root, 'backend', '.env')
$frontendEnv = [IO.Path]::Combine($root, 'pointcloud-frontend', '.env')

$backendHost = "127.0.0.1"
$backendPort = "8000"
$neo4jUri = "(not configured)"
$ollamaUrl = "(not configured)"
$azureEndpoint = "(not configured)"

if (Test-Path $backendEnv) {
  $content = Get-Content $backendEnv -Raw
  if ($content -match "BACKEND_HOST\s*=\s*([^\s\r\n]+)") { $backendHost = $Matches[1] }
  if ($content -match "BACKEND_PORT\s*=\s*(\d+)") { $backendPort = $Matches[1] }
  if ($content -match "NEO4J_URI\s*=\s*([^\s\r\n]+)") { $neo4jUri = $Matches[1] }
  if ($content -match "OLLAMA_BASE_URL\s*=\s*([^\s\r\n]+)") { $ollamaUrl = $Matches[1] }
  if ($content -match "AZURE_OPENAI_ENDPOINT\s*=\s*([^\s\r\n]+)") { $azureEndpoint = $Matches[1] }
}

Write-Host "  Backend:       http://${backendHost}:${backendPort}" -ForegroundColor White
Write-Host "  Frontend:      http://localhost:5173" -ForegroundColor White
Write-Host "  Neo4j:         $neo4jUri" -ForegroundColor Gray
Write-Host "  Ollama:        $ollamaUrl" -ForegroundColor Gray
Write-Host "  Azure OpenAI:  $azureEndpoint" -ForegroundColor Gray

# ============================================================================
# Port Availability Check
# ============================================================================
Write-Host ""
Write-Host "--- Port Check ---" -ForegroundColor Cyan

$backendPortNum = [int]$backendPort
$backendInUse = Get-NetTCPConnection -LocalPort $backendPortNum -State Listen -ErrorAction SilentlyContinue
if ($backendInUse) {
  Write-Host "[!] Port $backendPort: IN USE - will stop existing process" -ForegroundColor Yellow
  Stop-Process -Id $backendInUse.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
Write-Host "[OK] Port $backendPort: Ready" -ForegroundColor Green

$frontendInUse = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($frontendInUse) {
  Write-Host "[!] Port 5173: IN USE - will stop existing process" -ForegroundColor Yellow
  Stop-Process -Id $frontendInUse.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
Write-Host "[OK] Port 5173: Ready" -ForegroundColor Green

# ============================================================================
# Start Services
# ============================================================================
Write-Host ""
Write-Host "--- Starting Services ---" -ForegroundColor Cyan

# Start backend in new window
Write-Host "Starting Backend Server..." -ForegroundColor Yellow
$backendScript = [IO.Path]::Combine($root, 'start-backend.ps1')
Start-Process powershell -ArgumentList "-NoExit", "-File", $backendScript, "-SkipChecks"

# Wait for backend to initialize
Write-Host "Waiting for backend to start (5s)..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# Verify backend started
try {
  $healthResp = Invoke-WebRequest -Uri "http://${backendHost}:${backendPort}/health" -Method GET -TimeoutSec 5 -ErrorAction SilentlyContinue
  if ($healthResp.StatusCode -eq 200) {
    Write-Host "[OK] Backend: Running" -ForegroundColor Green
  }
} catch {
  Write-Host "[!] Backend: May still be starting..." -ForegroundColor Yellow
}

# Start frontend in new window
Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
$frontendScript = [IO.Path]::Combine($root, 'start-frontend.ps1')
Start-Process powershell -ArgumentList "-NoExit", "-File", $frontendScript, "-SkipChecks"

Start-Sleep -Seconds 2

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API: http://${backendHost}:${backendPort}" -ForegroundColor Cyan
Write-Host "  API Docs:    http://${backendHost}:${backendPort}/docs" -ForegroundColor Cyan
Write-Host "  Frontend:    http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Stop all: .\stop-all.ps1" -ForegroundColor Yellow
Write-Host ""
