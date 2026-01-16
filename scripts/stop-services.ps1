param(
  [switch]$Aps,
  [switch]$Frontend,
  [switch]$Api,
  [switch]$All,
  [switch]$Force
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidDir = Join-Path $repoRoot '.pids'

function Get-EnvValueFromFile([string]$path, [string]$key) {
  if (-not (Test-Path $path)) { return $null }
  foreach ($line in (Get-Content -LiteralPath $path -ErrorAction SilentlyContinue)) {
    if (-not $line) { continue }
    $t = $line.Trim()
    if (-not $t) { continue }
    if ($t.StartsWith('#')) { continue }
    $m = [regex]::Match($t, "^\s*" + [regex]::Escape($key) + "\s*=\s*(.+?)\s*$")
    if (-not $m.Success) { continue }
    $val = $m.Groups[1].Value.Trim()
    if ($val.Length -ge 2) {
      if (($val.StartsWith('"') -and $val.EndsWith('"')) -or ($val.StartsWith("'") -and $val.EndsWith("'"))) {
        $val = $val.Substring(1, $val.Length - 2)
      }
    }
    return $val
  }
  return $null
}

function Stop-ByPidFile([string]$name) {
  $pidFile = Join-Path $pidDir ("$name.pid")
  if (-not (Test-Path $pidFile)) {
    Write-Host "[$name] pid file not found"
    return
  }

  $pidText = (Get-Content -Raw $pidFile).Trim()
  if (-not ($pidText -match '^\d+$')) {
    Write-Host "[$name] invalid pid file contents: $pidText"
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
    return
  }

  $processId = [int]$pidText
  try {
    Stop-Process -Id $processId -Force:$Force -ErrorAction Stop
    Write-Host "[$name] stopped (pid=$processId)"
  } catch {
    Write-Host "[$name] not running (pid=$processId)"
  }

  Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
}

function Stop-ByPort([string]$name, [int]$port) {
  try {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop
  } catch {
    return
  }
  $pids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
  foreach ($processId in $pids) {
    try {
      Stop-Process -Id $processId -Force:$Force -ErrorAction Stop
      Write-Host "[$name] stopped by port $port (pid=$processId)"
    } catch {
      # ignore
    }
  }
}

$stopAps = $All -or (-not ($Aps -or $Frontend -or $Api)) -or $Aps
$stopFrontend = $All -or (-not ($Aps -or $Frontend -or $Api)) -or $Frontend
$stopApi = $All -or (-not ($Aps -or $Frontend -or $Api)) -or $Api

if ($stopFrontend) {
  Stop-ByPidFile 'frontend'
  Stop-ByPort 'frontend' 5173
}

if ($stopAps) {
  Stop-ByPidFile 'aps-service'
  $envPath = Join-Path $repoRoot 'backend\.env'
  $apsPort = 3001
  $apsPortValue = Get-EnvValueFromFile -path $envPath -key 'APS_SERVICE_PORT'
  if ($apsPortValue -and ($apsPortValue -match '^\d+$')) {
    $apsPort = [int]$apsPortValue
  }
  Stop-ByPort 'aps-service' $apsPort
}

if ($stopApi) {
  Stop-ByPidFile 'api'
  $envPath = Join-Path $repoRoot 'backend\.env'
  $backendPort = 8000
  $portValue = Get-EnvValueFromFile -path $envPath -key 'BACKEND_PORT'
  if ($portValue -and ($portValue -match '^\d+$')) {
    $backendPort = [int]$portValue
  }
  Stop-ByPort 'api' $backendPort
}

Write-Host "Done"