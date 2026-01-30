<#
.SYNOPSIS
  Stop BaseX HTTP Server
#>

$basexHome = $env:BASEX_HOME
if (-not $basexHome) { $basexHome = "C:\Program Files (x86)\BaseX" }

if (-not (Test-Path "$basexHome\bin\basexhttp.bat")) {
    $basexHome = "D:\BaseX"
}

if (Test-Path "$basexHome\bin\basexhttp.bat") {
    Write-Host "Stopping BaseX HTTP Server..."
    Start-Process -FilePath "$basexHome\bin\basexhttp.bat" -ArgumentList "stop" -WindowStyle Hidden
} else {
    Write-Warning "BaseX executable not found."
}
