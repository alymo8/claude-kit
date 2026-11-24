<#
.SYNOPSIS
  Install agent-kit as a Claude Code skills-dir plugin (Windows wrapper).

.DESCRIPTION
  Runs plugin\install.py, the cross-platform installer (ADR 0033), with the
  same parameters. It junctions <SkillsDir>\agent-kit to this plugin folder,
  checks the prerequisites (python 3.11+, git, gh, the superpowers plugin) and
  adds the kit's status line when none is configured. Idempotent; refuses to
  overwrite anything else at that path. With -Agent codex or cursor it links
  the kit's skills into <Home>\.agents\skills and merges the kit's hook runner
  into that agent's user hook file instead. With -Agent vibe it installs the
  agent-kit and superpowers Vibe plugins under <Home>\.vibe\plugins and removes
  the old Vibe install.

.PARAMETER SkillsDir
  Where the agent looks for skills. Default: <Home>\.claude\skills for
  claude, <Home>\.agents\skills for the other agents. For vibe it only names
  where old kit skill links are removed.

.PARAMETER Settings
  Claude Code user settings file. Default: <Home>\.claude\settings.json

.PARAMETER Agent
  The agent to install for: claude (default), vibe, codex or cursor.

.PARAMETER Home
  The home folder every default is built from. Default: ~
#>
param(
  [string]$SkillsDir,
  [string]$Settings,
  [ValidateSet("claude", "vibe", "codex", "cursor")][string]$Agent = "claude",
  [Alias("Home")][string]$HomeDir
)

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "ERROR: python not found on PATH; install Python 3.11+."
  exit 1
}
$arguments = @((Join-Path $PSScriptRoot "install.py"), "--agent", $Agent)
if ($HomeDir) { $arguments += @("--home", $HomeDir) }
if ($Agent -eq "claude") {
  $base = if ($HomeDir) { $HomeDir } else { $HOME }
  if (-not $SkillsDir) { $SkillsDir = Join-Path $base ".claude\skills" }
  if (-not $Settings) { $Settings = Join-Path $base ".claude\settings.json" }
}
if ($SkillsDir) { $arguments += @("--skills-dir", $SkillsDir) }
if ($Settings) { $arguments += @("--settings", $Settings) }
& python @arguments
exit $LASTEXITCODE
