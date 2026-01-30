<#
.SYNOPSIS
  Start BIMTwinOps APS (Autodesk Platform Services) proxy server

.DESCRIPTION
  Checks configuration, verifies node_modules, and starts the Express server on port 3001

.EXAMPLE
  .\start-aps.ps1
  .\start-aps.ps1 -SkipChecks

.NOTES
  Requires APS_CLIENT_ID and APS_CLIENT_SECRET in backend/.env for full functionality
#>

Param(
  [switch]$SkipChecks
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BIMTwinOps APS Service" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# Check Node
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Host "[X] Node.js: NOT FOUND" -ForegroundColor Red
  Write-Host "    Install from https://nodejs.org/" -ForegroundColor Yellow
  exit 1
}
$nodeVersion = node --version
Write-Host "[OK] Node.js: $nodeVersion" -ForegroundColor Green

# Check npm
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Host "[X] npm: NOT FOUND" -ForegroundColor Red
  exit 1
}
$npmVersion = npm --version
Write-Host "[OK] npm: v$npmVersion" -ForegroundColor Green

# Paths
$apsDir = [IO.Path]::Combine($root, 'backend', 'aps-service')
$backendEnv = [IO.Path]::Combine($root, 'backend', '.env')

# Navigate to APS service
Set-Location $apsDir

# Check node_modules
if (-not (Test-Path "node_modules")) {
  Write-Host "[!] node_modules not found. Installing..." -ForegroundColor Yellow
  npm install
}
Write-Host "[OK] node_modules: Found" -ForegroundColor Green

# ============================================================================
# Read Configuration from backend/.env
# ============================================================================
Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Cyan

$apsPort = 3001
$apsClientId = ""
$apsClientSecret = ""
$apsCallbackUrl = ""
$apsBucketKey = ""

if (Test-Path $backendEnv) {
  Write-Host "[OK] backend/.env: Found" -ForegroundColor Green
  $content = Get-Content $backendEnv -Raw
  
  if ($content -match "APS_SERVICE_PORT\s*=\s*(\d+)") { $apsPort = [int]$Matches[1] }
  if ($content -match "APS_CLIENT_ID\s*=\s*([^\s\r\n]+)") { $apsClientId = $Matches[1] }
  if ($content -match "APS_CLIENT_SECRET\s*=\s*([^\s\r\n]+)") { $apsClientSecret = $Matches[1] }
  if ($content -match "APS_CALLBACK_URL\s*=\s*([^\s\r\n]+)") { $apsCallbackUrl = $Matches[1] }
  if ($content -match "APS_BUCKET_KEY\s*=\s*([^\s\r\n]+)") { $apsBucketKey = $Matches[1] }
} else {
  Write-Host "[!] backend/.env: Not found (APS will use defaults)" -ForegroundColor Yellow
}

Write-Host "     APS Port: $apsPort" -ForegroundColor White

# Check APS credentials
if ($apsClientId -and $apsClientId -ne "" -and $apsClientId -ne "YOUR_APS_CLIENT_ID") {
  Write-Host "[OK] APS_CLIENT_ID: Configured" -ForegroundColor Green
} else {
  Write-Host "[!] APS_CLIENT_ID: Not configured (2-legged auth unavailable)" -ForegroundColor Yellow
}

if ($apsClientSecret -and $apsClientSecret -ne "" -and $apsClientSecret -ne "YOUR_APS_CLIENT_SECRET") {
  Write-Host "[OK] APS_CLIENT_SECRET: Configured" -ForegroundColor Green
} else {
  Write-Host "[!] APS_CLIENT_SECRET: Not configured (2-legged auth unavailable)" -ForegroundColor Yellow
}

if ($apsCallbackUrl -and $apsCallbackUrl -ne "") {
  Write-Host "[OK] APS_CALLBACK_URL: $apsCallbackUrl" -ForegroundColor Green
} else {
  Write-Host "[--] APS_CALLBACK_URL: Not set (3-legged OAuth unavailable)" -ForegroundColor Gray
}

# ============================================================================
# Connection Checks
# ============================================================================
if (-not $SkipChecks) {
  Write-Host ""
  Write-Host "--- Connection Checks ---" -ForegroundColor Cyan
  
  # Check if port is available
  $portInUse = Get-NetTCPConnection -LocalPort $apsPort -State Listen -ErrorAction SilentlyContinue
  if ($portInUse) {
    Write-Host "[X] Port ${apsPort}: IN USE (PID: $($portInUse.OwningProcess))" -ForegroundColor Red
    Write-Host "    Run .\stop-all.ps1 first or change APS_SERVICE_PORT in backend/.env" -ForegroundColor Yellow
    exit 1
  } else {
    Write-Host "[OK] Port ${apsPort}: Available" -ForegroundColor Green
  }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting APS Proxy Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  URL:    http://localhost:$apsPort" -ForegroundColor White
Write-Host "  Health: http://localhost:$apsPort/health" -ForegroundColor White
Write-Host "  Config: http://localhost:$apsPort/aps/config" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Run the server
node src/server.js
