<#
.SYNOPSIS
  Stop BIMTwinOps backend server

.DESCRIPTION
  Stops the FastAPI/Uvicorn server (reads port from backend/.env)

.EXAMPLE
  .\stop-backend.ps1
#>

$ErrorActionPreference = 'SilentlyContinue'
$root = $PSScriptRoot

# Read port from .env (default: 8000)
$backendPort = 8000
$envFile = [IO.Path]::Combine($root, 'backend', '.env')
if (Test-Path $envFile) {
  $content = Get-Content $envFile -Raw
  if ($content -match "BACKEND_PORT\s*=\s*(\d+)") { $backendPort = [int]$Matches[1] }
}

Write-Host ""
Write-Host "Stopping BIMTwinOps Backend (port $backendPort)..." -ForegroundColor Yellow
Write-Host ""

$stopped = $false

# Find process on configured port
$procs = Get-NetTCPConnection -LocalPort $backendPort -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $procs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping process: $($proc.Name) (PID: $procId)" -ForegroundColor Cyan
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      $stopped = $true
    }
  }
}

if ($stopped) {
  Write-Host "Backend stopped" -ForegroundColor Green
} else {
  Write-Host "Backend was not running" -ForegroundColor Yellow
}
Write-Host ""
