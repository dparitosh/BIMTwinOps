#Requires -Version 7.0
<#
.SYNOPSIS
    Stop all BIMTwinOps services
    
.DESCRIPTION
    Gracefully stops all running BIMTwinOps services by finding and terminating
    processes on the service ports:
    - Backend API (port 8008)
    - Frontend (port 5173)
    - APS Service (port 3001)
    
.EXAMPLE
    .\stop-services.ps1
    
.NOTES
    Author: BIMTwinOps Team
    Date: 2026-02-22
#>

$ErrorActionPreference = "Stop"

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

# Header
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  BIMTwinOps Service Shutdown" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# Function to kill process on port
function Stop-ProcessOnPort {
    param(
        [int]$Port,
        [string]$ServiceName
    )
    
    Write-Status "Stopping $ServiceName (port $Port)..."
    
    try {
        $connections = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue
        
        if ($connections) {
            $processIds = $connections | Select-Object -ExpandProperty OwningProcess -Unique
            
            foreach ($processId in $processIds) {
                try {
                    $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
                    if ($process) {
                        $processName = $process.Name
                        Stop-Process -Id $processId -Force -ErrorAction Stop
                        Write-Success "Stopped $ServiceName (PID: $processId, Process: $processName)"
                    }
                } catch {
                    Write-Warning "Could not stop process $processId : $_"
                }
            }
        } else {
            Write-Status "$ServiceName was not running"
        }
    } catch {
        Write-Warning "Error checking port $Port : $_"
    }
}

# Stop services
Stop-ProcessOnPort -Port 8008 -ServiceName "Backend API"
Stop-ProcessOnPort -Port 5173 -ServiceName "Frontend"
Stop-ProcessOnPort -Port 3001 -ServiceName "APS Service"

# Give processes time to clean up
Start-Sleep -Seconds 1

# Verify all stopped
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Shutdown Complete" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

$stillRunning = @()
if (Get-NetTCPConnection -LocalPort 8008 -ErrorAction SilentlyContinue) { $stillRunning += "Backend (8008)" }
if (Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue) { $stillRunning += "Frontend (5173)" }
if (Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue) { $stillRunning += "APS (3001)" }

if ($stillRunning.Count -gt 0) {
    Write-Warning "Some services may still be running:"
    $stillRunning | ForEach-Object { Write-Host "    - $_" }
    Write-Host ""
} else {
    Write-Success "All services stopped successfully"
    Write-Host ""
}
