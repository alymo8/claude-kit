# Vibe native plugin Implementation Plan

- **Status:** approved
- **Date:** 2026-11-23
- **Frozen:** `tests/test_vibe_plugin.py` (the spec has no Frozen bullet, spec D6; this plan writes that file's full content in Task 1 and success criterion 1 depends on it)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `python plugin/install.py --agent vibe` builds two native Mistral Vibe plugins (`agent-kit`, `superpowers`) under `~/.vibe/plugins/` and removes the old link-and-hook install.

**Architecture:** A new module `plugin/vibe_plugin.py` assembles both plugin folders from the checkout into a staging folder beside the output folder and swaps them in. `plugin/install.py` checks every precondition first, then calls the builder, then strips the kit's old `~/.vibe/hooks.toml` block, repoints the `~/.vibe/AGENTS.md` fallback line and removes the old skill links when Codex and Cursor do not use them. Docs, the tool mapping, the version (1.1.0) and ADR 0053 follow.

**Tech Stack:** Python 3.11 (install.py and vibe_plugin.py stay parseable by 3.8), pytest, ruff, PowerShell wrapper, Markdown.

**Spec:** `docs/superpowers/specs/2026-11-23-vibe-plugin-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-23-vibe-plugin-design.md`

## Context for the executor

This repo is the kit; the Claude Code plugin lives in `plugin/`. Work in the
worktree `<repo-root>/.claude/worktrees/vibe-plugin` on branch
`feat/vibe-plugin`; never switch branches. Setup once:
`pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks: `pytest`
(plain, `pyproject.toml` already adds `-q`), `ruff check plugin tests`,
`ruff format --check plugin tests`. `tests/helpers.py` exports `PLUGIN` (the
`plugin/` path), `REPO`, `load_module(path, name)` and `clean_env()`.
`tests/test_install.py` already has `run_agent(tmp_path, agent, *extra)`
(runs the installer with `--home <tmp>/home --python sys.executable`),
`skills(tmp_path)`, `snapshot(root)`, `installer()` (imports install.py),
`make_dir_link`, `is_link`, `out(result)` and `VENDOR`. Never run
`plugin/install.py` from a test without a temporary `--home`. The repo is
public: never write a machine username or a private repo name into a tracked
file. Test code must fit ruff's 88-character lines. Edit test files with the
Edit or Write tool, never through a bash heredoc (it mangles `\n` escapes).
Commit after each task with a message ending in
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Global Constraints

- Plugin manifest `$schema` is exactly `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`.
- Plugin folder and `name`: lowercase letters, digits, `.` and `-`; the names are `agent-kit` and `superpowers`.
- Vibe extension: `"extensions": {"ai.mistral.vibe": {"schemaVersion": 1, ...}}`; `agent-kit` adds `"displayName": "agent-kit"`.
- `agent-kit` `repository` is `https://github.com/alymo8/claude-kit`.
- Marker file `.agent-kit-build` in both folders, one line: the kit version (from `plugin/.claude-plugin/plugin.json`) plus `\n`.
- Both built folders hold plain files only: no symlinks, no junctions, no `.claude-plugin/`.
- Staging folder: `<out parent>/.agent-kit-staging/` (for `~/.vibe/plugins/` that is `~/.vibe/.agent-kit-staging/`), removed on success, on failure, and first when stale.
- Hook names and types: `agent-kit-session-start` (`session_start`) and `agent-kit-stop` (`post_agent`, `match = "main"`); no `timeout` key (see Task 1, plan question 4).
- Final installer line for Vibe: `Next: start a new Vibe session (or run /reload-plugins).`
- Kit version becomes `1.1.0`; `.claude-plugin/marketplace.json` is unchanged.
- `plugin/install.py` and `plugin/vibe_plugin.py` stay parseable by Python 3.8 (`from __future__ import annotations`, no `match`, no `tomllib` import).
- Codex and Cursor installs are unchanged.

## Review Focus

- A Vibe session is open on Windows while the installer swaps the folders, so a rename fails: both previous copies must come back intact, the staging folder must be gone, and the installer exits 1. Pinned by `test_failed_swap_restores_both_copies` (Task 1).
- The hook runner's own `__pycache__/` exists in the copy after Vibe ran it: a rerun must still replace the copy cleanly and the marker check must not trip. Pinned by `test_rebuild_is_byte_identical_and_drops_runtime_files` (Task 1).
- The python command or the home folder holds a space or an apostrophe: the hook command must stay one valid TOML string and split into the right argv. Pinned by `test_hooks_toml_quotes_spaces` and `test_hooks_toml_survives_quote_in_python_path` (Task 1).
- A dangling skill link into the current checkout (a skill since deleted) sits in `~/.agents/skills/`: it is a kit link and is removed. Pinned by `test_vibe_removes_dangling_kit_link` (Task 2).
- `~/.codex/hooks.json` exists but is malformed: treat it as in use, keep the links and warn, never crash. Pinned by `test_vibe_unreadable_other_hook_file_counts_as_in_use` (Task 2).

## Answers to the spec gate's plan questions

Each answer is applied in the task named.

1. **Check order (Task 2).** `install_vibe` runs, before any write: (a) the foreign-folder check on both plugin folders, (b) the `hooks.toml` strip of both blocks, (c) the `AGENTS.md` block. Any failure prints one `ERROR:` line and returns 1 with nothing changed. Only then: build (stage both, swap both), write `hooks.toml`/`AGENTS.md`, handle links.
2. **`VERSION` parsing (Task 1).** Each line is split on its first `:`; keys and values are stripped. `version` and `source` must both be present and non-empty, else `BuildError` naming the missing key.
3. **Swap (Task 1).** Every move uses `os.rename` inside one filesystem (staging is a sibling of the output folder). Per plugin: rename the existing target to `<staging>/<name>.old`, rename `<staging>/<name>` to the target. Standalone `--out DIR` uses the same rule: staging is `DIR/../.agent-kit-staging`.
4. **Timeout (Task 1).** No `timeout` key: the spec calls them "the same two the user block holds today", which set none, and Vibe's unit for it is undocumented. The live run (Task 4) checks a session start completes.
5. **Staging and mixed state (Task 1).** Both plugins are fully staged before either swaps. If any swap fails, every plugin already swapped is removed and its `.old` renamed back, and a target already moved aside to `<name>.old` whose new copy failed to rename in is renamed back too, so no mixed state is left; then `BuildError`.
6. **Unreadable Codex/Cursor `hooks.json` (Task 2).** Counts as in use: links kept, warning printed. A missing file counts as not in use.
7. **Links into another checkout (Task 2).** Only links into the current checkout's three skill roots (`under_kit_roots`, dangling ones included) are removed. A link named like a kit skill that points elsewhere is kept and reported with one `Kept <name>: ...` line.
8. **Copied `hooks/hooks.json` (Task 1, Task 4).** It must stay in the copy: the copy's `hooks/run.py` reads it. Vibe loads plugin hooks only from `ai.mistral.vibe/hooks.toml`, so it is ignored; Task 4's check that `/plugins` shows no warnings and a turn ends without a hook warning confirms it. If Vibe does register it, stop and report.
9. **Standalone `vibe_plugin.py --out DIR` (Task 1).** Refuses an unmarked folder too (the check lives in `build`); default `--python` is `python`, as in `install.py`.
10. **"Left empty" (Task 2).** After stripping, a file whose text is empty or whitespace only is deleted, and only when the strip changed it; otherwise the text is written as `rest.rstrip("\n") + "\n"`.

---

### Task 1: The Vibe plugin builder

**Files:**
- Create: `plugin/vibe_plugin.py`
- Test: `tests/test_vibe_plugin.py` (frozen)

**Depends on:** none

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces (in `plugin/vibe_plugin.py`):
  - constants `NAMES = ("agent-kit", "superpowers")`, `MARKER = ".agent-kit-build"`, `STAGING = ".agent-kit-staging"`, `SCHEMA`, `REPOSITORY`, `KIT = Path(__file__).resolve().parent.parent`;
  - `class BuildError(Exception)`;
  - `read_version_file(path: Path) -> tuple[str, str]` (version, source);
  - `runner_command(python: str, runner: Path, event: str) -> str`;
  - `hooks_toml(python: str, runner: Path) -> str`;
  - `foreign_folders(out: Path) -> list[Path]`;
  - `merge_skills(roots: list[Path], dest: Path) -> list[str]`;
  - `build(out: Path, python: str = "python", kit: Path = KIT) -> None` (raises `BuildError`);
  - `main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_vibe_plugin.py` with exactly this content (frozen: do not edit it later; if a test looks wrong, stop and report):

```python
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest
from helpers import PLUGIN, REPO, clean_env, load_module

BUILDER = PLUGIN / "vibe_plugin.py"
VENDOR = REPO / "vendor" / "superpowers"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
NAME_RE = re.compile(r"[a-z0-9.-]+")
NAMES = ("agent-kit", "superpowers")
STAGING = ".agent-kit-staging"


def builder():
    return load_module(BUILDER, "vibe_plugin")


def claude_manifest():
    path = PLUGIN / ".claude-plugin" / "plugin.json"
    return json.loads(path.read_text(encoding="utf-8"))


def run_builder(out, *extra):
    command = [sys.executable, str(BUILDER), "--out", str(out)]
    command += ["--python", sys.executable, *extra]
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("vibe") / "plugins"
    result = run_builder(out)
    assert result.returncode == 0, result.stdout + result.stderr
    return out


def manifest(root, name):
    return json.loads((root / name / "plugin.json").read_text(encoding="utf-8"))


def skill_names(root):
    return {d.name for d in root.iterdir() if (d / "SKILL.md").is_file()}


def is_link(path):
    try:
        os.readlink(path)
    except (OSError, ValueError):
        return False
    return True


def snapshot(root):
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


@pytest.mark.parametrize("name", NAMES)
def test_manifest_shape(built, name):
    data = manifest(built, name)
    assert data["$schema"] == SCHEMA
    assert data["name"] == name and NAME_RE.fullmatch(data["name"])
    assert data["extensions"]["ai.mistral.vibe"]["schemaVersion"] == 1


def test_agent_kit_manifest_follows_claude_manifest(built):
    data = manifest(built, "agent-kit")
    claude = claude_manifest()
    for key in ("version", "description", "author", "license"):
        assert data[key] == claude[key], key
    assert data["repository"] == "https://github.com/alymo8/claude-kit"
    assert data["extensions"]["ai.mistral.vibe"]["displayName"] == "agent-kit"


def test_superpowers_manifest_follows_version_file(built):
    version, source = builder().read_version_file(VENDOR / "VERSION")
    data = manifest(built, "superpowers")
    assert data["version"] == version and data["repository"] == source
    assert data["license"] == "MIT"
    assert "agent-kit" in data["description"]


def test_skill_sets(built):
    kit = skill_names(PLUGIN / "skills") | skill_names(PLUGIN / "agent-skills")
    assert skill_names(built / "agent-kit" / "skills") == kit
    assert len(kit) == 20
    vendored = skill_names(VENDOR / "skills")
    assert skill_names(built / "superpowers" / "skills") == vendored
    assert len(vendored) == 12


@pytest.mark.parametrize("name", NAMES)
def test_skill_names_match_folders(built, name):
    for skill in sorted((built / name / "skills").iterdir()):
        text = (skill / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---", 2)[1]
        found = re.search(r"^name:\s*(\S+)\s*$", front, re.M)
        assert found and found.group(1) == skill.name, skill.name


def test_hooks_toml(built):
    path = built / "agent-kit" / "ai.mistral.vibe" / "hooks.toml"
    hooks = tomllib.loads(path.read_text(encoding="utf-8"))["hooks"]
    runner = (built / "agent-kit" / "hooks" / "run.py").resolve().as_posix()
    names = [h["name"] for h in hooks]
    assert names == ["agent-kit-session-start", "agent-kit-stop"]
    assert hooks[0]["type"] == "session_start" and "match" not in hooks[0]
    assert hooks[1]["type"] == "post_agent" and hooks[1]["match"] == "main"
    for hook, event in zip(hooks, ("SessionStart", "Stop"), strict=True):
        argv = shlex.split(hook["command"])
        assert argv[1] == runner
        assert argv[2:] == ["--agent", "vibe", "--event", event]


@pytest.mark.parametrize("name", NAMES)
def test_plain_files_only(built, name):
    root = built / name
    for dirpath, dirnames, filenames in os.walk(root):
        for entry in dirnames + filenames:
            assert not is_link(os.path.join(dirpath, entry)), entry
    assert not (root / ".claude-plugin").exists()
    marker = (root / ".agent-kit-build").read_text(encoding="utf-8")
    assert marker == claude_manifest()["version"] + "\n"


def test_agent_kit_copy_leaves_out_installer_files(built):
    root = built / "agent-kit"
    for name in ("agent-skills", "install.py", "install.ps1", "vibe_plugin.py"):
        assert not (root / name).exists(), name
    assert not list(root.rglob("__pycache__")) and not list(root.rglob("*.pyc"))
    for name in ("rules.md", "hooks/hooks.json", "conventions/README.md"):
        assert (root / name).is_file(), name


def test_superpowers_carries_license_and_version(built):
    for name in ("LICENSE", "VERSION"):
        copied = (built / "superpowers" / name).read_bytes()
        assert copied == (VENDOR / name).read_bytes(), name


def test_built_runner_prints_kit_map(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    runner = out / "agent-kit" / "hooks" / "run.py"
    project = tmp_path / "proj"
    project.mkdir()
    result = subprocess.run(
        [sys.executable, str(runner), "--agent", "vibe", "--event", "SessionStart"],
        input=json.dumps({"cwd": str(project), "source": "startup"}),
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=project,
        env=clean_env(),
        timeout=120,
    )
    data = json.loads(result.stdout)
    text = data["hook_specific_output"]["additional_context"]
    assert "Kit map (agent-kit)" in text
    root = (out / "agent-kit").resolve().as_posix()
    assert f"Plugin root: {root}" in text


def test_rebuild_is_byte_identical_and_drops_runtime_files(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    before = snapshot(out)
    cache = out / "agent-kit" / "hooks" / "__pycache__"
    cache.mkdir()
    (cache / "x.pyc").write_bytes(b"0")
    assert run_builder(out).returncode == 0
    assert snapshot(out) == before
    assert not (tmp_path / STAGING).exists()


@pytest.mark.parametrize("name", NAMES)
def test_foreign_folder_refused(tmp_path, name):
    out = tmp_path / "plugins"
    (out / name).mkdir(parents=True)
    (out / name / "mine.txt").write_text("mine", encoding="utf-8")
    result = run_builder(out)
    assert result.returncode == 1 and "ERROR" in result.stdout
    assert f"plugins{os.sep}{name}" in result.stdout
    assert sorted(p.name for p in out.iterdir()) == [name]
    assert (out / name / "mine.txt").read_text(encoding="utf-8") == "mine"
    assert not (tmp_path / STAGING).exists()


def test_stale_staging_removed(tmp_path):
    stale = tmp_path / STAGING / "agent-kit"
    stale.mkdir(parents=True)
    (stale / "junk.txt").write_text("x", encoding="utf-8")
    assert run_builder(tmp_path / "plugins").returncode == 0
    assert not (tmp_path / STAGING).exists()


def fake_kit(tmp_path):
    kit = tmp_path / "kit"
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    shutil.copytree(PLUGIN, kit / "plugin", ignore=ignore)
    shutil.copytree(VENDOR, kit / "vendor" / "superpowers", ignore=ignore)
    return kit


def test_failed_build_keeps_previous_copy(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    before = snapshot(out)
    kit = fake_kit(tmp_path)
    version_file = kit / "vendor" / "superpowers" / "VERSION"
    version_file.write_text("version: 1.0.0\n", encoding="utf-8")
    mod = builder()
    with pytest.raises(mod.BuildError, match="source"):
        mod.build(out, sys.executable, kit=kit)
    assert snapshot(out) == before
    assert not (tmp_path / STAGING).exists()


def test_failed_swap_restores_both_copies(tmp_path, monkeypatch):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    before = snapshot(out)
    real = os.rename

    def flaky(src, dst):
        src = Path(src)
        if src.name == "superpowers" and src.parent.name == STAGING:
            raise OSError("locked")
        return real(src, dst)

    monkeypatch.setattr(mod.os, "rename", flaky)
    with pytest.raises(mod.BuildError, match="locked"):
        mod.build(out, sys.executable)
    assert snapshot(out) == before
    assert not (tmp_path / STAGING).exists()


def test_version_file_needs_both_lines(tmp_path):
    mod = builder()
    path = tmp_path / "VERSION"
    path.write_text("version: 7.0.2\nsource: https://x.test/sp\n", encoding="utf-8")
    assert mod.read_version_file(path) == ("7.0.2", "https://x.test/sp")
    for text in ("version: 7.0.2\n", "source: https://x.test/sp\n", "version:\n"):
        path.write_text(text, encoding="utf-8")
        with pytest.raises(mod.BuildError):
            mod.read_version_file(path)


def test_duplicate_skill_name_is_a_build_error(tmp_path):
    mod = builder()
    for root in ("a", "b"):
        (tmp_path / root / "same").mkdir(parents=True)
        (tmp_path / root / "same" / "SKILL.md").write_text("x", encoding="utf-8")
    with pytest.raises(mod.BuildError, match="same"):
        mod.merge_skills([tmp_path / "a", tmp_path / "b"], tmp_path / "out")


def test_hooks_toml_quotes_spaces(tmp_path):
    python = "C:/Program Files/Python/python.exe"
    runner = tmp_path / "dir with space" / "run.py"
    hooks = tomllib.loads(builder().hooks_toml(python, runner))["hooks"]
    argv = shlex.split(hooks[0]["command"])
    assert argv[:2] == [python, runner.as_posix()]


def test_hooks_toml_survives_quote_in_python_path(tmp_path):
    python = "C:/Users/O'Neil/python.exe"
    text = builder().hooks_toml(python, tmp_path / "run.py")
    hooks = tomllib.loads(text)["hooks"]
    assert hooks[0]["command"].startswith(python + " ")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_vibe_plugin.py -o addopts=""`
Expected: every test fails or errors (`vibe_plugin.py` does not exist).

- [ ] **Step 3: Implement `plugin/vibe_plugin.py`**

Module docstring: what it builds, the usage line
`python plugin/vibe_plugin.py --out DIR [--python CMD]`, the spec path and
ADR 0053, and "Keep this file parseable by Python 3.8" (install.py imports
it). Start with `from __future__ import annotations`. The functions:

- `read_version_file(path)`: answer 2 above; an unreadable file is a `BuildError` too. The error message names the missing key (`... has no source: line`).
- `runner_command(python, runner, event)`: the same quoting rule as `install.hook_command`: `exe = f'"{python}"' if " " in python else python`, then `f'{exe} "{runner.as_posix()}" --agent vibe --event {event}'`.
- `hooks_toml(python, runner)`: the two `[[hooks]]` tables in this order, separated by one blank line, ending in `\n`; each `command` value written with `json.dumps(...)` (as `install.vibe_hooks` does today); keys `name`, `type`, then `match = "main"` for the stop hook only, then `command`. No `timeout` (answer 4).
- `foreign_folders(out)`: each `out / name` for `name in NAMES` that `os.path.lexists` and has no `MARKER` file.
- `merge_skills(roots, dest)`: copy every child folder of each root that holds a `SKILL.md` to `dest/<name>` (`shutil.copytree`, ignoring `__pycache__` and `*.pyc`); a name seen twice raises `BuildError` naming the skill and both roots; returns the sorted names.
- `build(out, python="python", kit=KIT)`:
  1. `out = Path(out).resolve()`; if `foreign_folders(out)`, raise `BuildError(f"{folder} exists and was not built by agent-kit; remove or rename it")` for the first one. Nothing is touched before this check.
  2. `staging = out.parent / STAGING`; remove it if it exists (stale).
  3. In a `try` whose `finally` removes `staging` (`shutil.rmtree(..., ignore_errors=True)`), with `OSError`, `ValueError` and `KeyError` re-raised as `BuildError`:
     - read the Claude manifest at `kit/plugin/.claude-plugin/plugin.json` and `read_version_file(kit/vendor/superpowers/VERSION)` first, so a bad input fails before any copy;
     - stage `agent-kit`: `shutil.copytree(kit/plugin, staging/"agent-kit")` ignoring, at the top level only, `.claude-plugin`, `agent-skills`, `skills`, `install.py`, `install.ps1`, `vibe_plugin.py`, and everywhere `__pycache__` and `*.pyc` (`copytree`'s default `symlinks=False` copies link targets as plain files); then `merge_skills([kit/plugin/skills, kit/plugin/agent-skills], staging/"agent-kit"/"skills")`; write `plugin.json` with keys in this order: `$schema`, `name`, `version`, `description`, `author`, `license` (the last four from the Claude manifest), `repository` (`REPOSITORY`), `extensions` (`{"ai.mistral.vibe": {"schemaVersion": 1, "displayName": "agent-kit"}}`); write `ai.mistral.vibe/hooks.toml` = `hooks_toml(python, out / "agent-kit" / "hooks" / "run.py")` (the final path, not the staging path); write `MARKER`;
     - stage `superpowers`: `merge_skills([kit/vendor/superpowers/skills], staging/"superpowers"/"skills")`, copy `LICENSE` and `VERSION` byte for byte, write `plugin.json` with `$schema`, `name` `superpowers`, `version` and `repository` from `VERSION`, `description` exactly `f"The superpowers skills, the copy bundled by agent-kit (from {source})."`, `license` `MIT`, `extensions` `{"ai.mistral.vibe": {"schemaVersion": 1}}`; write `MARKER`;
     - `out.mkdir(parents=True, exist_ok=True)`, then swap both as in answers 3 and 5, every move through `os.rename` (the frozen swap test patches `os.rename`). A swap `OSError` becomes `BuildError(f"could not swap in the new copy: {exc}")`.
  4. Every generated text file (`plugin.json` via `json.dumps(data, indent=2) + "\n"`, `hooks.toml`, the marker) is written with `encoding="utf-8", newline="\n"`, so a rerun is byte-identical.
- `main(argv)`: argparse `--out` (required) and `--python` (default `python`); on `BuildError` print `f"ERROR: {exc}; nothing changed."` and return 1; on success print `f"Built agent-kit and superpowers in {out}"` and return 0. `if __name__ == "__main__": raise SystemExit(main())`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_vibe_plugin.py -o addopts=""`
Expected: 23 passed.

- [ ] **Step 5: Lint**

Run: `ruff check plugin tests; ruff format --check plugin tests`
Expected: `All checks passed!` and no file to reformat.

- [ ] **Step 6: Commit**

```bash
git add plugin/vibe_plugin.py tests/test_vibe_plugin.py
git commit -m "Build the agent-kit and superpowers Vibe plugins (vibe_plugin.py)"
```

---

### Task 2: `install.py --agent vibe` installs the plugins and removes the old install

**Files:**
- Modify: `plugin/install.py` (docstring, `NEXT_STEP["vibe"]`, `hook_command`, `fallback_line`, `install_agent`, `main`; remove `vibe_hooks`)
- Modify: `plugin/install.ps1` (help text only)
- Test: `tests/test_install.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: from `plugin/vibe_plugin.py`: `BuildError`, `NAMES`, `foreign_folders(out)`, `build(out, python)` (`runner_command` is used only by a test).
- Produces (in `plugin/install.py`):
  - `hook_command(python: str, agent: str, event: str, runner: Path = RUNNER) -> str`;
  - `fallback_line(python: str, agent: str, runner: Path = RUNNER) -> str`;
  - `agents_block(text: str, python: str, agent: str, runner: Path = RUNNER) -> str`;
  - `kit_hooks_in_use(home: Path) -> list[Path]`;
  - `remove_kit_links(skills_dir: Path) -> None`;
  - `install_vibe(home: Path, skills_dir: Path, python: str) -> int`.

- [ ] **Step 1: Update the existing tests**

In `tests/test_install.py`:

- `test_agent_links_every_skill`: parametrize over `("codex", "cursor")` instead of `AGENTS`.
- `test_agent_skills_dir_override`, `test_foreign_entry_left_alone`, `test_kit_link_to_moved_skill_relinked`: run `"codex"` instead of `"vibe"`; assertions unchanged.
- Delete `test_vibe_hooks_toml_keeps_other_entries` and `test_vibe_toml_survives_quote_in_path` (replaced below and by Task 1's TOML tests).
- `test_damaged_block_markers_change_nothing`: add `assert not (tmp_path / "home" / ".vibe" / "plugins").exists()`.
- `legacy_files(agent)`: return `[md]` for every agent (the Vibe `hooks.toml` legacy case moves to `test_vibe_removes_legacy_block_*` below).
- `test_powershell_wrapper_agent_vibe`: replace the body after the `subprocess.run` with:

```python
    assert result.returncode == 0, out(result)
    plugins = tmp_path / ".vibe" / "plugins"
    for name in ("agent-kit", "superpowers"):
        assert (plugins / name / "plugin.json").is_file(), name
    assert not (tmp_path / ".agents").exists()
    assert not (tmp_path / ".claude" / "skills").exists()
    written = {
        Path(line.split(" ", 1)[1]).resolve()
        for line in result.stdout.splitlines()
        if line.startswith(("Wrote ", "Unchanged "))
    }
    assert (tmp_path / ".vibe").resolve() / "AGENTS.md" in written
    for path in written:
        assert path.is_relative_to(tmp_path.resolve()), path
```

`test_agents_md_block`, `test_second_run_changes_no_byte` and `test_report_names_next_step` keep their `vibe` cases unchanged.

- [ ] **Step 2: Add the new Vibe tests**

Append to `tests/test_install.py` (`PLUGIN`, `load_module`, `tomllib`, `VENDOR` and the helpers named in "Context for the executor" are already there):

```python
def vibe(tmp_path):
    return tmp_path / "home" / ".vibe"


def kit_link(tmp_path, name, target):
    skills(tmp_path).mkdir(parents=True, exist_ok=True)
    make_dir_link(skills(tmp_path) / name, target)


def test_vibe_installs_two_plugins(tmp_path):
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    for name in ("agent-kit", "superpowers"):
        folder = vibe(tmp_path) / "plugins" / name
        assert (folder / "plugin.json").is_file(), name
        assert (folder / ".agent-kit-build").is_file(), name
    assert not skills(tmp_path).exists()
    assert not (vibe(tmp_path) / "hooks.toml").exists()
    assert not (vibe(tmp_path) / ".agent-kit-staging").exists()
    step = "Next: start a new Vibe session (or run /reload-plugins)."
    assert step in result.stdout


def test_vibe_removes_kit_block_keeps_user_hook(tmp_path):
    mod = installer()
    path = vibe(tmp_path) / "hooks.toml"
    path.parent.mkdir(parents=True)
    mine = '[[hooks]]\nname = "mine"\ntype = "session_start"\ncommand = "echo"\n'
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    path.write_text(f"{mine}\n{block}", encoding="utf-8")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    text = path.read_text(encoding="utf-8")
    assert mod.TOML_BEGIN not in text and "old = 1" not in text
    assert [h["name"] for h in tomllib.loads(text)["hooks"]] == ["mine"]


def test_vibe_removes_legacy_block_keeps_user_text(tmp_path):
    mod = installer()
    path = vibe(tmp_path) / "hooks.toml"
    path.parent.mkdir(parents=True)
    old = f"{mod.LEGACY_TOML_BEGIN}\nold = 1\n{mod.LEGACY_TOML_END}\n"
    path.write_text(f"mine = 1\n\n{old}", encoding="utf-8")
    assert run_agent(tmp_path, "vibe").returncode == 0
    assert path.read_text(encoding="utf-8") == "mine = 1\n"


def test_vibe_removes_legacy_block_and_deletes_empty_file(tmp_path):
    mod = installer()
    path = vibe(tmp_path) / "hooks.toml"
    path.parent.mkdir(parents=True)
    old = f"{mod.LEGACY_TOML_BEGIN}\nold = 1\n{mod.LEGACY_TOML_END}\n"
    new = f"{mod.TOML_BEGIN}\nnew = 1\n{mod.TOML_END}\n"
    path.write_text(f"\n{old}\n{new}", encoding="utf-8")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert not path.exists()


def test_vibe_agents_md_names_the_copy(tmp_path):
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    text = (vibe(tmp_path) / "AGENTS.md").read_text(encoding="utf-8")
    runner = vibe(tmp_path) / "plugins" / "agent-kit" / "hooks" / "run.py"
    expected = f'"{runner.resolve().as_posix()}" --agent vibe --event SessionStart'
    assert expected in text


def test_vibe_removes_old_kit_links_keeps_foreign(tmp_path):
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    kit_link(tmp_path, "ship", PLUGIN / "agent-skills" / "ship")
    kit_link(tmp_path, "brainstorming", VENDOR / "brainstorming")
    mine = tmp_path / "mine"
    mine.mkdir()
    kit_link(tmp_path, "mine", mine)
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert sorted(os.listdir(skills(tmp_path))) == ["mine"]
    assert is_link(skills(tmp_path) / "mine")


def test_vibe_removes_dangling_kit_link(tmp_path):
    skills(tmp_path).mkdir(parents=True)
    gone = skills(tmp_path) / "gone"
    try:
        make_dir_link(gone, PLUGIN / "skills" / "no-such-skill")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("cannot create a dangling link here")
    assert run_agent(tmp_path, "vibe").returncode == 0
    assert not os.path.lexists(gone)


@pytest.mark.parametrize("agent", ["codex", "cursor"])
def test_vibe_keeps_links_while_other_agent_uses_them(tmp_path, agent):
    path = tmp_path / "home" / f".{agent}" / "hooks.json"
    path.parent.mkdir(parents=True)
    text = installer().json_hooks("", agent, sys.executable)
    path.write_text(text, encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert is_link(skills(tmp_path) / "spec-gate")
    assert "WARNING" in result.stdout and "twice" in result.stdout


def test_vibe_unreadable_other_hook_file_counts_as_in_use(tmp_path):
    path = tmp_path / "home" / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text("{oops", encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert is_link(skills(tmp_path) / "spec-gate")
    assert "WARNING" in result.stdout and "twice" in result.stdout


@pytest.mark.parametrize("name", ["agent-kit", "superpowers"])
def test_vibe_foreign_plugin_folder_changes_nothing(tmp_path, name):
    mod = installer()
    base = vibe(tmp_path)
    (base / "plugins" / name).mkdir(parents=True)
    (base / "plugins" / name / "plugin.json").write_text("{}", encoding="utf-8")
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    (base / "hooks.toml").write_text(block, encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    before = snapshot(tmp_path / "home")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 1 and "ERROR" in result.stdout
    assert f"plugins{os.sep}{name}" in result.stdout
    assert snapshot(tmp_path / "home") == before


def test_vibe_runner_command_matches_hook_command(tmp_path):
    builder = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    runner = tmp_path / "run.py"
    for python in ("python", "C:/Program Files/python.exe"):
        expected = installer().hook_command(python, "vibe", "Stop", runner=runner)
        assert builder.runner_command(python, runner, "Stop") == expected
```

- [ ] **Step 3: Run the tests to verify the new ones fail**

Run: `pytest tests/test_install.py -o addopts=""`
Expected: the new `test_vibe_*` tests and the rewritten PowerShell test fail (the installer still links skills and writes `hooks.toml`), except `test_vibe_removes_dangling_kit_link`, which the old `link_skills` already satisfies; the Codex, Cursor and Claude cases pass.

- [ ] **Step 4: Implement the Vibe install in `plugin/install.py`**

- `hook_command(python, agent, event, runner=RUNNER)` and `fallback_line(python, agent, runner=RUNNER)`: the new `runner` keyword replaces `RUNNER` in the command; existing callers are unchanged.
- Remove `vibe_hooks` (its block text now comes from `vibe_plugin.hooks_toml`; its tests moved to Task 1).
- `NEXT_STEP["vibe"] = "Next: start a new Vibe session (or run /reload-plugins)."`
- `kit_hooks_in_use(home)`: for `home/".codex"/"hooks.json"` and `home/".cursor"/"hooks.json"`, a missing file is not in use; a file that cannot be read or parsed is in use (answer 6); otherwise it is in use when any string value anywhere in the JSON (walk dicts and lists) satisfies `is_kit_command`. Returns the paths in use.
- `remove_kit_links(skills_dir)`: when `skills_dir` is a folder, for each entry in sorted order: `target = link_target(entry)`; if `target is not None and under_kit_roots(target, entry)`, `remove_link(entry)` and print `Removed old link <name>` (dangling ones included); elif `target is not None` and the name is one of `{f.name for f in skill_sources()}`, print `Kept <name>: it links outside this kit checkout (remove it by hand if it points into an old checkout)` (answer 7). Never creates `skills_dir`.
- `install_vibe(home, skills_dir, python)`, in this order (answer 1):
  1. Import the builder lazily: put `str(PLUGIN)` on `sys.path` if missing, then `import vibe_plugin` (install.py must stay importable by Python 3.8 before the version check, so no top-level import).
  2. `plugins = (home / ".vibe" / "plugins").resolve()`; for the first of `vibe_plugin.foreign_folders(plugins)`, print `ERROR: <folder> exists and was not built by agent-kit; remove or rename it, then rerun. Nothing changed.` and return 1.
  3. `hooks = home/".vibe"/"hooks.toml"`: `old = read_text(hooks)`, `rest = strip_block(strip_block(old, LEGACY_TOML_BEGIN, LEGACY_TOML_END), TOML_BEGIN, TOML_END)`. `rules = home/".vibe"/"AGENTS.md"`: `new_rules = agents_block(read_text(rules), python, "vibe")` with the fallback line built from `runner = plugins / "agent-kit" / "hooks" / "run.py"` (give `agents_block` a `runner: Path = RUNNER` keyword passed through to `fallback_line`). A `ValueError` prints `ERROR: <file> cannot be updated (<exc>); nothing changed.` and returns 1 (same wording as today).
  4. `vibe_plugin.build(plugins, python)`; a `BuildError` prints `ERROR: <exc>; nothing changed.` and returns 1. Print `Installed the agent-kit and superpowers plugins in <plugins>`.
  5. If `rest != old`: when `rest.strip() == ""` delete `hooks` and print `Removed <hooks> (only the kit's hooks were in it)`; else write `rest.rstrip("\n") + "\n"` (utf-8, `newline="\n"`) and print `Wrote <hooks>` (answer 10). If `rest == old`, write nothing.
  6. Write `rules` when it changed (`Wrote <rules>`), else print `Unchanged <rules>`, as `install_agent` does today.
  7. `in_use = kit_hooks_in_use(home)`; if empty, `remove_kit_links(skills_dir)`; else print `WARNING: kept the kit's skill links in <skills_dir>: <comma-separated in_use paths> still run the kit's hooks, so Vibe lists the kit's skills twice (bare and agent-kit:-prefixed) until Codex and Cursor stop using them.`
  8. Print `NEXT_STEP["vibe"]`; return 0.
- `install_agent` now only handles `codex` and `cursor` (drop its `vibe` branches); `main` calls `install_vibe(home, skills_dir, args.python)` for `--agent vibe`, with `skills_dir` defaulting to `home/.agents/skills` as today.
- Module docstring: replace the `--agent vibe` part of the last paragraph with what `install_vibe` does (build the two plugins into `<home>/.vibe/plugins`, remove the old `hooks.toml` block and, when Codex and Cursor do not use them, the old skill links; keep the `AGENTS.md` fallback line pointing at the copy).

- [ ] **Step 5: Update `plugin/install.ps1` help**

`.DESCRIPTION`: replace the last sentence with: `With -Agent codex or cursor it links the kit's skills into <Home>\.agents\skills and merges the kit's hook runner into that agent's user hook file instead. With -Agent vibe it installs the agent-kit and superpowers Vibe plugins under <Home>\.vibe\plugins and removes the old Vibe install.`
`.PARAMETER SkillsDir`: append `For vibe it only names where old kit skill links are removed.` The script body is unchanged.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pytest tests/test_install.py tests/test_vibe_plugin.py -o addopts=""`
Expected: all pass (the PowerShell test is skipped only where PowerShell is not on PATH).

- [ ] **Step 7: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` (expected clean), then:

```bash
git add plugin/install.py plugin/install.ps1 tests/test_install.py
git commit -m "install.py --agent vibe installs the Vibe plugins and removes the old install"
```

---

### Task 3: Version 1.1.0, tool mapping, docs and ADR 0053

**Files:**
- Modify: `plugin/.claude-plugin/plugin.json` (`version`)
- Modify: `tests/test_plugin_manifest.py` (`test_version_is_1_0_0`)
- Modify: `plugin/references/agent-tools.md`
- Modify: `docs/setup.md`, `README.md`, `AGENTS.md`
- Create: `knowledge/decisions/0053-vibe-native-plugin.md`
- Modify: `knowledge/decisions/README.md`, `knowledge/decisions/0052-published-plugin.md`, `knowledge/decisions/0050-agent-agnostic-kit.md`
- Test: `tests/test_docs.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing (the docs describe Task 2's behaviour as the spec states it).
- Produces: version `1.1.0` in the Claude manifest, which Task 1's built `agent-kit` manifest copies.

- [ ] **Step 1: Write the failing tests**

In `tests/test_plugin_manifest.py`, rename `test_version_is_1_0_0` to `test_version_is_1_1_0` and assert `data["version"] == "1.1.0"`.

Append to `tests/test_docs.py`:

```python
def test_docs_cover_vibe_plugins():
    heading = "## Using the kit with Vibe, Codex or Cursor"
    section = " ".join(_setup_section(heading).split())
    for needle in (
        "~/.vibe/plugins/",
        'disabled_plugins = ["agent-kit"]',
        "/reload-plugins",
        "twice",
    ):
        assert needle in section, needle
    assert "until a native Vibe plugin exists" not in section
    tools = (PLUGIN / "references" / "agent-tools.md").read_text(encoding="utf-8")
    assert "`agent-kit:<name>`" in tools and "`/agent-kit:ship`" in tools
    readme = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    assert readme.count("~/.vibe/plugins/") >= 2
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "python plugin/install.py --agent vibe" in agents


def test_vibe_plugin_adr_0053():
    decisions = REPO / "knowledge" / "decisions"
    adr = "0053-vibe-native-plugin.md"
    text = (decisions / adr).read_text(encoding="utf-8")
    assert "- **Status:** accepted" in text and "- **Date:** 2026-11-23" in text
    assert "0050" in text and "drift" in text
    index = (decisions / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
    for number, word in (("0050", "amended"), ("0052", "extended")):
        old = next(decisions.glob(f"{number}-*.md"))
        row = next(line for line in index.splitlines() if f"]({old.name})" in line)
        assert f"{word} by" in row and "0053" in row, number
        lines = old.read_text(encoding="utf-8").splitlines()
        status = next(line for line in lines if line.startswith("- **Status:**"))
        assert f"{word} by 0053" in status, number
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_plugin_manifest.py tests/test_docs.py -o addopts=""`
Expected: the three new or renamed tests fail; the rest pass.

- [ ] **Step 3: Bump the version**

`plugin/.claude-plugin/plugin.json`: `"version": "1.1.0"`. Do not touch the description or `.claude-plugin/marketplace.json`.

- [ ] **Step 4: Tool mapping** (`plugin/references/agent-tools.md`)

- Under "## Skill names", add a second paragraph: `In Vibe the kit's skills are the plugin skills` `` `agent-kit:<name>` `` `and` `` `superpowers:<name>` ``, `so Claude's names work as written.`
- Under "## Slash commands", add: `In Vibe, /ship is` `` `/agent-kit:ship` `` `(each command is the plugin skill of the same name).`
Leave the other sections unchanged.

- [ ] **Step 5: Docs**

- `docs/setup.md`, section "Using the kit with Vibe, Codex or Cursor":
  - Split what the installer does: for Codex and Cursor the existing bullets (links into `~/.agents/skills/`, hook runner into `~/.codex/hooks.json` or `~/.cursor/hooks.json`, the Codex `AGENTS.md` fallback line); for Vibe: it builds two native plugins, `agent-kit` and `superpowers`, under `~/.vibe/plugins/` (so `/plugins` lists them and the skills are `/agent-kit:<name>` and `/superpowers:<name>`); removes the kit's block from `~/.vibe/hooks.toml` (deleting the file if nothing else is in it); removes the old kit skill links from `~/.agents/skills/` unless Codex or Cursor still runs the kit's hooks; keeps the fallback line in `~/.vibe/AGENTS.md`, pointing at the copy; refuses, with nothing changed, when `~/.vibe/plugins/agent-kit` or `superpowers` exists and was not built by the kit.
  - Add: the Vibe plugins are a copy, so rerun the installer after updating the checkout; turn the kit off with `disabled_plugins = ["agent-kit"]` in `~/.vibe/config.toml`; a later Codex or Cursor install re-creates the skill links Vibe also reads, so Vibe then lists the kit's skills twice.
  - Reword "Vibe, Codex and Cursor users: rerun the installer after updating the checkout, once per agent, until a native Vibe plugin exists." to keep the phrase "rerun the installer after updating" (pinned by an existing test) without "until a native Vibe plugin exists", for example: `Vibe, Codex and Cursor users: rerun the installer after updating the checkout, once per agent: Vibe runs a copy, and Codex and Cursor pick up new or removed skills only then.` (the test is case-sensitive: keep the phrase lowercase)
  - Next steps: split "Vibe and Cursor: start a new session." into `Vibe: start a new session (or run /reload-plugins).` and `Cursor: start a new session.`
  - In the paragraph on `--home`, `--skills-dir` and `--python`: say that for Vibe `--skills-dir` only names where old links are removed, and that relinking moved skills and removing links to deleted skills apply to Codex and Cursor.
  - Keep `--agent vibe`, `--agent codex`, `--agent cursor`, `/hooks`, `vendor-superpowers.py`, `agent-skills.py` and `/ship-many` in the section (pinned by `test_docs_cover_other_agents`).
- `README.md`:
  - The sentence "Contributors, and Vibe, Codex and Cursor users, install from a checkout with `python plugin/install.py` instead ...": add that for Vibe `--agent vibe` installs two native plugins under `~/.vibe/plugins/` instead of skill links.
  - The agents paragraph starting "The kit also runs in Mistral Vibe, Codex and Cursor:": Vibe gets the `agent-kit` and `superpowers` plugins under `~/.vibe/plugins/`; Codex and Cursor get the links into `~/.agents/skills/` and the hooks. Keep "Codex", "Cursor" and the `docs/setup.md` link within the first 400 characters after "Mistral Vibe" (pinned by `test_docs_cover_other_agents`).
- `AGENTS.md` ("Developing the kit"), after the paragraph on hook edits: `Vibe runs a copy of the plugin, so to try an edit in Vibe rerun` `` `python plugin/install.py --agent vibe` `` `(then /reload-plugins or a new session).`

- [ ] **Step 6: ADR 0053 and the status lines**

Create `knowledge/decisions/0053-vibe-native-plugin.md` in the shape of ADR 0052: title `# ADR 0053: Mistral Vibe gets the kit as two native plugins built by the installer`, `- **Status:** accepted`, `- **Date:** 2026-11-23`, then `## Context` (the link-and-hook install gave the kit no identity in Vibe; Vibe 3.1.3's plugin format; links outside a plugin folder are rejected), `## Decision` (D1–D5 of the spec, one bullet each with the rejected options), `## Consequences` (Vibe users rerun after updating; skills are `agent-kit:<name>` and `superpowers:<name>`; Codex and Cursor stay on links; the format is experimental). Include one paragraph saying why an install-time copy does not reopen ADR 0050 D1's rejection of per-agent copies: nothing is committed twice, so the copy cannot drift from the checkout it was built from. Link ADRs as relative file links (`0050-agent-agnostic-kit.md`, `0052-published-plugin.md`).
- `knowledge/decisions/README.md`: append the row `| [0053](0053-vibe-native-plugin.md) | Mistral Vibe gets the kit as two native plugins built by the installer | accepted | 2026-11-23 |`; change the 0050 row's status to `accepted; amended by 0052, 0053` and the 0052 row's status to `accepted; extended by 0053`.
- `knowledge/decisions/0052-published-plugin.md` Status line: `- **Status:** accepted; extended by 0053 ([ADR 0053](0053-vibe-native-plugin.md): the native Vibe plugin of D3 now exists)`.
- `knowledge/decisions/0050-agent-agnostic-kit.md` Status line: append `; amended by 0053 ([ADR 0053](0053-vibe-native-plugin.md): Vibe gets native plugins instead of skill links and a user hook block)`, keeping the existing `amended by 0052` text (pinned by `test_published_plugin_adr_amends_others`).

- [ ] **Step 7: Run the full suite and lint**

Run: `pytest`, then `ruff check plugin tests; ruff format --check plugin tests`
Expected: no failures (including `test_relative_markdown_links_resolve`, `test_published_plugin_adr_amends_others`, `test_docs_cover_other_agents`, `test_agent_claude_matches_default` and `tests/test_workspace_rules_inject.py`); ruff clean.

- [ ] **Step 8: Commit**

```bash
git add plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py plugin/references/agent-tools.md docs/setup.md README.md AGENTS.md knowledge/decisions tests/test_docs.py
git commit -m "Vibe plugin docs, tool mapping, ADR 0053 and version 1.1.0"
```

---

### Task 4: Live run in Vibe 3.1.3 (success criterion 3)

**Files:** none (verification only; record the results in the PR description)

**Depends on:** Task 2, Task 3

**Interfaces:**
- Consumes: the finished installer (Task 2) and docs/version (Task 3).
- Produces: the evidence for success criterion 3.

The user's go-ahead on the spec covers running the installer against the real home. Vibe is an interactive TUI: where the executor cannot drive it, ask the user to run each check and paste the result.

- [ ] **Step 1: Install against the real home**

Run, from the worktree: `python plugin/install.py --agent vibe`
Expected: exit 0; `Installed the agent-kit and superpowers plugins in ...`; the last line is `Next: start a new Vibe session (or run /reload-plugins).`; `~/.vibe/hooks.toml` no longer holds `# >>> agent-kit hooks` (check with `grep -cE "(agent|claude)-kit hooks" ~/.vibe/hooks.toml`, expected 0 or "No such file").

- [ ] **Step 2: `/plugins`**

In a new Vibe session: `/plugins` lists `agent-kit` and `superpowers`, nothing under "Not loaded", no warnings (this also confirms the copied Claude `hooks/hooks.json` and `commands/` are ignored; answer 8).

- [ ] **Step 3: Session-start context**

In a new Vibe session inside a child repo, ask the agent to quote the `Kit map (agent-kit)` line, its `Plugin root:` line and the workspace-rules header line. Expected: the plugin root is the copy under `~/.vibe/plugins/agent-kit`.

- [ ] **Step 4: Skills and the Stop hook**

`/agent-kit:handoff` runs; `/superpowers:brainstorming` resolves; the turn ends with no hook warning (the `post_agent` Stop hook).

- [ ] **Step 5: Record**

Put the four results (with the quoted lines) under a "Live run" heading in the PR description. Any failure: stop and report it rather than changing the design.
