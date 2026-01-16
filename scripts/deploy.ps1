<#
.SYNOPSIS
  SMART_BIM Deploy Script - Starts all services and validates endpoints (verbose mode)

.DESCRIPTION
  This script:
  1. Checks that setup was completed
  2. Reads configuration from .env files
  3. Starts Backend API (FastAPI/Uvicorn)
  4. Starts APS Service (Node.js)
  5. Starts Frontend (Vite)
  6. Validates all endpoints are responding
  7. Opens the browser

.EXAMPLE
  .\scripts\deploy.ps1
  .\scripts\deploy.ps1 -SkipBrowser
  .\scripts\deploy.ps1 -ApiOnly

.NOTES
  Run setup.ps1 first if this is a fresh clone.
#>

param(
  [switch]$ApiOnly,
  [switch]$FrontendOnly,
  [switch]$SkipBrowser,
  [switch]$Dev  # Enable hot-reload for API
)

$ErrorActionPreference = 'Continue'  # Don't stop on non-fatal errors
$ProgressPreference = 'Continue'

# Colors for output
function Write-Header($msg) {
  Write-Host ""
  Write-Host ("=" * 70) -ForegroundColor Cyan
  Write-Host "  $msg" -ForegroundColor Cyan
  Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step($msg) {
  Write-Host ""
  Write-Host "[STEP] $msg" -ForegroundColor Yellow
  Write-Host ("-" * 50) -ForegroundColor DarkGray
}

function Write-Success($msg) {
  Write-Host "[OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
  Write-Host "[FAIL] $msg" -ForegroundColor Red
}

function Write-Info($msg) {
  Write-Host "[INFO] $msg" -ForegroundColor Gray
}

function Write-Warn($msg) {
  Write-Host "[WARN] $msg" -ForegroundColor DarkYellow
}

function Write-Running($msg) {
  Write-Host "[RUN] $msg" -ForegroundColor Magenta
}

# Get repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Split-Path -Parent $scriptDir

# PID directory for tracking processes
# Use string concatenation to avoid Join-Path issues with dotfiles in PS 5.1
$pidDir = "$repoRoot\.pids"
if (-not (Test-Path $pidDir)) {
  New-Item -ItemType Directory -Path $pidDir -Force | Out-Null
}

Write-Header "SMART_BIM Deploy Script"
Write-Host "Repository: $repoRoot"
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"

# ============================================================================
# Helper Functions
# ============================================================================

function Get-EnvValue($envPath, $key) {
  if (-not (Test-Path $envPath)) { return $null }
  $content = Get-Content $envPath -Raw
  foreach ($line in $content -split "`n") {
    $line = $line.Trim()
    if ($line -match "^$key\s*=\s*(.*)$") {
      $val = $Matches[1].Trim()
      # Remove quotes
      if ($val.StartsWith('"') -and $val.EndsWith('"')) { $val = $val.Substring(1, $val.Length - 2) }
      if ($val.StartsWith("'") -and $val.EndsWith("'")) { $val = $val.Substring(1, $val.Length - 2) }
      return $val
    }
  }
  return $null
}

function Test-PortInUse($port) {
  $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
  return ($null -ne $conn)
}

function Wait-ForEndpoint($url, $timeoutSec = 30, $description = "endpoint") {
  Write-Info "Waiting for $description at $url ..."
  $elapsed = 0
  $interval = 2
  
  while ($elapsed -lt $timeoutSec) {
    try {
      $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 5 -ErrorAction Stop
      if ($response.StatusCode -eq 200) {
        Write-Success "$description is UP (HTTP $($response.StatusCode))"
        return $true
      }
    } catch {
      # Still waiting
    }
    Write-Host "  ... waiting ($elapsed/$timeoutSec sec)" -ForegroundColor DarkGray
    Start-Sleep -Seconds $interval
    $elapsed += $interval
  }
  
  Write-Fail "$description did not respond within $timeoutSec seconds"
  return $false
}

function Stop-ExistingProcess($name, $pidFile) {
  if (Test-Path $pidFile) {
    $processId = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($processId) {
      $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
      if ($proc) {
        Write-Info "Stopping existing $name (PID: $processId)..."
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 500
      }
    }
    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
  }
}

function Start-ServiceProcess($name, $workingDir, $command, $pidFile, $logFile, $errFile) {
  Write-Running "Starting $name..."
  Write-Info "  Working dir: $workingDir"
  Write-Info "  Command: $command"
  
  # Stop existing if running
  Stop-ExistingProcess $name $pidFile
  
  Push-Location $workingDir
  try {
    $proc = Start-Process -FilePath "cmd.exe" `
      -ArgumentList "/c", $command `
      -WindowStyle Hidden `
      -RedirectStandardOutput $logFile `
      -RedirectStandardError $errFile `
      -PassThru
    
    Set-Content -Path $pidFile -Value $proc.Id
    Write-Info "  PID: $($proc.Id)"
    Write-Info "  Logs: $logFile"
    Write-Info "  Errors: $errFile"
    
    # Wait a moment and check if it's still running
    Start-Sleep -Seconds 2
    
    $check = Get-Process -Id $proc.Id -ErrorAction SilentlyContinue
    if ($check) {
      Write-Success "$name started (PID: $($proc.Id))"
      return $proc.Id
    } else {
      Write-Fail "$name exited immediately!"
      if (Test-Path $errFile) {
        Write-Host ""
        Write-Host "=== Error Log (last 20 lines) ===" -ForegroundColor Red
        Get-Content $errFile -Tail 20 | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
      }
      return $null
    }
  } finally {
    Pop-Location
  }
}

# ============================================================================
# STEP 1: Pre-flight Checks
# ============================================================================
Write-Step "Pre-flight Checks"

# Check venv exists (use string concat for PS 5.1 compatibility with dotfiles)
$venvPython = "$repoRoot\.venv\Scripts\python.exe"
if (Test-Path $venvPython) {
  $pyVer = & $venvPython --version 2>&1
  Write-Success "Python venv: $pyVer"
} else {
  Write-Fail "Python venv not found at: $venvPython"
  Write-Host ""
  Write-Host "Setup has not been run yet. Running setup.ps1 now..." -ForegroundColor Yellow
  Write-Host ""
  
  $setupScript = Join-Path $scriptDir 'setup.ps1'
  if (Test-Path $setupScript) {
    & $setupScript
    if ($LASTEXITCODE -ne 0) {
      Write-Fail "Setup failed! Check errors above."
      exit 1
    }
    # Re-check venv after setup
    if (-not (Test-Path $venvPython)) {
      Write-Fail "Setup completed but venv still not found!"
      exit 1
    }
    $pyVer = & $venvPython --version 2>&1
    Write-Success "Python venv ready: $pyVer"
  } else {
    Write-Fail "setup.ps1 not found at: $setupScript"
    exit 1
  }
}

# Check .env files
$backendEnv = "$repoRoot\backend\.env"
$apsEnv = "$repoRoot\backend\aps-service\.env"
$frontendEnv = "$repoRoot\pointcloud-frontend\.env"

if (Test-Path $backendEnv) {
  Write-Success "Backend .env exists"
} else {
  Write-Fail "Backend .env missing - run setup.ps1"
  exit 1
}

# Read configuration
Write-Info "Reading configuration..."
$backendHost = Get-EnvValue $backendEnv 'BACKEND_HOST'
if (-not $backendHost) { $backendHost = '127.0.0.1' }

$backendPort = Get-EnvValue $backendEnv 'BACKEND_PORT'
if (-not $backendPort) { $backendPort = '8000' }

$apsPort = Get-EnvValue $apsEnv 'APS_SERVICE_PORT'
if (-not $apsPort) { $apsPort = Get-EnvValue $backendEnv 'APS_SERVICE_PORT' }
if (-not $apsPort) { $apsPort = '3001' }

$frontendPort = '5173'  # Vite default

Write-Info "Configuration:"
Write-Host "  Backend API:  http://${backendHost}:${backendPort}" -ForegroundColor White
Write-Host "  APS Service:  http://127.0.0.1:${apsPort}" -ForegroundColor White
Write-Host "  Frontend:     http://localhost:${frontendPort}" -ForegroundColor White

# Check for port conflicts
Write-Info "Checking for port conflicts..."
$conflicts = @()

if (Test-PortInUse $backendPort) {
  $existing = Get-NetTCPConnection -LocalPort $backendPort -State Listen | Select-Object -First 1
  $procName = (Get-Process -Id $existing.OwningProcess -ErrorAction SilentlyContinue).ProcessName
  Write-Warn "Port $backendPort in use by $procName (PID: $($existing.OwningProcess))"
  $conflicts += $backendPort
}

if (Test-PortInUse $apsPort) {
  $existing = Get-NetTCPConnection -LocalPort $apsPort -State Listen | Select-Object -First 1
  $procName = (Get-Process -Id $existing.OwningProcess -ErrorAction SilentlyContinue).ProcessName
  Write-Warn "Port $apsPort in use by $procName (PID: $($existing.OwningProcess))"
  $conflicts += $apsPort
}

if (Test-PortInUse $frontendPort) {
  $existing = Get-NetTCPConnection -LocalPort $frontendPort -State Listen | Select-Object -First 1
  $procName = (Get-Process -Id $existing.OwningProcess -ErrorAction SilentlyContinue).ProcessName
  Write-Warn "Port $frontendPort in use by $procName (PID: $($existing.OwningProcess))"
  $conflicts += $frontendPort
}

if ($conflicts.Count -gt 0) {
  Write-Host ""
  Write-Host "Port conflicts detected! Options:" -ForegroundColor Yellow
  Write-Host "  1. Stop the conflicting processes manually" -ForegroundColor Gray
  Write-Host "  2. Run .\scripts\stop-services.ps1 -All -Force" -ForegroundColor Gray
  Write-Host "  3. Run .\scripts\configure.ps1 to pick different ports" -ForegroundColor Gray
  Write-Host ""
  $continue = Read-Host "Continue anyway? (y/N)"
  if ($continue -ne 'y' -and $continue -ne 'Y') {
    Write-Host "Aborted." -ForegroundColor Red
    exit 1
  }
}

# ============================================================================
# STEP 2: Start Backend API
# ============================================================================
if (-not $FrontendOnly) {
  Write-Step "Starting Backend API (FastAPI + Uvicorn)"
  
  $reloadFlag = if ($Dev) { " --reload" } else { "" }
  $apiCommand = "`"$venvPython`" -m uvicorn api.main:app --host $backendHost --port $backendPort$reloadFlag"
  
  $apiPid = Start-ServiceProcess `
    -name "Backend API" `
    -workingDir (Join-Path $repoRoot 'backend') `
    -command $apiCommand `
    -pidFile (Join-Path $pidDir 'api.pid') `
    -logFile (Join-Path $pidDir 'api.out.log') `
    -errFile (Join-Path $pidDir 'api.err.log')
  
  if ($apiPid) {
    $apiUp = Wait-ForEndpoint "http://${backendHost}:${backendPort}/docs" 30 "Backend API /docs"
    if (-not $apiUp) {
      Write-Host ""
      Write-Host "=== Backend Error Log ===" -ForegroundColor Red
      $errLog = Join-Path $pidDir 'api.err.log'
      if (Test-Path $errLog) {
        Get-Content $errLog -Tail 30 | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
      }
    }
  }
}

# ============================================================================
# STEP 3: Start APS Service
# ============================================================================
if (-not $FrontendOnly -and -not $ApiOnly) {
  Write-Step "Starting APS Service (Node.js)"
  
  $apsCommand = "npm start"
  
  $apsPid = Start-ServiceProcess `
    -name "APS Service" `
    -workingDir (Join-Path $repoRoot 'backend\aps-service') `
    -command $apsCommand `
    -pidFile (Join-Path $pidDir 'aps-service.pid') `
    -logFile (Join-Path $pidDir 'aps-service.out.log') `
    -errFile (Join-Path $pidDir 'aps-service.err.log')
  
  if ($apsPid) {
    $apsUp = Wait-ForEndpoint "http://127.0.0.1:${apsPort}/aps/config" 20 "APS Service /aps/config"
  }
}

# ============================================================================
# STEP 4: Start Frontend
# ============================================================================
if (-not $ApiOnly) {
  Write-Step "Starting Frontend (Vite + React)"
  
  $frontendCommand = "npm run dev"
  
  $frontendPid = Start-ServiceProcess `
    -name "Frontend" `
    -workingDir (Join-Path $repoRoot 'pointcloud-frontend') `
    -command $frontendCommand `
    -pidFile (Join-Path $pidDir 'frontend.pid') `
    -logFile (Join-Path $pidDir 'frontend.out.log') `
    -errFile (Join-Path $pidDir 'frontend.err.log')
  
  if ($frontendPid) {
    $frontendUp = Wait-ForEndpoint "http://localhost:${frontendPort}" 30 "Frontend"
  }
}

# ============================================================================
# STEP 5: Final Validation
# ============================================================================
Write-Step "Final Endpoint Validation"

$allGood = $true

# Backend API
if (-not $FrontendOnly) {
  Write-Info "Testing Backend API..."
  try {
    $apiTest = Invoke-WebRequest -Uri "http://${backendHost}:${backendPort}/docs" -UseBasicParsing -TimeoutSec 5
    Write-Success "Backend API: http://${backendHost}:${backendPort}/docs (HTTP $($apiTest.StatusCode))"
  } catch {
    Write-Fail "Backend API: http://${backendHost}:${backendPort}/docs - NOT RESPONDING"
    $allGood = $false
  }
  
  # Test /upload endpoint exists (OPTIONS or error is fine, just not connection refused)
  try {
    $uploadTest = Invoke-WebRequest -Uri "http://${backendHost}:${backendPort}/upload" -Method HEAD -UseBasicParsing -TimeoutSec 5 -ErrorAction SilentlyContinue
    Write-Success "Backend /upload endpoint reachable"
  } catch {
    if ($_.Exception.Message -match 'Method Not Allowed|405') {
      Write-Success "Backend /upload endpoint exists (POST required)"
    } elseif ($_.Exception.Message -match 'Connection refused|Unable to connect') {
      Write-Fail "Backend /upload endpoint NOT reachable"
      $allGood = $false
    } else {
      Write-Success "Backend /upload endpoint exists"
    }
  }
}

# APS Service
if (-not $FrontendOnly -and -not $ApiOnly) {
  Write-Info "Testing APS Service..."
  try {
    $apsTest = Invoke-WebRequest -Uri "http://127.0.0.1:${apsPort}/aps/config" -UseBasicParsing -TimeoutSec 5
    Write-Success "APS Service: http://127.0.0.1:${apsPort}/aps/config (HTTP $($apsTest.StatusCode))"
  } catch {
    Write-Warn "APS Service: http://127.0.0.1:${apsPort}/aps/config - NOT RESPONDING (optional)"
  }
}

# Frontend
if (-not $ApiOnly) {
  Write-Info "Testing Frontend..."
  try {
    $frontendTest = Invoke-WebRequest -Uri "http://localhost:${frontendPort}" -UseBasicParsing -TimeoutSec 5
    Write-Success "Frontend: http://localhost:${frontendPort} (HTTP $($frontendTest.StatusCode))"
  } catch {
    Write-Fail "Frontend: http://localhost:${frontendPort} - NOT RESPONDING"
    $allGood = $false
  }
}

# ============================================================================
# Summary
# ============================================================================
Write-Header "Deployment Complete"

if ($allGood) {
  Write-Success "All services are running!"
} else {
  Write-Warn "Some services failed to start - check logs in .pids/ folder"
}

Write-Host ""
Write-Host "SERVICE URLs:" -ForegroundColor White
if (-not $FrontendOnly) {
  Write-Host "  Backend API:     http://${backendHost}:${backendPort}" -ForegroundColor Cyan
  Write-Host "  Backend Docs:    http://${backendHost}:${backendPort}/docs" -ForegroundColor Cyan
}
if (-not $FrontendOnly -and -not $ApiOnly) {
  Write-Host "  APS Service:     http://127.0.0.1:${apsPort}" -ForegroundColor Cyan
}
if (-not $ApiOnly) {
  Write-Host "  Frontend:        http://localhost:${frontendPort}" -ForegroundColor Green
}

Write-Host ""
Write-Host "LOG FILES:" -ForegroundColor White
Write-Host "  .pids\api.out.log       - Backend stdout" -ForegroundColor Gray
Write-Host "  .pids\api.err.log       - Backend stderr" -ForegroundColor Gray
Write-Host "  .pids\aps-service.*.log - APS service logs" -ForegroundColor Gray
Write-Host "  .pids\frontend.*.log    - Frontend logs" -ForegroundColor Gray

Write-Host ""
Write-Host "COMMANDS:" -ForegroundColor White
Write-Host "  Stop all:    .\scripts\stop-services.ps1 -All -Force" -ForegroundColor Gray
Write-Host "  View logs:   Get-Content .\.pids\api.err.log -Tail 50 -Wait" -ForegroundColor Gray

# Open browser
if (-not $SkipBrowser -and -not $ApiOnly -and $allGood) {
  Write-Host ""
  Write-Info "Opening browser..."
  Start-Process "http://localhost:${frontendPort}"
}

Write-Host ""
