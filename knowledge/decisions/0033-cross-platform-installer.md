# ADR 0033: Cross-platform Python installer

- **Status:** accepted
- **Date:** 2026-10-13

## Context
The kit gained a second contributor whose OS may not be Windows. The only
installer, `plugin/install.ps1`, creates a junction and checks nothing, while
every hook runs `python` (absent on many macOS and Linux machines) and the
kit's flow depends on the superpowers plugin, `git` and `gh`.

## Decision
- `plugin/install.py` (standard library only) is the installer on every OS:
  a junction on Windows, a symlink elsewhere, with the same idempotency and
  refusal rules as before.
- Before touching disk it checks that the `python` command the hooks run is
  3.11 or later; otherwise it prints the fix for the OS and exits 1.
- Missing `git`, `gh` or an enabled `superpowers@claude-plugins-official`
  only warn; superpowers is never installed automatically.
- `plugin/install.ps1` stays as a thin wrapper with the same parameters.
- This amends ADR 0005's "created by `plugin/install.ps1`".

## Alternatives
- A parallel `install.sh`: two implementations to keep in sync.
- A marketplace install: rejected in ADR 0005 (cache copy, version bumps).
- A `python3` fallback in `hooks.json`: changes every hook command and
  depends on the hook shell; on Windows `python3` can be the Store stub.
- Installing superpowers automatically: needs the `claude` CLI and changes
  plugin state without a prompt.

## Consequences
One installer, tested on Ubuntu and Windows CI. A machine without a working
`python` cannot install the kit until it has one.
