# Kit foundation: plugin packaging, hooks, tests, decision log

- **Status:** approved
- **Date:** 2026-09-14

## Purpose

This repo (`alymo8/claude-kit`, checked out at `Desktop/Github`) holds the
workspace-level way of working: `CLAUDE.md`, the five conventions, a shared spec
renderer, and one skill. A review on 2026-09-14 found that the parts meant to be
*enforced* are only *described*:

- `skills/supabase-cli` is never loaded by Claude Code (nothing wires it in).
- "Regenerate the HTML whenever the `.md` changes" and "a feature is not done until
  its worktree and branch are gone" depend on the model remembering; three of four
  adopting repos had drifted HTML and all three active repos had leftover worktrees.
- The repo preaches tests, CI, and ADRs and has none of its own.

This spec turns the kit into a real Claude Code plugin with hooks that enforce the
two rules above, gives the repo a test suite and CI, and records its decisions as
ADRs.

## Scope

**In:**

1. Restructure into a `plugin/` subfolder that is a valid Claude Code plugin,
   delivered as a *skills-dir plugin* through a junction
   `~/.claude/skills/claude-kit -> Github/plugin`.
2. Two hooks: auto-render spec/plan HTML after edits; advisory stale-worktree audit
   at session start.
3. `pyproject.toml` (pinned deps, ruff, pytest), a pytest suite, and a GitHub
   Actions workflow running on Ubuntu and Windows.
4. `knowledge/decisions/` with an index, a template, and seven backfilled ADRs.
5. Trim the "Building a new feature" section of `CLAUDE.md` to what is unique to
   this workspace, pointing at the two superpowers skills that own the rest.

**Out (later specs):**

- The `/new-project` scaffolder, workflow templates for project repos (CI, AI
  review, secret scan), and spec lifecycle statuses / index: *Spec 2*.
- Any change to project repos beyond what the hooks do at
  runtime.
- Marketplace distribution (`marketplace.json`). The layout keeps it possible.

## Design

### 1. Repo layout

```
Github/                          repo root: workspace preferences (role unchanged)
  CLAUDE.md  README.md  .gitignore  pyproject.toml
  conventions/                   unchanged
  knowledge/decisions/           NEW: README.md index, 0000-template.md, 0001-0007
  docs/superpowers/specs/        NEW: this spec (dogfooding); .html is gitignored
  docs/superpowers/plans/        NEW: its plan
  plugin/                        NEW: the Claude Code plugin; the junction target
    .claude-plugin/plugin.json   {"name": "claude-kit", "version", "description"}
    skills/supabase-cli/         moved from /skills, content unchanged
    scripts/render-spec.py       moved from /scripts, content unchanged
    hooks/hooks.json             hook declarations
    hooks/on_spec_edit.py        PostToolUse handler
    hooks/worktree_audit.py      SessionStart handler
    install.ps1                  creates the junction; idempotent
  tests/                         NEW: pytest suite
  .github/workflows/ci.yml       NEW: kit CI
```

- `.gitignore` whitelist becomes `!/.gitignore !/CLAUDE.md !/README.md
  !/pyproject.toml !/conventions/ !/plugin/ !/knowledge/ !/docs/ !/tests/
  !/.github/`; `!/scripts/` and `!/skills/` are removed. The secrets guard stays;
  `docs/superpowers/**/*.html` is added.
- `CLAUDE.md`'s renderer command becomes `python ../plugin/scripts/render-spec.py`.
- `plugin.json` carries only `name`, `version`, `description`. Skills load from
  `plugin/skills/` by default; hooks from `plugin/hooks/hooks.json`. Skills are
  addressed as `claude-kit:<name>`.
- `install.ps1`: if `~/.claude/skills/claude-kit` does not exist, create a junction
  to the script's own `plugin/` directory; if it exists and points elsewhere, print
  the conflict and exit 1; if it already points here, print "already installed".
  `README.md` documents it as the one-time per-machine step.

### 2. Hooks

Both handlers are Python 3 scripts (Python is on every machine here and sidesteps
bash-vs-PowerShell differences in hook commands). Each reads the hook JSON event
from stdin, does its work, and **always exits 0**: a hook must never block work.
Any internal error is swallowed (printed to stderr) rather than raised.

`hooks/hooks.json`:

```json
{
  "hooks": {
    "PostToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{ "type": "command",
                  "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/on_spec_edit.py\"" }]
    }],
    "SessionStart": [{
      "hooks": [{ "type": "command",
                  "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/worktree_audit.py\"" }]
    }]
  }
}
```

**`on_spec_edit.py`** reads `tool_input.file_path`; if it matches
`docs/superpowers/(specs|plans)/<name>.md` (path separators normalised), it runs
`render-spec.py` on that single file. Otherwise it is a no-op. It never opens a
browser; opening stays a Claude action per `CLAUDE.md`. It locates
`render-spec.py` relative to its own file (`../scripts/`), so it works both through
the junction and in the checkout.

**`worktree_audit.py`**, when `cwd` is inside a git work tree:

1. `git worktree list --porcelain`: every worktree except the main one.
2. Local branches other than `main`/`master` that are either already merged into
   the default branch (`git branch --merged <default>`) or have no upstream.

If either list is non-empty, print one short block, e.g.

```
[claude-kit] Leftover from earlier feature work in this repo:
  worktrees: .claude/worktrees/ui-found (feat/ui-foundation)
  branches:  feat/ui-foundation (merged), worktree-x (no upstream)
Clean up with superpowers:finishing-a-development-branch once the work is landed.
```

If both are empty, or `cwd` is not a git repo, print nothing. Read-only: it never
deletes or prunes. The default branch is `main` if it exists, else `master`.

### 3. Tests, tooling, CI

