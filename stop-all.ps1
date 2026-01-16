<#
.SYNOPSIS
  Stop all BIMTwinOps services

.DESCRIPTION
  Stops all running uvicorn (backend) and node (frontend) processes
  related to BIMTwinOps

.EXAMPLE
  .\stop-all.ps1

.NOTES
  Finds and terminates processes by port
#>

$ErrorActionPreference = 'SilentlyContinue'

Write-Host ""
Write-Host "======================================" -ForegroundColor Yellow
Write-Host "  Stopping BIMTwinOps Services" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Yellow
Write-Host ""

$stopped = 0

# Stop backend (port 8000)
$backendProcs = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $backendProcs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping backend (PID: $procId, Name: $($proc.Name))..." -ForegroundColor Cyan
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      $stopped++
    }
  }
}

# Stop frontend (port 5173)
$frontendProcs = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $frontendProcs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping frontend (PID: $procId, Name: $($proc.Name))..." -ForegroundColor Cyan
      Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
      $stopped++
    }
  }
}

# Stop APS service (port 3001)
$apsProcs = Get-NetTCPConnection -LocalPort 3001 -State Listen -ErrorAction SilentlyContinue | 
  Select-Object -ExpandProperty OwningProcess -Unique

foreach ($procId in $apsProcs) {
  if ($procId -and $procId -gt 0) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc) {
      Write-Host "Stopping APS service (PID: $procId, Name: $($proc.Name))..." -ForegroundColor Cyan
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
