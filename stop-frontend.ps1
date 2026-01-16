<#
.SYNOPSIS
  Stop BIMTwinOps frontend server

.DESCRIPTION
  Stops the Vite dev server running on port 5173

.EXAMPLE
  .\stop-frontend.ps1
#>

$ErrorActionPreference = 'SilentlyContinue'

Write-Host ""
Write-Host "Stopping BIMTwinOps Frontend..." -ForegroundColor Yellow
Write-Host ""

$stopped = $false

# Find process on port 5173
$procs = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | 
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
  Write-Host "Frontend stopped" -ForegroundColor Green
} else {
  Write-Host "Frontend was not running" -ForegroundColor Yellow
}
Write-Host ""
