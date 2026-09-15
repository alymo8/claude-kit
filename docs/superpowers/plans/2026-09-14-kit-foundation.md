# Kit Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn this workspace-preferences repo into a real Claude Code plugin (`plugin/`) with two enforcing hooks, a pytest suite with CI, a backfilled decision log, and a trimmed `CLAUDE.md`.

**Architecture:** Everything Claude Code loads moves under `plugin/` (a *skills-dir plugin*: a folder under `~/.claude/skills/` containing `.claude-plugin/plugin.json`, made live by a junction). Two Python hook scripts in `plugin/hooks/` read the hook event from stdin and always exit 0. Tests live in `tests/` and exercise the scripts by importing them from their file path or running them as subprocesses. Decisions are recorded as ADRs under `knowledge/decisions/`.

**Tech Stack:** Python 3.11+ (3.13 on this machine), `markdown~=3.10`, `pytest`, `ruff`, PowerShell 5.1 (`install.ps1`), git ≥ 2.28, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-09-14-kit-foundation-design.md` — read it first; this plan implements it section by section.

## Why this exists (for an executor with no context)

A review found that this repo *describes* rules it cannot *enforce*: its one skill is never loaded by Claude Code, the "re-render spec HTML on every edit" and "clean up worktrees when done" rules depend on the model remembering (and were being missed), and the repo preaches tests/CI/ADRs while having none. This plan fixes all of that without changing any project repo.

## Decisions already made (do not relitigate)

- **Skills-dir plugin via junction, not a marketplace.** Marketplace installs copy the plugin into a cache, so edits need reloads or version bumps. Rejected.
- **Plugin lives in `plugin/`, not at the repo root.** The root directory also contains ~30 gitignored project folders; a plugin root there risks a loader scan or a multi-GB copy. Rejected.
- **Hooks are Python, always exit 0, never open a browser, never delete anything.**
- **This repo's `main` gate:** CI on every push; feature-sized work (this plan) goes through a branch + PR; one-line doc fixes may go straight to `main`.
- **Only the spec's seven ADRs are backfilled** — no others.

## Global Constraints

- Repo root: `C:\Users\alymo\Desktop\Github` (git remote `alymo8/claude-kit`, **public** — never write private repo names or the Windows username into tracked files; refer to other repos as "a project repo").
- The repo root `.gitignore` ignores everything (`/*`) and whitelists specific entries. **Every new top-level path must be added to the whitelist or it is silently untracked.**
- Rendered HTML (`docs/superpowers/**/*.html`) is never committed.
- `ruff` and `pytest` must be invoked with explicit paths (`ruff check plugin tests`) because the repo directory contains unrelated project folders.
- Hook scripts must run on Windows (Git Bash / PowerShell) and Linux; use `sys.executable`, `pathlib`, forward-slash normalisation.
- Commit messages: imperative subject, body explaining why; end with the attribution lines the session provides (Co-Authored-By / Claude-Session).
- Lines ≤ 88 chars in Python (ruff default).

---

## Prerequisites (fresh session starts cold)

1. On `main`, up to date: `git -C C:\Users\alymo\Desktop\Github status -sb` shows `## main...origin/main` with nothing ahead/behind. If not, stop and ask.
2. Python 3.11+ on PATH as `python`; `git` ≥ 2.28; `gh` authenticated (`gh auth status`).
3. Install dev deps once: `pip install "markdown~=3.10" pytest ruff`.
4. Create the isolated worktree with the `superpowers:using-git-worktrees` skill, branch name `feat/kit-foundation`. All tasks below run **inside that worktree** unless a step says otherwise. In commands below, `<wt>` means the worktree path the skill reports.

## File structure

| Path | Responsibility |
|---|---|
| `pyproject.toml` | Dependency pins, pytest and ruff config. No build backend. |
| `plugin/.claude-plugin/plugin.json` | Plugin manifest (`name: claude-kit`). |
| `plugin/skills/supabase-cli/` | Existing skill, moved verbatim. |
| `plugin/scripts/render-spec.py` | Existing renderer, moved verbatim. |
| `plugin/hooks/hooks.json` | Declares the two hooks. |
| `plugin/hooks/on_spec_edit.py` | PostToolUse: re-render one spec/plan file. |
| `plugin/hooks/worktree_audit.py` | SessionStart: print leftover worktrees/branches. |
| `plugin/install.ps1` | Create the junction `~/.claude/skills/claude-kit → plugin/`. |
| `tests/helpers.py` | `REPO`, `PLUGIN`, `load_module`, `run_script`. |
| `tests/test_plugin_manifest.py` | Manifest + hooks.json validity. |
| `tests/test_render_spec.py` | Renderer behaviour. |
| `tests/test_on_spec_edit.py` | Hook 1. |
| `tests/test_worktree_audit.py` | Hook 2 (against temp git repos). |
| `tests/test_install.py` | `install.ps1` (Windows only). |
| `tests/test_docs.py` | Links resolve; `CLAUDE.md` paths exist. |
| `knowledge/decisions/` | `README.md` index, `0000-template.md`, `0001`–`0007`. |
| `.github/workflows/ci.yml` | ruff + pytest on ubuntu and windows. |
| `CLAUDE.md`, `README.md`, `conventions/*.md`, `.gitignore` | Updated references. |

---

### Task 1: Tooling and the `plugin/` layout

