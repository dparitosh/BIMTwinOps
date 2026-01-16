<#
.SYNOPSIS
  Stop BIMTwinOps backend server

.DESCRIPTION
  Stops the FastAPI/Uvicorn server running on port 8000

.EXAMPLE
  .\stop-backend.ps1
#>

$ErrorActionPreference = 'SilentlyContinue'

Write-Host ""
Write-Host "Stopping BIMTwinOps Backend..." -ForegroundColor Yellow
Write-Host ""

$stopped = $false

# Find process on port 8000
$procs = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | 
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
