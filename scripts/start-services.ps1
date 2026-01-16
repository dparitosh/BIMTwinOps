param(
  [switch]$Aps,
  [switch]$Frontend,
  [switch]$Api,
  [switch]$All,
  [switch]$Dev
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$pidDir = Join-Path $repoRoot '.pids'
New-Item -ItemType Directory -Force -Path $pidDir | Out-Null

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
    "Set-Location -LiteralPath '$($wd.Path.Replace("'", "''"))';",
    $command
  ) -join ' '

  $proc = Start-Process -FilePath "powershell.exe" -ArgumentList @(
      "-NoProfile",
      "-ExecutionPolicy", "Bypass",
      "-Command", $psCommand
    ) -WindowStyle Hidden -RedirectStandardOutput $stdoutLogFile -RedirectStandardError $stderrLogFile -PassThru

  Set-Content -Path $pidFile -Value $proc.Id -Encoding ascii
  Write-Host "[$name] started (pid=$($proc.Id))"

  # Give the process a moment to bind ports / initialize.
  Start-Sleep -Milliseconds 600
  if (-not (Test-ProcessRunning -processId $proc.Id)) {
    Write-Host "[$name] failed to stay running (pid=$($proc.Id)). Check logs:" -ForegroundColor Yellow
    if (Test-Path $stderrLogFile) {
      try {
        $tail = Get-Content -LiteralPath $stderrLogFile -Tail 30 -ErrorAction SilentlyContinue
        if ($tail) {
          Write-Host ("--- {0} (last 30 lines) ---" -f (Split-Path -Leaf $stderrLogFile)) -ForegroundColor Yellow
          $tail | ForEach-Object { Write-Host $_ }
        }
      } catch {
        # ignore
      }
    }
    Remove-Item -Force $pidFile -ErrorAction SilentlyContinue
  }
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
  # Load .env to get BACKEND_PORT
  $envPath = Join-Path $repoRoot 'backend\.env'
  $backendHost = '127.0.0.1'
  $hostValue = Get-EnvValueFromFile -path $envPath -key 'BACKEND_HOST'
  if ($hostValue) {
    $backendHost = $hostValue
  }
  $backendPort = '8000'
  $portValue = Get-EnvValueFromFile -path $envPath -key 'BACKEND_PORT'
  if ($portValue -and ($portValue -match '^\d+$')) {
    $backendPort = $portValue
  }
  # Prefer workspace venv Python if present.
  $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
  $pythonExe = if (Test-Path $venvPython) { '"' + $venvPython + '"' } else { 'python' }

  # NOTE: Uvicorn --reload can be unstable when started as a background process with redirected stdio,
  # and it also breaks PID tracking (it spawns child processes). Default to non-reload mode for stability.
  $reloadFlag = if ($Dev) { ' --reload' } else { '' }
  Start-TrackedProcess -name 'api' -workingDir (Join-Path $repoRoot 'backend') -command "$pythonExe -m uvicorn api.main:app --host $backendHost --port $backendPort$reloadFlag"
}

Write-Host "Logs + PIDs in: $pidDir"