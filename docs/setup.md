# Setting up the kit

How to install agent-kit on a new machine, on Windows, macOS or Linux, and
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
  - macOS: install Homebrew `python@3` and put its `libexec/bin` folder
    (`$(brew --prefix)/opt/python@3/libexec/bin`) on `PATH` in
    `~/.zprofile`, then restart the Claude app. A shell alias does not work:
    hooks run in a non-interactive shell, which ignores aliases.
  - Linux: install the `python-is-python3` package, or link `python` to
    `python3` on your `PATH`.

## Install

In Claude Code, run:

```
/plugin install superpowers@claude-plugins-official
/plugin marketplace add alymo8/claude-kit
/plugin install agent-kit@agent-kit
```

Optionally run `/agent-kit:statusline` to add the kit's status line.

To update, marketplace users get a new version through `/plugin` when the
version changes.

### For your company admin

Managed work laptops often allowlist the sources plugins may come from, so
the marketplace commands above fail until an admin allows them. Add this to
the managed settings to allow the kit and superpowers, and to install both
for every user:

```json
{
  "strictKnownMarketplaces": [
    {"source": "github", "repo": "anthropics/claude-plugins-official"},
    {"source": "github", "repo": "alymo8/claude-kit"},
    {"source": "skills-dir"}
  ],
  "extraKnownMarketplaces": {
    "agent-kit": {"source": {"source": "github", "repo": "alymo8/claude-kit"}}
  },
  "enabledPlugins": {
    "agent-kit@agent-kit": true,
    "superpowers@claude-plugins-official": true
  }
}
```

`{"source": "skills-dir"}` keeps the contributor install (a link under
`~/.claude/skills/`) working. See
<https://code.claude.com/docs/en/plugins/org.md> for where managed settings
live and what each key does.

### From a checkout (contributors)

```
git clone https://github.com/alymo8/claude-kit.git agent-kit
cd agent-kit
python plugin/install.py
```

The installer detects the OS (Windows, macOS or Linux) and prints it; it
never asks. It checks `python` first and stops with the fix for that OS if it
is missing or older than 3.11, changing nothing. On macOS the fix names the
exact Homebrew folder to add when one is installed. It then links
`~/.claude/skills/agent-kit` to the checkout's `plugin/` folder (a junction
on Windows, a symlink elsewhere), so the kit loads in place and edits are
live. It adds the kit's status line to `~/.claude/settings.json` when none is
set, and warns if `git`, `gh` or superpowers is missing. Running it again is
safe. Start a new Claude Code session (or run `/reload-plugins`) afterwards.
The installer removes the old link from before the rename to `agent-kit` and
migrates its status line,
and does not link when the marketplace copy of `agent-kit` is installed.

On Windows you can also run `plugin\install.ps1`, which wraps the same
installer. If PowerShell refuses to run it (execution policy), use
`powershell -ExecutionPolicy Bypass -File plugin\install.ps1`.

To update a checkout, `git pull` in it. Skill and command edits are live;
hook edits need a new session or `/reload-plugins`.

## Using the kit with Vibe, Codex or Cursor

The kit also runs in Mistral Vibe, Codex and Cursor (ADR 0050). From the
checkout, run the installer once per agent:

```
python plugin/install.py --agent vibe
python plugin/install.py --agent codex
python plugin/install.py --agent cursor
```

On Windows, `plugin\install.ps1 -Agent vibe` (or `codex`, `cursor`) does the
same. For that agent the installer:

- links the kit skills, one wrapper skill per kit command and the bundled
  superpowers skills (`vendor/superpowers/`) into `~/.agents/skills/`;
- adds the kit's hook runner (`plugin/hooks/run.py`) to the agent's user hook
  file (`~/.vibe/hooks.toml`, `~/.codex/hooks.json` or
  `~/.cursor/hooks.json`), which injects the workspace rules, kit map
  and handoff at session start;
- for Vibe and Codex, adds a fallback line to `~/.vibe/AGENTS.md` or
  `~/.codex/AGENTS.md` that tells the agent to run the runner itself when the
  kit map is missing from its context.

`--home` changes the base of every default path, and `--skills-dir` and
`--python` work as for Claude Code. Rerunning is safe: it relinks moved
skills and removes links to skills that no longer exist. The installer does
not read `CODEX_HOME` or `VIBE_HOME`: if you moved an agent's home, link the
skills and edit its hook file by hand, or point `--home` at the folder that
holds `.codex` or `.vibe`. Links into a kit checkout you have since deleted
are reported as `Skipped`; remove them by hand and rerun.

Vibe, Codex and Cursor users: rerun the installer after updating the
checkout, once per agent, until a native Vibe plugin exists.

Next steps:

- Codex: run `/hooks` and trust the agent-kit hooks.
- Vibe and Cursor: start a new session.
- Cursor runs session-start hooks without waiting for them, so the kit map
  may not reach the model. If it does not, paste the line the installer
  prints into Cursor's user rules.

Claude-only: `/ship-many`, the status line, `token-report.py`, `audit --user`,
and the transcript, precompact and spec-edit hooks. In other agents `/ship`
and `/ship-fast` run in one session and use subagents where the agent has
them.

For kit developers: after editing a command, run
`python plugin/scripts/agent-skills.py` to regenerate its wrapper skill. To
refresh the bundled superpowers, run
`python plugin/scripts/vendor-superpowers.py --from <dir>`, where `<dir>` is a
superpowers checkout or its Claude Code plugin cache folder, and commit the
result.

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
`CLAUDE_KIT_AGENT` is not a switch to set by hand; `plugin/hooks/run.py` sets
it to `vibe`, `codex` or `cursor` for the hooks it runs.

| Variable | Default | Effect |
|---|---|---|
| `CLAUDE_KIT_LEAN_CONTEXT` | on | `0` stops injecting the lean-context rule (also deny `Skill(agent-kit:lean-context)`) |
| `CLAUDE_KIT_PRECOMPACT` | on | `0` stops steering the compaction summary toward dead ends and open problems |
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

## Personal vault

The personal-vault tooling moved out of the kit into the second-brain-kit
plugin; install that plugin to use a vault (ADR 0051).

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
