<#
.SYNOPSIS
  Install claude-kit as a Claude Code skills-dir plugin.

.DESCRIPTION
  Creates a junction  <SkillsDir>\claude-kit  ->  this plugin folder, so Claude Code
  loads the kit's skills, hooks and commands directly from the git checkout.
  Idempotent: re-running when already installed is a no-op. Refuses to overwrite
  anything else at that path.

.PARAMETER SkillsDir
  Where Claude Code looks for skills-dir plugins. Default: ~\.claude\skills
#>
param(
  [string]$SkillsDir = (Join-Path $HOME ".claude\skills")
)

$ErrorActionPreference = "Stop"
$target = (Resolve-Path $PSScriptRoot).Path
$link = Join-Path $SkillsDir "claude-kit"

function Normalize-Path([string]$path) {
  return [System.IO.Path]::GetFullPath($path).TrimEnd('\')
}

if (-not (Test-Path $SkillsDir)) {
  New-Item -ItemType Directory -Path $SkillsDir | Out-Null
}

if (Test-Path $link) {
  $item = Get-Item $link -Force
  $existingTarget = $null
  if ($item.LinkType) { $existingTarget = @($item.Target)[0] }
  if ($existingTarget) {
    $resolvedExisting = Normalize-Path (Resolve-Path $existingTarget).Path
    $resolvedTarget = Normalize-Path $target
    if ($resolvedExisting -ieq $resolvedTarget) {
      Write-Host "claude-kit already installed: $link -> $target"
      exit 0
    }
  }
  Write-Host "ERROR: $link already exists and is not a junction to $target. Remove it first."
  exit 1
}

New-Item -ItemType Junction -Path $link -Target $target | Out-Null
Write-Host "Installed: $link -> $target"
Write-Host "Start a new Claude Code session (or run /reload-plugins) to load the kit."
exit 0