**Files:**
- Create: `pyproject.toml`, `tests/helpers.py`, `tests/test_plugin_manifest.py`, `plugin/.claude-plugin/plugin.json`
- Move: `scripts/render-spec.py` → `plugin/scripts/render-spec.py`; `skills/supabase-cli/` → `plugin/skills/supabase-cli/`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `tests/helpers.py` exporting `REPO: Path`, `PLUGIN: Path`, `load_module(path: Path, name: str) -> module`, `run_script(script: Path, *args, stdin: str = "", cwd: Path | None = None) -> subprocess.CompletedProcess[str]`. Every later test file imports from it.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "claude-kit"
version = "0.1.0"
description = "Workspace conventions, a Claude Code plugin, and shared tooling"
requires-python = ">=3.11"
dependencies = ["markdown~=3.10"]

[dependency-groups]
dev = ["pytest>=8", "ruff>=0.6"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
```

- [ ] **Step 2: Create `tests/helpers.py`**

```python
"""Shared helpers for the kit's tests."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / "plugin"


def load_module(path: Path, name: str) -> ModuleType:
    """Import a script by file path (works for names with hyphens)."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader, path
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_script(
    script: Path, *args: str, stdin: str = "", cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a Python script the way a hook runner would: stdin in, text out."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd,
        timeout=60,
    )
```

- [ ] **Step 3: Write the failing manifest test**

`tests/test_plugin_manifest.py`:

```python
import json

from helpers import PLUGIN


def test_plugin_manifest_is_valid():
    data = json.loads(
        (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert data["name"] == "claude-kit"
    assert data["version"]


def test_skill_and_renderer_live_under_plugin():
    assert (PLUGIN / "skills" / "supabase-cli" / "SKILL.md").exists()
    assert (PLUGIN / "scripts" / "render-spec.py").exists()
```

- [ ] **Step 4: Run it to verify it fails**

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: 2 FAILED — `FileNotFoundError` for `plugin/.claude-plugin/plugin.json`, and the assertion in the second test.

- [ ] **Step 5: Move the existing code and add the manifest**

```bash
mkdir -p plugin/.claude-plugin
git mv scripts plugin/scripts
git mv skills plugin/skills
```

`plugin/.claude-plugin/plugin.json`:

```json
{
  "name": "claude-kit",
  "version": "0.1.0",
  "description": "Workspace conventions as a plugin: spec renderer hook, worktree audit, supabase-cli skill."
}
```

- [ ] **Step 6: Update the `.gitignore` whitelist**

Replace the whitelist block so the file reads:

```gitignore
# This repo tracks ONLY the Desktop/Github workspace preferences.
#
# Everything at the workspace root is ignored by default; the pref files are
# whitelisted below. The many project folders under Github/ (and any .env files
# inside them) are therefore NEVER committed. `/*` is anchored to the root, so it
# ignores only top-level entries — un-ignoring a directory here tracks all of its
# contents.

# Ignore every top-level entry...
/*

# ...but keep the workspace-preference files:
!/.gitignore
!/CLAUDE.md
!/README.md
!/pyproject.toml
!/conventions/
!/plugin/
!/knowledge/
!/docs/
!/tests/
!/.github/

# ...and never track secrets or local state, even inside the whitelisted dirs
# (un-ignoring a directory above tracks everything beneath it).
.env
.env.*
*.local
__pycache__/
.pytest_cache/
.ruff_cache/

# Rendered spec/plan views are local only (see CLAUDE.md)
docs/superpowers/**/*.html
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: 2 passed.

Also confirm nothing important is silently ignored: `git status --short` must list `pyproject.toml`, `tests/`, `plugin/.claude-plugin/plugin.json`, and the renames.

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "Move skills and scripts under plugin/, add manifest and test tooling"
```

---

### Task 2: Renderer characterisation tests

The renderer already works; these tests lock in its behaviour before hooks depend on it. They should pass on first run — if one fails, the renderer has a bug: fix the renderer, not the test.

**Files:**
- Create: `tests/test_render_spec.py`

**Interfaces:**
- Consumes: `plugin/scripts/render-spec.py` — `render(md_path: Path) -> Path` and `main(argv: list[str]) -> int`.

- [ ] **Step 1: Write the tests**

```python
from helpers import PLUGIN, load_module, run_script

RENDERER = PLUGIN / "scripts" / "render-spec.py"


def render(md):
    return load_module(RENDERER, "render_spec").render(md)


def test_title_from_h1(tmp_path):
    md = tmp_path / "x.md"
    md.write_text("# Hello Spec\n\nbody\n", encoding="utf-8")
    render(md)
    assert "<title>Hello Spec</title>" in (tmp_path / "x.html").read_text("utf-8")


def test_title_falls_back_to_filename(tmp_path):
    md = tmp_path / "fallback.md"
    md.write_text("no heading here\n", encoding="utf-8")
    render(md)
    assert "<title>fallback</title>" in (tmp_path / "fallback.html").read_text("utf-8")


def test_html_written_next_to_md(tmp_path):
    md = tmp_path / "doc.md"
    md.write_text("# T\n", encoding="utf-8")
    out = render(md)
    assert out == md.with_suffix(".html")
    assert out.exists()


def test_arabic_survives_and_bidi_rule_present(tmp_path):
    md = tmp_path / "ar.md"
    md.write_text("# عنوان\n\nهذا نص عربي.\n\n- بند\n", encoding="utf-8")
    html = render(md).read_text("utf-8")
    assert "unicode-bidi: plaintext" in html
    assert "هذا نص عربي." in html


def test_cli_renders_given_file(tmp_path):
    md = tmp_path / "cli.md"
    md.write_text("# CLI\n", encoding="utf-8")
    result = run_script(RENDERER, str(md), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "cli.html").exists()


def test_cli_with_nothing_to_render_exits_1(tmp_path):
    result = run_script(RENDERER, cwd=tmp_path)
    assert result.returncode == 1
    assert "No Markdown files" in result.stdout


def test_module_exposes_main():
    mod = load_module(RENDERER, "render_spec_main")
    assert callable(mod.main)
```

- [ ] **Step 2: Run them**

Run: `pytest tests/test_render_spec.py -v`
Expected: 7 passed. If `test_cli_with_nothing_to_render_exits_1` fails, check the renderer's `main()` still prints `No Markdown files to render.` and returns 1.

- [ ] **Step 3: Commit**

```bash
git add tests/test_render_spec.py
git commit -m "Add renderer tests"
```

---

### Task 3: Update every reference to the moved paths

**Files:**
- Create: `tests/test_docs.py`
- Modify: `CLAUDE.md` (renderer section), `README.md`, `conventions/spec-driven-development.md` (no path there — verify), `plugin/skills/supabase-cli/SKILL.md` (verify `tools/new-migration.sh` is still relative — it is; no change)

- [ ] **Step 1: Write the failing docs test**

`tests/test_docs.py`:

```python
import re
import subprocess

from helpers import REPO

LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
SCRIPT_REF_RE = re.compile(r"python \.\./(\S+\.py)")


FENCE_RE = re.compile(r"^```.*?^```[ 	]*$", re.M | re.S)
# Plans embed snippets of other files (with their own relative links); skip them.
SKIP_DIRS = ("docs/superpowers/plans/",)


def tracked_markdown():
    out = subprocess.run(
        ["git", "ls-files", "--", "*.md"],
        cwd=REPO, capture_output=True, text=True, check=True,
    ).stdout
    return [
        REPO / line
        for line in out.splitlines()
        if line and not line.startswith(SKIP_DIRS)
    ]


def prose(md):
    """Markdown text with fenced code blocks removed."""
    return FENCE_RE.sub("", md.read_text(encoding="utf-8"))


def test_relative_markdown_links_resolve():
    broken = []
    for md in tracked_markdown():
        for match in LINK_RE.finditer(prose(md)):
            href = match.group(1).split("#", 1)[0]
            if not href or "://" in href or href.startswith("mailto:"):
                continue
            if not (md.parent / href).exists():
                broken.append(f"{md.relative_to(REPO)} -> {href}")
    assert not broken, "\n".join(broken)


def test_claude_md_script_paths_exist():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    refs = SCRIPT_REF_RE.findall(text)
    assert refs, "CLAUDE.md should reference the renderer as python ../<path>.py"
    missing = [r for r in refs if not (REPO / r).exists()]
    assert not missing, missing
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_docs.py -v`
Expected: `test_claude_md_script_paths_exist` FAILS with `['scripts/render-spec.py']` missing. (The link test may already pass.)

- [ ] **Step 3: Fix `CLAUDE.md`**

In the block under "Use the shared renderer at …", change every `scripts/render-spec.py` to `plugin/scripts/render-spec.py`, so it reads:

```markdown
Use the shared renderer at `Desktop/Github/plugin/scripts/render-spec.py`. Run it
from inside a repo (repos live one level under `Github/`, so `../plugin/` resolves):

```
python ../plugin/scripts/render-spec.py <path-to-spec.md>   # one file
python ../plugin/scripts/render-spec.py                      # all specs in ./docs/superpowers/specs
```

Requires `pip install markdown` (once per machine). Do not copy the script into
individual repos — keep the single shared copy so it never drifts. When the
claude-kit plugin is installed (see `README.md`), a hook re-renders automatically
after every Write/Edit to a spec or plan; you only need the command for bulk
re-renders.
```

- [ ] **Step 4: Fix `README.md`**

Replace the `skills/` and `scripts/` bullets in "What's here" with:

```markdown
- **[`plugin/`](plugin/)** — a Claude Code plugin: the `supabase-cli` skill, the
  spec → HTML renderer, and two hooks (auto-render specs/plans after edits; report
  leftover worktrees at session start). Install once per machine with
  `plugin\install.ps1` — it junctions `~/.claude/skills/claude-kit` to this folder
  so edits are live.
- **[`knowledge/decisions/`](knowledge/decisions/)** — this repo's own ADRs.
- **[`docs/superpowers/`](docs/superpowers/)** — specs and plans for changes to
  the kit itself.
```

and add a section at the end:

```markdown
## Developing the kit

```
pip install "markdown~=3.10" pytest ruff     # once
pytest                                         # full suite
pytest tests/test_render_spec.py::test_title_from_h1   # one test
ruff check plugin tests && ruff format plugin tests    # lint + format
```

CI runs the same three commands on Ubuntu and Windows for every push and PR.
Feature-sized changes go through a branch and PR; one-line doc fixes may land on
`main` directly (ADR 0006).
```

Note: `knowledge/decisions/` does not exist yet — the link test will fail until Task 7. To keep Task 3 green, **create `knowledge/decisions/README.md` now** with just the heading `# Decisions` and one line `Index of this repo's ADRs; see [decision-log](../../conventions/decision-log.md).` — Task 7 fills it in.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_docs.py tests/test_plugin_manifest.py -v`
Expected: all passed.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Point docs at plugin/ paths; add docs consistency tests"
```

---

### Task 4: Hook 1 — auto-render specs and plans after edits

**Files:**
- Create: `plugin/hooks/on_spec_edit.py`, `plugin/hooks/hooks.json`, `tests/test_on_spec_edit.py`
- Modify: `tests/test_plugin_manifest.py` (add hook-command check)

**Interfaces:**
- Produces: `on_spec_edit.target_from_event(raw: str) -> Path | None` (pure; used by tests) and `main() -> int` (always 0).
- Hook event shape (stdin JSON from Claude Code): `{"tool_name": "Write", "tool_input": {"file_path": "..."}, ...}`.

- [ ] **Step 1: Write the failing tests**

`tests/test_on_spec_edit.py`:

```python
import json
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "on_spec_edit.py"


def event(path: str) -> str:
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})


def test_spec_path_is_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    p = "C:/repo/docs/superpowers/specs/2026-01-01-x-design.md"
    assert mod.target_from_event(event(p)) == Path(p)


def test_plan_path_with_backslashes_is_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    p = r"C:\repo\docs\superpowers\plans\2026-01-01-x.md"
    assert mod.target_from_event(event(p)) == Path(p)


def test_unrelated_path_is_not_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    assert mod.target_from_event(event("C:/repo/src/app.py")) is None
    assert mod.target_from_event(event("C:/repo/docs/superpowers/specs/x.html")) is None


def test_malformed_event_is_not_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    assert mod.target_from_event("") is None
    assert mod.target_from_event("{not json") is None
    assert mod.target_from_event(json.dumps({"tool_input": {}})) is None


def test_hook_renders_spec(tmp_path):
    spec_dir = tmp_path / "docs" / "superpowers" / "specs"
    spec_dir.mkdir(parents=True)
    md = spec_dir / "2026-01-01-thing-design.md"
    md.write_text("# Thing\n", encoding="utf-8")
    result = run_script(HOOK, stdin=event(str(md)), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (spec_dir / "2026-01-01-thing-design.html").exists()


def test_hook_ignores_unrelated_file(tmp_path):
    other = tmp_path / "notes.md"
    other.write_text("# n\n", encoding="utf-8")
    result = run_script(HOOK, stdin=event(str(other)), cwd=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / "notes.html").exists()


def test_hook_survives_garbage_stdin(tmp_path):
    result = run_script(HOOK, stdin="{{{", cwd=tmp_path)
    assert result.returncode == 0
    assert list(tmp_path.iterdir()) == []
```

Append to `tests/test_plugin_manifest.py`:

```python
import re


def test_hook_commands_reference_existing_scripts():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [
        h["command"]
        for groups in hooks["hooks"].values()
        for group in groups
        for h in group["hooks"]
    ]
    assert commands
    for command in commands:
        match = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"]+)", command)
        assert match, command
        assert (PLUGIN / match.group(1)).exists(), command
```

(Move the `import re` to the top of the file with the other imports.)

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_on_spec_edit.py tests/test_plugin_manifest.py -v`
Expected: all `test_on_spec_edit` tests FAIL (file not found); `test_hook_commands_reference_existing_scripts` FAILS (no hooks.json).

- [ ] **Step 3: Implement the hook**

`plugin/hooks/on_spec_edit.py`:

```python
#!/usr/bin/env python3
"""PostToolUse hook: re-render a spec or plan's HTML after its Markdown is written.

Reads the hook event JSON from stdin. If ``tool_input.file_path`` points at
``docs/superpowers/specs/*.md`` or ``docs/superpowers/plans/*.md``, runs the shared
renderer on that one file. Never opens a browser. Always exits 0: a hook must never
block work, so any failure is reported on stderr and otherwise swallowed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

RENDERER = Path(__file__).resolve().parent.parent / "scripts" / "render-spec.py"
TARGET_RE = re.compile(r"docs/superpowers/(specs|plans)/[^/]+\.md$")


def target_from_event(raw: str) -> Path | None:
    """Return the spec/plan path named by a hook event, or None if not one."""
    try:
        event = json.loads(raw)
    except ValueError:
        return None
    if not isinstance(event, dict):
        return None
    tool_input = event.get("tool_input")
    file_path = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(file_path, str):
        return None
    if not TARGET_RE.search(file_path.replace("\\", "/")):
        return None
    return Path(file_path)


def main() -> int:
    try:
        target = target_from_event(sys.stdin.read())
        if target is None or not target.exists():
            return 0
        result = subprocess.run(
            [sys.executable, str(RENDERER), str(target)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"[claude-kit] render failed: {result.stderr.strip()}", file=sys.stderr)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] on_spec_edit error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

`plugin/hooks/hooks.json` (SessionStart entry is added in Task 5):

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/on_spec_edit.py\""
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_on_spec_edit.py tests/test_plugin_manifest.py -v`
Expected: all passed.

- [ ] **Step 5: Lint**

Run: `ruff check plugin tests && ruff format plugin tests`
Expected: no errors; format may rewrite files — re-run pytest if it did.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Add PostToolUse hook that re-renders edited specs and plans"
```

---

### Task 5: Hook 2 — session-start worktree audit

**Files:**
- Create: `plugin/hooks/worktree_audit.py`, `tests/test_worktree_audit.py`
- Modify: `plugin/hooks/hooks.json` (add SessionStart)

**Interfaces:**
- Produces: `worktree_audit.report(cwd: Path) -> str` (empty string when nothing to report) and `main() -> int` (always 0). Output format exactly:

```
[claude-kit] Leftover from earlier feature work in this repo:
  worktrees: <path> (<branch>), ...
  branches:  <name> (merged), <name> (no upstream), ...
Clean up with superpowers:finishing-a-development-branch once the work is landed; ask before deleting anything unmerged.
```

Rules: the main worktree and the worktree `cwd` is in are never listed; the current branch, `main`, and `master` are never listed; a branch is listed as `(merged)` if merged into the default branch (`main` if it exists, else `master`), otherwise `(no upstream)` if it has no upstream; branches with an upstream that are unmerged are not listed.

- [ ] **Step 1: Write the failing tests**

`tests/test_worktree_audit.py`:

```python
import subprocess
from pathlib import Path

import pytest

from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "worktree_audit.py"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=True
    ).stdout


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", "a.txt", cwd=root)
    git("commit", "-q", "-m", "init", cwd=root)
    return root