- `pyproject.toml`: project metadata; `dependencies = ["markdown~=3.10"]`;
  `[dependency-groups] dev = ["pytest", "ruff"]`; ruff config (line length 88,
  default rules); pytest `testpaths = ["tests"]`. The repo is not a package, so
  install for development with `pip install markdown~=3.10 pytest ruff` (CI does
  the same); no build backend.
- Commands, recorded in `README.md`: `pytest` (all),
  `pytest tests/test_render_spec.py::test_title_from_h1` (one), `ruff check .`,
  `ruff format .`.
- Test files and what they cover:
  - `tests/test_render_spec.py`: title from first H1; filename fallback; `.html`
    written next to `.md`; output contains `unicode-bidi: plaintext`; Arabic text
    survives the round-trip; no arguments and no specs dir gives exit 1.
  - `tests/test_on_spec_edit.py`: spec path creates `.html`; plan path does the
    same; unrelated path writes nothing; malformed or empty stdin exits 0 and
    writes nothing; Windows and POSIX separators both match.
  - `tests/test_worktree_audit.py`: builds a temp git repo; clean repo gives empty
    stdout; an added worktree is listed; a merged branch is listed as merged; run
    from a non-git temp dir gives empty stdout; always exit 0.
  - `tests/test_docs.py`: every relative markdown link under the repo (excluding
    ignored dirs) resolves; every repo path cited in a `CLAUDE.md` fenced command
    (`../plugin/scripts/render-spec.py`) points at an existing file.
  - `tests/test_plugin_manifest.py`: `plugin.json` and `hooks.json` parse; every
    hook command references a script that exists under `plugin/hooks/`.
- `.github/workflows/ci.yml`: on `push` (all branches) and `pull_request`; matrix
  `ubuntu-latest`, `windows-latest`; Python 3.12; steps: install, `ruff check .`,
  `ruff format --check .`, `pytest`.

### 4. Decision log and `CLAUDE.md` trim

`knowledge/decisions/README.md` (index table: number, title, status, date),
`0000-template.md` (from `conventions/decision-log.md`), and:

| # | Title | Status |
|---|-------|--------|
| 0001 | Workspace prefs repo tracks only whitelisted files | accepted |
| 0002 | Spec/plan HTML is a local view, never committed | accepted |
| 0003 | Specs and plans live under `docs/superpowers/` | accepted |
| 0004 | ADRs live under `knowledge/decisions/` (two repos grandfathered) | accepted |
| 0005 | Kit is a skills-dir Claude Code plugin in `plugin/`, installed by junction | accepted |
| 0006 | Kit `main` gate: CI on every push; PRs for feature work; direct commits for small doc fixes | accepted |
| 0007 | Hook handlers are Python scripts that always exit 0 | accepted |

Each is dated to the commit or conversation that made it (0001: 2026-07-31;
0002-0007: 2026-09-14) and lists the alternatives rejected (for 0005: marketplace
install, whose cache copy breaks the live edit loop; root-as-plugin, whose plugin
root would contain every project folder).

The `CLAUDE.md` "Building a new feature" section is rewritten to roughly:

> 1. Pre-flight (unchanged): on `main`, `main` in sync with remote, else stop and
>    warn.
> 2. Build in a worktree: `superpowers:using-git-worktrees`, after pulling `main`.
> 3. Finish with `superpowers:finishing-a-development-branch`. A feature is not done
>    until the worktree, the branch (local and remote), and any scratch files are
>    gone. The session-start audit reports leftovers; never delete anything with
>    unmerged work without asking.

The step-by-step cleanup list and worktree mechanics are removed since the two
skills own them.

### 5. Migration

Order matters because the junction and the hooks reference paths:

1. Move `scripts/` to `plugin/scripts/` and `skills/` to `plugin/skills/`
   (`git mv`).
2. Update `.gitignore`, `CLAUDE.md`, `README.md`, and `conventions/*` references.
3. Add `plugin.json`, hooks, tests, CI, ADRs.
4. Run `plugin/install.ps1`; verify in a fresh session.

Project repos need no change: they call the renderer by path from `CLAUDE.md`,
which is updated here, and receive the hooks automatically once the junction exists.

## Decisions made during design

- **Skills-dir plugin via junction, not marketplace.** Marketplace installs copy
  the plugin to a cache, so edits need reload or version bumps; the kit is edited
  constantly. The layout keeps marketplace possible (`source: "./plugin"`).
- **`plugin/` subfolder, not repo root.** The root contains ~30 ignored project
  folders; a plugin root there risks a loader scan or a multi-GB cache copy.
- **Hooks render only, never open the browser.** A tab per edit is noise; opening
  remains an explicit Claude action.
- **Audit is advisory.** It prints; it never prunes or deletes.
- **Python for hooks.** Cross-platform without shell dialect issues.
- **CI on push + PRs for feature work.** The "scale to the project" reading of the
  engineering practices for a solo prefs repo; recorded as ADR 0006.

## Success criteria

1. `ruff check .`, `ruff format --check .`, and `pytest` are green locally and in
   CI on both Ubuntu and Windows.
2. After `plugin/install.ps1`, a fresh Claude Code session lists
   `claude-kit:supabase-cli` among available skills.
3. Editing a spec `.md` under `docs/superpowers/specs/` in a project repo via
   Write/Edit produces an updated `.html` with no action from Claude.
4. Starting a session in a project repo with stale worktrees prints its leftover
   worktrees/branches; starting one in this repo prints nothing.
5. `tests/test_docs.py` passes: every relative link resolves and every path cited
   in `CLAUDE.md` exists.
6. The work lands on `main` via a feature branch and PR with CI green; the worktree
   and branch are removed afterwards.
