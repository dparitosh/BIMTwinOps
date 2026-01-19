<#
.SYNOPSIS
  Stop all BIMTwinOps services

.DESCRIPTION
  Stops all running uvicorn (backend) and node (frontend) processes
  related to BIMTwinOps. Reads port config from .env files.

.EXAMPLE
  .\stop-all.ps1

.NOTES
  Finds and terminates processes by port
#>

$ErrorActionPreference = 'SilentlyContinue'
$root = $PSScriptRoot

# Read port configuration from .env files
$backendPort = 8000
$frontendPort = if ($env:FRONTEND_PORT) { [int]$env:FRONTEND_PORT } else { 5173 }
$apsPort = 3001

$backendEnv = [IO.Path]::Combine($root, 'backend', '.env')
if (Test-Path $backendEnv) {
  $content = Get-Content $backendEnv -Raw
  if ($content -match "BACKEND_PORT\s*=\s*(\d+)") { $backendPort = [int]$Matches[1] }
  if ($content -match "APS_SERVICE_PORT\s*=\s*(\d+)") { $apsPort = [int]$Matches[1] }
}

Write-Host ""
Write-Host "======================================" -ForegroundColor Yellow
Write-Host "  Stopping BIMTwinOps Services" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Yellow
Write-Host "  Backend port:  $backendPort" -ForegroundColor Gray
Write-Host "  Frontend port: $frontendPort" -ForegroundColor Gray
Write-Host "  APS port:      $apsPort" -ForegroundColor Gray
Write-Host ""

$stopped = 0

# Stop backend
$backendProcs = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $backendProcs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping backend on port $backendPort (PID: $procId, Name: $($proc.Name))..." -ForegroundColor Cyan
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      $stopped++
    }
  }
}

# Stop frontend
$frontendProcs = Get-NetTCPConnection -LocalPort $frontendPort -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $frontendProcs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping frontend on port $frontendPort (PID: $procId, Name: $($proc.Name))..." -ForegroundColor Cyan
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      $stopped++
    }
  }
}

# Stop APS service
$apsProcs = Get-NetTCPConnection -LocalPort $apsPort -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $apsProcs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping APS service on port $apsPort (PID: $procId, Name: $($proc.Name))..." -ForegroundColor Cyan
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      $stopped++
    }
  }
}

Write-Host ""
if ($stopped -gt 0) {
  Write-Host "Stopped $stopped service(s)" -ForegroundColor Green
} else {
  Write-Host "No BIMTwinOps services were running" -ForegroundColor Yellow
}
Write-Host ""