def report(cwd: Path) -> str:
    return load_module(HOOK, "worktree_audit").report(cwd)


def test_clean_repo_reports_nothing(repo):
    assert report(repo) == ""


def test_non_git_dir_reports_nothing(tmp_path):
    assert report(tmp_path) == ""


def test_leftover_worktree_is_listed(repo, tmp_path):
    wt = tmp_path / "wt-feature"
    git("worktree", "add", "-q", "-b", "feat/x", str(wt), cwd=repo)
    text = report(repo)
    assert "worktrees:" in text
    assert "feat/x" in text
    assert "wt-feature" in text


def test_merged_branch_is_listed_as_merged(repo):
    git("branch", "done-branch", cwd=repo)  # points at main => merged
    text = report(repo)
    assert "done-branch (merged)" in text


def test_current_branch_is_never_listed(repo):
    git("checkout", "-q", "-b", "wip", cwd=repo)
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    git("add", "b.txt", cwd=repo)
    git("commit", "-q", "-m", "wip", cwd=repo)
    assert "wip" not in report(repo)


def test_unmerged_branch_with_upstream_is_not_listed(repo):
    git("checkout", "-q", "-b", "tracked", cwd=repo)
    (repo / "c.txt").write_text("c\n", encoding="utf-8")
    git("add", "c.txt", cwd=repo)
    git("commit", "-q", "-m", "c", cwd=repo)
    git("checkout", "-q", "main", cwd=repo)
    git("branch", "--set-upstream-to=main", "tracked", cwd=repo)
    assert report(repo) == ""


