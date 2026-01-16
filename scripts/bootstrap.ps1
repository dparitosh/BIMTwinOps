param(
  [switch]$SkipPython,
  [switch]$SkipNode,
  [switch]$SkipPointNet,
  [switch]$ForceEnv
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

function Write-Step([string]$msg) {
  Write-Host "\n==> $msg"
}

function Ensure-EnvFile([string]$src, [string]$dst) {
  if ((-not (Test-Path $dst)) -or $ForceEnv) {
    if (Test-Path $src) {
      Copy-Item -Force $src $dst
      Write-Host "Created $dst from example"
    } else {
      Write-Host "Warning: missing example file $src"
    }
  } else {
    Write-Host "Keeping existing $dst"
  }
}

function Get-PythonExe() {
  $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
  if (Test-Path $venvPython) { return $venvPython }

  # Try py launcher first (common on Windows)
  $py = Get-Command py -ErrorAction SilentlyContinue
  if ($py) { return 'py -3' }

  $python = Get-Command python -ErrorAction SilentlyContinue
  if ($python) { return 'python' }

  throw "Python not found. Install Python 3.10+ and ensure 'python' or 'py' is available."
}

function Ensure-Venv() {
  $venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
  if (Test-Path $venvPython) { return $venvPython }

  $pyCmd = Get-PythonExe
  Write-Step "Creating venv at .venv (using: $pyCmd)"
  if ($pyCmd -eq 'py -3') {
    & py -3 -m venv "$repoRoot/.venv"
  } else {
    & $pyCmd -m venv "$repoRoot/.venv"
  }

  if (-not (Test-Path $venvPython)) {
    throw "Failed to create venv at $venvPython"
  }

  return $venvPython
}

function Ensure-Npm() {
  $npm = Get-Command npm -ErrorAction SilentlyContinue
  if (-not $npm) {
    throw "npm not found. Install Node.js 18+ (which includes npm)."
  }
}

Write-Host "SMART_BIM bootstrap (Windows)"
Write-Host "Repo: $repoRoot"

# --- Env files ---
Write-Step "Ensuring .env files exist"
Ensure-EnvFile (Join-Path $repoRoot 'backend\.env.example') (Join-Path $repoRoot 'backend\.env')
Ensure-EnvFile (Join-Path $repoRoot 'backend\aps-service\.env.example') (Join-Path $repoRoot 'backend\aps-service\.env')
Ensure-EnvFile (Join-Path $repoRoot 'pointcloud-frontend\.env.example') (Join-Path $repoRoot 'pointcloud-frontend\.env')

# --- Python deps ---
if (-not $SkipPython) {
  $venvPython = Ensure-Venv

  Write-Step "Installing backend Python dependencies"
  & $venvPython -m pip install --upgrade pip
  & $venvPython -m pip install -r (Join-Path $repoRoot 'backend\api\requirements.txt')

  # PointNet deps are optional but commonly needed for point cloud segmentation
  $pointnetReq = Join-Path $repoRoot 'backend\pointnet_s3dis\requirements.txt'
  if ($SkipPointNet) {
    Write-Host "Skipping PointNet deps (SkipPointNet set)"
  } elseif (Test-Path $pointnetReq) {
    Write-Step "Installing PointNet (pointnet_s3dis) dependencies"
    & $venvPython -m pip install -r $pointnetReq
  } else {
    Write-Host "Skipping PointNet deps (requirements not found at $pointnetReq)"
  }
}

# --- Node deps ---
if (-not $SkipNode) {
  Ensure-Npm

  Write-Step "Installing frontend dependencies (pointcloud-frontend)"
  Push-Location (Join-Path $repoRoot 'pointcloud-frontend')
  try {
    npm install
  } finally {
    Pop-Location
  }

  Write-Step "Installing APS service dependencies (backend/aps-service)"
  Push-Location (Join-Path $repoRoot 'backend\aps-service')
  try {
    npm install
  } finally {
    Pop-Location
  }
}

Write-Step "Bootstrap complete"
Write-Host "Next: run .\\scripts\\start-services.ps1 -All"
