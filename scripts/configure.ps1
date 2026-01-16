param(
  [switch]$NonInteractive,
  [switch]$Force,
  [switch]$Quiet
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

function Write-Step([string]$msg) {
  if (-not $Quiet) {
    Write-Host "`n==> $msg"
  }
}

function Parse-EnvFile([string]$path) {
  $map = @{}
  if (-not (Test-Path $path)) { return $map }

  foreach ($line in (Get-Content -LiteralPath $path -ErrorAction SilentlyContinue)) {
    if (-not $line) { continue }
    $t = $line.Trim()
    if (-not $t) { continue }
    if ($t.StartsWith('#')) { continue }

    # Support lines like: KEY=value (do not attempt to fully parse quoted dotenv syntax)
    $idx = $t.IndexOf('=')
    if ($idx -lt 1) { continue }

    $key = $t.Substring(0, $idx).Trim()
    $value = $t.Substring($idx + 1)

    if ($value -ne $null) {
      $value = $value.Trim()
      # Strip surrounding quotes if present
      if ($value.Length -ge 2) {
        if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
          $value = $value.Substring(1, $value.Length - 2)
        }
      }
    }

    if ($key) {
      $map[$key] = $value
    }
  }

  return $map
}

function Get-PlainText([System.Security.SecureString]$secure) {
  if ($null -eq $secure) { return '' }
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
  try {
    return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
  } finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
}

function Format-EnvValue([string]$value) {
  if ($null -eq $value) { return '' }

  # Quote values that contain whitespace, #, or double quotes.
  $needsQuotes = $value -match '[\s#"]'
  if (-not $needsQuotes) {
    return $value
  }

  $escaped = $value.Replace('"', '\"')
  return '"' + $escaped + '"'
}

function Prompt-EnvValue(
  [hashtable]$existing,
  [string]$key,
  [string]$label,
  [string]$example,
  [string]$defaultValue,
  [switch]$Secret,
  [switch]$Optional
) {
  $current = $null
  if ($existing.ContainsKey($key)) {
    $current = [string]$existing[$key]
  }

  $effectiveDefault = if ($current -ne $null -and $current -ne '') { $current } else { $defaultValue }

  if ($NonInteractive) {
    return $effectiveDefault
  }

  if ($Secret) {
    $hint = if ($current) { '<kept>' } else { '<empty>' }
    $prompt = "$label ($key) - example: $example (Enter to keep $hint)"
    $secure = Read-Host -AsSecureString $prompt
    $plain = Get-PlainText $secure
    if (-not $plain) {
      if ($current -ne $null) { return $current }
      return ''
    }
    return $plain
  }

  $suffix = ''
  if ($effectiveDefault) {
    $suffix = " [default: $effectiveDefault]"
  } elseif ($Optional) {
    $suffix = ' [optional]'
  }

  $prompt = "$label ($key) - example: $example$suffix"
  $input = Read-Host $prompt

  if (($input -eq $null) -or ($input.Trim() -eq '')) {
    if ($effectiveDefault -ne $null) { return $effectiveDefault }
    return ''
  }

  return $input.Trim()
}

function Ensure-ParentDir([string]$path) {
  $dir = Split-Path -Parent $path
  if ($dir -and (-not (Test-Path $dir))) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
  }
}

function Write-EnvFile([string]$path, [string[]]$lines) {
  Ensure-ParentDir $path
  if ((Test-Path $path) -and (-not $Force)) {
    # We still overwrite if user confirmed by running configure; but keep a backup.
    $backup = "$path.bak.$(Get-Date -Format 'yyyyMMdd-HHmmss')"
    Copy-Item -Force $path $backup
    Write-Host "Backed up existing .env to $backup"
  }

  Set-Content -LiteralPath $path -Value $lines -Encoding utf8
  Write-Host "Wrote $path"
}

Write-Host "SMART_BIM configuration wizard (Windows)"
Write-Host "Repo: $repoRoot"

$backendEnvPath = Join-Path $repoRoot 'backend\.env'
$apsEnvPath = Join-Path $repoRoot 'backend\aps-service\.env'
$frontendEnvPath = Join-Path $repoRoot 'pointcloud-frontend\.env'

$existingBackend = Parse-EnvFile $backendEnvPath
$existingAps = Parse-EnvFile $apsEnvPath
$existingFrontend = Parse-EnvFile $frontendEnvPath

