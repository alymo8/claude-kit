# ADR 0007: Hook handlers are Python scripts that always exit 0

- **Status:** accepted
- **Date:** 2026-09-14

## Context
Hook commands run on Windows (Git Bash / PowerShell) and, in CI, on Linux. Shell
scripts differ between those; Python is present everywhere the kit is used. A
hook that exits non-zero can block or interrupt Claude's work.

## Decision
Hook handlers are Python scripts invoked as `python "${CLAUDE_PLUGIN_ROOT}/hooks/
<name>.py"`, reading the event JSON from stdin. They catch every exception,
report on stderr, and always exit 0. They never open a browser and never delete.

## Consequences
Predictable behaviour on every platform; a broken hook degrades to a no-op with
a stderr line instead of stopping work. Python must be on PATH as `python`.