def test_script_exit_code_is_zero_everywhere(repo, tmp_path):
    assert run_script(HOOK, cwd=repo).returncode == 0
    assert run_script(HOOK, cwd=tmp_path).returncode == 0


def test_script_prints_report_to_stdout(repo):
    git("branch", "old", cwd=repo)
    result = run_script(HOOK, cwd=repo)
    assert result.stdout.startswith("[claude-kit] Leftover")
    assert "old (merged)" in result.stdout
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_worktree_audit.py -v`
Expected: all FAIL (script missing).

- [ ] **Step 3: Implement the hook**

`plugin/hooks/worktree_audit.py`:

```python
#!/usr/bin/env python3
"""SessionStart hook: report worktrees and branches left over from finished work.

Advisory only. Prints one short block when the repo containing ``cwd`` has
worktrees other than the main one (and the one we are in), or local branches that
are already merged into the default branch or have no upstream. Prints nothing
when clean or outside a git repo. Never deletes or prunes. Always exits 0.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FOOTER = (
    "Clean up with superpowers:finishing-a-development-branch once the work is "
    "landed; ask before deleting anything unmerged."
)


def git(*args: str, cwd: Path) -> str | None:
    """Run git; return stdout on success, None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def default_branch(cwd: Path) -> str | None:
    for name in ("main", "master"):
        if git("rev-parse", "--verify", "--quiet", f"refs/heads/{name}", cwd=cwd):
            return name
    return None


