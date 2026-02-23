<#
.SYNOPSIS
  Start all BIMTwinOps services

.DESCRIPTION
  Checks prerequisites, displays configuration, verifies external connections,
  and launches all services (Backend, Frontend, APS, BaseX)

.EXAMPLE
  .\start-all.ps1
  .\start-all.ps1 -SkipChecks

.NOTES
  Run bootstrap.ps1 first if this is a fresh clone
#>

Param(
  [switch]$SkipChecks
)

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

# node_modules (frontend)
$nodeModules = [IO.Path]::Combine($root, 'pointcloud-frontend', 'node_modules')
if (Test-Path $nodeModules) {
  Write-Host "[OK] Frontend node_modules: Found" -ForegroundColor Green
} else {
  Write-Host "[!] Frontend node_modules: Not found (will be installed)" -ForegroundColor Yellow
}

# node_modules (APS service)
$apsNodeModules = [IO.Path]::Combine($root, 'backend', 'aps-service', 'node_modules')
if (Test-Path $apsNodeModules) {
  Write-Host "[OK] APS node_modules: Found" -ForegroundColor Green
} else {
  Write-Host "[!] APS node_modules: Not found (will be installed)" -ForegroundColor Yellow
}

# ============================================================================
# Configuration Display
# ============================================================================
Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Cyan

$backendEnv = [IO.Path]::Combine($root, 'backend', '.env')
$frontendEnv = [IO.Path]::Combine($root, 'pointcloud-frontend', '.env')

$backendHost = "127.0.0.1"
$backendPort = "8008"
$frontendPort = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { "5173" }
$apsPort = "3001"
$neo4jUri = ""
$neo4jUser = ""
$ollamaUrl = ""
$azureEndpoint = ""

if (Test-Path $backendEnv) {
  $content = Get-Content $backendEnv -Raw
  if ($content -match "BACKEND_HOST\s*=\s*([^\s\r\n]+)") { $backendHost = $Matches[1] }
  if ($content -match "BACKEND_PORT\s*=\s*(\d+)") { $backendPort = $Matches[1] }
  if ($content -match "APS_SERVICE_PORT\s*=\s*(\d+)") { $apsPort = $Matches[1] }
  if ($content -match "NEO4J_URI\s*=\s*([^\s\r\n]+)") { $neo4jUri = $Matches[1] }
  if ($content -match "NEO4J_USER\s*=\s*([^\s\r\n]+)") { $neo4jUser = $Matches[1] }
  if ($content -match "OLLAMA_BASE_URL\s*=\s*([^\s\r\n]+)") { $ollamaUrl = $Matches[1] }
  if ($content -match "AZURE_OPENAI_ENDPOINT\s*=\s*([^\s\r\n]+)") { $azureEndpoint = $Matches[1] }
}

Write-Host "  Backend:       http://${backendHost}:${backendPort}" -ForegroundColor White
Write-Host "  Frontend:      http://localhost:${frontendPort}" -ForegroundColor White
Write-Host "  APS Service:   http://localhost:${apsPort}" -ForegroundColor White

# ============================================================================
# External Service Connection Checks
# ============================================================================
if (-not $SkipChecks) {
  Write-Host ""
  Write-Host "--- External Service Checks ---" -ForegroundColor Cyan

  # Neo4j Check
  if ($neo4jUri -and $neo4jUri -ne "") {
    Write-Host "  Neo4j URI: $neo4jUri" -ForegroundColor White
    try {
      if ($neo4jUri -match "bolt://([^:]+):(\d+)") {
        $neo4jHost = $Matches[1]
        $neo4jPort = [int]$Matches[2]
        $tcpTest = Test-NetConnection -ComputerName $neo4jHost -Port $neo4jPort -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($tcpTest.TcpTestSucceeded) {
          Write-Host "[OK] Neo4j: Connected (${neo4jHost}:${neo4jPort})" -ForegroundColor Green
        } else {
          Write-Host "[X] Neo4j: Connection FAILED - Is Neo4j running?" -ForegroundColor Red
          Write-Host "    Start Neo4j Desktop or run: neo4j console" -ForegroundColor Yellow
        }
      }
    } catch {
      Write-Host "[!] Neo4j: Could not verify connection" -ForegroundColor Yellow
    }
  } else {
    Write-Host "[--] Neo4j: Not configured (Knowledge Graph unavailable)" -ForegroundColor Gray
  }

  # Ollama Check
  if ($ollamaUrl -and $ollamaUrl -ne "") {
    Write-Host "  Ollama URL: $ollamaUrl" -ForegroundColor White
    try {
      $ollamaResp = Invoke-WebRequest -Uri "$ollamaUrl/api/tags" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
      if ($ollamaResp.StatusCode -eq 200) {
        $models = ($ollamaResp.Content | ConvertFrom-Json).models
        $modelCount = if ($models) { $models.Count } else { 0 }
        Write-Host "[OK] Ollama: Connected ($modelCount models available)" -ForegroundColor Green
      }
    } catch {
      Write-Host "[X] Ollama: Not running or unreachable" -ForegroundColor Red
      Write-Host "    Start Ollama: ollama serve" -ForegroundColor Yellow
    }
  } else {
    Write-Host "[--] Ollama: Not configured (local LLM unavailable)" -ForegroundColor Gray
  }

  # Azure OpenAI Check
  if ($azureEndpoint -and $azureEndpoint -ne "") {
    Write-Host "  Azure OpenAI: $azureEndpoint" -ForegroundColor White
    Write-Host "[OK] Azure OpenAI: Configured (auth verified on first request)" -ForegroundColor Green
  } else {
    Write-Host "[--] Azure OpenAI: Not configured (cloud LLM unavailable)" -ForegroundColor Gray
  }

  # BaseX Check (optional)
  $basexPort = 8984
  try {
    $basexResp = Invoke-WebRequest -Uri "http://localhost:$basexPort" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    Write-Host "[OK] BaseX: Running on port $basexPort" -ForegroundColor Green
  } catch {
    Write-Host "[--] BaseX: Not running (will attempt to start)" -ForegroundColor Gray
  }
}

