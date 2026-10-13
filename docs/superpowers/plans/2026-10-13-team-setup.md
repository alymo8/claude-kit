# Team setup Implementation Plan

- **Status:** approved
- **Date:** 2026-10-13

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a teammate on any OS install the kit with one command and get the same rules and flow in any repo: a cross-platform Python installer with prerequisite checks, a SessionStart hook that injects the workspace rules in repos outside the kit folder, three process rules moved from personal memory into `CLAUDE.md`, and a setup guide.

**Architecture:** `plugin/install.py` (stdlib only) replaces the logic of `plugin/install.ps1`, which becomes a thin wrapper. It checks that the `python` command the hooks run is 3.11+ before touching disk, links `~/.claude/skills/claude-kit` to `plugin/` (junction on Windows, symlink elsewhere), adds the status line, and warns about missing `git`, `gh` or superpowers. A new hook, `plugin/hooks/workspace_rules_inject.py`, shaped like `kit_map_inject.py`, prints the workspace `CLAUDE.md` (minus `## Developing the kit`) only when the session's project is outside the kit root and not a git worktree of the kit. Docs, three ADRs and the manifest describe it.

**Tech Stack:** Python 3 (stdlib only), PowerShell 5.1 wrapper, pytest, ruff; Markdown and JSON.

**Spec:** `docs/superpowers/specs/2026-10-13-team-setup-design.md`

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/` plus workspace
conventions under `conventions/`. It is a public GitHub repo. Hooks are Python
scripts registered in `plugin/hooks/hooks.json`; each SessionStart hook prints
one JSON object `{"hookSpecificOutput": {"hookEventName": "SessionStart",
"additionalContext": "..."}}` and always exits 0 (ADR 0007).
`tests/helpers.py` exports `REPO` (repo root), `PLUGIN` (`REPO / "plugin"`),
`clean_env(**extra)` (a copy of `os.environ` without `CLAUDE_KIT_*`, plus
`extra`), `load_module(path, name)` and `run_script(script, *args, stdin="",
env=None)` (runs a script with `sys.executable`, returns
`CompletedProcess[str]`).

Before every commit run the full suite and lint from the repo root:

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
```

`pyproject.toml` sets `addopts = "-q"`; plain `pytest` is quiet already.
Every commit message ends with a blank line and
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

Several tracked files use CRLF line endings (`CLAUDE.md`, `README.md`,
`plugin/install.ps1`, `knowledge/decisions/README.md`,
`tests/test_install.py`). Edit them with an editor tool, not shell
heredocs; if `ruff format --check` flags a `.py` file, run
`ruff format <file>`.

Decisions already made (do not relitigate): one Python installer with
`install.ps1` as a wrapper (not a parallel `install.sh`, not a marketplace);
superpowers is checked, never installed; `hooks.json` keeps calling `python`
(no `python3` fallback), so a missing or old `python` is a hard installer
error; the workspace rules arrive through a SessionStart hook (not an `@`
import in `~/.claude/CLAUDE.md`); `/ship` keeps its autonomous squash-merge;
no macOS CI job; one spec and one PR, release 0.24.0.

## Global Constraints

- Minimum Python for hooks: 3.11 (`MIN_VERSION = (3, 11)`).
- `install.py` stays parseable by Python 3.8: no `match` statements, no
  `X | Y` unions outside annotations, and keep
  `from __future__ import annotations`, so an old interpreter still reaches
  the version error.
- Env switch: `CLAUDE_KIT_WORKSPACE_RULES=0` turns the new hook off; any other
  value, or none, is on.
- The new hook always exits 0; errors go to stderr as
  `[claude-kit] workspace-rules inject error: ...`.
- The new hook's `additionalContext` is at most 12,000 characters.
- Superpowers plugin id: `superpowers@claude-plugins-official`.
- Plugin version becomes `0.24.0`.
- New ADRs are 0033, 0034 and 0035 (0032 is the latest on `origin/main`).
- No private repo names and no machine username in tracked files; the repo's
  own public slug `alymo8/claude-kit` may appear.
- Test code must fit ruff's 88-character line limit.
- Tests that create a link remove only the link (`os.rmdir` for a Windows
  junction, `os.unlink` for a symlink), never a recursive delete through it.

## Review Focus

- `install.py` run when the link already exists and points at `plugin/`: it must still run the status line and superpowers steps, exit 0 (Task 1 test `test_second_run_is_idempotent` checks the superpowers warning still prints).
- A dangling junction or symlink at the link path: ERROR, exit 1, the link left alone (Task 1 test `test_dangling_link_fails_cleanly`).
- `--python` naming a missing command: exit 1 before anything is created (Task 1 test `test_missing_python_changes_nothing`).
- A session in a git worktree of the kit placed outside the kit folder: silent, so the rules are not loaded twice (Task 2 test `test_kit_worktree_elsewhere_is_silent`).
- `CLAUDE_PROJECT_DIR` unset, project taken from stdin `cwd` (Task 2 test `test_project_dir_from_stdin`), and malformed stdin falls back to the current directory without an error (Task 2 test `test_malformed_stdin_is_ignored`).

---

### Task 1: Cross-platform installer

**Files:**
- Create: `plugin/install.py`
- Modify: `plugin/install.ps1` (whole file)
- Test: `tests/test_install.py` (whole file rewritten)

**Depends on:** none

