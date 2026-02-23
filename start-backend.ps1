<#
.SYNOPSIS
  Start BIMTwinOps Python backend server

.DESCRIPTION
  Activates virtual environment, checks connections, and starts FastAPI/Uvicorn

.EXAMPLE
  .\start-backend.ps1
  .\start-backend.ps1 -Reload
  .\start-backend.ps1 -SkipChecks

.NOTES
  Run bootstrap.ps1 first if .venv doesn't exist
#>

Param(
  [switch]$Reload,
  [switch]$SkipChecks
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BIMTwinOps Backend Server" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "[X] Python: NOT FOUND" -ForegroundColor Red
  exit 1
}
$pyVersion = python --version 2>&1
Write-Host "[OK] Python: $pyVersion" -ForegroundColor Green

# Paths
$venvDir = [IO.Path]::Combine($root, '.venv')
$venvActivate = [IO.Path]::Combine($venvDir, 'Scripts', 'Activate.ps1')
$venvPython = [IO.Path]::Combine($venvDir, 'Scripts', 'python.exe')
$backendDir = [IO.Path]::Combine($root, 'backend')
$envFile = [IO.Path]::Combine($backendDir, '.env')

# Check venv
if (-not (Test-Path $venvPython)) {
  Write-Host "[!] Virtual environment not found. Running bootstrap..." -ForegroundColor Yellow
  & "$root\bootstrap.ps1"
}
Write-Host "[OK] Virtual Environment: .venv" -ForegroundColor Green

# Activate venv
& $venvActivate

# Navigate to backend
Set-Location $backendDir

# ============================================================================
# Read Configuration from .env
# ============================================================================
Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Cyan

$bindHost = "127.0.0.1"
$port = 8008
$neo4jUri = ""
$neo4jUser = ""
$ollamaUrl = ""
$azureEndpoint = ""

if (Test-Path $envFile) {
  Write-Host "[OK] .env file: Found" -ForegroundColor Green
  $content = Get-Content $envFile -Raw
  
  if ($content -match "BACKEND_HOST\s*=\s*([^\s\r\n]+)") { $bindHost = $Matches[1] }
  if ($content -match "BACKEND_PORT\s*=\s*(\d+)") { $port = $Matches[1] }
  if ($content -match "NEO4J_URI\s*=\s*([^\s\r\n]+)") { $neo4jUri = $Matches[1] }
  if ($content -match "NEO4J_USER\s*=\s*([^\s\r\n]+)") { $neo4jUser = $Matches[1] }
  if ($content -match "OLLAMA_BASE_URL\s*=\s*([^\s\r\n]+)") { $ollamaUrl = $Matches[1] }
  if ($content -match "AZURE_OPENAI_ENDPOINT\s*=\s*([^\s\r\n]+)") { $azureEndpoint = $Matches[1] }
} else {
  Write-Host "[!] .env file: Not found (using defaults)" -ForegroundColor Yellow
}

Write-Host "     Backend Host: $bindHost" -ForegroundColor White
Write-Host "     Backend Port: $port" -ForegroundColor White