# ============================================================================
# Port Availability Check
# ============================================================================
Write-Host ""
Write-Host "--- Port Check ---" -ForegroundColor Cyan

$backendPortNum = [int]$backendPort
$frontendPortNum = [int]$frontendPort
$apsPortNum = [int]$apsPort

# Check and free backend port
$backendInUse = Get-NetTCPConnection -LocalPort $backendPortNum -State Listen -ErrorAction SilentlyContinue
if ($backendInUse) {
  Write-Host "[!] Port ${backendPort}: IN USE - will stop existing process" -ForegroundColor Yellow
  Stop-Process -Id $backendInUse.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
Write-Host "[OK] Port ${backendPort}: Ready (Backend)" -ForegroundColor Green

# Check and free frontend port
$frontendInUse = Get-NetTCPConnection -LocalPort $frontendPortNum -State Listen -ErrorAction SilentlyContinue
if ($frontendInUse) {
  Write-Host "[!] Port ${frontendPort}: IN USE - will stop existing process" -ForegroundColor Yellow
  Stop-Process -Id $frontendInUse.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
Write-Host "[OK] Port ${frontendPort}: Ready (Frontend)" -ForegroundColor Green

# Check and free APS port
$apsInUse = Get-NetTCPConnection -LocalPort $apsPortNum -State Listen -ErrorAction SilentlyContinue
if ($apsInUse) {
  Write-Host "[!] Port ${apsPort}: IN USE - will stop existing process" -ForegroundColor Yellow
  Stop-Process -Id $apsInUse.OwningProcess -Force -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 1
}
Write-Host "[OK] Port ${apsPort}: Ready (APS Service)" -ForegroundColor Green

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

# Start APS service in new window
Write-Host "Starting APS Service..." -ForegroundColor Yellow
$apsScript = [IO.Path]::Combine($root, 'start-aps.ps1')
if (Test-Path $apsScript) {
  Start-Process powershell -ArgumentList "-NoExit", "-File", $apsScript, "-SkipChecks"
  Start-Sleep -Seconds 3
  
  # Verify APS started
  try {
    $apsResp = Invoke-WebRequest -Uri "http://localhost:${apsPort}/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($apsResp.StatusCode -eq 200) {
      Write-Host "[OK] APS Service: Running" -ForegroundColor Green
    }
  } catch {
    Write-Host "[!] APS Service: May still be starting..." -ForegroundColor Yellow
  }
} else {
  Write-Host "[!] APS start script not found at $apsScript" -ForegroundColor Yellow
}

# Start BaseX (optional)
Write-Host "Starting BaseX Server..." -ForegroundColor Yellow
$basexScript = [IO.Path]::Combine($root, 'scripts', 'start-basex.ps1')
if (Test-Path $basexScript) {
  Start-Process powershell -ArgumentList "-File", $basexScript
} else {
  Write-Host "[--] BaseX start script not found (optional)" -ForegroundColor Gray
}

# Start frontend in new window
Write-Host "Starting Frontend Server..." -ForegroundColor Yellow
$frontendScript = [IO.Path]::Combine($root, 'start-frontend.ps1')
Start-Process powershell -ArgumentList "-NoExit", "-File", $frontendScript, "-SkipChecks"

Start-Sleep -Seconds 3

# Final verification
Write-Host ""
Write-Host "--- Final Verification ---" -ForegroundColor Cyan

# Verify all services
$allOk = $true

try {
  $backendCheck = Invoke-WebRequest -Uri "http://${backendHost}:${backendPort}/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
  if ($backendCheck.StatusCode -eq 200) {
    Write-Host "[OK] Backend API: http://${backendHost}:${backendPort}" -ForegroundColor Green
  }
} catch {
  Write-Host "[X] Backend API: Not responding" -ForegroundColor Red
  $allOk = $false
}

try {
  $apsCheck = Invoke-WebRequest -Uri "http://localhost:${apsPort}/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
  if ($apsCheck.StatusCode -eq 200) {
    Write-Host "[OK] APS Service: http://localhost:${apsPort}" -ForegroundColor Green
  }
} catch {
  Write-Host "[!] APS Service: Not responding (ACC/Forge features unavailable)" -ForegroundColor Yellow
}

try {
  $frontendCheck = Invoke-WebRequest -Uri "http://localhost:${frontendPort}" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
  if ($frontendCheck.StatusCode -eq 200) {
    Write-Host "[OK] Frontend: http://localhost:${frontendPort}" -ForegroundColor Green
  }
} catch {
  Write-Host "[!] Frontend: May still be compiling..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Services Started!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend API:   http://${backendHost}:${backendPort}" -ForegroundColor Cyan
Write-Host "  API Docs:      http://${backendHost}:${backendPort}/docs" -ForegroundColor Cyan
Write-Host "  GraphQL:       http://${backendHost}:${backendPort}/api/graphql" -ForegroundColor Cyan
Write-Host "  APS Service:   http://localhost:${apsPort}" -ForegroundColor Cyan
Write-Host "  BaseX (opt):   http://localhost:8984/dba" -ForegroundColor Gray
Write-Host "  Frontend:      http://localhost:${frontendPort}" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Stop all: .\stop-all.ps1" -ForegroundColor Yellow
Write-Host ""