**Interfaces:**
- Consumes: `plugin/scripts/install-statusline.py --settings <path> --skills-dir <path>` (existing; prints `statusLine added to <path>` or `statusLine already configured; left unchanged`; exits 1 on malformed JSON).
- Produces: `python plugin/install.py [--skills-dir DIR] [--settings FILE] [--python CMD]`; exit 0 on success or already installed, 1 on a prerequisite or link error. Output lines that tests and docs rely on: `Installed: <link> -> <target>`, `claude-kit already installed: <link> -> <target>`, `ERROR: <link> already exists and is not a link to <target>. Remove it first.`, `ERROR: hooks run "<cmd>", which is not on PATH.`, `WARNING: git not found on PATH; ...`, `WARNING: the superpowers plugin is not enabled. ...`.

- [ ] **Step 1: Write the failing tests**

Replace the whole of `tests/test_install.py` with:

```python
import json
import os
import shutil
import subprocess
import sys

import pytest
from helpers import PLUGIN

INSTALL = PLUGIN / "install.py"
WRAPPER = PLUGIN / "install.ps1"
SUPERPOWERS = "superpowers@claude-plugins-official"


def run_install(tmp_path, python=sys.executable, env=None):
    return subprocess.run(
        [
            sys.executable,
            str(INSTALL),
            "--skills-dir",
            str(tmp_path / "skills"),
            "--settings",
            str(tmp_path / "settings.json"),
            "--python",
            python,
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )


def out(result):
    return result.stdout + result.stderr


def is_link(path):
    try:
        os.readlink(path)
    except (OSError, ValueError):
        return False
    return True


def make_dir_link(link, target):
    if sys.platform == "win32":
        subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(link), str(target)],
            check=True,
            capture_output=True,
        )
    else:
        os.symlink(target, link, target_is_directory=True)


def remove_link(link):
    # Only the link itself: a recursive delete would follow it into plugin/.
    if sys.platform == "win32":
        os.rmdir(link)
    else:
        os.unlink(link)


@pytest.fixture(autouse=True)
def drop_kit_link(tmp_path):
    yield
    link = tmp_path / "skills" / "claude-kit"
    if os.path.lexists(link) and is_link(link):
        remove_link(link)


def test_creates_link_to_plugin(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    link = tmp_path / "skills" / "claude-kit"
    assert (link / ".claude-plugin" / "plugin.json").exists()
    assert os.path.samefile(link, PLUGIN)
    assert "Installed" in result.stdout
    assert "Start a new Claude Code session" in result.stdout


def test_second_run_is_idempotent(tmp_path):
    assert run_install(tmp_path).returncode == 0
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "already installed" in result.stdout
    assert "superpowers plugin is not enabled" in result.stdout
    assert "Start a new Claude Code session" not in result.stdout


def test_conflicting_directory_fails(tmp_path):
    folder = tmp_path / "skills" / "claude-kit"
    folder.mkdir(parents=True)
    (folder / "keep.txt").write_text("x", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 1
    assert "already exists" in out(result)
    assert (folder / "keep.txt").read_text(encoding="utf-8") == "x"


def test_dangling_link_fails_cleanly(tmp_path):
    skills = tmp_path / "skills"
    skills.mkdir()
    victim = tmp_path / "victim"
    victim.mkdir()
    link = skills / "claude-kit"
    make_dir_link(link, victim)
    victim.rmdir()  # the link now dangles
    result = run_install(tmp_path)
    assert result.returncode == 1
    assert "already exists" in out(result)
    assert os.path.lexists(link)


def test_install_adds_statusline_to_given_settings(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "statusLine added" in result.stdout
    text = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "statusLine" in json.loads(text)
    assert "statusline.py" in text


def test_install_survives_malformed_settings(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text("{oops", encoding="utf-8")
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "Installed" in result.stdout
    assert settings.read_text(encoding="utf-8") == "{oops"
    assert "WARNING: status line not configured" in result.stdout
    assert "superpowers plugin is not enabled" in result.stdout


def test_superpowers_enabled_gives_no_warning(tmp_path):
    settings = tmp_path / "settings.json"
    settings.write_text(
        json.dumps({"enabledPlugins": {SUPERPOWERS: True}}), encoding="utf-8"
    )
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert "superpowers plugin is not enabled" not in result.stdout


def test_superpowers_missing_warns_with_install_command(tmp_path):
    result = run_install(tmp_path)
    assert result.returncode == 0, out(result)
    assert f"/plugin install {SUPERPOWERS}" in result.stdout


def test_missing_python_changes_nothing(tmp_path):
    result = run_install(tmp_path, python="claude-kit-no-such-python")
    assert result.returncode == 1
    assert 'ERROR: hooks run "claude-kit-no-such-python"' in result.stdout
    assert "is not on PATH" in result.stdout
    assert not os.path.lexists(tmp_path / "skills" / "claude-kit")
    assert not (tmp_path / "settings.json").exists()


def test_missing_git_and_gh_only_warn(tmp_path):
    only_python = os.path.dirname(sys.executable)
    if shutil.which("git", path=only_python) or shutil.which("gh", path=only_python):
        pytest.skip("git or gh sits next to the Python interpreter")
    env = dict(os.environ, PATH=only_python)
    result = run_install(tmp_path, env=env)
    assert result.returncode == 0, out(result)
    assert "WARNING: git not found on PATH" in result.stdout
    assert "WARNING: gh not found on PATH" in result.stdout


@pytest.mark.skipif(sys.platform != "win32", reason="PowerShell wrapper")
def test_powershell_wrapper_runs_installer(tmp_path):
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(WRAPPER),
            "-SkillsDir",
            str(tmp_path / "skills"),
            "-Settings",
            str(tmp_path / "settings.json"),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, out(result)
    assert os.path.samefile(tmp_path / "skills" / "claude-kit", PLUGIN)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_install.py -o addopts=""`
