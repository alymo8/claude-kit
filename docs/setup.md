# Setting up the kit

How to install claude-kit on a new machine, on Windows, macOS or Linux, and
work the same way as everyone else on the team.

## Prerequisites

- **Claude Code** (CLI, desktop app or IDE extension).
- **The superpowers plugin.** The kit's flow uses its skills (brainstorming,
  writing plans, worktrees, test-driven development, verification). In
  Claude Code run `/plugin install superpowers@claude-plugins-official`.
- **git** and **gh**, the GitHub CLI, signed in (`gh auth login`). `/ship`
  and the worktree flow need both.
- **Python 3.11 or later, reachable as `python`.** Every hook runs
  `python`, so `python3` alone is not enough:
  - Windows: install Python from python.org with "Add python.exe to PATH"
    ticked.
  - macOS: install Homebrew `python@3` and put its `libexec/bin` folder on
    `PATH`, or make `python` an alias of `python3`.
  - Linux: install the `python-is-python3` package, or link `python` to
    `python3` on your `PATH`.

## Install

```
git clone https://github.com/alymo8/claude-kit.git
cd claude-kit
python plugin/install.py
```

The installer checks `python` first and stops with the fix if it is missing
or older than 3.11, changing nothing. It then links
`~/.claude/skills/claude-kit` to the checkout's `plugin/` folder (a junction
on Windows, a symlink elsewhere), so the kit loads in place and edits are
live. It adds the kit's status line to `~/.claude/settings.json` when none is
set, and warns if `git`, `gh` or superpowers is missing. Running it again is
safe. Start a new Claude Code session (or run `/reload-plugins`) afterwards.

On Windows you can also run `plugin\install.ps1`, which wraps the same
installer. If PowerShell refuses to run it (execution policy), use
`powershell -ExecutionPolicy Bypass -File plugin\install.ps1`.

To update, `git pull` in the checkout. Skill and command edits are live;
hook edits need a new session or `/reload-plugins`.

## Where project repos live

Either works:

- **Inside the kit checkout** (a folder beside `plugin/`). Claude Code loads
  the workspace [`CLAUDE.md`](../CLAUDE.md) as a parent-folder file. The
  checkout's `.gitignore` keeps those folders out of the kit repo.
- **Anywhere else.** A session-start hook injects the same workspace rules,
  without the kit-development section, and the kit map gives the playbooks'
  absolute paths.

## Switches

Set these under `env` in `~/.claude/settings.json`.

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_KIT_LEAN_CONTEXT` | on | `0` stops injecting the lean-context rule (also deny `Skill(claude-kit:lean-context)`) |
| `CLAUDE_KIT_KIT_MAP` | on | `0` stops injecting the kit map |
| `CLAUDE_KIT_WORKSPACE_RULES` | on | `0` stops injecting the workspace rules in repos outside the kit folder |
| `CLAUDE_KIT_GRILL` | off | `1` turns on the spec grill before a spec is written |
| `CLAUDE_KIT_NUDGE_AT` | 300000 | context tokens at which the first `/handoff` nudge fires |
| `CLAUDE_KIT_NUDGE_STEP` | 100000 | tokens between later nudges |

## Docker Desktop on Windows

Docker Desktop keeps its data in `%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`.
The file grows as Docker writes and does not shrink when data is deleted,
unless the distro is sparse. The one-time fix is to quit Docker Desktop, then
run `wsl --manage docker-desktop --set-sparse true`. Optionally cap the build
cache in Docker Desktop, Settings, Docker Engine:
`"builder": {"gc": {"enabled": true, "defaultKeepStorage": "5GB"}}`. The kit
never changes these settings itself.

`python plugin/scripts/docker-disk.py` shows the state, and `/ship`'s clean-up
prints it when a task used Docker. `/docker-compact` reclaims space that has
already built up: it asks first, stops Docker and needs one UAC prompt.

## How changes ship

The flow is in the [README](../README.md): brainstorm, spec, spec gate,
plan, plan gate, build test-first in a worktree, CI, review, merge.
`/ship <spec.md>` runs it from an approved spec to a merged change, and
`/ship-fast` is the light path for a POC ([overview](ship-fast.md)).
`/ship` squash-merges its own pull request once CI is green and its review
findings are fixed; it does not wait for a human approval.

## Contributing to the kit

- Install the dev dependencies once:
  `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`.
- Before pushing: `pytest`, `ruff check plugin tests`,
  `ruff format --check plugin tests`. CI runs them on Ubuntu and Windows.
- Changes go through a feature branch and a pull request
  ([ADR 0006](../knowledge/decisions/0006-kit-main-gate.md)).
- This repo is public: never write the names of private repos or a
  machine's username into tracked files. Use `%USERPROFILE%` or
  `<repo-root>` in paths, and grep your diff before committing.
