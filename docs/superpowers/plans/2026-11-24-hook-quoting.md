# Hook quoting and Vibe installer hardening Implementation Plan

- **Status:** approved
- **Date:** 2026-11-24
- **Frozen:** none (the spec has no Frozen bullet, spec D7; this plan only adds or changes cases in existing test files)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hook commands quote any python path that needs it (and refuse the four characters no quoting protects), and the Vibe installer ends every failure path with a clear message and the right exit code instead of a traceback, a false "nothing changed" or a lost backup.

**Architecture:** `plugin/install.py` and `plugin/vibe_plugin.py` each get the same small quoting helper and refusal helper (two copies, pinned identical by tests). `vibe_plugin` gains a `RestoreError(BuildError)` that keeps the staging folder, plus a `restore_backups` step that runs before a stale staging folder is removed. `install_vibe` catches post-build `OSError`s, link-removal errors and the new error class, and splits unreadable hook files out of the duplicate-skills warning. The publish guards in `tests/test_publish.py` also scan untracked, unignored files. Version 1.1.1.

**Tech Stack:** Python 3.11 (both plugin modules stay parseable by Python 3.8), pytest, ruff, Markdown.

**Spec:** `docs/superpowers/specs/2026-11-24-hook-quoting-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-24-hook-quoting-design.md`

## Context for the executor

This repo is the kit; the Claude Code plugin lives in `plugin/`. Work in the
worktree `<repo-root>/.worktrees/hook-quoting` on branch
`feat/hook-quoting`; never switch branches. Setup once:
`pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks: `pytest`
(plain; `pyproject.toml` already adds `-q`), `ruff check plugin tests`,
`ruff format --check plugin tests`.

Existing helpers you will use:

- `tests/helpers.py`: `PLUGIN` (the `plugin/` path), `REPO`,
  `load_module(path, name)` (imports a file and registers it in
  `sys.modules[name]`).
- `tests/test_install.py`: `run_install(tmp_path, python=..., extra=())`
  (Claude Code install with temp home), `run_agent(tmp_path, agent, *extra)`
  (runs `install.py --agent <agent> --home <tmp>/home --python sys.executable`
  plus `extra`; argparse keeps the last `--python`, so passing
  `"--python", value` in `extra` overrides it), `installer()` (imports
  install.py as `kit_install`), `skills(tmp_path)` (`<tmp>/home/.agents/skills`),
  `vibe(tmp_path)` (`<tmp>/home/.vibe`), `kit_link(tmp_path, name, target)`,
  `make_dir_link`, `is_link`, `snapshot(root)`, `out(result)`, `VENDOR`, and
  an autouse fixture that drops every link under `tmp_path` after each test.
- `tests/test_vibe_plugin.py`: `builder()` (imports vibe_plugin as
  `vibe_plugin`), `run_builder(out, *extra)` (runs `vibe_plugin.py --out <out>
  --python sys.executable` plus `extra`), `snapshot(root)`, `fake_kit(tmp_path)`
  (a copy of the kit you can break), `STAGING = ".agent-kit-staging"`,
  `NAMES`.

`install_vibe` does `import vibe_plugin`, so an in-process test that first
calls `load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")` and then
monkeypatches that module affects the installer's calls too.

Rules: never run `plugin/install.py` from a test without a temporary
`--home` (and `--skills-dir` for Claude Code). The repo is public: never write
a machine username or a private repo name into a tracked file. Test code must
fit ruff's 88-character lines; split long string literals by hand. Edit test
files with the Edit or Write tool, never through a bash heredoc (it mangles
`\n` escapes). Commit after each task with a message ending in
`Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Global Constraints

- Safe characters (written bare): any character where `str.isalnum()` is true, plus `_ . / : \ -`. Any other character makes the python path double-quoted.
- Refused characters: `"`, `$`, backtick, `%`. Checked before anything is written and, in `install.py`, before the existing python check.
- `python`, `C:/Python311/python.exe` and `C:/Users/José/python.exe` produce byte-identical hook commands to today's.
- The runner path stays double-quoted as today.
- `hook_command` (install.py) and `runner_command` (vibe_plugin.py) return identical strings for the same input.
- Only `--agent vibe|codex|cursor` installs and `vibe_plugin.py` refuse; `--agent claude` (the default) does not.
- Version becomes `1.1.1` in `plugin/.claude-plugin/plugin.json`; no new ADR.
- `plugin/install.py` and `plugin/vibe_plugin.py` stay parseable by Python 3.8 (`from __future__ import annotations`, no `match`, no `tomllib` import).
- Claude Code's `plugin/hooks/hooks.json` is not touched.

## Decisions answering the spec gate's plan questions