Expected: FAIL (the installer `plugin/install.py` does not exist; the
wrapper test is skipped off Windows).

- [ ] **Step 3: Write `plugin/install.py`**

```python
#!/usr/bin/env python3
"""Install claude-kit as a Claude Code skills-dir plugin, on any OS.

Usage: install.py [--skills-dir DIR] [--settings FILE] [--python CMD]

Links <skills-dir>/claude-kit to this plugin folder (a junction on Windows, a
symlink elsewhere), so Claude Code loads the kit from the git checkout
(ADR 0005, amended by ADR 0033). First checks that the command the hooks run
(default "python") is Python 3.11+, and exits 1 with nothing changed if not.
Warns when git, gh or the superpowers plugin is missing. Adds the kit's status
line when none is configured. Idempotent; refuses to overwrite anything else
at the link path.

Keep this file parseable by Python 3.8, so an old interpreter still reaches
the version error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parent
MIN_VERSION = (3, 11)
SUPERPOWERS = "superpowers@claude-plugins-official"
FIXES = {
    "win32": (
        "install Python 3.11+ from python.org with "
        '"Add python.exe to PATH" ticked.'
    ),
    "darwin": (
        "install Homebrew python@3 and put its libexec/bin folder on PATH, "
        "or make python an alias of python3."
    ),
    "linux": (
        "install the python-is-python3 package, or link python to python3 "
        "on your PATH."
    ),
}


def python_version(command: str) -> tuple[int, int] | None:
    """(major, minor) of the given python command, or None if it cannot run."""
    if shutil.which(command) is None:
        return None
    try:
        done = subprocess.run(
            [command, "-c", "import sys; print(*sys.version_info[:2])"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    parts = done.stdout.split()
    if done.returncode != 0 or len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def check_python(command: str) -> bool:
    version = python_version(command)
    if version is not None and version >= MIN_VERSION:
        return True
    if version is None:
        problem = "is not on PATH"
    else:
        problem = f"is {version[0]}.{version[1]}"
    key = "linux" if sys.platform.startswith("linux") else sys.platform
    print(f'ERROR: hooks run "{command}", which {problem}.')
    print(f"Fix: {FIXES.get(key, FIXES['linux'])}")
    return False


def warn_missing_tools() -> None:
    for tool in ("git", "gh"):
        if shutil.which(tool) is None:
            print(
                f"WARNING: {tool} not found on PATH; "
                "/ship and the worktree flow need it."
            )


def is_link(path: Path) -> bool:
    """True for a symlink or a Windows junction, dangling or not."""
    try:
        os.readlink(path)
    except (OSError, ValueError):
        return False
    return True


def points_at_plugin(link: Path) -> bool:
    try:
        return os.path.samefile(link, PLUGIN)
    except OSError:
        return False


def make_link(link: Path) -> None:
    if sys.platform == "win32":
        shell = os.environ.get("COMSPEC", "cmd")
        done = subprocess.run(
            [shell, "/c", "mklink", "/J", str(link), str(PLUGIN)],
            capture_output=True,
            text=True,
        )
        if done.returncode != 0:
            raise OSError((done.stdout + done.stderr).strip())
    else:
        os.symlink(PLUGIN, link, target_is_directory=True)


def install_link(skills_dir: Path) -> str | None:
    """'installed' or 'present'; None after printing an error."""
    link = skills_dir / "claude-kit"
    if os.path.lexists(link):
        if is_link(link) and points_at_plugin(link):
            print(f"claude-kit already installed: {link} -> {PLUGIN}")
            return "present"
        print(
            f"ERROR: {link} already exists and is not a link to {PLUGIN}. "
            "Remove it first."
        )
        return None
    skills_dir.mkdir(parents=True, exist_ok=True)
    make_link(link)
    print(f"Installed: {link} -> {PLUGIN}")
    return "installed"


def install_statusline(settings: Path, skills_dir: Path) -> None:
    script = PLUGIN / "scripts" / "install-statusline.py"
    command = [sys.executable, str(script), "--settings", str(settings)]
    command += ["--skills-dir", str(skills_dir)]
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"WARNING: could not run install-statusline.py: {exc}")
        return
    if done.stdout.strip():
        print(done.stdout.strip())
    if done.returncode != 0:
        if done.stderr.strip():
            print(done.stderr.strip())
        print(
            "WARNING: status line not configured (install-statusline.py "
            f"exited {done.returncode}); see the message above."
        )


def superpowers_enabled(settings: Path) -> bool:
    try:
        data = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    plugins = data.get("enabledPlugins") if isinstance(data, dict) else None
    return isinstance(plugins, dict) and plugins.get(SUPERPOWERS) is True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    home = Path.home() / ".claude"
    parser.add_argument("--skills-dir", default=str(home / "skills"))
    parser.add_argument("--settings", default=str(home / "settings.json"))
    parser.add_argument(
        "--python", default="python", help="the command the hooks run"
    )
    args = parser.parse_args(argv)
    if not check_python(args.python):
        return 1
    warn_missing_tools()
    skills_dir, settings = Path(args.skills_dir), Path(args.settings)
    try:
        outcome = install_link(skills_dir)
    except OSError as exc:
        print(f"ERROR: could not create the link: {exc}")
        return 1
    if outcome is None:
        return 1
    install_statusline(settings, skills_dir)
    if not superpowers_enabled(settings):
        print(
            "WARNING: the superpowers plugin is not enabled. The kit's flow "
            f"uses its skills. In Claude Code run: /plugin install {SUPERPOWERS}"
        )
    if outcome == "installed":
        print(
            "Start a new Claude Code session (or run /reload-plugins) "
            "to load the kit."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Replace `plugin/install.ps1` with the wrapper**

```powershell
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
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_install.py -o addopts=""`
Expected: all PASS (on Windows the wrapper test runs too; elsewhere it is
skipped; `test_missing_git_and_gh_only_warn` may skip where `git` sits next
to the interpreter).

- [ ] **Step 6: Full suite, lint, commit**

```bash
ruff format plugin/install.py tests/test_install.py
pytest
ruff check plugin tests
ruff format --check plugin tests
git add plugin/install.py plugin/install.ps1 tests/test_install.py
git commit -m "Cross-platform Python installer with prerequisite checks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Workspace-rules hook