def leftover_worktrees(cwd: Path) -> list[str]:
    out = git("worktree", "list", "--porcelain", cwd=cwd)
    if not out:
        return []
    here = _norm(git("rev-parse", "--show-toplevel", cwd=cwd) or "")
    found: list[str] = []
    for entry in out.strip().split("\n\n")[1:]:  # first entry is the main worktree
        path = branch = None
        for line in entry.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree ") :]
            elif line.startswith("branch "):
                branch = line[len("branch ") :].removeprefix("refs/heads/")
        if path and _norm(path) != here:
            found.append(f"{path} ({branch or 'detached'})")
    return found


def leftover_branches(cwd: Path, default: str) -> list[str]:
    current = (git("branch", "--show-current", cwd=cwd) or "").strip()
    merged_out = git("branch", "--format=%(refname:short)", "--merged", default, cwd=cwd)
    merged = {line.strip() for line in (merged_out or "").splitlines()}
    refs = git(
        "for-each-ref", "--format=%(refname:short) %(upstream:short)", "refs/heads/",
        cwd=cwd,
    )
    found: list[str] = []
    for line in (refs or "").splitlines():
        name, _, upstream = line.partition(" ")
        if name in (default, "main", "master", current):
            continue
        if name in merged:
            found.append(f"{name} (merged)")
        elif not upstream:
            found.append(f"{name} (no upstream)")
    return found


def report(cwd: Path) -> str:
    if git("rev-parse", "--is-inside-work-tree", cwd=cwd) is None:
        return ""
    default = default_branch(cwd)
    worktrees = leftover_worktrees(cwd)
    branches = leftover_branches(cwd, default) if default else []
    if not worktrees and not branches:
        return ""
    lines = ["[claude-kit] Leftover from earlier feature work in this repo:"]
    if worktrees:
        lines.append("  worktrees: " + ", ".join(worktrees))
    if branches:
        lines.append("  branches:  " + ", ".join(branches))
    lines.append(FOOTER)
    return "\n".join(lines)


def main() -> int:
    try:
        text = report(Path.cwd())
        if text:
            print(text)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] worktree audit error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add the SessionStart entry to `plugin/hooks/hooks.json` so the whole file is:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/on_spec_edit.py\""
          }
        ]
      }
    ],
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/worktree_audit.py\""
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_worktree_audit.py tests/test_plugin_manifest.py -v`
Expected: all passed. If `test_leftover_worktree_is_listed` fails on Windows because paths differ in case or slashes, the `_norm` comparison is the place to look — never compare raw strings.

- [ ] **Step 5: Lint, then run the full suite**

Run: `ruff check plugin tests && ruff format plugin tests && pytest`
Expected: clean, all passed.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "Add SessionStart hook that reports leftover worktrees and branches"
```