1. **Shared helper or two copies (Design 1):** two copies, `quote_python` and `unquotable`, one in each module, as `runner_command` already duplicates `hook_command` today. `vibe_plugin.py` must import on its own and `install.py` loads it only inside `install_vibe`. `test_vibe_runner_command_matches_hook_command` is extended to every criterion path, and a new test pins the refusal message as identical. (Task 1)
2. **Library refusal and wording (Design 2):** `vibe_plugin.build` itself refuses (raises `BuildError`) as its first step, so `vibe_plugin.main` needs no extra check and library callers are protected too. `install.py`'s `main` refuses separately for non-Claude agents, before `check_python`. The exact text, in both: `--python <path> contains <char>, which a hook command cannot quote safely`, printed as `ERROR: <text>; nothing changed.` (Task 1)
3. **Recognising the restore failure (Design 3):** a subclass `class RestoreError(BuildError)` with a `staging: Path` attribute. `build` sets a local `keep = True` in an `except RestoreError` clause, and its `finally` removes staging only when `keep` is false. `install_vibe` and `vibe_plugin.main` catch `RestoreError` before `BuildError` and print `ERROR: <message>` without the `; nothing changed.` suffix. (Task 2)
4. **Rerun restore (Design 3, D5):** a new `restore_backups(out, staging)` creates `<out>` (`mkdir(parents=True, exist_ok=True)`) when it has to move a `.old` copy back. A failed move raises `RestoreError` naming the `.old` path, the target and the staging folder, and staging is kept. `test_vibe_build_turns_stuck_staging_into_build_error` changes its stale entry from `agent-kit.old` to `agent-kit` (a stale staged copy, not a backup), so it still expects a `BuildError` and no `<out>`. (Task 2)
5. **A partial new copy next to a `.old` (Design 3):** during rollback, a swapped-in target that `shutil.rmtree` cannot fully remove is not renamed over. It counts as not restored, and the message says a partial new copy is left at `<out>/<name>` and must be deleted by hand before rerunning to get the previous copy back (a partial copy may have lost its marker, so a rerun can refuse it as not built by agent-kit). The rerun follows the spec rule exactly: it moves a `.old` back only when `<out>/<name>` is missing; otherwise the `.old` is removed with the stale staging folder and the rerun builds a fresh copy. (Task 2)
6. **Warning with only unreadable files (Design 4):** yes, the "Vibe lists the kit's skills twice" warning prints only when at least one readable hook file holds a kit command. With only unreadable files, only their "cannot be read" lines print. (Task 3)
7. **What still runs after an error (Design 5, 6):** after a `hooks.toml` error, the `AGENTS.md` write, the link handling and `NEXT_STEP["vibe"]` all still run; after an `AGENTS.md` error, the link handling and `NEXT_STEP` still run. The exit code is 1 when any of them failed. `remove_kit_links` returns `bool` (True when every kit link was removed). A `RestoreError` or `BuildError` still returns 1 before any of these steps, as today. (Task 3)
8. **Injecting `OSError`s (Design 5, 6):** in-process calls to `install_vibe` with `monkeypatch` for `hooks.toml` (patching `vibe_plugin.write_text` and `pathlib.Path.unlink` for that one path) and for `remove_link` (patching `kit_install.remove_link` for one link name). `AGENTS.md` uses a file-system setup that fails on both Windows and POSIX: a directory at `~/.vibe/AGENTS.md`, run through the real CLI so the test also sees that no traceback reaches stderr. (Task 3)
9. **Publish-guard test (Design 8):** a temporary git repo. `tracked(*paths, root=REPO)` gains a `root` parameter, and the hit collection of `test_claude_kit_only_in_allowed_places` moves into `claude_kit_hits(root)`, so the test runs a real guard against the temp repo without writing into the real one. (Task 4)

## Review Focus

- `--agent claude` (the default) with an unusual `--python` such as `C:/a%b/python.exe`: it writes no hook command, so the refusal must not fire; the existing python check reports it instead. Pinned by `test_claude_install_does_not_refuse_python_path` (Task 1).
- A backslash path `C:\Python311\python.exe` (out of scope, "stays bare, as today"): must stay byte-identical, not newly quoted. Pinned by `test_hook_command_keeps_backslash_path_bare` (Task 1).
- Codex rerun with a quoted python path: the kit's old entry must still be recognised and replaced, not duplicated. Pinned by `test_codex_hooks_rerun_with_quoted_python_is_stable` (Task 1).
- The installer is killed mid-swap after `<out>/<name>` was moved to staging and `<out>` itself is gone: the rerun must recreate `<out>` and move the copy back. Pinned by `test_restore_backups_creates_missing_out` (Task 2).
- A successful swap whose staging clean-up was blocked (Windows file lock) leaves a `.old` next to an existing `<out>/<name>`: the rerun must still succeed and remove staging, not refuse. Pinned by `test_stale_backup_next_to_existing_copy_is_dropped` (Task 2).

---

### Task 1: Quoting rule and refusal of unquotable paths

Spec Design 1, Design 2, D1, D2, D4.

