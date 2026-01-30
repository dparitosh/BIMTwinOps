<#
.SYNOPSIS
  Start BaseX HTTP Server
#>
param(
    [switch]$SkipChecks
)

$basexHome = $env:BASEX_HOME
if (-not $basexHome) { $basexHome = "C:\Program Files (x86)\BaseX" }

# Check alternate common location
if (-not (Test-Path "$basexHome\bin\basexhttp.bat")) {
    $basexHome = "D:\BaseX"
}

if (-not (Test-Path "$basexHome\bin\basexhttp.bat")) {
    Write-Warning "BaseX not found. Expected at D:\BaseX or C:\Program Files (x86)\BaseX"
    Write-Warning "Please download BaseX from https://basex.org/download/"
    exit
}

$port = $env:BASEX_PORT
if (-not $port) { $port = 8984 }

# Check if port is in use
$inUse = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
if ($inUse) {
    Write-Host "BaseX port $port is already in use." -ForegroundColor Yellow
} else {
    Write-Host "Starting BaseX on port $port..."
    Start-Process -FilePath "$basexHome\bin\basexhttp.bat" -WindowStyle Hidden
}
