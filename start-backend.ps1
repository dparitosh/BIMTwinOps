<#
.SYNOPSIS
  Start the BIMTwinOps Python backend

.DESCRIPTION
  Activates venv and starts FastAPI/Uvicorn on port 8000

.EXAMPLE
  .\start-backend.ps1
  .\start-backend.ps1 -Reload

.NOTES
  Run bootstrap.ps1 first if venv doesn't exist.
#>

Param(
  [switch]$Reload
)

Write-Host "Starting BIMTwinOps Backend Server..." -ForegroundColor Green

# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
  exit 1
}

$root = $PSScriptRoot
$backendDir = [IO.Path]::Combine($root, 'backend')
$venvDir = [IO.Path]::Combine($root, '.venv')
$venvActivate = [IO.Path]::Combine($venvDir, 'Scripts', 'Activate.ps1')
$venvPython = [IO.Path]::Combine($venvDir, 'Scripts', 'python.exe')

# Check if venv exists
if (-not (Test-Path $venvPython)) {
  Write-Host "Virtual environment not found. Running bootstrap..." -ForegroundColor Yellow
  & "$root\bootstrap.ps1"
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $venvActivate

# Navigate to backend
Set-Location $backendDir

# Check for .env
$envFile = [IO.Path]::Combine($backendDir, '.env')
if (-not (Test-Path $envFile)) {
  Write-Host "Note: .env file not found. Using defaults." -ForegroundColor Yellow
  Write-Host "Create backend/.env for custom configuration." -ForegroundColor Yellow
  Write-Host ""
}

# Read port from .env or use default
$port = 8000
$bindHost = "127.0.0.1"
if (Test-Path $envFile) {
  $content = Get-Content $envFile -Raw
  if ($content -match "BACKEND_PORT\s*=\s*(\d+)") {
    $port = $Matches[1]
  }
  if ($content -match "BACKEND_HOST\s*=\s*([^\s]+)") {
    $bindHost = $Matches[1]
  }
}

# Build uvicorn command
$reloadFlag = if ($Reload) { "--reload" } else { "" }

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Starting FastAPI server..." -ForegroundColor Green
Write-Host "API URL: http://${bindHost}:${port}" -ForegroundColor Cyan
Write-Host "API Docs: http://${bindHost}:${port}/docs" -ForegroundColor Cyan
Write-Host "GraphQL: http://${bindHost}:${port}/api/graphql" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

$cmd = "python -m uvicorn api.main:app --host $bindHost --port $port $reloadFlag"
Invoke-Expression $cmd
