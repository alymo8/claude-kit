<#
.SYNOPSIS
  Install claude-kit as a Claude Code skills-dir plugin (Windows wrapper).

.DESCRIPTION
  Runs plugin\install.py, the cross-platform installer (ADR 0033), with the
  same parameters. It junctions <SkillsDir>\claude-kit to this plugin folder,
  checks the prerequisites (python 3.11+, git, gh, the superpowers plugin) and
  adds the kit's status line when none is configured. Idempotent; refuses to
  overwrite anything else at that path.

.PARAMETER SkillsDir
  Where Claude Code looks for skills-dir plugins. Default: ~\.claude\skills

.PARAMETER Settings
  Claude Code user settings file. Default: ~\.claude\settings.json
#>
param(
  [string]$SkillsDir = (Join-Path $HOME ".claude\skills"),
  [string]$Settings = (Join-Path $HOME ".claude\settings.json")
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "ERROR: python not found on PATH; install Python 3.11+."
  exit 1
}
& python (Join-Path $PSScriptRoot "install.py") --skills-dir $SkillsDir --settings $Settings
exit $LASTEXITCODE
