param(
  [switch]$NonInteractive,
  [switch]$ForceEnv,
  [switch]$SkipPython,
  [switch]$SkipNode,
  [switch]$SkipPointNet,
  [switch]$SkipConfigure,
  [switch]$Start,
  [switch]$All,
  [switch]$Aps,
  [switch]$Frontend,
  [switch]$Api
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

function Write-Step([string]$msg) {
  Write-Host "`n==> $msg"
}

Write-Host "SMART_BIM auto installer (Windows)"
Write-Host "Repo: $repoRoot"

if (-not $SkipConfigure) {
  Write-Step 'Collecting configuration (prompts with examples)'
  & (Join-Path $PSScriptRoot 'configure.ps1') -NonInteractive:$NonInteractive -Force:$ForceEnv
}

Write-Step 'Installing dependencies (Python/Node)'
& (Join-Path $PSScriptRoot 'bootstrap.ps1') -SkipPython:$SkipPython -SkipNode:$SkipNode -SkipPointNet:$SkipPointNet -ForceEnv:$ForceEnv

if ($Start) {
  Write-Step 'Starting services'
  $startArgs = @()
  if ($All -or (-not ($Aps -or $Frontend -or $Api))) {
    $startArgs += '-All'
  } else {
    if ($Aps) { $startArgs += '-Aps' }
    if ($Frontend) { $startArgs += '-Frontend' }
    if ($Api) { $startArgs += '-Api' }
  }

  & (Join-Path $PSScriptRoot 'start-services.ps1') @startArgs
}

Write-Step 'Done'
Write-Host 'Tips:'
Write-Host '  - Start: .\scripts\start-services.ps1 -All'
Write-Host '  - Stop : .\scripts\stop-services.ps1 -All -Force'
Write-Host '  - Logs : .\.pids\*.out.log / *.err.log'
Write-Host ''
Write-Host 'Notes:'
Write-Host '  - If you change .env values, restart the affected service(s).'
Write-Host '    (Especially the Vite frontend: it reads VITE_* vars at startup.)'
Write-Host '  - If the API port is already in use, re-run .\scripts\configure.ps1 to pick a free port.'
Write-Host '  - PointNet segmentation weights are not bundled. If missing, /upload may run in fallback mode.'
