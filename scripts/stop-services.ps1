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
  Stop-ByPort 'aps-service' 3001
}

if ($stopApi) {
  Stop-ByPidFile 'api'
  Stop-ByPort 'api' 8000
}

Write-Host "Done"