Write-Step 'Backend (FastAPI / Knowledge Graph)'

$NEO4J_URI = Prompt-EnvValue $existingBackend 'NEO4J_URI' 'Neo4j URI' 'neo4j://127.0.0.1:7687' 'neo4j://127.0.0.1:7687'
$NEO4J_USER = Prompt-EnvValue $existingBackend 'NEO4J_USER' 'Neo4j username' 'neo4j' 'neo4j'
$NEO4J_PASSWORD = Prompt-EnvValue $existingBackend 'NEO4J_PASSWORD' 'Neo4j password' '<your-neo4j-password>' '' -Secret
$NEO4J_DATABASE = Prompt-EnvValue $existingBackend 'NEO4J_DATABASE' 'Neo4j database' 'smartbim' 'smartbim'

$BACKEND_HOST = Prompt-EnvValue $existingBackend 'BACKEND_HOST' 'Backend host (bind)' '127.0.0.1' '127.0.0.1' -Optional
$BACKEND_PORT = Prompt-EnvValue $existingBackend 'BACKEND_PORT' 'Backend port' '8000' '8000' -Optional

$LLM_PROVIDER = Prompt-EnvValue $existingBackend 'LLM_PROVIDER' 'LLM provider (ollama|gemini|azure)' 'ollama' 'ollama' -Optional

$OLLAMA_BASE_URL = Prompt-EnvValue $existingBackend 'OLLAMA_BASE_URL' 'Ollama base URL' 'http://localhost:11434' 'http://localhost:11434' -Optional
$OLLAMA_MODEL = Prompt-EnvValue $existingBackend 'OLLAMA_MODEL' 'Ollama chat model tag' 'llama3.2:1b' 'llama3.2:1b' -Optional
$OLLAMA_EMBED_MODEL = Prompt-EnvValue $existingBackend 'OLLAMA_EMBED_MODEL' 'Ollama embed model tag' 'nomic-embed-text:latest' 'nomic-embed-text:latest' -Optional

$GOOGLE_API_KEY = Prompt-EnvValue $existingBackend 'GOOGLE_API_KEY' 'Google Gemini API key (for /chat)' '<your-google-api-key>' '' -Secret -Optional

Write-Step 'Azure OpenAI (optional)'
$AZURE_OPENAI_ENDPOINT = Prompt-EnvValue $existingBackend 'AZURE_OPENAI_ENDPOINT' 'Azure OpenAI endpoint' 'https://your-resource.openai.azure.com' '' -Optional
$AZURE_OPENAI_API_KEY = Prompt-EnvValue $existingBackend 'AZURE_OPENAI_API_KEY' 'Azure OpenAI API key' '<your-azure-openai-key>' '' -Secret -Optional
$AZURE_OPENAI_DEPLOYMENT = Prompt-EnvValue $existingBackend 'AZURE_OPENAI_DEPLOYMENT' 'Azure OpenAI deployment name' 'gpt-4o' 'gpt-4o' -Optional
$AZURE_OPENAI_API_VERSION = Prompt-EnvValue $existingBackend 'AZURE_OPENAI_API_VERSION' 'Azure OpenAI API version' '2024-08-01-preview' '2024-08-01-preview' -Optional

Write-Step 'APS (Autodesk Platform Services)'
$APS_SERVICE_PORT = Prompt-EnvValue $existingBackend 'APS_SERVICE_PORT' 'APS service port' '3001' '3001' -Optional
$APS_CLIENT_ID = Prompt-EnvValue $existingBackend 'APS_CLIENT_ID' 'APS Client ID' '<your-aps-client-id>' '' -Optional
$APS_CLIENT_SECRET = Prompt-EnvValue $existingBackend 'APS_CLIENT_SECRET' 'APS Client Secret' '<your-aps-client-secret>' '' -Secret -Optional
$APS_CALLBACK_URL = Prompt-EnvValue $existingBackend 'APS_CALLBACK_URL' 'APS OAuth callback URL (3-legged)' 'http://127.0.0.1:3001/aps/oauth/callback' "http://127.0.0.1:$APS_SERVICE_PORT/aps/oauth/callback" -Optional
$APS_SCOPES = Prompt-EnvValue $existingBackend 'APS_SCOPES' 'APS scopes (2-legged)' 'data:read' 'data:read' -Optional
$APS_OAUTH_SCOPES = Prompt-EnvValue $existingBackend 'APS_OAUTH_SCOPES' 'APS OAuth scopes (3-legged)' 'data:read viewables:read' 'data:read viewables:read' -Optional
$APS_CORS_ORIGINS = Prompt-EnvValue $existingBackend 'APS_CORS_ORIGINS' 'APS CORS origins (comma-separated)' 'http://localhost:5173,http://127.0.0.1:5173' 'http://localhost:5173,http://127.0.0.1:5173' -Optional