**Files:**
- Modify: `plugin/install.py` (`hook_command` near line 322, new `quote_python` and `unquotable` beside it, `main` near line 620, module docstring)
- Modify: `plugin/vibe_plugin.py` (`runner_command` near line 62, new `quote_python` and `unquotable`, `build` near line 191)
- Test: `tests/test_install.py`, `tests/test_vibe_plugin.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing new.
- Produces, in both `plugin/install.py` and `plugin/vibe_plugin.py`:
  - `SAFE = "_./:\\-"` and `REFUSED = ('"', "$", "`", "%")` (module constants).
  - `quote_python(python: str) -> str`: `python` bare when every character is `isalnum()` or in `SAFE`, else `f'"{python}"'`.
  - `unquotable(python: str) -> str | None`: the first character of `python` that is in `REFUSED`, or `None`.
  - `refusal(python: str, char: str) -> str`: returns exactly `f"--python {python} contains {char}, which a hook command cannot quote safely"`.
  - `hook_command` and `runner_command` keep their signatures and use `quote_python`.

- [ ] **Step 1: Write the failing tests in `tests/test_install.py`**

Add `import shlex` to the imports. Add after `test_vibe_runner_command_matches_hook_command` (and replace that test's loop list):

```python
PATHS = [
    "python",
    "C:/Python311/python.exe",
    "C:/Program Files/python.exe",
    "C:/Users/O'Neil/python.exe",
    "C:/a&b/python.exe",
    "C:/py(3)/python.exe",
    "C:/Users/José/python.exe",
]
UNCHANGED = ["python", "C:/Python311/python.exe", "C:/Users/José/python.exe"]
BAD = [
    'C:/a"b/python.exe',
    "C:/a$b/python.exe",
    "C:/a`b/python.exe",
    "C:/a%b/python.exe",
]


def refusal_line(python):
    char = next(c for c in python if c in '"$`%')
    return (
        f"ERROR: --python {python} contains {char}, which a hook command "
        "cannot quote safely; nothing changed."
    )


@pytest.mark.parametrize("python", PATHS)
def test_hook_command_splits_back_to_python(tmp_path, python):
    runner = tmp_path / "run.py"
    command = installer().hook_command(python, "codex", "Stop", runner=runner)
    assert shlex.split(command)[:2] == [python, runner.as_posix()]


@pytest.mark.parametrize("python", UNCHANGED)
def test_hook_command_unchanged_for_plain_paths(tmp_path, python):
    runner = tmp_path / "run.py"
    command = installer().hook_command(python, "codex", "Stop", runner=runner)
    assert command == f'{python} "{runner.as_posix()}" --agent codex --event Stop'


def test_hook_command_keeps_backslash_path_bare(tmp_path):
    python = "C:\\Python311\\python.exe"
    runner = tmp_path / "run.py"
    command = installer().hook_command(python, "codex", "Stop", runner=runner)
    assert command.startswith(python + " ")


def test_codex_hooks_rerun_with_quoted_python_is_stable():
    mod = installer()
    python = "C:/Users/O'Neil/python.exe"
    once = mod.json_hooks("", "codex", python)
    assert mod.json_hooks(once, "codex", python) == once
    assert len(json.loads(once)["hooks"]["Stop"]) == 1


@pytest.mark.parametrize("agent", ["vibe", "codex"])
@pytest.mark.parametrize("python", BAD)
def test_unquotable_python_refused(tmp_path, agent, python):
    mod = installer()
    base = vibe(tmp_path)
    base.mkdir(parents=True)
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    (base / "hooks.toml").write_text(block, encoding="utf-8")
    before = snapshot(tmp_path)
    result = run_agent(tmp_path, agent, "--python", python)
    assert result.returncode == 1, out(result)
    assert refusal_line(python) in result.stdout
    assert "is not on PATH" not in result.stdout
    assert snapshot(tmp_path) == before


def test_claude_install_does_not_refuse_python_path(tmp_path):
    result = run_install(tmp_path, python="C:/a%b/python.exe")
    assert result.returncode == 1
    assert "cannot quote safely" not in result.stdout
    assert "is not on PATH" in result.stdout


def test_refusal_text_matches_builder():
    builder = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    for python in BAD:
        char = installer().unquotable(python)
        assert char == builder.unquotable(python)
        assert installer().refusal(python, char) == builder.refusal(python, char)
```

Change the loop in `test_vibe_runner_command_matches_hook_command` to
`for python in [*PATHS, "C:\\Python311\\python.exe"]:` (move `PATHS` above
that test if needed so it is defined first).

- [ ] **Step 2: Write the failing tests in `tests/test_vibe_plugin.py`**

Replace the body of `test_hooks_toml_survives_quote_in_python_path` (spec D2):

```python
def test_hooks_toml_survives_quote_in_python_path(tmp_path):
    python = "C:/Users/O'Neil/python.exe"
    runner = tmp_path / "run.py"
    hooks = tomllib.loads(builder().hooks_toml(python, runner))["hooks"]
    for hook in hooks:
        assert shlex.split(hook["command"])[:2] == [python, runner.as_posix()]
```

Add:

```python
PATHS = [
    "python",
    "C:/Python311/python.exe",
    "C:/Program Files/python.exe",
    "C:/Users/O'Neil/python.exe",
    "C:/a&b/python.exe",
    "C:/py(3)/python.exe",
    "C:/Users/José/python.exe",
]
BAD = [
    'C:/a"b/python.exe',
    "C:/a$b/python.exe",
    "C:/a`b/python.exe",
    "C:/a%b/python.exe",
]


