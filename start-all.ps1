<#
.SYNOPSIS
  Start all BIMTwinOps services

.DESCRIPTION
  Opens separate PowerShell windows for backend and frontend

.EXAMPLE
  .\start-all.ps1

.NOTES
  Run bootstrap.ps1 first if this is a fresh clone.
#>

Write-Host "Starting BIMTwinOps Full Stack Application..." -ForegroundColor Green
Write-Host ""

$root = $PSScriptRoot

# Start backend in a new PowerShell window
Write-Host "Starting Backend Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", "$root\start-backend.ps1"

# Wait a bit for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Start frontend in a new PowerShell window
Write-Host "Starting Frontend Server..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-File", "$root\start-frontend.ps1"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "BIMTwinOps Services Starting..." -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the individual PowerShell windows to stop services" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Green