$APS_BUCKET_KEY = Prompt-EnvValue $existingBackend 'APS_BUCKET_KEY' 'APS OSS bucket key' 'smartbim-demo-bucket' 'smartbim-demo-bucket' -Optional
$APS_OSS_REGION = Prompt-EnvValue $existingBackend 'APS_OSS_REGION' 'APS OSS region (US|EMEA)' 'US' 'US' -Optional

$APS_STORE = Prompt-EnvValue $existingBackend 'APS_STORE' 'APS session store (memory|redis)' 'memory' 'memory' -Optional
$REDIS_URL = Prompt-EnvValue $existingBackend 'REDIS_URL' 'Redis URL (used when APS_STORE=redis)' 'redis://127.0.0.1:6379' 'redis://127.0.0.1:6379' -Optional
$APS_SESSION_TTL_SECONDS = Prompt-EnvValue $existingBackend 'APS_SESSION_TTL_SECONDS' 'APS session TTL seconds' '86400' '86400' -Optional

Write-Step 'Frontend integration'
$FRONTEND_MODE = Prompt-EnvValue $existingBackend 'FRONTEND_MODE' 'Frontend mode (proxy|static)' 'proxy' 'proxy' -Optional
$FRONTEND_DEV_URL = Prompt-EnvValue $existingBackend 'FRONTEND_DEV_URL' 'Frontend dev server URL' 'http://localhost:5173' 'http://localhost:5173' -Optional
$FRONTEND_DIST_DIR = Prompt-EnvValue $existingBackend 'FRONTEND_DIST_DIR' 'Frontend dist dir (static mode)' '../../pointcloud-frontend/dist' '../../pointcloud-frontend/dist' -Optional

# Derived values for the frontend .env
$VITE_BACKEND_API_URL = Prompt-EnvValue $existingFrontend 'VITE_BACKEND_API_URL' 'Vite backend API URL' 'http://127.0.0.1:8000' "http://127.0.0.1:$BACKEND_PORT" -Optional
$VITE_APS_API_URL = Prompt-EnvValue $existingFrontend 'VITE_APS_API_URL' 'Vite APS API URL' 'http://127.0.0.1:3001' "http://127.0.0.1:$APS_SERVICE_PORT" -Optional