@pytest.mark.parametrize("python", PATHS)
def test_runner_command_splits_back_to_python(tmp_path, python):
    runner = tmp_path / "run.py"
    command = builder().runner_command(python, runner, "Stop")
    assert shlex.split(command)[:2] == [python, runner.as_posix()]


@pytest.mark.parametrize("python", BAD)
def test_builder_refuses_unquotable_python(tmp_path, python):
    out = tmp_path / "plugins"
    char = next(c for c in python if c in '"$`%')
    result = run_builder(out, "--python", python)
    assert result.returncode == 1
    expected = (
        f"ERROR: --python {python} contains {char}, which a hook command "
        "cannot quote safely; nothing changed."
    )
    assert expected in result.stdout
    assert not out.exists() and not (tmp_path / STAGING).exists()
    mod = builder()
    with pytest.raises(mod.BuildError, match="cannot quote safely"):
        mod.build(out, python)
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `pytest tests/test_install.py tests/test_vibe_plugin.py -k "splits_back or unchanged_for_plain or backslash or rerun_with_quoted or unquotable or does_not_refuse or refusal_text or survives_quote or matches_hook_command"`
Expected: FAIL (the apostrophe, `&` and `(` cases split wrongly; `unquotable`, `refusal` do not exist; nothing is refused), except `test_vibe_runner_command_matches_hook_command`, `test_hook_command_unchanged_for_plain_paths` and `test_hook_command_keeps_backslash_path_bare`, which already pass (they pin today's behaviour).

- [ ] **Step 4: Implement the helpers in both modules**

In `plugin/vibe_plugin.py` and `plugin/install.py`, add `SAFE`, `REFUSED`, `quote_python`, `unquotable` and `refusal` as in Interfaces, and make `hook_command` / `runner_command` use `quote_python(python)` instead of the `" " in python` test. Keep both copies textually the same.

- [ ] **Step 5: Refuse in `vibe_plugin.build` and `install.py` `main`**

- `vibe_plugin.build`: first statement after resolving `out` and `kit`: when `unquotable(python)` returns a character, `raise BuildError(refusal(python, char))`. `main` already prints `ERROR: <exc>; nothing changed.`.
- `install.py` `main`: right after `print(f"Detected: ...")` and before `check_python`, when `args.agent != "claude"` and `unquotable(args.python)` returns a character, print `f"ERROR: {refusal(args.python, char)}; nothing changed."` and return 1.
- `install.py` module docstring: after the sentence on the python check, add one sentence: for Vibe, Codex and Cursor it first refuses a python path holding `"`, `$`, a backtick or `%`, which no hook shell quoting protects.

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pytest tests/test_install.py tests/test_vibe_plugin.py`
Expected: all pass, including `test_hooks_toml_quotes_spaces`, `test_agent_claude_matches_default`, `test_codex_hooks_json` and `test_cursor_hooks_json`.

- [ ] **Step 7: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` (expected: clean; run `ruff format plugin tests` first if needed).

```bash
git add plugin/install.py plugin/vibe_plugin.py tests/test_install.py tests/test_vibe_plugin.py
git commit -m "Quote hook python paths that need it, refuse unquotable ones"
```

---

### Task 2: A failed rollback keeps the backup

Spec Design 3, D5.

**Files:**
- Modify: `plugin/vibe_plugin.py` (new `RestoreError`, new `restore_backups`, `swap`, `build`, `main`)
- Modify: `plugin/install.py` (`install_vibe`'s `vibe_plugin.build` call, near line 556)
- Test: `tests/test_vibe_plugin.py`, `tests/test_install.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing new.
- Produces, in `plugin/vibe_plugin.py`:
  - `class RestoreError(BuildError)`: `__init__(self, message: str, staging: Path)`, stores `self.staging`.
  - `restore_backups(out: Path, staging: Path) -> None`: for each name in `NAMES`, when `<staging>/<name>.old` exists and `<out>/<name>` does not (`os.path.lexists`), creates `<out>` if missing and renames the `.old` to `<out>/<name>`. A failing rename raises `RestoreError(f"could not move {old} back to {target}: {exc}; the previous copy is kept in {staging}", staging)`.
  - `swap(out, staging)`: same signature; raises `RestoreError` (message below) instead of `BuildError` when any restore failed.
  - `build(...)`: same signature; calls `restore_backups(out, staging)` right before removing a stale staging folder; keeps staging when a `RestoreError` passes through.
  - `main`: prints `f"ERROR: {exc}"` for `RestoreError`, `f"ERROR: {exc}; nothing changed."` for other `BuildError`s.

- [ ] **Step 1: Write the failing tests in `tests/test_vibe_plugin.py`**

```python
def fail_restore(mod, monkeypatch, out):
    """Make the superpowers swap fail and the agent-kit restore fail too."""
    real = os.rename

    def flaky(src, dst):
        src, dst = Path(src), Path(dst)
        if src.name == "superpowers" and src.parent.name == STAGING:
            raise OSError("locked")
        if src.name == "agent-kit.old" and dst.parent == out.resolve():
            raise OSError("restore blocked")
        return real(src, dst)

    monkeypatch.setattr(mod.os, "rename", flaky)


def test_failed_restore_keeps_staging_with_backup(tmp_path, monkeypatch):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    fail_restore(mod, monkeypatch, out)
    with pytest.raises(mod.RestoreError) as info:
        mod.build(out, sys.executable)
    staging = (tmp_path / STAGING).resolve()
    assert info.value.staging == staging
    assert str(staging) in str(info.value) and "agent-kit" in str(info.value)
    assert "nothing changed" not in str(info.value)
    assert (staging / "agent-kit.old" / ".agent-kit-build").is_file()
    assert not (out / "agent-kit").exists()


def test_builder_cli_restore_error_drops_nothing_changed(
    tmp_path, monkeypatch, capsys
):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    fail_restore(mod, monkeypatch, out)
    code = mod.main(["--out", str(out), "--python", sys.executable])
    printed = capsys.readouterr().out
    assert code == 1
    assert str((tmp_path / STAGING).resolve()) in printed
    assert "nothing changed" not in printed


def test_rerun_moves_backup_back_before_removing_staging(tmp_path):
    out = tmp_path / "plugins"
    mod = builder()
    mod.build(out, sys.executable)
    before = snapshot(out / "agent-kit")
    staging = tmp_path / STAGING
    staging.mkdir()
    os.rename(out / "agent-kit", staging / "agent-kit.old")
    kit = fake_kit(tmp_path)
    version_file = kit / "vendor" / "superpowers" / "VERSION"
    version_file.write_text("version: 1.0.0\n", encoding="utf-8")
    with pytest.raises(mod.BuildError, match="source"):
        mod.build(out, sys.executable, kit=kit)
    assert snapshot(out / "agent-kit") == before
    assert not staging.exists()


def test_restore_backups_creates_missing_out(tmp_path):
    staging = tmp_path / STAGING
    (staging / "agent-kit.old").mkdir(parents=True)
    (staging / "agent-kit.old" / ".agent-kit-build").write_text("1\n")
    out = tmp_path / "plugins"
    builder().restore_backups(out, staging)
    assert (out / "agent-kit" / ".agent-kit-build").is_file()
    assert not (staging / "agent-kit.old").exists()


def test_failed_rerun_restore_keeps_staging(tmp_path, monkeypatch):
    staging = tmp_path / STAGING
    (staging / "agent-kit.old").mkdir(parents=True)
    mod = builder()

    def blocked(src, dst):
        raise OSError("blocked")

    monkeypatch.setattr(mod.os, "rename", blocked)
    with pytest.raises(mod.RestoreError, match="blocked"):
        mod.build(tmp_path / "plugins", sys.executable)
    assert (staging / "agent-kit.old").is_dir()


def test_stale_backup_next_to_existing_copy_is_dropped(tmp_path):
    out = tmp_path / "plugins"
    assert run_builder(out).returncode == 0
    junk = tmp_path / STAGING / "agent-kit.old"
    junk.mkdir(parents=True)
    (junk / "junk.txt").write_text("x", encoding="utf-8")
    assert run_builder(out).returncode == 0
    assert not (tmp_path / STAGING).exists()
    assert not (out / "agent-kit" / "junk.txt").exists()
```

The existing `test_failed_swap_restores_both_copies` stays as is: when every
restore succeeds, a plain `BuildError` is raised and staging is removed.

- [ ] **Step 2: Update `test_vibe_build_turns_stuck_staging_into_build_error` in `tests/test_install.py`**

Change its stale entry from `".agent-kit-staging" / "agent-kit.old"` to
`".agent-kit-staging" / "agent-kit"` (a stale staged copy, not a backup, so
`restore_backups` leaves it and `assert not out.exists()` still holds).
Add the installer-side test:

```python
def test_vibe_restore_error_keeps_staging_message(tmp_path, monkeypatch, capsys):
    vp = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    home = tmp_path / "home"
    plugins = (home / ".vibe" / "plugins").resolve()
    vp.build(plugins, sys.executable)
    real = os.rename

    def flaky(src, dst):
        src, dst = Path(src), Path(dst)
        if src.name == "superpowers" and src.parent.name == ".agent-kit-staging":
            raise OSError("locked")
        if src.name == "agent-kit.old" and dst.parent == plugins:
            raise OSError("restore blocked")
        return real(src, dst)

    monkeypatch.setattr(vp.os, "rename", flaky)
    code = installer().install_vibe(home, skills(tmp_path), sys.executable)
    printed = capsys.readouterr().out
    assert code == 1
    assert str(plugins.parent / ".agent-kit-staging") in printed
    assert "nothing changed" not in printed
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run: `pytest tests/test_vibe_plugin.py tests/test_install.py -k "restore or rerun_moves or stale_backup or stuck_staging"`
Expected: FAIL (`RestoreError` and `restore_backups` do not exist; the backup is deleted).

- [ ] **Step 4: Implement `RestoreError` and `restore_backups` in `plugin/vibe_plugin.py`**

As in Interfaces.

- [ ] **Step 5: Change `swap`'s rollback**

Collect the names that could not be restored in a list `lost` instead of
swallowing the errors:

- the current plugin: its `moved` rename back fails, so add `name`;
- an earlier plugin: after `shutil.rmtree(prev_target, ignore_errors=True)`, when `os.path.lexists(prev_target)` is still true and `prev_old` is not `None`, add `f"{name} (a partial new copy is left at {prev_target}; delete it by hand before rerunning to get the previous copy back from {prev_old})"` and do not try the rename; otherwise, when the rename of `prev_old` fails, add the name.

Keep the names of earlier plugins next to `done` (store `(name, target, old)`).
When `lost` is empty, raise `BuildError(f"could not swap in the new copy: {exc}")`
as today. Otherwise raise
`RestoreError(f"could not swap in the new copy: {exc}; could not restore the previous copy of {', '.join(lost)}; the staging folder {staging} keeps it as {', '.join(olds)}, and the next build moves a copy back when its plugin folder is missing", staging)`,
where `olds` lists the actual `<name>.old` file names of the `lost` entries
(for example `agent-kit.old`).

- [ ] **Step 6: Change `build` and `main`**

`build`: before `shutil.rmtree(staging)` of a stale folder, call
`restore_backups(out, staging)`. Add a local `keep = False`; add
`except RestoreError: keep = True; raise` before `except BuildError: raise`;
in `finally`, remove staging only when not `keep`.
`main`: `except RestoreError as exc: print(f"ERROR: {exc}"); return 1` before
the existing `except BuildError` clause.

- [ ] **Step 7: Change `install_vibe` in `plugin/install.py`**

Around `vibe_plugin.build(plugins, python)`: add
`except vibe_plugin.RestoreError as exc: print(f"ERROR: {exc}"); return 1`
before the existing `except vibe_plugin.BuildError` clause.

- [ ] **Step 8: Run the tests to verify they pass**

Run: `pytest tests/test_vibe_plugin.py tests/test_install.py`
Expected: all pass, including `test_failed_swap_restores_both_copies`, `test_stale_staging_removed` and `test_failed_build_keeps_previous_copy`.

- [ ] **Step 9: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` (expected: clean).

```bash
git add plugin/vibe_plugin.py plugin/install.py tests/test_vibe_plugin.py tests/test_install.py
git commit -m "Keep the Vibe plugin backup when a rollback fails"
```

---

### Task 3: Installer warnings and errors after the build

Spec Design 4, Design 5, Design 6, D6.

**Files:**
- Modify: `plugin/install.py` (`kit_hooks_in_use` near line 491, `remove_kit_links` near line 511, new `kit_links`, `install_vibe` after the build near line 561)
- Test: `tests/test_install.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing new.
- Produces, in `plugin/install.py`:
  - `kit_links(skills_dir: Path) -> list[Path]`: the sorted entries of `skills_dir` whose `link_target` is under this checkout's skill roots (`under_kit_roots`), dangling ones included; `[]` when `skills_dir` is not a directory. These are exactly the links `remove_kit_links` removes.
  - `remove_kit_links(skills_dir: Path) -> bool`: removes each link in `kit_links(skills_dir)`; on `OSError` from `remove_link` prints `f"Could not remove {entry.name}: {exc}"` and continues. Still prints the `Kept <name>: ...` lines for same-named links outside the checkout. Returns `True` when every kit link was removed (also when there were none).
  - `kit_hooks_in_use(home: Path) -> tuple[list[Path], list[Path]]`: `(files holding a kit hook command, files that cannot be read or parsed)`, over `~/.codex/hooks.json` and `~/.cursor/hooks.json`; a missing file is in neither list.

- [ ] **Step 1: Write the failing tests**

Update the existing tests:

- `test_vibe_keeps_links_while_other_agent_uses_them`: also `assert str(path) in result.stdout`.
- `test_vibe_unreadable_other_hook_file_counts_as_in_use`: replace the last line with:

```python
    line = (
        f"Kept the kit's skill links: {path} cannot be read, "
        "so it may still use them."
    )
    assert line in result.stdout
    assert "twice" not in result.stdout
```

Add:

```python
def test_vibe_warning_names_only_readable_kit_hook_file(tmp_path):
    codex = tmp_path / "home" / ".codex" / "hooks.json"
    cursor = tmp_path / "home" / ".cursor" / "hooks.json"
    for path in (codex, cursor):
        path.parent.mkdir(parents=True)
    codex.write_text(installer().json_hooks("", "codex", sys.executable))
    cursor.write_text("{oops", encoding="utf-8")
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    warning = next(x for x in result.stdout.splitlines() if "twice" in x)
    assert str(codex) in warning and str(cursor) not in warning
    assert f"Kept the kit's skill links: {cursor} cannot be read" in result.stdout


def test_vibe_no_kit_links_prints_no_kept_lines(tmp_path):
    codex = tmp_path / "home" / ".codex" / "hooks.json"
    cursor = tmp_path / "home" / ".cursor" / "hooks.json"
    for path in (codex, cursor):
        path.parent.mkdir(parents=True)
    codex.write_text(installer().json_hooks("", "codex", sys.executable))
    cursor.write_text("{oops", encoding="utf-8")
    elsewhere = tmp_path / "old-checkout" / "spec-gate"
    elsewhere.mkdir(parents=True)
    kit_link(tmp_path, "spec-gate", elsewhere)
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert "twice" not in result.stdout
    assert "cannot be read" not in result.stdout


@pytest.mark.parametrize("user_text", [False, True])
def test_vibe_hooks_toml_write_error_exits_1(
    tmp_path, monkeypatch, capsys, user_text
):
    mod = installer()
    vp = load_module(PLUGIN / "vibe_plugin.py", "vibe_plugin")
    home = tmp_path / "home"
    hooks = home / ".vibe" / "hooks.toml"
    hooks.parent.mkdir(parents=True)
    mine = "mine = 1\n\n" if user_text else ""
    block = f"{mod.TOML_BEGIN}\nold = 1\n{mod.TOML_END}\n"
    hooks.write_text(mine + block, encoding="utf-8")
    real_write, real_unlink = vp.write_text, Path.unlink

    def write(path, text):
        if Path(path) == hooks:
            raise OSError("read-only")
        return real_write(path, text)

    def unlink(self, *args, **kwargs):
        if self == hooks:
            raise OSError("read-only")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(vp, "write_text", write)
    monkeypatch.setattr(Path, "unlink", unlink)
    code = mod.install_vibe(home, skills(tmp_path), sys.executable)
    printed = capsys.readouterr().out
    assert code == 1
    assert "Installed the agent-kit and superpowers plugins" in printed
    assert f"remove the kit block from {hooks} by hand or rerun" in printed
    assert (home / ".vibe" / "AGENTS.md").is_file()
    assert "Next: start a new Vibe session" in printed


def test_vibe_agents_md_write_error_exits_1(tmp_path):
    (vibe(tmp_path) / "AGENTS.md").mkdir(parents=True)
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 1
    assert "Traceback" not in out(result)
    assert "Installed the agent-kit and superpowers plugins" in result.stdout
    rules = vibe(tmp_path) / "AGENTS.md"
    assert f"update the kit block in {rules} by hand or rerun" in result.stdout
    assert "Next: start a new Vibe session" in result.stdout


def test_vibe_link_removal_error_continues_and_exits_1(
    tmp_path, monkeypatch, capsys
):
    mod = installer()
    kit_link(tmp_path, "spec-gate", PLUGIN / "skills" / "spec-gate")
    kit_link(tmp_path, "ship", PLUGIN / "agent-skills" / "ship")
    real = mod.remove_link

    def flaky(link):
        if Path(link).name == "spec-gate":
            raise OSError("in use")
        return real(link)

    monkeypatch.setattr(mod, "remove_link", flaky)
    code = mod.install_vibe(tmp_path / "home", skills(tmp_path), sys.executable)
    printed = capsys.readouterr().out
    assert code == 1
    assert "Could not remove spec-gate: in use" in printed
    assert not os.path.lexists(skills(tmp_path) / "ship")
    assert is_link(skills(tmp_path) / "spec-gate")
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run: `pytest tests/test_install.py -k "vibe_keeps_links or unreadable_other or names_only_readable or no_kit_links or write_error or link_removal_error"`
Expected: FAIL (no "cannot be read" line, tracebacks on write errors, the removal error propagates).

- [ ] **Step 3: Implement `kit_links`, `remove_kit_links` and `kit_hooks_in_use` as in Interfaces**

- [ ] **Step 4: Change `install_vibe` after the "Installed the agent-kit and superpowers plugins" line**

Track `ok = True`.

- Wrap the `hooks.toml` delete/write in `try`/`except OSError as exc`: print `f"ERROR: could not update {hooks} ({exc}); the plugins are installed, but remove the kit block from {hooks} by hand or rerun."` and set `ok = False`. The "Removed"/"Wrote" lines print only on success.
- Wrap the `AGENTS.md` write the same way: `f"ERROR: could not write {rules} ({exc}); the plugins are installed, but update the kit block in {rules} by hand or rerun."`, `ok = False`.
- Then `in_use, unreadable = kit_hooks_in_use(home)`. When both lists are empty: `ok = remove_kit_links(skills_dir) and ok`. Otherwise, only when `kit_links(skills_dir)` is not empty: print `f"Kept the kit's skill links: {path} cannot be read, so it may still use them."` for each path in `unreadable`, then, only when `in_use` is not empty, the existing "WARNING: kept the kit's skill links in ..." warning naming the `in_use` paths only.
- Print `NEXT_STEP["vibe"]` as today and return `0 if ok else 1`.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_install.py`
Expected: all pass, including `test_vibe_removes_old_kit_links_keeps_foreign` and `test_vibe_removes_dangling_kit_link`.

- [ ] **Step 6: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` (expected: clean).

```bash
git add plugin/install.py tests/test_install.py
git commit -m "Vibe installer: clear warnings and exit 1 on post-build errors"
```

---

### Task 4: Publish guards check untracked files

Spec Design 8.

**Files:**
- Modify: `tests/test_publish.py` (`tracked` near line 48, `test_claude_kit_only_in_allowed_places` near line 168)

**Depends on:** none

**Interfaces:**
- Consumes: nothing new.
- Produces, in `tests/test_publish.py`:
  - `tracked(*paths: str, root: Path = REPO) -> list[str]`: the output lines of `git ls-files <paths>` followed by those of `git ls-files --others --exclude-standard <paths>`, both run with `cwd=root`.
  - `claude_kit_hits(root: Path) -> list[str]`: the `rel:line` hits that `test_claude_kit_only_in_allowed_places` collects today, over `tracked(root=root)`, reading files under `root`.

- [ ] **Step 1: Write the failing test**

Add `from pathlib import Path` to the imports. Add:

```python
def test_guards_check_untracked_unignored_files(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("ignored.md\n", encoding="utf-8")
    (tmp_path / "new.md").write_text("see claude-kit\n", encoding="utf-8")
    (tmp_path / "ignored.md").write_text("claude-kit\n", encoding="utf-8")
    files = tracked(root=tmp_path)
    assert "new.md" in files and "ignored.md" not in files
    assert claude_kit_hits(tmp_path) == ["new.md:1"]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_publish.py::test_guards_check_untracked_unignored_files`
Expected: FAIL (`tracked` has no `root` parameter; `claude_kit_hits` is not defined).

- [ ] **Step 3: Implement `tracked` and `claude_kit_hits` as in Interfaces**

`test_claude_kit_only_in_allowed_places` becomes
`hits = claude_kit_hits(REPO); assert not hits, "\n".join(hits)`. The other
guards keep calling `tracked(...)` unchanged.

- [ ] **Step 4: Run the file to verify it passes**

Run: `pytest tests/test_publish.py`
Expected: all pass (if a guard now flags an untracked file in the worktree, that file is a real finding: fix or ignore it, do not weaken the guard).

- [ ] **Step 5: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` (expected: clean).

```bash
git add tests/test_publish.py
git commit -m "Publish guards also check untracked, unignored files"
```

---

### Task 5: Docs and version 1.1.1

Spec Design 7, Design 9, D3.

**Files:**
- Modify: `docs/setup.md` (the sentence near line 154)
- Modify: `plugin/.claude-plugin/plugin.json` (`"version"`)
- Modify: `tests/test_plugin_manifest.py` (`test_version_is_1_1_0` near line 212)

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing test**

In `tests/test_plugin_manifest.py`, rename `test_version_is_1_1_0` to
`test_version_is_1_1_1` and make it assert `data["version"] == "1.1.1"`.

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_plugin_manifest.py::test_version_is_1_1_1`
Expected: FAIL (`'1.1.0' == '1.1.1'`).

- [ ] **Step 3: Bump the version and fix the docs sentence**

- `plugin/.claude-plugin/plugin.json`: `"version": "1.1.1"`.
- `docs/setup.md`: replace "Links into a kit checkout you have since deleted are reported as `Skipped`; remove them by hand and rerun." with "For Codex and Cursor, links into a kit checkout you have since deleted are reported as `Skipped`; remove them by hand and rerun. For Vibe, a same-named link into another checkout is reported as `Kept <name>` and left in place." (keep the paragraph wrapped near 78 columns).

- [ ] **Step 4: Run the full suite and lint**

Run: `pytest`, then `ruff check plugin tests; ruff format --check plugin tests`
Expected: all tests pass (including `test_agent_kit_manifest_follows_claude_manifest`, `test_vibe_runner_command_matches_hook_command`, `test_agent_claude_matches_default`), ruff clean.

- [ ] **Step 5: Check the diff for private names, then commit**

Run: `git diff main --stat` and grep the diff for the machine's username and any private repo name (expected: no hits).

```bash
git add docs/setup.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "Version 1.1.1; setup guide notes Kept links for Vibe"
```

---

## Verification (spec success criteria)

1. **Tests:** every case in criterion 1 maps to a test above: quoting (Task 1: `test_hook_command_splits_back_to_python`, `test_hook_command_unchanged_for_plain_paths`, `test_runner_command_splits_back_to_python`, `test_hooks_toml_survives_quote_in_python_path`); refusal (Task 1: `test_unquotable_python_refused`, `test_builder_refuses_unquotable_python`); rollback (Task 2); warning, write and link errors (Task 3); guards (Task 4); version (Task 5).
2. **Unchanged elsewhere:** `pytest` passes in full and `ruff check plugin tests` and `ruff format --check plugin tests` are clean (Task 5, Step 4).
3. **Live check (after merging, not part of the tasks):** from the main checkout run `python plugin/install.py --agent vibe`; expect exit 0. Then in a child repo run a headless `vibe -p` asking it to quote the `Kit map (agent-kit)` line; expect the plugin root to be `~/.vibe/plugins/agent-kit`. Where the executor cannot run Vibe, ask the user to run it and paste the result.