**Files:**
- Create: `plugin/hooks/workspace_rules_inject.py`
- Modify: `plugin/hooks/hooks.json` (new SessionStart group after the `kit_map_inject.py` group)
- Test: `tests/test_workspace_rules_inject.py`

**Depends on:** none

**Interfaces:**
- Consumes: the workspace `CLAUDE.md` at the kit root; its `## Developing the kit` heading marks where the injected text stops.
- Produces: SessionStart output whose `additionalContext` starts with `Workspace rules (claude-kit, from <root>/CLAUDE.md).`; env switch `CLAUDE_KIT_WORKSPACE_RULES`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_workspace_rules_inject.py`:

```python
import json
import shutil
import subprocess

from helpers import PLUGIN, REPO, clean_env, run_script

HOOK = PLUGIN / "hooks" / "workspace_rules_inject.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@example.com"]
GIT += ["-c", "commit.gpgsign=false"]


def run(script=HOOK, stdin="{}", **env: str):
    environment = clean_env(**env)
    if "CLAUDE_PROJECT_DIR" not in env:
        environment.pop("CLAUDE_PROJECT_DIR", None)
    return run_script(script, stdin=stdin, env=environment)


def context(result) -> str:
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    return out["additionalContext"]


def make_kit(tmp_path, claude_md):
    kit = tmp_path / "kit"
    (kit / "plugin" / "hooks").mkdir(parents=True)
    shutil.copy(HOOK, kit / "plugin" / "hooks" / HOOK.name)
    if claude_md is not None:
        (kit / "CLAUDE.md").write_text(claude_md, encoding="utf-8")
    return kit


def test_outside_the_kit_injects_rules_without_kit_dev(tmp_path):
    result = run(CLAUDE_PROJECT_DIR=str(tmp_path))
    assert result.returncode == 0, result.stderr
    text = context(result)
    assert text.startswith("Workspace rules (claude-kit, from ")
    assert f"{REPO.as_posix()}/CLAUDE.md" in text
    assert "## How we work" in text
    assert "## Developing the kit" not in text


def test_inside_the_kit_is_silent():
    for project in (REPO, REPO / "plugin"):
        result = run(CLAUDE_PROJECT_DIR=str(project))
        assert result.returncode == 0
        assert result.stdout == "", project


def test_kit_worktree_elsewhere_is_silent(tmp_path):
    kit = make_kit(tmp_path, "# Rules\n\n## How we work\n\nx\n")
    subprocess.run(GIT + ["init", "-q", str(kit)], check=True)
    subprocess.run(GIT + ["-C", str(kit), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(kit), "commit", "-qm", "init"], check=True)
    worktree = tmp_path / "wt"
    subprocess.run(
        GIT + ["-C", str(kit), "worktree", "add", "-q", str(worktree)], check=True
    )
    hook = kit / "plugin" / "hooks" / HOOK.name
    assert run(hook, CLAUDE_PROJECT_DIR=str(worktree)).stdout == ""
    other = tmp_path / "other"
    other.mkdir()
    assert "## How we work" in context(run(hook, CLAUDE_PROJECT_DIR=str(other)))


def test_project_dir_from_stdin(tmp_path):
    stdin = json.dumps({"cwd": str(tmp_path)})
    assert "## How we work" in context(run(stdin=stdin))
    stdin = json.dumps({"cwd": str(REPO)})
    assert run(stdin=stdin).stdout == ""


def test_malformed_stdin_is_ignored():
    # Falls back to the current directory: the test process runs in the kit.
    result = run(stdin="not json")
    assert result.returncode == 0
    assert result.stderr == ""


def test_zero_turns_it_off(tmp_path):
    result = run(CLAUDE_KIT_WORKSPACE_RULES="0", CLAUDE_PROJECT_DIR=str(tmp_path))
    assert result.returncode == 0
    assert result.stdout == ""


def test_missing_claude_md_prints_nothing(tmp_path):
    kit = make_kit(tmp_path, None)
    other = tmp_path / "other"
    other.mkdir()
    result = run(kit / "plugin" / "hooks" / HOOK.name, CLAUDE_PROJECT_DIR=str(other))
    assert result.returncode == 0
    assert result.stdout == ""