# --- Write backend/.env ---
$backendLines = @(
  '# =============================================================================',
  '# SMART_BIM (BIMTwinOps) - generated by scripts/configure.ps1',
  "# Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
  '# =============================================================================',
  '',
  '# --- Neo4j (required for KG features) ---',
  "NEO4J_URI=$(Format-EnvValue $NEO4J_URI)",
  "NEO4J_USER=$(Format-EnvValue $NEO4J_USER)",
  "NEO4J_PASSWORD=$(Format-EnvValue $NEO4J_PASSWORD)",
  "NEO4J_DATABASE=$(Format-EnvValue $NEO4J_DATABASE)",
  '',
  '# --- Backend server ---',
  "BACKEND_HOST=$(Format-EnvValue $BACKEND_HOST)",
  "BACKEND_PORT=$(Format-EnvValue $BACKEND_PORT)",
  '',
  '# --- LLM ---',
  "LLM_PROVIDER=$(Format-EnvValue $LLM_PROVIDER)",
  "GOOGLE_API_KEY=$(Format-EnvValue $GOOGLE_API_KEY)",
  "OLLAMA_BASE_URL=$(Format-EnvValue $OLLAMA_BASE_URL)",
  "OLLAMA_MODEL=$(Format-EnvValue $OLLAMA_MODEL)",
  "OLLAMA_EMBED_MODEL=$(Format-EnvValue $OLLAMA_EMBED_MODEL)",
  '',
  '# --- Azure OpenAI (optional) ---',
  "AZURE_OPENAI_ENDPOINT=$(Format-EnvValue $AZURE_OPENAI_ENDPOINT)",
  "AZURE_OPENAI_API_KEY=$(Format-EnvValue $AZURE_OPENAI_API_KEY)",
  "AZURE_OPENAI_DEPLOYMENT=$(Format-EnvValue $AZURE_OPENAI_DEPLOYMENT)",
  "AZURE_OPENAI_API_VERSION=$(Format-EnvValue $AZURE_OPENAI_API_VERSION)",
  '',
  '# --- APS (Autodesk Platform Services) ---',
  "APS_SERVICE_PORT=$(Format-EnvValue $APS_SERVICE_PORT)",
  "APS_CLIENT_ID=$(Format-EnvValue $APS_CLIENT_ID)",
  "APS_CLIENT_SECRET=$(Format-EnvValue $APS_CLIENT_SECRET)",
  "APS_SCOPES=$(Format-EnvValue $APS_SCOPES)",
  "APS_CALLBACK_URL=$(Format-EnvValue $APS_CALLBACK_URL)",
  "APS_OAUTH_SCOPES=$(Format-EnvValue $APS_OAUTH_SCOPES)",
  "APS_CORS_ORIGINS=$(Format-EnvValue $APS_CORS_ORIGINS)",
  "APS_STORE=$(Format-EnvValue $APS_STORE)",
  "REDIS_URL=$(Format-EnvValue $REDIS_URL)",
  "APS_SESSION_TTL_SECONDS=$(Format-EnvValue $APS_SESSION_TTL_SECONDS)",
  "APS_BUCKET_KEY=$(Format-EnvValue $APS_BUCKET_KEY)",
  "APS_OSS_REGION=$(Format-EnvValue $APS_OSS_REGION)",
  '',
  '# --- Frontend hosting (APS service entrypoint) ---',
  "FRONTEND_MODE=$(Format-EnvValue $FRONTEND_MODE)",
  "FRONTEND_DEV_URL=$(Format-EnvValue $FRONTEND_DEV_URL)",
  "FRONTEND_DIST_DIR=$(Format-EnvValue $FRONTEND_DIST_DIR)"
)

Write-EnvFile $backendEnvPath $backendLines

# --- Write backend/aps-service/.env ---
$apsLines = @(
  '# Generated by scripts/configure.ps1',
  '# Note: aps-service also loads ../.env by default; this file is optional.',
  '',
  "APS_SERVICE_PORT=$(Format-EnvValue $APS_SERVICE_PORT)",
  "APS_CLIENT_ID=$(Format-EnvValue $APS_CLIENT_ID)",
  "APS_CLIENT_SECRET=$(Format-EnvValue $APS_CLIENT_SECRET)",
  "APS_SCOPES=$(Format-EnvValue $APS_SCOPES)",
  "APS_CALLBACK_URL=$(Format-EnvValue $APS_CALLBACK_URL)",
  "APS_OAUTH_SCOPES=$(Format-EnvValue $APS_OAUTH_SCOPES)",
  "APS_CORS_ORIGINS=$(Format-EnvValue $APS_CORS_ORIGINS)",
  "APS_STORE=$(Format-EnvValue $APS_STORE)",
  "REDIS_URL=$(Format-EnvValue $REDIS_URL)",
  "APS_SESSION_TTL_SECONDS=$(Format-EnvValue $APS_SESSION_TTL_SECONDS)",
  "APS_BUCKET_KEY=$(Format-EnvValue $APS_BUCKET_KEY)",
  "APS_OSS_REGION=$(Format-EnvValue $APS_OSS_REGION)",
  '',
  "FRONTEND_MODE=$(Format-EnvValue $FRONTEND_MODE)",
  "FRONTEND_DEV_URL=$(Format-EnvValue $FRONTEND_DEV_URL)",
  "FRONTEND_DIST_DIR=$(Format-EnvValue $FRONTEND_DIST_DIR)"
)

Write-EnvFile $apsEnvPath $apsLines

# --- Write pointcloud-frontend/.env ---
$frontendLines = @(
  '# Generated by scripts/configure.ps1',
  '# Vite env vars must start with VITE_ to be exposed to the browser.',
  '',
  "VITE_BACKEND_API_URL=$(Format-EnvValue $VITE_BACKEND_API_URL)",
  "VITE_APS_API_URL=$(Format-EnvValue $VITE_APS_API_URL)"
)

Write-EnvFile $frontendEnvPath $frontendLines

Write-Step 'Configuration complete'
Write-Host "Next: run .\\scripts\\bootstrap.ps1 (or .\\scripts\\install.ps1 when available)"