---

### Task 6: `install.ps1` and its test

**Files:**
- Create: `plugin/install.ps1`, `tests/test_install.py`

**Interfaces:**
- `install.ps1 [-SkillsDir <path>]` — default `$HOME\.claude\skills`. Exit 0 on install or already-installed; exit 1 if `<SkillsDir>\claude-kit` exists and is not a junction to this `plugin/` folder.

- [ ] **Step 1: Write the failing test (Windows-only)**

`tests/test_install.py`:

```python
import subprocess
import sys

import pytest

from helpers import PLUGIN

INSTALL = PLUGIN / "install.ps1"
pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="junctions are Windows-only")


def run_install(skills_dir):
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(INSTALL),
         "-SkillsDir", str(skills_dir)],
        capture_output=True, text=True, timeout=60,
    )


def test_creates_junction_to_plugin(tmp_path):
    skills = tmp_path / "skills"
    result = run_install(skills)
    assert result.returncode == 0, result.stdout + result.stderr
    link = skills / "claude-kit"
    assert link.is_dir()
    assert (link / ".claude-plugin" / "plugin.json").exists()
    assert "Installed" in result.stdout


def test_second_run_is_idempotent(tmp_path):
    skills = tmp_path / "skills"
    assert run_install(skills).returncode == 0
    result = run_install(skills)
    assert result.returncode == 0
    assert "already installed" in result.stdout


def test_conflicting_directory_fails(tmp_path):
    skills = tmp_path / "skills"
    (skills / "claude-kit").mkdir(parents=True)  # a plain folder, not our junction
    result = run_install(skills)
    assert result.returncode == 1
    assert "already exists" in result.stdout + result.stderr
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_install.py -v`
Expected: 3 FAILED (script not found, PowerShell error).

- [ ] **Step 3: Write `plugin/install.ps1`**

```powershell
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

if (-not (Test-Path $SkillsDir)) {
  New-Item -ItemType Directory -Path $SkillsDir | Out-Null
}

if (Test-Path $link) {
  $item = Get-Item $link -Force
  $existingTarget = $null
  if ($item.LinkType) { $existingTarget = @($item.Target)[0] }
  if ($existingTarget -and ((Resolve-Path $existingTarget).Path -eq $target)) {
    Write-Host "claude-kit already installed: $link -> $target"
    exit 0
  }
  Write-Host "ERROR: $link already exists and is not a junction to $target. Remove it first."
  exit 1
}

New-Item -ItemType Junction -Path $link -Target $target | Out-Null
Write-Host "Installed: $link -> $target"
Write-Host "Start a new Claude Code session (or run /reload-plugins) to load the kit."
exit 0
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_install.py -v`
Expected: 3 passed. If `test_second_run_is_idempotent` fails, print `$item.LinkType` and `$item.Target` inside the script — on PowerShell 5.1 a junction reports `LinkType = Junction` and `Target` as an array with one path.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add install.ps1 that junctions the plugin into ~/.claude/skills"
```

---

### Task 7: Decision log

**Files:**
- Create: `knowledge/decisions/0000-template.md`, `0001` … `0007`
- Modify: `knowledge/decisions/README.md` (replace the stub from Task 3)

- [ ] **Step 1: Write the template and index**

`knowledge/decisions/0000-template.md`:

```markdown
# ADR NNNN: <Title>

- **Status:** proposed | accepted | superseded
- **Date:** YYYY-MM-DD

## Context
<the forces at play, the situation forcing a decision>

## Decision
<the choice made>

## Consequences
<tradeoffs — what this enables and what it costs>
```

`knowledge/decisions/README.md`:

```markdown
# Decisions

Architecture Decision Records for this repo (the kit itself), following
[the decision-log convention](../../conventions/decision-log.md). New decisions take
the next number; superseded ones are never deleted.

| # | Title | Status | Date |
|---|-------|--------|------|
| [0001](0001-whitelist-gitignore-workspace-repo.md) | Workspace prefs repo tracks only whitelisted files | accepted | 2026-07-31 |
| [0002](0002-spec-html-is-local-view.md) | Spec/plan HTML is a local view, never committed | accepted | 2026-09-14 |
| [0003](0003-specs-under-docs-superpowers.md) | Specs and plans live under `docs/superpowers/` | accepted | 2026-09-14 |
| [0004](0004-adrs-under-knowledge-decisions.md) | ADRs live under `knowledge/decisions/` | accepted | 2026-09-14 |
| [0005](0005-kit-is-a-skills-dir-plugin.md) | Kit is a skills-dir Claude Code plugin in `plugin/`, installed by junction | accepted | 2026-09-14 |
| [0006](0006-kit-main-gate.md) | Kit `main` gate: CI on every push; PRs for feature work | accepted | 2026-09-14 |
| [0007](0007-hooks-are-python-exit-zero.md) | Hook handlers are Python scripts that always exit 0 | accepted | 2026-09-14 |
```

- [ ] **Step 2: Write the seven ADRs**

`0001-whitelist-gitignore-workspace-repo.md`:

```markdown
# ADR 0001: Workspace prefs repo tracks only whitelisted files

- **Status:** accepted
- **Date:** 2026-07-31

## Context
The workspace directory (`Desktop/Github`) holds both the workspace-level way of
working (`CLAUDE.md`, conventions, tooling) and ~30 independent project checkouts,
some private, some containing `.env` files. The preferences need to be versioned
and shareable; the projects must never be swept into that repo.