def test_whole_file_when_no_kit_dev_section(tmp_path):
    kit = make_kit(tmp_path, "# Rules\n\n## Only\n\nkeep me\n")
    other = tmp_path / "other"
    other.mkdir()
    hook = kit / "plugin" / "hooks" / HOOK.name
    assert "keep me" in context(run(hook, CLAUDE_PROJECT_DIR=str(other)))


def test_size_cap(tmp_path):
    assert len(context(run(CLAUDE_PROJECT_DIR=str(tmp_path)))) <= 12_000


def test_registered_after_kit_map_without_matcher():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    groups = hooks["hooks"]["SessionStart"]
    commands = [g["hooks"][0]["command"] for g in groups]
    kit = next(i for i, c in enumerate(commands) if "kit_map_inject.py" in c)
    rules = groups[kit + 1]
    assert "hooks/workspace_rules_inject.py" in rules["hooks"][0]["command"]
    assert "matcher" not in rules
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_workspace_rules_inject.py -o addopts=""`
Expected: FAIL (the hook file does not exist).

- [ ] **Step 3: Write `plugin/hooks/workspace_rules_inject.py`**

```python
#!/usr/bin/env python3
"""SessionStart hook: inject the workspace rules in repos outside the kit.

Claude Code loads the workspace CLAUDE.md only for repos inside the kit
checkout. In any other repo this prints that file, up to its
"## Developing the kit" section, so the rules apply wherever a repo is cloned
(ADR 0034). Silent inside the kit root and in git worktrees of the kit, which
load a kit CLAUDE.md natively. On by default; CLAUDE_KIT_WORKSPACE_RULES=0
turns it off. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

KIT_DEV = "## Developing the kit"


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_WORKSPACE_RULES") != "0"


def kit_root() -> Path | None:
    """The kit checkout: the parent of the real plugin/ folder, links followed."""
    root = Path(__file__).resolve().parents[2]
    return root if (root / "CLAUDE.md").is_file() else None


def project_dir(stdin_text: str) -> Path:
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    try:
        data = json.loads(stdin_text) if stdin_text.strip() else {}
    except ValueError:
        data = {}
    cwd = data.get("cwd") if isinstance(data, dict) else None
    return Path(cwd).resolve() if cwd else Path.cwd().resolve()


def same(a: Path, b: Path) -> bool:
    return os.path.normcase(str(a)) == os.path.normcase(str(b))


def inside(path: Path, root: Path) -> bool:
    return same(path, root) or any(same(parent, root) for parent in path.parents)


def in_kit_worktree(project: Path, root: Path) -> bool:
    """True when the project is in a git worktree whose common dir is the kit's."""
    try:
        done = subprocess.run(
            ["git", "-C", str(project), "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    common = done.stdout.strip()
    if done.returncode != 0 or not common:
        return False
    return same((project / common).resolve(), (root / ".git").resolve())


def rules(root: Path) -> str:
    lines = (root / "CLAUDE.md").read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.startswith(KIT_DEV):
            lines = lines[:index]
            break
    return "\n".join(lines).strip()


def build(root: Path) -> str:
    where = root.as_posix()
    header = (
        f"Workspace rules (claude-kit, from {where}/CLAUDE.md). This repo is "
        "outside the kit folder, so Claude Code did not load them; follow them "
        f"as you would a CLAUDE.md. Relative links resolve against {where}."
    )
    return f"{header}\n\n{rules(root)}"


def main() -> int:
    try:
        stdin_text = "" if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read()
        root = kit_root() if enabled() else None
        if root is not None:
            project = project_dir(stdin_text)
            if not inside(project, root) and not in_kit_worktree(project, root):
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "SessionStart",
                        "additionalContext": build(root),
                    }
                }
                print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] workspace-rules inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

If `ruff format --check` reformats the long `stdin_text = ...` line, accept
ruff's formatting (`ruff format plugin/hooks/workspace_rules_inject.py`).

- [ ] **Step 4: Register the hook**

In `plugin/hooks/hooks.json`, directly after the SessionStart group whose
command runs `hooks/kit_map_inject.py`, insert this group (no `matcher`):

```json
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/workspace_rules_inject.py\""
          }
        ]
      },
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_workspace_rules_inject.py tests/test_kit_map_inject.py tests/test_plugin_manifest.py -o addopts=""`
Expected: all PASS (the kit-map registration test still finds the kit map
right after the lean-context group).

- [ ] **Step 6: Full suite, lint, commit**

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
git add plugin/hooks/workspace_rules_inject.py plugin/hooks/hooks.json tests/test_workspace_rules_inject.py
git commit -m "Inject the workspace rules in repos outside the kit folder" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Rules moved into CLAUDE.md and ADRs 0033 to 0035

**Files:**
- Modify: `CLAUDE.md` (the "A feature is not finished" paragraph and the "Developing the kit" section)
- Create: `knowledge/decisions/0033-cross-platform-installer.md`
- Create: `knowledge/decisions/0034-workspace-rules-inject.md`
- Create: `knowledge/decisions/0035-process-rules-in-claude-md.md`
- Modify: `knowledge/decisions/README.md` (row 0005; rows 0033 to 0035 appended)
- Modify: `knowledge/decisions/0005-kit-is-a-skills-dir-plugin.md` (Status line)
- Test: `tests/test_docs.py` (one new test appended)

