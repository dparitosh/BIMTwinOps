param(
  [switch]$Aps,
  [switch]$Frontend,
  [switch]$Api,
  [switch]$All
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidDir = Join-Path $repoRoot '.pids'
New-Item -ItemType Directory -Force -Path $pidDir | Out-Null

function Test-ProcessRunning([int]$processId) {
  try {
    $p = Get-Process -Id $processId -ErrorAction Stop
    return $true
  } catch {
    return $false
  }
}

function Get-PidFile([string]$name) { return Join-Path $pidDir ("$name.pid") }
function Get-StdoutLogFile([string]$name) { return Join-Path $pidDir ("$name.out.log") }
function Get-StderrLogFile([string]$name) { return Join-Path $pidDir ("$name.err.log") }

function Start-TrackedProcess(
  [string]$name,
  [string]$workingDir,
  [string]$command
) {
  $pidFile = Get-PidFile $name
  $stdoutLogFile = Get-StdoutLogFile $name
  $stderrLogFile = Get-StderrLogFile $name

  if (Test-Path $pidFile) {
    $existingPid = (Get-Content -Raw $pidFile).Trim()
    if ($existingPid -match '^\d+$' -and (Test-ProcessRunning([int]$existingPid))) {
      Write-Host "[$name] already running (pid=$existingPid)"
      return
    }
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
  }

  $wd = Resolve-Path $workingDir
  
  # Clean up old log files (ignore if locked)
  Remove-Item -Path $stdoutLogFile -Force -ErrorAction SilentlyContinue
  Remove-Item -Path $stderrLogFile -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 100
  
  try {
    "" | Out-File -FilePath $stdoutLogFile -Encoding utf8 -ErrorAction Stop
    "" | Out-File -FilePath $stderrLogFile -Encoding utf8 -ErrorAction Stop
  } catch {
    Write-Host "[$name] Warning: Could not create log files (may be locked)"
    # Create temp files instead
    $stdoutLogFile = Join-Path $pidDir ("$name.$(Get-Date -Format 'yyyyMMdd-HHmmss').out.log")
    $stderrLogFile = Join-Path $pidDir ("$name.$(Get-Date -Format 'yyyyMMdd-HHmmss').err.log")
    "" | Out-File -FilePath $stdoutLogFile -Encoding utf8
    "" | Out-File -FilePath $stderrLogFile -Encoding utf8
  }

  $psCommand = @(
    "Set-Location -LiteralPath '$($wd.Path)';",
    $command
  ) -join ' '

  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
      "-NoProfile",
      "-ExecutionPolicy", "Bypass",
      "-Command", $psCommand
    ) -WindowStyle Hidden -RedirectStandardOutput $stdoutLogFile -RedirectStandardError $stderrLogFile -PassThru

  Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
  Write-Host "[$name] started (pid=$($proc.Id))"
}

$startAps = $All -or (-not ($Aps -or $Frontend -or $Api)) -or $Aps
$startFrontend = $All -or (-not ($Aps -or $Frontend -or $Api)) -or $Frontend
$startApi = $All -or (-not ($Aps -or $Frontend -or $Api)) -or $Api

if ($startFrontend) {
  Start-TrackedProcess -name 'frontend' -workingDir (Join-Path $repoRoot 'pointcloud-frontend') -command 'npm run dev'
}

if ($startAps) {
  Start-TrackedProcess -name 'aps-service' -workingDir (Join-Path $repoRoot 'backend\\aps-service') -command 'npm run dev'
}

if ($startApi) {
  # Requires python + uvicorn installed in your environment.
  Start-TrackedProcess -name 'api' -workingDir (Join-Path $repoRoot 'backend') -command 'python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload'
}

Write-Host "Logs + PIDs in: $pidDir"