<#
.SYNOPSIS
  Start the BIMTwinOps React frontend

.DESCRIPTION
  Runs npm dev server (Vite) on port 5173

.EXAMPLE
  .\start-frontend.ps1

.NOTES
  Run bootstrap.ps1 first if node_modules doesn't exist.
#>

Write-Host "Starting BIMTwinOps Frontend..." -ForegroundColor Green

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
  Write-Host "Error: Node.js is not installed or not in PATH" -ForegroundColor Red
  Write-Host "Please install Node.js from https://nodejs.org/" -ForegroundColor Yellow
  exit 1
}

# Check if npm is installed
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Write-Host "Error: npm is not installed or not in PATH" -ForegroundColor Red
  exit 1
}

# Display versions
Write-Host "Node version: $(node --version)" -ForegroundColor Cyan
Write-Host "npm version: $(npm --version)" -ForegroundColor Cyan
Write-Host ""

$root = $PSScriptRoot
$frontendDir = [IO.Path]::Combine($root, 'pointcloud-frontend')

# Navigate to frontend directory
Set-Location $frontendDir

# Check if .env file exists
if (-not (Test-Path ".env")) {
  Write-Host "Creating default .env file..." -ForegroundColor Yellow
  @"
VITE_API_BASE_URL=http://localhost:8000
VITE_APS_SERVICE_URL=http://localhost:3001
"@ | Out-File -FilePath ".env" -Encoding UTF8
  Write-Host "Created .env with default values" -ForegroundColor Green
}

# Check if node_modules exists
if (-not (Test-Path "node_modules")) {
  Write-Host "node_modules not found. Installing dependencies..." -ForegroundColor Yellow
  npm install
} else {
  Write-Host "Checking for dependency updates..." -ForegroundColor Yellow
  npm install
}

# Start the development server
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Starting Vite dev server..." -ForegroundColor Green
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

npm run dev
