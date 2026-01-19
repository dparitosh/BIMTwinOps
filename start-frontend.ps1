<#
.SYNOPSIS
  Start BIMTwinOps React frontend

.DESCRIPTION
  Checks configuration and runs Vite development server (default port: 5173)

.EXAMPLE
  .\start-frontend.ps1
  .\start-frontend.ps1 -SkipChecks

.NOTES
  Run bootstrap.ps1 first if node_modules doesn't exist
  Set FRONTEND_PORT env var to override default port
#>

Param(
  [switch]$SkipChecks
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  BIMTwinOps Frontend Server" -ForegroundColor Green
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
$frontendDir = [IO.Path]::Combine($root, 'pointcloud-frontend')

# Navigate to frontend
Set-Location $frontendDir

# Check node_modules
if (-not (Test-Path "node_modules")) {
  Write-Host "[!] node_modules not found. Installing..." -ForegroundColor Yellow
  npm install
}
Write-Host "[OK] node_modules: Found" -ForegroundColor Green

# ============================================================================
# Read Configuration from .env
# ============================================================================
Write-Host ""
Write-Host "--- Configuration ---" -ForegroundColor Cyan

# Frontend port (can be overridden via FRONTEND_PORT env var)
$frontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 5173 }

$apiBaseUrl = "http://localhost:8000"
$apsServiceUrl = "http://localhost:3001"

if (Test-Path ".env") {
  Write-Host "[OK] .env file: Found" -ForegroundColor Green
  $content = Get-Content ".env" -Raw
  
  if ($content -match "VITE_API_BASE_URL\s*=\s*([^\s\r\n]+)") { $apiBaseUrl = $Matches[1] }
  if ($content -match "VITE_APS_SERVICE_URL\s*=\s*([^\s\r\n]+)") { $apsServiceUrl = $Matches[1] }
} else {
  Write-Host "[!] .env file: Creating default..." -ForegroundColor Yellow
  @"
VITE_API_BASE_URL=http://localhost:8000
VITE_APS_SERVICE_URL=http://localhost:3001
"@ | Out-File -FilePath ".env" -Encoding UTF8
  Write-Host "[OK] .env file: Created" -ForegroundColor Green
}

Write-Host "     API Base URL: $apiBaseUrl" -ForegroundColor White
Write-Host "     APS Service:  $apsServiceUrl" -ForegroundColor White

# ============================================================================
# Connection Checks
# ============================================================================
if (-not $SkipChecks) {
  Write-Host ""
  Write-Host "--- Connection Checks ---" -ForegroundColor Cyan
  
  # Check if frontend port is available
  $portInUse = Get-NetTCPConnection -LocalPort $frontendPort -State Listen -ErrorAction SilentlyContinue
  if ($portInUse) {
    Write-Host "[X] Port ${frontendPort}: IN USE (PID: $($portInUse.OwningProcess))" -ForegroundColor Red
    Write-Host "    Run .\stop-frontend.ps1 first" -ForegroundColor Yellow
    exit 1
  } else {
    Write-Host "[OK] Port ${frontendPort}: Available" -ForegroundColor Green
  }
  
  # Check Backend API connection
  try {
    $backendResp = Invoke-WebRequest -Uri "$apiBaseUrl/health" -Method GET -TimeoutSec 3 -ErrorAction SilentlyContinue
    if ($backendResp.StatusCode -eq 200) {
      Write-Host "[OK] Backend API: Connected ($apiBaseUrl)" -ForegroundColor Green
    } else {
      Write-Host "[!] Backend API: Responded with status $($backendResp.StatusCode)" -ForegroundColor Yellow
    }
  } catch {
    Write-Host "[X] Backend API: Not running or unreachable" -ForegroundColor Red
    Write-Host "    Start backend first: .\start-backend.ps1" -ForegroundColor Yellow
  }
  
  # Check APS Service connection (optional)
  try {
    $apsResp = Invoke-WebRequest -Uri "$apsServiceUrl/health" -Method GET -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($apsResp.StatusCode -eq 200) {
      Write-Host "[OK] APS Service: Connected ($apsServiceUrl)" -ForegroundColor Green
    }
  } catch {
    Write-Host "[--] APS Service: Not running (optional)" -ForegroundColor Gray
  }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Starting Vite Dev Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  URL: http://localhost:$frontendPort" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

# Pass port to Vite if non-default
if ($frontendPort -ne 5173) {
  npm run dev -- --port $frontendPort
} else {
  npm run dev
}