# ============================================================================
# Connection Checks
# ============================================================================
if (-not $SkipChecks) {
  Write-Host ""
  Write-Host "--- Connection Checks ---" -ForegroundColor Cyan
  
  # Check if port is available
  $portInUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  if ($portInUse) {
    Write-Host "[X] Port ${port}: IN USE (PID: $($portInUse.OwningProcess))" -ForegroundColor Red
    Write-Host "    Run .\stop-backend.ps1 first or change BACKEND_PORT in .env" -ForegroundColor Yellow
    exit 1
  } else {
    Write-Host "[OK] Port ${port}: Available" -ForegroundColor Green
  }
  
  # Check Neo4j connection
  if ($neo4jUri -and $neo4jUri -ne "") {
    Write-Host "     Neo4j URI: $neo4jUri" -ForegroundColor White
    try {
      # Extract host and port from URI
      if ($neo4jUri -match "bolt://([^:]+):(\d+)") {
        $neo4jHost = $Matches[1]
        $neo4jPort = [int]$Matches[2]
        $tcpTest = Test-NetConnection -ComputerName $neo4jHost -Port $neo4jPort -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
        if ($tcpTest.TcpTestSucceeded) {
          Write-Host "[OK] Neo4j: Connected ($neo4jHost`:$neo4jPort)" -ForegroundColor Green
        } else {
          Write-Host "[X] Neo4j: Not reachable — attempting auto-start..." -ForegroundColor Yellow
          $neo4jSvc = Get-Service -Name "Neo4j*" -ErrorAction SilentlyContinue | Select-Object -First 1
          if ($neo4jSvc) {
            if ($neo4jSvc.Status -ne 'Running') {
              try { Start-Service -Name $neo4jSvc.Name -ErrorAction Stop; Start-Sleep -Seconds 5; Write-Host "[OK] Neo4j service started" -ForegroundColor Green }
              catch { Write-Host "[!] Could not start Neo4j service: $_" -ForegroundColor Yellow }
            }
          } else {
            $neo4jPaths = @(
              "$env:ProgramFiles\Neo4j Desktop\Neo4j Desktop.exe",
              "$env:LOCALAPPDATA\Programs\neo4j-desktop\Neo4j Desktop.exe",
              "$env:ProgramFiles\Neo4j\bin\neo4j.bat"
            )
            $found = $false
            foreach ($p in $neo4jPaths) {
              if (Test-Path $p) { Start-Process $p; Start-Sleep -Seconds 8; $found = $true; break }
            }
            if (-not $found) {
              Write-Host "[!] Neo4j not found. Start Neo4j Desktop manually." -ForegroundColor Red
            }
          }
        }
      }
    } catch {
      Write-Host "[!] Neo4j: Could not verify connection" -ForegroundColor Yellow
    }
  } else {
    Write-Host "[--] Neo4j: Not configured (optional)" -ForegroundColor Gray
  }
  
  # Check Ollama connection
  if ($ollamaUrl -and $ollamaUrl -ne "") {
    Write-Host "     Ollama URL: $ollamaUrl" -ForegroundColor White
    try {
      $ollamaResp = Invoke-WebRequest -Uri "$ollamaUrl/api/tags" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
      if ($ollamaResp.StatusCode -eq 200) {
        Write-Host "[OK] Ollama: Connected" -ForegroundColor Green
      } else {
        Write-Host "[X] Ollama: Connection FAILED" -ForegroundColor Red
      }
    } catch {
      Write-Host "[X] Ollama: Not running or unreachable" -ForegroundColor Red
    }
  } else {
    Write-Host "[--] Ollama: Not configured (optional)" -ForegroundColor Gray
  }
  
  # Check Azure OpenAI
  if ($azureEndpoint -and $azureEndpoint -ne "") {
    Write-Host "     Azure OpenAI: $azureEndpoint" -ForegroundColor White
    Write-Host "[OK] Azure OpenAI: Configured (will verify on first request)" -ForegroundColor Green
  } else {
    Write-Host "[--] Azure OpenAI: Not configured (optional)" -ForegroundColor Gray
  }
}

# Build command
$reloadFlag = ""
if ($Reload) {
  $reloadFlag = "--reload"
  Write-Host ""
  Write-Host "[!] Hot-reload enabled" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting FastAPI Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  API URL:  http://${bindHost}:${port}" -ForegroundColor White
Write-Host "  Docs:     http://${bindHost}:${port}/docs" -ForegroundColor White
Write-Host "  GraphQL:  http://${bindHost}:${port}/api/graphql" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""


# Run uvicorn with correct reload flag handling
if ($Reload) {
  python -m uvicorn api.main:app --host $bindHost --port $port --reload
} else {
  python -m uvicorn api.main:app --host $bindHost --port $port
}