## Decision
The workspace root is itself a git repo whose `.gitignore` ignores every top-level
entry (`/*`) and un-ignores an explicit whitelist of preference files and folders.
A secrets guard (`.env*`, `*.local`) applies inside whitelisted folders too.

## Consequences
Nothing project-specific can be committed by accident. The cost: every new
top-level file or folder must be added to the whitelist or it is silently
untracked — tests and reviewers must watch for that.
```

`0002-spec-html-is-local-view.md`:

```markdown
# ADR 0002: Spec/plan HTML is a local view, never committed

- **Status:** accepted
- **Date:** 2026-09-14

## Context
Specs and plans are Markdown; a co-located HTML rendering exists so they can be
read comfortably in a browser (including RTL Arabic content). Committing the HTML
doubled every doc change, produced noisy diffs, and drifted from the `.md` in
three of four repos.

## Decision
The `.md` is the only source of truth and the only tracked file. Every repo
gitignores `docs/superpowers/**/*.html`. The HTML is regenerated locally by the
shared renderer, automatically via the kit's PostToolUse hook.

## Consequences
Clean diffs and no drift to police. Anyone without the kit sees only Markdown,
which is fine — the HTML was always a convenience.
```

`0003-specs-under-docs-superpowers.md`:

```markdown
# ADR 0003: Specs and plans live under `docs/superpowers/`

- **Status:** accepted
- **Date:** 2026-09-14

## Context
The written convention said `docs/specs/` and `docs/plans/`, but the
`superpowers:brainstorming` and `superpowers:writing-plans` skills write to
`docs/superpowers/specs/` and `docs/superpowers/plans/` by default, the shared
renderer looked there, and every adopting repo used that path. The convention was
the only thing out of step.

## Decision
`docs/superpowers/specs/` and `docs/superpowers/plans/` are the convention.

## Consequences
Convention, tooling, and practice agree; nothing has to be configured or moved.
The `superpowers` name in the path is a dependency on that plugin's defaults; if
the plugin ever changes them, revisit this ADR rather than diverging silently.
```

`0004-adrs-under-knowledge-decisions.md`:

```markdown
# ADR 0004: ADRs live under `knowledge/decisions/`

- **Status:** accepted
- **Date:** 2026-09-14

## Context
Adopting repos had split two ways: `knowledge/decisions/` (as the convention
said) and `docs/decisions/`. Decisions are part of what a project *knows* — they
are made against the knowledge base and belong next to it.

## Decision
`knowledge/decisions/` is the fixed location, with a `README.md` index and a
`0000-template.md`. Two older repos that already use `docs/decisions/` keep it
as a grandfathered exception; they are not migrated.

## Consequences
One place to look in every new repo. The exceptions are named in the convention
so nobody "fixes" them later.
```

`0005-kit-is-a-skills-dir-plugin.md`:

```markdown
# ADR 0005: Kit is a skills-dir Claude Code plugin in `plugin/`, installed by junction

- **Status:** accepted
- **Date:** 2026-09-14

## Context
The kit's skill was never loaded by Claude Code because nothing wired it in, and
the rules meant to be enforced (re-render HTML, clean up worktrees) were prose.
Claude Code can load skills, hooks and commands from a plugin. Two delivery
mechanisms exist: a marketplace install, which copies the plugin into a cache;
or a *skills-dir plugin*, a folder under `~/.claude/skills/` with a
`.claude-plugin/plugin.json`, loaded in place.

## Decision
Everything Claude Code loads lives in `plugin/` (manifest, `skills/`, `hooks/`,
`scripts/`). It is installed by a junction `~/.claude/skills/claude-kit ->
plugin/`, created by `plugin/install.ps1`, once per machine.

Rejected: marketplace install (cache copy means edits need reloads or version
bumps, and the kit is edited constantly); repo root as plugin root (the root
contains ~30 ignored project folders, risking a loader scan or a huge copy).

## Consequences
Edits are live; one copy of every file. The layout keeps a marketplace possible
later (`source: "./plugin"`). Each machine needs the one-line install; the
junction is not recorded in git.
```

`0006-kit-main-gate.md`:

```markdown
# ADR 0006: Kit `main` gate: CI on every push; PRs for feature work

- **Status:** accepted
- **Date:** 2026-09-14

## Context
The engineering-practices convention wants a protected `main` with CI, AI and
human review on every change. This repo is a solo preferences repo where many
changes are one-line convention edits; a full PR gate on each would be friction
without benefit. The convention itself says to scale to the project.

## Decision
CI (`ruff`, `pytest` on Ubuntu and Windows) runs on every push and PR.
Feature-sized changes (anything with a spec) go through a branch and PR with CI
green. One-line doc fixes may be committed directly to `main`. No branch
protection is enabled.

## Consequences
Breakage is always visible; the ceremony matches the change. If a second
contributor ever appears, enable protection and supersede this ADR.
```

`0007-hooks-are-python-exit-zero.md`:

```markdown
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
```

- [ ] **Step 3: Run the docs tests**

Run: `pytest tests/test_docs.py -v`
Expected: passed (all index links resolve).

- [ ] **Step 4: Commit**

```bash
git add knowledge
git commit -m "Add decision log with seven backfilled ADRs"
```

---

### Task 8: Trim the `CLAUDE.md` feature-workflow section

**Files:**
- Modify: `CLAUDE.md` — the section starting `## Building a new feature: check branch state first, use a worktree, then clean up` through the end of the file.

- [ ] **Step 1: Replace the section**

Replace everything from that heading to the end of the file with:

