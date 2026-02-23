#Requires -Version 7.0
<#
.SYNOPSIS
    Start all BIMTwinOps services (Backend, Frontend, APS)
    
.DESCRIPTION
    Starts the complete BIMTwinOps platform stack:
    - Backend API (FastAPI on port 8008)
    - Frontend (Vite on port 5173)
    - APS Service (Node.js on port 3001)
    - Neo4j (if not running on port 7687)
    
.EXAMPLE
    .\start-services.ps1
    
.NOTES
    Author: BIMTwinOps Team
    Date: 2026-02-22
#>

$ErrorActionPreference = "Stop"
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# Color output functions
function Write-Status($message) {
    Write-Host "  [INFO] " -NoNewline -ForegroundColor Cyan
    Write-Host $message
}

function Write-Success($message) {
    Write-Host "  [OK] " -NoNewline -ForegroundColor Green
    Write-Host $message
}

function Write-Warning($message) {
    Write-Host "  [WARN] " -NoNewline -ForegroundColor Yellow
    Write-Host $message
}

function Write-Error($message) {
    Write-Host "  [ERROR] " -NoNewline -ForegroundColor Red
    Write-Host $message
}

# Header
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BIMTwinOps Service Startup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Check if already running
Write-Status "Checking for running services..."

$backendRunning = Get-NetTCPConnection -LocalPort 8008 -ErrorAction SilentlyContinue
$frontendRunning = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue
$apsRunning = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue

if ($backendRunning -or $frontendRunning -or $apsRunning) {
    Write-Warning "Some services are already running:"
    if ($backendRunning) { Write-Host "    - Backend (port 8008)" }
    if ($frontendRunning) { Write-Host "    - Frontend (port 5173)" }
    if ($apsRunning) { Write-Host "    - APS Service (port 3001)" }
    Write-Host ""
    $response = Read-Host "Stop existing services and restart? (y/n)"
    if ($response -ne 'y') {
        Write-Status "Startup cancelled."
        exit 0
    }
    Write-Status "Stopping existing services..."
    & "$PSScriptRoot\stop-services.ps1"
    Start-Sleep -Seconds 2
}

# Verify prerequisites
Write-Status "Verifying environment..."

# Check Python virtual environment
if (-not (Test-Path "$PSScriptRoot\..\.venv\Scripts\python.exe")) {
    Write-Error "Python virtual environment not found. Run: python -m venv .venv"
    exit 1
}

# Check Node.js
try {
    $nodeVersion = node --version 2>$null
    Write-Success "Node.js: $nodeVersion"
} catch {
    Write-Error "Node.js not found. Please install Node.js 18+."
    exit 1
}

# Check Neo4j
Write-Status "Checking Neo4j..."
try {
    $neo4jRunning = Test-NetConnection -ComputerName localhost -Port 7687 -ErrorAction SilentlyContinue -WarningAction SilentlyContinue
    if ($neo4jRunning.TcpTestSucceeded) {
        Write-Success "Neo4j is running on port 7687"
    } else {
        Write-Warning "Neo4j not detected on port 7687. Some features may not work."
    }
} catch {
    Write-Warning "Could not check Neo4j status."
}

# Start services
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Starting Services" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 1. Start Backend
Write-Status "Starting Backend API (port 8008)..."
$backendPath = Join-Path $PSScriptRoot "..\backend"
$venvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"

Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$backendPath'; & '$venvPython' -m uvicorn api.main:app --host 0.0.0.0 --port 8008 --reload"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Verify backend started
$backendCheck = $null
for ($i = 1; $i -le 10; $i++) {
    try {
        $backendCheck = Invoke-WebRequest -Uri "http://localhost:8008/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($backendCheck.StatusCode -eq 200) {
            Write-Success "Backend API started successfully"
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $backendCheck -or $backendCheck.StatusCode -ne 200) {
    Write-Warning "Backend may not have started correctly (will continue anyway)"
}

# 2. Start Frontend
Write-Status "Starting Frontend (port 5173)..."
$frontendPath = Join-Path $PSScriptRoot "..\pointcloud-frontend"

Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$frontendPath'; npm run dev"
) -WindowStyle Normal

Start-Sleep -Seconds 5

# Verify frontend started
$frontendCheck = $null
for ($i = 1; $i -le 10; $i++) {
    try {
        $frontendCheck = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($frontendCheck.StatusCode -eq 200) {
            Write-Success "Frontend started successfully"
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $frontendCheck -or $frontendCheck.StatusCode -ne 200) {
    Write-Warning "Frontend may not have started correctly (will continue anyway)"
}

# 3. Start APS Service
Write-Status "Starting APS Service (port 3001)..."
$apsPath = Join-Path $PSScriptRoot "..\backend\aps-service"

Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$apsPath'; npm start"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Verify APS started
$apsCheck = $null
for ($i = 1; $i -le 10; $i++) {
    try {
        $apsCheck = Invoke-WebRequest -Uri "http://localhost:3001/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue
        if ($apsCheck.StatusCode -eq 200) {
            Write-Success "APS Service started successfully"
            break
        }
    } catch {
        Start-Sleep -Milliseconds 500
    }
}

if (-not $apsCheck -or $apsCheck.StatusCode -ne 200) {
    Write-Warning "APS Service may not have started correctly"
}

# Summary
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Service Startup Complete" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Services are now running:`n"
Write-Host "  Backend API:  " -NoNewline; Write-Host "http://localhost:8008" -ForegroundColor Cyan
Write-Host "  API Docs:     " -NoNewline; Write-Host "http://localhost:8008/docs" -ForegroundColor Cyan
Write-Host "  Frontend:     " -NoNewline; Write-Host "http://localhost:5173" -ForegroundColor Cyan
Write-Host "  APS Service:  " -NoNewline; Write-Host "http://localhost:3001" -ForegroundColor Cyan
if ($neo4jRunning.TcpTestSucceeded) {
    Write-Host "  Neo4j:        " -NoNewline; Write-Host "bolt://localhost:7687" -ForegroundColor Cyan
}

Write-Host "`nTo stop all services, run: " -NoNewline
Write-Host ".\stop-services.ps1" -ForegroundColor Yellow
Write-Host ""