**Depends on:** none

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: the ADR file names above (Task 4's setup guide links ADR 0006 only, not these); the three CLAUDE.md phrases `never suggests deleting`, `Never write the names of private repos`, `fold it into an existing flow step`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs.py`:

```python
def test_claude_md_has_rules_moved_from_memory():
    text = " ".join((REPO / "CLAUDE.md").read_text(encoding="utf-8").split())
    for phrase in (
        "never suggests deleting",
        "Never write the names of private repos",
        "fold it into an existing flow step",
    ):
        assert phrase in text, phrase
    kit_dev = text.split("## Developing the kit", 1)[1]
    assert "Never write the names of private repos" in kit_dev
    assert "fold it into an existing flow step" in kit_dev


def test_team_setup_adrs_indexed():
    decisions = REPO / "knowledge" / "decisions"
    index = (decisions / "README.md").read_text(encoding="utf-8")
    for name in (
        "0033-cross-platform-installer.md",
        "0034-workspace-rules-inject.md",
        "0035-process-rules-in-claude-md.md",
    ):
        assert (decisions / name).is_file(), name
        assert f"]({name})" in index, name
    row = next(line for line in index.splitlines() if "0005-kit-is" in line)
    assert "amended by 0033" in row
    adr = (decisions / "0005-kit-is-a-skills-dir-plugin.md").read_text("utf-8")
    assert "amended by 0033" in adr
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_docs.py -o addopts="" -k "moved_from_memory or team_setup_adrs"`
Expected: FAIL (phrases and ADR files missing).

- [ ] **Step 3: Edit `CLAUDE.md`**

In the paragraph that starts `**A feature is not finished until its
workspace is gone.**`, replace

```
locally and on the remote, and any scratch files created outside the repo deleted.
```

with

```
locally and on the remote, and any scratch files created outside the repo deleted.
Clean-up never deletes a repository and never suggests deleting one; the repo's
owner does that.
```

In `## Developing the kit (this repo)`, replace

```
Hook edits (`plugin/hooks/`) need a new session or `/reload-plugins`; `SKILL.md`
and command edits are live (the plugin is loaded in place through a junction,
ADR 0005). Never run `plugin/install.ps1` from a test without `-SkillsDir <tmp>`.
```

with

```
Hook edits (`plugin/hooks/`) need a new session or `/reload-plugins`; `SKILL.md`
and command edits are live (the plugin is loaded in place through a junction or
symlink, ADR 0005). Never run `plugin/install.py` (or its wrapper
`plugin/install.ps1`) from a test without a temporary `--skills-dir`
(`-SkillsDir`).

- This repo is public. Never write the names of private repos or a machine's
  username into tracked files; refer to them generically ("a project repo") and
  use `%USERPROFILE%` or `<repo-root>` in paths. Grep the diff for them before
  committing.
- When a new behaviour should recur (say, at the end of each session), first
  fold it into an existing flow step, such as `/ship`'s clean-up; propose
  session-end automation only as an alternative.
```

- [ ] **Step 4: Write the three ADRs**

`knowledge/decisions/0033-cross-platform-installer.md`:

```markdown
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
```

`knowledge/decisions/0034-workspace-rules-inject.md`:

```markdown
# ADR 0034: Workspace rules injected outside the kit folder

- **Status:** accepted
- **Date:** 2026-10-13

## Context
Claude Code loads the workspace `CLAUDE.md` only for repos inside the kit
checkout. A contributor who clones project repos elsewhere gets the plugin
and the kit map (ADR 0032) but none of the workspace rules.

## Decision
- A SessionStart hook (`workspace_rules_inject.py`, no matcher) injects the
  workspace `CLAUDE.md` up to its `## Developing the kit` section.
- It is silent when the project dir is the kit root or inside it, and when
  the project is a git worktree of the kit (its git common dir is the kit's
  `.git`), because those sessions load a kit `CLAUDE.md` natively.
- On by default; `CLAUDE_KIT_WORKSPACE_RULES=0` switches it off.

## Alternatives
- An `@` import in `~/.claude/CLAUDE.md`: loads twice inside the kit tree,
  includes the kit-development rules, and edits a personal file.
- Requiring every repo to live under the kit checkout.

## Consequences
About 2k to 2.5k tokens (under 12,000 characters) per session, in repos
outside the kit folder only. There the rules arrive as hook context rather
than as a `CLAUDE.md`.
```

`knowledge/decisions/0035-process-rules-in-claude-md.md`:

```markdown
# ADR 0035: Process rules move from personal memory into CLAUDE.md

- **Status:** accepted
- **Date:** 2026-10-13

## Context
Three rules lived only, or only partly, in the kit owner's auto-memory,
which a teammate never sees: clean-up never deletes or suggests deleting a
repo; the kit repo is public, so tracked files name no private repo or
machine username; recurring behaviour goes into an existing flow step first.

## Decision
The three rules become workspace rules in `CLAUDE.md`. The repo-deletion
rule joins the feature clean-up paragraph; the other two go under
"Developing the kit", so they are not injected into project repos.

## Alternatives
Leave them personal: every new contributor would have to learn them by
correction.

## Consequences
Every contributor follows them. The owner's memory copies are removed after
the change merges.
```

- [ ] **Step 5: Update the ADR index and ADR 0005**

In `knowledge/decisions/README.md`, change the 0005 row's status cell from
`accepted` to `accepted; amended by 0033`, and append after the 0032 row:

```markdown
| [0033](0033-cross-platform-installer.md) | Cross-platform Python installer | accepted | 2026-10-13 |
| [0034](0034-workspace-rules-inject.md) | Workspace rules injected outside the kit folder | accepted | 2026-10-13 |
| [0035](0035-process-rules-in-claude-md.md) | Process rules move from personal memory into `CLAUDE.md` | accepted | 2026-10-13 |
```

In `knowledge/decisions/0005-kit-is-a-skills-dir-plugin.md`, change
`- **Status:** accepted` to
`- **Status:** accepted; amended by 0033 ([ADR 0033](0033-cross-platform-installer.md))`.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pytest tests/test_docs.py -o addopts=""`
Expected: all PASS, including `test_relative_markdown_links_resolve` and
`test_learnings_capture_is_part_of_finishing`.

- [ ] **Step 7: Full suite, lint, commit**

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
git add CLAUDE.md knowledge/decisions tests/test_docs.py
git commit -m "Move three process rules into CLAUDE.md; ADRs 0033-0035" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Setup guide and README

**Files:**
- Create: `docs/setup.md`
- Modify: `README.md` (the `plugin/` bullet under "What's here")
- Test: `tests/test_docs.py` (three new tests appended)

**Depends on:** Task 1, Task 2

**Interfaces:**
- Consumes: the installer's command line and messages (Task 1); the env
  switch `CLAUDE_KIT_WORKSPACE_RULES` (Task 2).
- Produces: `docs/setup.md`, linked from `README.md` as `](docs/setup.md)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_docs.py` (add `import re` at the top if it is not
already imported; it is):

```python
def _tracked_plugin_text():
    """Every tracked text file under plugin/ (binary files are skipped)."""
    out = subprocess.run(
        ["git", "ls-files", "plugin"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for line in out.splitlines():
        try:
            yield (REPO / line).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue


def test_setup_guide_exists_and_is_linked():
    assert (REPO / "docs" / "setup.md").is_file()
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "](docs/setup.md)" in readme


def test_setup_guide_lists_every_env_switch():
    guide = (REPO / "docs" / "setup.md").read_text(encoding="utf-8")
    names = set()
    for text in _tracked_plugin_text():
        names |= set(re.findall(r"CLAUDE_KIT_[A-Z][A-Z_]*", text))
    names.add("CLAUDE_KIT_WORKSPACE_RULES")
    missing = sorted(name for name in names if name not in guide)
    assert not missing, missing


def test_setup_guide_names_prerequisites_and_installer():
    guide = (REPO / "docs" / "setup.md").read_text(encoding="utf-8")
    assert "superpowers@claude-plugins-official" in guide
    assert "install.py" in guide
    assert "ExecutionPolicy" in guide
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "ExecutionPolicy" not in readme
    assert "ten hooks" in readme
    assert "CLAUDE_KIT_WORKSPACE_RULES=0" in readme
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_docs.py -o addopts="" -k setup_guide`
Expected: FAIL (`docs/setup.md` missing).

- [ ] **Step 3: Write `docs/setup.md`**

````markdown
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
````

The switch defaults above come from the hooks: `DEFAULT_AT = 300_000` and
`DEFAULT_STEP = 100_000` in `plugin/hooks/context_nudge.py`;
`lean_context_inject.py`, `kit_map_inject.py` and the new
`workspace_rules_inject.py` are on unless `0`; `grill_inject.py` is on only
when `1`. Re-check them in those files before committing.

- [ ] **Step 4: Edit `README.md`**

In the `plugin/` bullet, replace

```
  measurement script, a status line, and nine hooks (regenerate the spec/plan
  index after edits and at every stop; report leftover worktrees, inject the
  branch handoff, inject the lean-context rule unless `CLAUDE_KIT_LEAN_CONTEXT=0`, inject the kit map unless `CLAUDE_KIT_KIT_MAP=0`, inject the grill rule when `CLAUDE_KIT_GRILL=1`,
```

with

```
  measurement script, a status line, and ten hooks (regenerate the spec/plan
  index after edits and at every stop; report leftover worktrees, inject the
  branch handoff, inject the lean-context rule unless `CLAUDE_KIT_LEAN_CONTEXT=0`, inject the kit map unless `CLAUDE_KIT_KIT_MAP=0`, inject the workspace rules in repos outside the kit folder unless `CLAUDE_KIT_WORKSPACE_RULES=0`, inject the grill rule when `CLAUDE_KIT_GRILL=1`,
```

and replace

```
  snapshot git state at session end). Install once per machine with `plugin\install.ps1` — it junctions
  `~/.claude/skills/claude-kit` to this folder so edits are live, and adds the
  kit's status line to `~/.claude/settings.json` when none is configured. If
  PowerShell refuses to run the script (execution policy), use
  `powershell -ExecutionPolicy Bypass -File plugin\install.ps1`. It also
```

with

```
  snapshot git state at session end). Install once per machine, on any OS,
  with `python plugin/install.py` (see the [setup guide](docs/setup.md)) —
  it checks the prerequisites, links `~/.claude/skills/claude-kit` to this
  folder (a junction on Windows, a symlink elsewhere) so edits are live, and
  adds the kit's status line to `~/.claude/settings.json` when none is
  configured. It also
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_docs.py -o addopts=""`
Expected: all PASS, including `test_relative_markdown_links_resolve`
(the guide's links `../CLAUDE.md`, `../README.md`, `ship-fast.md` and the
ADR 0006 link resolve).

- [ ] **Step 6: Full suite, lint, commit**

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
git add docs/setup.md README.md tests/test_docs.py
git commit -m "Setup guide for any OS; README points to it" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Manifest 0.24.0

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json` (`version`, end of `description`)
- Test: `tests/test_plugin_manifest.py` (`test_version_is_0_23_0` renamed; one test appended)

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: version `0.24.0`; description containing `cross-platform installer`.

- [ ] **Step 1: Update the tests**

In `tests/test_plugin_manifest.py`, replace

```python
def test_version_is_0_23_0():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "0.23.0"
```

with

```python
def test_version_is_0_24_0():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "0.24.0"


def test_description_mentions_cross_platform_installer():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert "cross-platform installer" in data["description"]
    assert "workspace rules" in data["description"]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_plugin_manifest.py -o addopts=""`
Expected: FAIL on the two tests above.

- [ ] **Step 3: Update `plugin/.claude-plugin/plugin.json`**

Change `"version": "0.23.0"` to `"version": "0.24.0"`. In `description`,
replace the ending

```
the absolute paths of the kit's playbooks and ADRs."
```

with

```
the absolute paths of the kit's playbooks and ADRs, a cross-platform installer (plugin/install.py) that checks the prerequisites, and workspace rules injected in repos outside the kit folder."
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_plugin_manifest.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Full suite, lint, commit**

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
git add plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "Bump plugin to 0.24.0" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Public-repo check before the PR

**Files:**
- none (a check; fix any hit in the file it names and commit the fix as a new commit)

**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5

**Interfaces:**
- Consumes: the branch's diff against `origin/main`.
- Produces: nothing.

- [ ] **Step 1: Grep the added lines (spec success criterion 2)**

From the worktree root, run this as ONE PowerShell command (variables do
not persist between separate tool calls):

```powershell
$slug = gh repo view --json nameWithOwner -q .nameWithOwner; $added = (git diff origin/main...HEAD) -match '^\+' -replace [regex]::Escape($slug), ''; @($env:USERNAME) + @(gh repo list --visibility private --limit 500 --json name -q '.[].name') | Where-Object { $_ } | ForEach-Object { $n = $_; $added | Where-Object { $_.IndexOf($n, [StringComparison]::OrdinalIgnoreCase) -ge 0 } | ForEach-Object { "HIT [$n]: $_" } }
```

Expected: no output. On bash use `$USER` and an equivalent `grep -iF`
loop.

- [ ] **Step 2: Fix any hit and commit**

Any `HIT` line: rewrite that line generically in the file it came from, then

```bash
pytest
ruff check plugin tests
ruff format --check plugin tests
git add -u
git commit -m "Remove private names from tracked files" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

With no hits, there is nothing to commit; the task is done.

---

## After merge (done by the `/ship` session, not part of the PR)

These touch files outside the repo and run after the squash-merge. The
`/ship` session does both at the end of its step 11 (Cleanup), after the
fast-forward of local `main` and before the step 12 report; the report
states each one as done or pending.

If step 11 did not fast-forward local `main` (the main checkout was not on
`main`, was dirty, or had its own commits), the main checkout has neither
`plugin/install.py` nor the new hook. Then skip step 1 below and report the
live check as pending for the owner, with the exact commands from step 1 to
run after they update `main`. Step 2 (memory clean-up) still runs, because
the change is merged on `origin/main` either way.

1. **Live check (spec success criterion 3).** In the main checkout run
   `python plugin/install.py`; expect `claude-kit already installed` and
   exit 0, and no superpowers warning (the owner has it enabled). Then run
   the hook directly from the main checkout. Bash:
   `CLAUDE_PROJECT_DIR=<a temp folder outside the kit> python plugin/hooks/workspace_rules_inject.py < /dev/null`;
   PowerShell:
   `$env:CLAUDE_PROJECT_DIR='<a temp folder outside the kit>'; '' | python plugin/hooks/workspace_rules_inject.py`.
   It prints JSON containing `Workspace rules`; with `CLAUDE_PROJECT_DIR`
   set to a project folder inside the kit checkout it prints nothing.
   The session-level part of criterion 3 needs a fresh session, which the
   `/ship` session cannot open, so report it as pending for the owner with
   these steps: run `/reload-plugins` (or start a new session); in a repo
   outside the kit folder, confirm the session context contains
   `Workspace rules (claude-kit, from`; in a repo under the kit folder,
   confirm it does not.
2. **Memory clean-up.** In the owner's auto-memory folder
   (`%USERPROFILE%\.claude\projects\<workspace-project>\memory\`), delete
   `no-suggest-repo-deletion.md`, `claude-kit-public-no-private-names.md`
   and `fold-into-existing-flow-steps.md`, remove their lines from
   `MEMORY.md`, and update `kit-map-and-team-setup.md` to say team setup
   shipped as 0.24.0 with its PR number.

## Verification (spec success criteria)

1. All tests above pass; `pytest`, `ruff check plugin tests` and
   `ruff format --check plugin tests` pass on CI for Ubuntu and Windows.
2. Task 6's grep has no hits.
3. The after-merge live check behaves as described.