```markdown
## Building a new feature: pre-flight, worktree, clean up

**Before implementing any new feature, run a pre-flight branch check and get my
go-ahead:**

1. **Confirm we are on `main`.** Run `git branch --show-current`. If not on `main`,
   **stop and warn me** — tell me the current branch and do not start until I
   confirm how to proceed.
2. **Confirm `main` is up to date.** `git fetch`, then check `git status -sb` /
   `git rev-list --count main..@{u}`. If local `main` is behind or ahead of the
   remote, **stop and warn me** — do not start until `main` is updated or I tell
   you to proceed anyway.

Only once both checks pass (or I have explicitly waived them) should you begin.

Then build in an isolated worktree using `superpowers:using-git-worktrees`, after
pulling the latest `main` so the worktree branches from up-to-date code.

**A feature is not finished until its workspace is gone.** When the work is merged
(or I have explicitly abandoned it), use `superpowers:finishing-a-development-branch`
to integrate and clean up: the worktree removed and pruned, the branch deleted
locally and on the remote, and any scratch files created outside the repo deleted.
The kit's session-start hook reports leftover worktrees and branches; treat that as
a to-do, but **never delete anything with unmerged commits or uncommitted changes
without asking me first.**
```

- [ ] **Step 2: Verify**

Run: `pytest tests/test_docs.py -v` and read the new section once end to end.
Expected: passed; the section no longer lists the individual `git worktree remove` / `git branch -d` steps.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "Trim feature-workflow section to what the superpowers skills do not cover"
```

---

### Task 9: CI workflow, full verification, PR, merge, install, clean up

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Write the workflow**

```yaml
name: ci
on:
  push:
  pull_request:

jobs:
  test:
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install "markdown~=3.10" pytest ruff
      - run: ruff check plugin tests
      - run: ruff format --check plugin tests
      - run: pytest
```

- [ ] **Step 2: Full local verification (success criteria 1 and 5)**

Run: `ruff format plugin tests && ruff check plugin tests && pytest -v`
Expected: no lint errors; every test passed (the `test_install.py` tests run on
Windows). If `ruff format` rewrote any file, run pytest again and include the
reformat in the next commit.

- [ ] **Step 3: Commit and push the branch**

```bash
git add .github
git commit -m "Add CI: ruff and pytest on Ubuntu and Windows"
git push -u origin feat/kit-foundation
```

- [ ] **Step 4: Open the PR and wait for CI**

```bash
gh pr create --title "Kit foundation: plugin packaging, hooks, tests, decision log" \
  --body-file - <<'EOF'
Implements docs/superpowers/specs/2026-09-14-kit-foundation-design.md.

- plugin/ is a skills-dir Claude Code plugin (manifest, supabase-cli skill, renderer)
- hooks: auto-render specs/plans after Write/Edit; session-start worktree audit
- pytest suite + CI (ubuntu, windows); ruff
- knowledge/decisions with ADRs 0001-0007
- CLAUDE.md feature-workflow section trimmed to the pre-flight + skill pointers

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01TsrL5dfX8pfhd8Xok81Etj
EOF
gh pr checks --watch
```

Expected: both matrix jobs green. If Windows fails on `test_install.py` or `test_worktree_audit.py`, read the log — the likely causes are path normalisation (`_norm`) or PowerShell output encoding; fix in the worktree, push, re-watch.

- [ ] **Step 5: Merge**

Do this only after CI is green. Ask the user before merging if anything in the PR diverged from the spec.

```bash
gh pr merge --squash --delete-branch
```

- [ ] **Step 6: Install the plugin from the main checkout (success criterion 2)**

Run **from the main checkout, not the worktree**, in PowerShell:

```powershell
git -C C:\Users\alymo\Desktop\Github pull --ff-only
C:\Users\alymo\Desktop\Github\plugin\install.ps1
```

Expected: `Installed: C:\Users\alymo\.claude\skills\claude-kit -> C:\Users\alymo\Desktop\Github\plugin`.

Then ask the user to start a **new** Claude Code session and confirm `claude-kit:supabase-cli` appears in the available-skills list (or run `/plugins` and look for `claude-kit@skills-dir`). This step cannot be verified from inside the current session.

- [ ] **Step 7: Verify the hooks live (success criteria 3 and 4)**

In the new session, in a project repo that has `docs/superpowers/specs/`:
1. Make a trivial Write/Edit to any spec `.md` (add and remove a blank line). Confirm the `.html` mtime updated without running the renderer by hand. Revert the edit.
2. The session start in a repo with a leftover worktree should have printed the `[claude-kit] Leftover…` block into context; a session started in `Desktop/Github` should print nothing.

Record the outcomes in the PR (a comment) or tell the user.

- [ ] **Step 8: Clean up (success criterion 6)**

Use `superpowers:finishing-a-development-branch`. Concretely:

```bash
cd C:\Users\alymo\Desktop\Github
git worktree remove <wt>
git worktree prune
git branch -d feat/kit-foundation      # remote branch already deleted by --delete-branch
git worktree list                        # only the main checkout remains
git branch                               # only main
```

Delete any scratch files created outside the repo during this work.

---

## Self-review against the spec

- §1 layout → Tasks 1, 3 (paths), 7 (knowledge/), 9 (.github). ✔
- §2 hooks → Tasks 4, 5; `install.ps1` → Task 6. ✔
- §3 tests/tooling/CI → Tasks 1–6 tests, Task 9 CI; README dev commands → Task 3. ✔
- §4 ADRs → Task 7; CLAUDE.md trim → Task 8. ✔
- §5 migration order → Task 1 moves first, Task 3 updates references, Task 9 installs last. ✔
- Success criteria 1–6 → Task 9 steps 2, 6, 7, 2, 5–8. ✔
- Names consistent: `target_from_event`, `report`, `run_script`, `load_module`, `REPO`, `PLUGIN` used identically across tasks. ✔
