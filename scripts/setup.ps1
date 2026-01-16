<#
.SYNOPSIS
  SMART_BIM Setup Script - Installs all dependencies (verbose mode)

.DESCRIPTION
  This script:
  1. Checks prerequisites (Python, Node.js, Git)
  2. Initializes git submodules
  3. Creates Python virtual environment
  4. Installs Python dependencies
  5. Installs Node.js dependencies
  6. Creates .env files from examples
  7. Validates the setup

.EXAMPLE
  .\scripts\setup.ps1
  .\scripts\setup.ps1 -SkipPointNet

.NOTES
  Run this ONCE on a fresh clone. Then use deploy.ps1 to start services.
#>

param(
  [switch]$SkipPointNet,
  [switch]$SkipNode
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'Continue'

# Colors for output
function Write-Header($msg) {
  Write-Host ""
  Write-Host ("=" * 70) -ForegroundColor Cyan
  Write-Host "  $msg" -ForegroundColor Cyan
  Write-Host ("=" * 70) -ForegroundColor Cyan
}

function Write-Step($msg) {
  Write-Host ""
  Write-Host "[STEP] $msg" -ForegroundColor Yellow
  Write-Host ("-" * 50) -ForegroundColor DarkGray
}

function Write-Success($msg) {
  Write-Host "[OK] $msg" -ForegroundColor Green
}

function Write-Fail($msg) {
  Write-Host "[FAIL] $msg" -ForegroundColor Red
}

function Write-Info($msg) {
  Write-Host "[INFO] $msg" -ForegroundColor Gray
}

function Write-Warn($msg) {
  Write-Host "[WARN] $msg" -ForegroundColor DarkYellow
}

# Get repo root
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$repoRoot = Split-Path -Parent $scriptDir

Write-Header "SMART_BIM Setup Script"
Write-Host "Repository: $repoRoot"
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host "PowerShell: $($PSVersionTable.PSVersion)"

# ============================================================================
# STEP 1: Check Prerequisites
# ============================================================================
Write-Step "Checking Prerequisites"

# Check Python
Write-Info "Looking for Python..."
$pythonCmd = $null
$pythonVersion = $null

try {
  $pythonVersion = & python --version 2>&1
  if ($pythonVersion -match 'Python (\d+\.\d+)') {
    $pythonCmd = 'python'
    Write-Success "Found: $pythonVersion (command: python)"
  }
} catch {
  Write-Info "  'python' command not found"
}

if (-not $pythonCmd) {
  try {
    $pythonVersion = & py -3 --version 2>&1
    if ($pythonVersion -match 'Python (\d+\.\d+)') {
      $pythonCmd = 'py -3'
      Write-Success "Found: $pythonVersion (command: py -3)"
    }
  } catch {
    Write-Info "  'py -3' command not found"
  }
}

if (-not $pythonCmd) {
  Write-Fail "Python 3.10+ is required but not found!"
  Write-Host "  Install from: https://www.python.org/downloads/" -ForegroundColor White
  Write-Host "  Make sure to check 'Add Python to PATH' during installation" -ForegroundColor White
  exit 1
}

# Check Node.js
Write-Info "Looking for Node.js..."
try {
  $nodeVersion = & node --version 2>&1
  Write-Success "Found: Node.js $nodeVersion"
} catch {
  Write-Fail "Node.js is required but not found!"
  Write-Host "  Install from: https://nodejs.org/" -ForegroundColor White
  exit 1
}

# Check npm
Write-Info "Looking for npm..."
try {
  $npmVersion = & npm --version 2>&1
  Write-Success "Found: npm $npmVersion"
} catch {
  Write-Fail "npm is required but not found!"
  exit 1
}

# Check Git
Write-Info "Looking for Git..."
try {
  $gitVersion = & git --version 2>&1
  Write-Success "Found: $gitVersion"
} catch {
  Write-Fail "Git is required but not found!"
  exit 1
}

# ============================================================================
# STEP 2: Initialize Git Submodules
# ============================================================================
Write-Step "Initializing Git Submodules"

Push-Location $repoRoot
try {
  Write-Info "Running: git submodule update --init --recursive"
  & git submodule update --init --recursive 2>&1 | ForEach-Object { Write-Host "  $_" }
  
  # Check if pointnet_s3dis is populated
  $pointnetDir = Join-Path $repoRoot 'backend\pointnet_s3dis'
  $pointnetFiles = Get-ChildItem $pointnetDir -ErrorAction SilentlyContinue
  if ($pointnetFiles.Count -gt 2) {
    Write-Success "Submodule backend/pointnet_s3dis initialized ($($pointnetFiles.Count) items)"
  } else {
    Write-Warn "Submodule backend/pointnet_s3dis may be empty"
  }
} finally {
  Pop-Location
}

# ============================================================================
# STEP 3: Create Python Virtual Environment
# ============================================================================
Write-Step "Creating Python Virtual Environment"

$venvPath = Join-Path $repoRoot '.venv'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'
$venvPip = Join-Path $venvPath 'Scripts\pip.exe'

if (Test-Path $venvPython) {
  Write-Info "Virtual environment already exists at: $venvPath"
  $existingVersion = & $venvPython --version 2>&1
  Write-Success "Using existing venv: $existingVersion"
} else {
  Write-Info "Creating new virtual environment..."
  Write-Info "Running: $pythonCmd -m venv `"$venvPath`""
  
  if ($pythonCmd -eq 'py -3') {
    & py -3 -m venv "$venvPath" 2>&1 | ForEach-Object { Write-Host "  $_" }
  } else {
    & python -m venv "$venvPath" 2>&1 | ForEach-Object { Write-Host "  $_" }
  }
  
  if (Test-Path $venvPython) {
    $venvVersion = & $venvPython --version 2>&1
    Write-Success "Created venv: $venvVersion"
  } else {
    Write-Fail "Failed to create virtual environment at $venvPath"
    exit 1
  }
}

# ============================================================================
# STEP 4: Install Python Dependencies
# ============================================================================
Write-Step "Installing Python Dependencies"

Write-Info "Upgrading pip..."
& $venvPython -m pip install --upgrade pip 2>&1 | ForEach-Object { Write-Host "  $_" }

$backendReq = Join-Path $repoRoot 'backend\api\requirements.txt'
if (Test-Path $backendReq) {
  Write-Info "Installing backend/api dependencies..."
  Write-Info "Running: pip install -r $backendReq"
  $pipOutput = & $venvPython -m pip install -r $backendReq 2>&1
  $pipOutput | ForEach-Object { Write-Host "  $_" }
  if ($LASTEXITCODE -ne 0) {
    Write-Fail "pip install failed! Check errors above."
    exit 1
  }
  Write-Success "Backend dependencies installed"
} else {
  Write-Fail "Backend requirements.txt not found at: $backendReq"
  exit 1
}

# PointNet dependencies (optional)
$pointnetReq = Join-Path $repoRoot 'backend\pointnet_s3dis\requirements.txt'
if ($SkipPointNet) {
  Write-Info "Skipping PointNet dependencies (-SkipPointNet flag)"
} elseif (Test-Path $pointnetReq) {
  Write-Info "Installing PointNet dependencies..."
  Write-Info "Running: pip install -r $pointnetReq"
  $pipOutput = & $venvPython -m pip install -r $pointnetReq 2>&1
  $pipOutput | ForEach-Object { Write-Host "  $_" }
  if ($LASTEXITCODE -ne 0) {
    Write-Warn "PointNet pip install had errors (non-critical)"
  } else {
    Write-Success "PointNet dependencies installed"
  }
} else {
  Write-Warn "PointNet requirements.txt not found (submodule may not be initialized)"
}

# Check for PointNet weights
$pointnetWeights = Join-Path $repoRoot 'backend\pointnet_s3dis\best_pointnet_s3dis.pth'
if (Test-Path $pointnetWeights) {
  Write-Success "PointNet weights found"
} else {
  Write-Warn "PointNet weights NOT found at: $pointnetWeights"
  Write-Warn "Point cloud uploads will run in FALLBACK mode (single segment)"
}

# ============================================================================
# STEP 5: Install Node.js Dependencies
# ============================================================================
if ($SkipNode) {
  Write-Step "Skipping Node.js Dependencies (-SkipNode flag)"
} else {
  Write-Step "Installing Node.js Dependencies"
  
  # Frontend
  $frontendDir = Join-Path $repoRoot 'pointcloud-frontend'
  Write-Info "Installing frontend dependencies..."
  Write-Info "Directory: $frontendDir"
  Push-Location $frontendDir
  try {
    & npm install 2>&1 | ForEach-Object { Write-Host "  $_" }
    Write-Success "Frontend dependencies installed"
  } catch {
    Write-Fail "Failed to install frontend dependencies: $_"
  } finally {
    Pop-Location
  }
  
  # APS Service
  $apsDir = Join-Path $repoRoot 'backend\aps-service'
  Write-Info "Installing APS service dependencies..."
  Write-Info "Directory: $apsDir"
  Push-Location $apsDir
  try {
    & npm install 2>&1 | ForEach-Object { Write-Host "  $_" }
    Write-Success "APS service dependencies installed"
  } catch {
    Write-Fail "Failed to install APS service dependencies: $_"
  } finally {
    Pop-Location
  }
}

# ============================================================================
# STEP 6: Create .env Files
# ============================================================================
Write-Step "Creating Environment Files"

function Copy-EnvExample($examplePath, $envPath, $name) {
  if (Test-Path $envPath) {
    Write-Info "$name .env already exists (keeping existing)"
  } elseif (Test-Path $examplePath) {
    Copy-Item $examplePath $envPath
    Write-Success "Created $name .env from example"
  } else {
    Write-Warn "$name .env.example not found at: $examplePath"
  }
}

Copy-EnvExample (Join-Path $repoRoot 'backend\.env.example') (Join-Path $repoRoot 'backend\.env') 'Backend'
Copy-EnvExample (Join-Path $repoRoot 'backend\aps-service\.env.example') (Join-Path $repoRoot 'backend\aps-service\.env') 'APS Service'
Copy-EnvExample (Join-Path $repoRoot 'pointcloud-frontend\.env.example') (Join-Path $repoRoot 'pointcloud-frontend\.env') 'Frontend'

# ============================================================================
# STEP 7: Validate Setup
# ============================================================================
Write-Step "Validating Setup"

$validationPassed = $true

# Check Python imports
Write-Info "Testing Python imports..."
$imports = @('fastapi', 'uvicorn', 'numpy', 'neo4j')
foreach ($mod in $imports) {
  $pyCode = "import $mod; print('$mod OK')"
  $result = & $venvPython -c $pyCode 2>&1
  if ($LASTEXITCODE -eq 0) {
    Write-Success "  $result"
  } else {
    Write-Fail "  Cannot import $mod"
    Write-Host "    Error: $result" -ForegroundColor DarkRed
    $validationPassed = $false
  }
}

# Check .env files exist
Write-Info "Checking .env files..."
$envFiles = @(
  (Join-Path $repoRoot 'backend\.env'),
  (Join-Path $repoRoot 'backend\aps-service\.env'),
  (Join-Path $repoRoot 'pointcloud-frontend\.env')
)
foreach ($envFile in $envFiles) {
  if (Test-Path $envFile) {
    Write-Success "  $(Split-Path -Leaf (Split-Path -Parent $envFile))\.env exists"
  } else {
    Write-Fail "  Missing: $envFile"
    $validationPassed = $false
  }
}

# Check node_modules
Write-Info "Checking node_modules..."
$nodeModuleDirs = @(
  (Join-Path $repoRoot 'pointcloud-frontend\node_modules'),
  (Join-Path $repoRoot 'backend\aps-service\node_modules')
)
foreach ($nmDir in $nodeModuleDirs) {
  if (Test-Path $nmDir) {
    $count = (Get-ChildItem $nmDir -Directory).Count
    Write-Success "  $(Split-Path -Leaf (Split-Path -Parent $nmDir))\node_modules ($count packages)"
  } else {
    Write-Fail "  Missing: $nmDir"
    $validationPassed = $false
  }
}

# ============================================================================
# Summary
# ============================================================================
Write-Header "Setup Complete"

if ($validationPassed) {
  Write-Success "All validations passed!"
} else {
  Write-Warn "Some validations failed - check messages above"
}

Write-Host ""
Write-Host "NEXT STEPS:" -ForegroundColor White
Write-Host "  1. Configure your .env files (especially Neo4j credentials)" -ForegroundColor Gray
Write-Host "     - backend\.env" -ForegroundColor Gray
Write-Host "     - backend\aps-service\.env (if using APS)" -ForegroundColor Gray
Write-Host "     - pointcloud-frontend\.env" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Run the deploy script to start services:" -ForegroundColor Gray
Write-Host "     .\scripts\deploy.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  Or run interactively to configure ports:" -ForegroundColor Gray
Write-Host "     .\scripts\configure.ps1" -ForegroundColor White
Write-Host ""
