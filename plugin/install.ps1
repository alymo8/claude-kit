<#
.SYNOPSIS
  Install claude-kit as a Claude Code skills-dir plugin.

.DESCRIPTION
  Creates a junction  <SkillsDir>\claude-kit  ->  this plugin folder, so Claude Code
  loads the kit's skills, hooks and commands directly from the git checkout.
  Idempotent: re-running when already installed is a no-op. Refuses to overwrite
  anything else at that path. Also adds the kit's status line to user settings
  when none is configured.

.PARAMETER SkillsDir
  Where Claude Code looks for skills-dir plugins. Default: ~\.claude\skills
#>
param(
  [string]$SkillsDir = (Join-Path $HOME ".claude\skills"),
  [string]$Settings = (Join-Path $HOME ".claude\settings.json")
)

$ErrorActionPreference = "Stop"
$target = (Resolve-Path $PSScriptRoot).Path
$link = Join-Path $SkillsDir "claude-kit"

function Normalize-Path([string]$path) {
  return [System.IO.Path]::GetFullPath($path).TrimEnd('\')
}

function Install-StatusLine {
  $script = Join-Path $PSScriptRoot "scripts\install-statusline.py"
  $previous = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $out = & python $script --settings $Settings --skills-dir $SkillsDir
    if ($LASTEXITCODE -ne 0) {
      Write-Host ("WARNING: status line not configured (install-statusline.py " +
        "exited $LASTEXITCODE); see the message above.")
    } elseif ($out) {
      Write-Host ($out -join "`n")
    }
  } catch {
    Write-Host "WARNING: could not run install-statusline.py (is python on PATH?): $_"
  } finally {
    $ErrorActionPreference = $previous
  }
}

if (-not (Test-Path $SkillsDir)) {
  New-Item -ItemType Directory -Path $SkillsDir | Out-Null
}

if (Test-Path $link) {
  $item = Get-Item $link -Force
  $existingTarget = $null
  if ($item.LinkType) { $existingTarget = @($item.Target)[0] }
  if ($existingTarget -and (Test-Path -LiteralPath $existingTarget) -and
      ((Normalize-Path $existingTarget) -ieq (Normalize-Path $target))) {
    Write-Host "claude-kit already installed: $link -> $target"
    Install-StatusLine
    exit 0
  }
  Write-Host "ERROR: $link already exists and is not a junction to $target. Remove it first."
  exit 1
}

New-Item -ItemType Junction -Path $link -Target $target | Out-Null
Write-Host "Installed: $link -> $target"
Install-StatusLine
Write-Host "Start a new Claude Code session (or run /reload-plugins) to load the kit."
exit 0
