# User-config audit (`audit --user`) Implementation Plan

- **Status:** approved
- **Date:** 2026-11-16
- **Frozen:** none (spec D5: nothing is frozen)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--user` mode to `claude-kit:audit` that audits the user-scope Claude Code setup outside any repo, backed by a new standard-library inventory script, `plugin/scripts/user-config-inventory.py`.

**Architecture:** The script walks a home directory and prints one JSON object (settings, MCP servers, installed plugins, skills, scheduled tasks, instructions) where every item carries a `file` and a 1-based `line`, and env/header values never appear. A new procedure file, `plugin/skills/audit/user-mode.md`, tells the session to run the script, read only cited lines of the settings files and `.claude.json`, apply `rules.md` section 4 plus user-scope checks, and write `~/.claude/claude-kit/audit/user-config.md`. `audit/SKILL.md` branches to it on `--user`. An ADR, a README sentence and a minor version bump finish the change.

**Tech Stack:** Python 3.11 standard library (`argparse`, `json`, `os`, `pathlib`), pytest, ruff, Markdown.

**Spec:** `docs/superpowers/specs/2026-11-15-user-config-audit-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-15-user-config-audit-design.md`

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/`. `tests/helpers.py`
exports `PLUGIN`, `REPO`, `load_module(path, name)` (imports a hyphenated script)
and `run_script(script, *args, stdin="", cwd=None, env=None)` (runs
`sys.executable script args`, returns a `CompletedProcess` with UTF-8 text
`stdout`/`stderr`). Scripts follow `plugin/scripts/docker-disk.py` and
`plugin/scripts/function-catalog.py`: `#!/usr/bin/env python3`, a module
docstring with usage, `from __future__ import annotations`, `argparse`,
`main(argv: list[str] | None = None) -> int`, `if __name__ == "__main__":
sys.exit(main())`, and `sys.stdout.reconfigure(encoding="utf-8")` guarded by
`hasattr`.

`plugin/scripts/check-findings.py ROOT REPORT` accepts an absolute path in a
finding's **Where** (it uses it as is; a relative one is joined to ROOT), so
findings on files outside the home directory still check.

Gotchas (`knowledge/kit-dev-gotchas.md`): test code must fit ruff's 88-character
lines; edit test files with the Edit/Write tools, not bash heredocs; run plain
`pytest` (not `-q`) to see the pass count. The installed kit is loaded through a
junction to the main checkout, not this worktree, so the manual run in Task 5
follows the worktree's files directly, not the installed skill.

Setup: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks:
`pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.

## Global Constraints

- Script: standard library only, Python 3.11; `sys.stdout.reconfigure(encoding="utf-8")`; CLI `user-config-inventory.py [--home DIR]`, `--home` defaulting to `Path.home()`.
- Every `file` is a posix path relative to the home directory (or absolute posix when outside it, see Plan questions); `line` is 1-based or `null`.
- Env and header values never appear in the inventory output; only key names (D4).
- A missing file or key yields an empty list (or `null` for a single-valued field), never an error. Malformed JSON yields an `errors` entry `{file, error}` and the rest still prints. Exit 0, or 2 when `--home` is not a directory.
- The audit stays read-only; it writes only `~/.claude/claude-kit/audit/` (the report) and the `audit-scratch` temp folder of `rules.md` section 1. `rules.md` and `check-findings.py` are not changed. `audit-deep` is not changed (D2).
- Report path, verbatim: `~/.claude/claude-kit/audit/user-config.md`; never inside a repo.
- ADR number: one above the highest in `knowledge/decisions/` on `origin/main` at implementation time (today `0047`). Version: one minor above `origin/main`'s `plugin.json` version at implementation time (today `0.31.1` → `0.32.0`).
- Public repo: no machine username or private repo names in tracked files; fixtures use generic names.

## Plan-level answers to the spec gate's plan questions

- **Install entries and "enabled":** one `plugins` item per entry in each `installed_plugins.json` `plugins.<name>` list (a dict value, the older format, counts as one entry), carrying `scope` and `project_path` (`projectPath`, or `null`). `enabled` is the plugin's value in the user-level `enabledPlugins`, with `.claude/settings.local.json` overriding `.claude/settings.json`; `null` when neither lists it. Project-scope installs are enabled by that project's own settings, which are outside this audit; user-mode.md tells the report to say so for each project-scope item rather than guess. (Task 2, Task 3)
- **Finding `line` in JSON:** `value_lines(text)`, a small position-tracking JSON scanner run only on text that `json.loads` accepted, maps each value's path (a tuple of object keys and list indices) to the 1-based line where it starts; for an object member that is the line of its key. Paths are unique by construction, so identical rules in one list get distinct lines; for a duplicate key in one object the last one wins, as in `json.loads`. A path the map lacks gives `line: null`. (Task 1)
- **Files outside the home directory:** a path under the home directory is written relative to it in posix form; any other path (an `installPath` or link target elsewhere) is written as an absolute posix path, which `check-findings.py <home>` accepts. Files inside a linked skills entry are cited through the entry path (`.claude/skills/<name>/hooks/hooks.json`), not the resolved target, so they stay home-relative; the target is reported separately in `target`. (Task 1, Task 2, Task 3)
- **`hooks` in a plugin's `plugin.json`:** the inventory does not parse it; it sets `manifest_hooks: true` on that plugin or skills entry. user-mode.md tells the session to read that `plugin.json` in full and every hooks file it names, and to treat those hooks like listed ones. (Task 2, Task 3)
- **Resolving hook commands:** the model, from the raw `command` the inventory prints. Plugin and skills-dir hooks carry the plugin's `root` (home-relative or absolute posix) so `${CLAUDE_PLUGIN_ROOT}` can be substituted. user-mode.md gives the rule: substitute `${CLAUDE_PLUGIN_ROOT}` with `root` and `~`, `$HOME`, `%USERPROFILE%` with the home directory; skip the interpreter (`python`, `python3`, `py`, `node`, `bash`, `sh`, `pwsh`, `powershell -File`, `uv run`); the first remaining path argument is the target, relative to `root` for plugin hooks and to the home directory otherwise; a command with no resolvable script (inline shell, a program on PATH) is judged on its text and listed under what was not read. (Task 3)
- **Setup steps and production bar:** the `--user` branch replaces everything in SKILL.md after the branch (Setup steps 1-5, Passes 1-4 and Output); user-mode.md carries its own setup. Production bar: the user's if given, else "one person's workstation: agents with tool access to their private repos, accounts and credentials", stated in the report header marked default. (Task 3)
- **Criterion 2's secret search:** a throwaway Python snippet in the `audit-scratch` temp folder loads the env values of both user settings files and every `env`/`headers` value in `.claude.json`, searches the report for each, and prints only `checked <n> values, found <m>` plus the key names (never values) of any hit. The model never reads the values. (Task 5)

## Review Focus

- A settings file where a field has the wrong type (`permissions.allow` a string, `hooks` a list, `mcpServers` a list): skipped as empty, the run still exits 0 with the other items (test in Task 2).
- Two identical permission rules in one list: each gets its own line, not both the first one's (test in Task 1, `value_lines` unit test).
- An installed plugin whose `installPath` is outside the home directory: `install_path`, `root` and its hooks' `file` are absolute posix paths that exist, not `..`-relative ones (test in Task 2).
- A skills entry that is a junction or symlink to a plugin checkout (the kit's own install): reported with `link` and `target`, marked `plugin: true`, and its hooks cited through the entry path (test in Task 2).
- An empty home directory (no `.claude/`, no `.claude.json`): every list empty, `errors` empty, exit 0 (test in Task 1).

---

### Task 1: Inventory skeleton, `value_lines` and the settings section

**Files:**
- Create: `plugin/scripts/user-config-inventory.py`
- Create: `tests/test_user_config_inventory.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces (Python API, imported in tests with `load_module(PLUGIN / "scripts" / "user-config-inventory.py", "user_config_inventory")`):
  - `value_lines(text: str) -> dict[tuple[str | int, ...], int]`: path → 1-based start line, as in the plan-level answer.
  - `rel(path: Path, home: Path) -> str`: home-relative posix path when `path` is under `home` (compared on `os.path.abspath`, without resolving links), else the absolute posix path.
  - `load_json(path: Path, home: Path, errors: list[dict]) -> tuple[object, dict] | None`: `None` when the file is missing; on a parse or decode error appends `{"file": rel(...), "error": str(exc)}` to `errors` and returns `None`; else `(data, value_lines(text))`. Reads UTF-8 (`utf-8-sig`, so a BOM is accepted).
  - `hooks_from(data: object, lines: dict, file: str, prefix: tuple = ("hooks",)) -> list[dict]`: from a `{"hooks": {event: [{"matcher": str, "hooks": [{"command": str}]}]}}` shape (as in settings files and `hooks/hooks.json`), one `{"event", "matcher", "command", "file", "line"}` per hook command; `matcher` is `null` when absent; `line` is that of `(*prefix, event, gi, "hooks", hi, "command")`. Wrong types yield `[]`.
  - `inventory(home: Path) -> dict`: the full object with keys `settings`, `mcp_servers`, `plugins`, `skills`, `scheduled_tasks`, `instructions`, `errors` (Task 2 fills the middle four; in this task they are `[]`).
  - `main(argv: list[str] | None = None) -> int`: prints `json.dumps(inventory(home), indent=2, ensure_ascii=False)`; prints `not a directory: <path>` to stderr and returns 2 when `--home` is not a directory.
  - `settings` item, one per present file (`.claude/settings.json`, then `.claude/settings.local.json`):
    `{"file", "permissions": [{"kind": "allow"|"ask"|"deny", "rule", "file", "line"}], "defaultMode": {"value", "file", "line"} | null, "hooks": [hook items], "env": [{"key", "file", "line"}], "enabledPlugins": [{"name", "enabled", "file", "line"}], "statusLine": {"command", "file", "line"} | null, "autoMode": {"keys": [str], "file", "line"} | null}`.
    Paths for lines: `("permissions", kind, i)`, `("permissions", "defaultMode")`, `("env", key)`, `("enabledPlugins", name)`, `("statusLine", "command")`, `("autoMode",)`.

- [ ] **Step 1: Write the failing tests**

In `tests/test_user_config_inventory.py`: a helper `write_json(path: Path, data) -> None` (creates parents, `json.dumps(data, indent=2)`), a helper `line_of(path: Path, needle: str) -> int` (1-based index of the first line containing `needle`), a helper `run(home: Path) -> dict` (`run_script(SCRIPT, "--home", str(home))`, asserts `returncode == 0`, returns `json.loads(stdout)`), and a fixture `home(tmp_path)` that creates and returns `tmp_path / "home"`, the full fake home used by every test in this file (Task 2 extends it). In this task it writes `.claude/settings.json` with:

```python
{
    "env": {"API_TOKEN": "SECRET-ENV-VALUE-1"},
    "permissions": {
        "allow": ["Bash(git log:*)", "Read(./**)", "Read(./**)"],
        "ask": ["Bash(git push:*)"],
        "deny": ["Read(./.env)"],
        "defaultMode": "acceptEdits",
    },
    "hooks": {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python ~/hooks/guard.py"}]}
        ]
    },
    "enabledPlugins": {"demo@market": True, "off@market": False},
    "statusLine": {"type": "command", "command": "python ~/.claude/statusline.py"},
    "autoMode": {"environment": ["a"], "rules": ["b"]},
}
```

and `.claude/settings.local.json` with `{"env": {"LOCAL_KEY": "SECRET-LOCAL-ENV-4"}, "enabledPlugins": {"off@market": True}}`.

Tests and their assertions:
- `test_value_lines_nested_and_duplicates`: on the text `'{\n "a": {\n  "b": [\n   "x",\n   "x"\n  ]\n },\n "a2": 1\n}'`, `value_lines` gives `("a",) → 2`, `("a", "b") → 3`, `("a", "b", 0) → 4`, `("a", "b", 1) → 5`, `("a2",) → 8`; on `'{"k": 1,\n "k": 2}'`, `("k",) → 2`.
- `test_permissions_listed_with_file_and_line`: the `.claude/settings.json` item has five permissions; each has `file == ".claude/settings.json"`; `Bash(git log:*)` has kind `allow` and `line == line_of(settings, '"Bash(git log:*)"')`; the two `Read(./**)` rules have different lines; `defaultMode == {"value": "acceptEdits", "file": ".claude/settings.json", "line": line_of(settings, '"defaultMode"')}`.
- `test_settings_hooks_status_line_and_auto_mode`: one hook `{"event": "PreToolUse", "matcher": "Bash", "command": "python ~/hooks/guard.py", "file": ".claude/settings.json", "line": line_of(settings, "guard.py")}`; `statusLine["command"] == "python ~/.claude/statusline.py"` with the line of `statusline.py`; `autoMode["keys"] == ["environment", "rules"]` with the line of `"autoMode"`.
- `test_env_keys_and_enabled_plugins`: settings env is `[{"key": "API_TOKEN", "file": ".claude/settings.json", "line": line_of(settings, '"API_TOKEN"')}]`; local env key is `LOCAL_KEY` with file `.claude/settings.local.json`; `enabledPlugins` of settings.json lists `demo@market` `True` and `off@market` `False`.
- `test_secret_values_absent_from_output`: no string starting `SECRET-` appears anywhere in the raw stdout (Task 2 adds more sentinels to the fixture; this test then covers them too).
- `test_malformed_settings_reports_error_and_continues`: overwrite `.claude/settings.json` with `{"permissions": ` (truncated); output `errors` has one entry with `file == ".claude/settings.json"` and a non-empty `error`; the `.claude/settings.local.json` item is still present; exit 0.
- `test_missing_home_exits_2`: `run_script(SCRIPT, "--home", str(tmp_path / "nope"))` returns 2 and stderr contains `not a directory`.
- `test_empty_home_yields_empty_lists`: on an empty `tmp_path / "empty"` directory, every top-level key `settings`, `mcp_servers`, `plugins`, `skills`, `scheduled_tasks`, `instructions`, `errors` is `[]`.
- `test_rel_inside_and_outside_home`: `rel(home / ".claude" / "x.json", home) == ".claude/x.json"`; `rel(tmp_path / "elsewhere" / "y.py", home) == (tmp_path / "elsewhere" / "y.py").as_posix()` (with `home = tmp_path / "home"`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_user_config_inventory.py -v`
Expected: FAIL (the script does not exist; collection or `load_module` errors).

- [ ] **Step 3: Implement the script up to the settings section**

Write `plugin/scripts/user-config-inventory.py` with the Interfaces above. The module docstring states the CLI, the output keys and the env/header rule. `value_lines` is a recursive-descent walk over the already-validated text: skip whitespace counting `\n`; at `{` read each key with `json.decoder.scanstring(text, i + 1)`, record `path + (key,)` at the key's line, then parse its value under that path; at `[` record each element's path `path + (index,)` at the line of its first character; strings via `scanstring`; numbers, `true`, `false`, `null` skipped with a regex. Every accessor checks types with `isinstance` and treats a wrong type as absent.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_user_config_inventory.py -v`
Expected: all 9 tests PASS.

- [ ] **Step 5: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests`
Expected: `All checks passed!` and no files would be reformatted.

```bash
git add plugin/scripts/user-config-inventory.py tests/test_user_config_inventory.py
git commit -m "Add user-config-inventory.py with the settings section"
```

### Task 2: MCP servers, plugins, skills, scheduled tasks and instructions

**Files:**
- Modify: `plugin/scripts/user-config-inventory.py`
- Modify: `tests/test_user_config_inventory.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: `rel`, `load_json`, `hooks_from`, `inventory`, the `home` fixture and helpers from Task 1.
- Produces (fills these `inventory()` keys; Task 3's user-mode.md names these fields):
  - `mcp_servers`: one per server, from `.claude.json` top-level `mcpServers` (scope `user`, `project: null`, line path `("mcpServers", name)`) and each `projects.<path>.mcpServers` (scope `local`, `project: <path>`, line path `("projects", path, "mcpServers", name)`): `{"name", "scope", "project", "type", "command", "args", "url", "env_keys", "header_keys", "file": ".claude.json", "line"}`. `type` defaults to `"stdio"` when absent and `command` is set; missing `command`/`url` are `null`, missing `args` is `[]`; `env_keys`/`header_keys` are sorted key names of `env`/`headers`.
  - `plugins`: one per install entry of `.claude/plugins/installed_plugins.json` `plugins.<name>` (a list, or a dict as one entry): `{"name", "scope", "project_path", "version", "git_commit_sha", "install_path", "root", "enabled", "file": ".claude/plugins/installed_plugins.json", "line", "manifest_hooks", "hooks"}`. `install_path` and `root` are `rel(Path(installPath), home)`; `line` path `("plugins", name, i)` (`("plugins", name)` for a dict value); `enabled` per the plan-level answer; `manifest_hooks` is `True` when `<installPath>/.claude-plugin/plugin.json` parses and has a `hooks` key; `hooks` is `hooks_from` on `<installPath>/hooks/hooks.json` with that file's `rel` path, `[]` when absent.
  - `skills`: one per entry of `.claude/skills/`, sorted by name: `{"name", "file": ".claude/skills/<name>", "link": "symlink" | "junction" | null, "target": str | null, "plugin": bool, "root": str | null, "manifest_hooks": bool, "hooks": [hook items]}`. `link` is `"symlink"` when `Path.is_symlink()`, else `"junction"` when `os.readlink` succeeds (Windows junction), else `null`; `target` is `rel(Path(os.readlink(entry)), home)` with a leading `\\?\` stripped. `plugin` is true when `<entry>/.claude-plugin/plugin.json` exists (read through the entry path); then `root` is the entry's `file` and `hooks` comes from `<entry>/hooks/hooks.json` cited through the entry path. A file entry (not a directory) is listed with `plugin: false`.
  - `scheduled_tasks`: one per folder in `.claude/scheduled-tasks/`, sorted: `{"name", "file": ".claude/scheduled-tasks/<name>", "files": [sorted home-relative paths of every file under it]}`.
  - `instructions`: `{"file"}` for `.claude/CLAUDE.md` when present, then every file (recursive, sorted) under `.claude/agents/`, `.claude/commands/` and `.claude/output-styles/`.

- [ ] **Step 1: Extend the fixture and write the failing tests**

Extend the `home` fixture so it also writes:
- `.claude.json`: `{"mcpServers": {"web": {"command": "npx", "args": ["-y", "some-mcp"], "env": {"WEB_KEY": "SECRET-MCP-ENV-2"}}}, "projects": {"/work/app": {"mcpServers": {"api": {"type": "http", "url": "https://mcp.example.com", "headers": {"Authorization": "SECRET-HEADER-3"}, "env": {"P": "SECRET-PROJECT-ENV-5"}}}}}}`.
- `.claude/plugins/installed_plugins.json`: `{"version": 2, "plugins": {"demo@market": [{"scope": "user", "installPath": str(home / ".claude/plugins/cache/market/demo/1.0.0"), "version": "1.0.0", "gitCommitSha": "abc1234"}, {"scope": "project", "projectPath": "/work/app", "installPath": str(home / ".claude/plugins/cache/market/demo/0.9.0"), "version": "0.9.0"}]}}`, and in the 1.0.0 install path a `hooks/hooks.json` with one `SessionStart` hook, command `node ${CLAUDE_PLUGIN_ROOT}/hooks/start.js`, and a `.claude-plugin/plugin.json` `{"name": "demo", "hooks": "./extra.json"}`.
- `.claude/skills/kitplug/.claude-plugin/plugin.json` (`{"name": "kitplug"}`) and `.claude/skills/kitplug/hooks/hooks.json` with one `UserPromptSubmit` hook, command `python ${CLAUDE_PLUGIN_ROOT}/hooks/nudge.py`.
- `.claude/skills/plain/SKILL.md` (any text).
- `.claude/scheduled-tasks/daily/SKILL.md` and `.claude/scheduled-tasks/daily/notes.txt`.
- `.claude/CLAUDE.md`, `.claude/agents/rev.md`, `.claude/commands/go.md`, `.claude/output-styles/terse.md`.

Tests and their assertions:
- `test_mcp_servers_user_and_local`: two servers; `web` has scope `user`, `project` `None`, `type` `"stdio"`, `command` `"npx"`, `args` `["-y", "some-mcp"]`, `env_keys` `["WEB_KEY"]`, `file` `".claude.json"`, `line == line_of(claude_json, '"web"')`; `api` has scope `local`, `project` `"/work/app"`, `url` `"https://mcp.example.com"`, `header_keys` `["Authorization"]`, `env_keys` `["P"]`, `line == line_of(claude_json, '"api"')`.
- `test_installed_plugin_entries_hooks_and_enabled`: two `demo@market` items; the user one has `git_commit_sha == "abc1234"`, `install_path == ".claude/plugins/cache/market/demo/1.0.0"`, `enabled is True`, `manifest_hooks is True`, and one hook `{"event": "SessionStart", "matcher": None, "command": "node ${CLAUDE_PLUGIN_ROOT}/hooks/start.js", "file": ".claude/plugins/cache/market/demo/1.0.0/hooks/hooks.json", "line": line_of(that hooks file, "start.js")}`; the project one has `scope == "project"`, `project_path == "/work/app"`, `git_commit_sha is None`, `hooks == []`; the two items' `line`s differ.
- `test_enabled_local_overrides_settings`: add install entries for `off@market` and `other@market` to the fixture's `installed_plugins.json`; the `off@market` item has `enabled is True` (settings.local.json overrides settings.json's `False`); the `other@market` item, which no settings file lists, has `enabled is None`.
- `test_skills_dir_plugin_marked_with_hooks`: `kitplug` has `plugin: True`, `root == ".claude/skills/kitplug"`, `link is None`, and one hook with event `UserPromptSubmit`, file `.claude/skills/kitplug/hooks/hooks.json` and the line of `nudge.py`; `plain` has `plugin: False` and `hooks == []`.
- `test_linked_skill_reports_link_and_target`: create `tmp_path / "checkout"` holding `.claude-plugin/plugin.json` and `hooks/hooks.json` (one `Stop` hook), and link `.claude/skills/linked` to it with `os.symlink(target, link, target_is_directory=True)`, falling back on `OSError` to `_winapi.CreateJunction(str(target), str(link))` when `os.name == "nt"`; the item has `link in {"symlink", "junction"}`, `target == (tmp_path / "checkout").as_posix()`, `plugin: True`, and its hook's `file == ".claude/skills/linked/hooks/hooks.json"`.
- `test_install_path_outside_home_is_absolute`: an install entry whose `installPath` is `tmp_path / "outside" / "p"` with a `hooks/hooks.json`; its `install_path`, `root` and hook `file` start with `(tmp_path / "outside").as_posix()`.
- `test_scheduled_task_files_listed`: one task `daily` with `files == [".claude/scheduled-tasks/daily/SKILL.md", ".claude/scheduled-tasks/daily/notes.txt"]`.
- `test_instructions_listed`: `[i["file"] for i in instructions] == [".claude/CLAUDE.md", ".claude/agents/rev.md", ".claude/commands/go.md", ".claude/output-styles/terse.md"]`.
- `test_wrong_types_do_not_crash`: in a fresh home write settings `{"permissions": {"allow": "Bash"}, "hooks": [], "env": "x"}` and `.claude.json` `{"mcpServers": []}`; exit 0, the settings item has `permissions == []`, `hooks == []`, `env == []`, `mcp_servers == []`, `errors == []`.
- The Task 1 test `test_secret_values_absent_from_output` now also covers `SECRET-MCP-ENV-2`, `SECRET-HEADER-3` and `SECRET-PROJECT-ENV-5`; leave it as is.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_user_config_inventory.py -v`
Expected: 8 new tests FAIL (empty lists); `test_wrong_types_do_not_crash` and the Task 1 tests PASS (Task 1 already treats wrong types as absent).

- [ ] **Step 3: Implement the five sections**

Fill `inventory()` per the Interfaces above, one helper per section (`mcp_servers(home, errors)`, `plugins(home, errors, enabled)`, `skills(home, errors)`, `scheduled_tasks(home)`, `instructions(home)`). `enabled` is the merged `{name: bool}` of the two settings files' `enabledPlugins`, local last. Never put an `env` or `headers` value into any output field.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_user_config_inventory.py -v`
Expected: all 18 tests PASS (on Windows without symlink rights the linked-skill test uses a junction and still passes).

- [ ] **Step 5: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests`
Expected: `All checks passed!` and no files would be reformatted.

```bash
git add plugin/scripts/user-config-inventory.py tests/test_user_config_inventory.py
git commit -m "Inventory MCP servers, plugins, skills, scheduled tasks and instructions"
```

### Task 3: `audit --user` mode

**Files:**
- Create: `plugin/skills/audit/user-mode.md`
- Modify: `plugin/skills/audit/SKILL.md`
- Modify: `tests/test_audit_skills.py`

**Depends on:** Task 2

**Interfaces:**
- Consumes: the CLI and output fields of `user-config-inventory.py` (Tasks 1 and 2): `file`, `line`, `root`, `manifest_hooks`, `hooks[].command`, `statusLine.command`, `scope`, `project_path`, `link`, `target`, `errors`.
- Produces: nothing code consumes.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_audit_skills.py`:

```python
def test_audit_skill_has_user_mode():
    body = read(AUDIT / "SKILL.md")
    front = frontmatter(AUDIT / "SKILL.md")
    assert "--user" in body and "user-mode.md" in body
    assert "--user" in front["description"]
    assert "--user" in front["argument-hint"]
    assert (AUDIT / "user-mode.md").is_file()


def test_user_mode_names_script_report_and_checker():
    text = read(AUDIT / "user-mode.md")
    assert "user-config-inventory.py" in text
    assert "~/.claude/claude-kit/audit/user-config.md" in text
    assert "check-findings.py" in text
    assert "never inside a repo" in text
    assert "`~/.claude/claude-kit/audit/` replaces `<repo>/docs/audit/`" in text
    assert (
        "Never read `.claude/settings.json`, `.claude/settings.local.json` "
        "or `.claude.json` in full"
    ) in text
    assert (PLUGIN / "scripts" / "user-config-inventory.py").is_file()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_audit_skills.py -v -k user`
Expected: both tests FAIL.

- [ ] **Step 3: Branch `SKILL.md` to user mode**

In `plugin/skills/audit/SKILL.md`: set `argument-hint: [path-to-repo | --user]`; append to `description` the sentence `With --user, audits the user-scope setup outside any repo (settings, MCP servers, plugins, hooks, skills, scheduled tasks, instructions) and writes ~/.claude/claude-kit/audit/user-config.md.` (the description must stay at most 1,024 characters); and insert, between the intro paragraph and `## Setup`, a section:

```markdown
## User mode

If `$ARGUMENTS` is `--user`, read `user-mode.md` in this skill's directory and
follow it instead of everything below (Setup, the four passes and Output).
```

- [ ] **Step 4: Write `plugin/skills/audit/user-mode.md`**

Sections, in order, each carrying the spec's Design "Audit `--user` mode" bullet plus the plan-level answers:
1. `# Audit: user mode` and one line: audits the user-scope Claude Code setup in the home directory, read-only.
2. `## Rules`: read `rules.md` in this directory in full; its read-only, finding-format, hard-rule and self-check sections bind this mode, with one change: "repo root" is the home directory, paths in **Where** are relative to it (a file outside it is cited by its absolute posix path, as the inventory writes it), and `~/.claude/claude-kit/audit/` replaces `<repo>/docs/audit/` as the one folder section 1 lets the audit write to. The scratch-file rule is unchanged.
3. `## Setup`: production bar (the user's, else the default from the plan-level answer, marked default in the header); if `~/.claude/claude-kit/audit/user-config.md` exists, ask before overwriting it.
4. `## Inventory`: run `python "${CLAUDE_PLUGIN_ROOT}/scripts/user-config-inventory.py"` (fallback `~/.claude/skills/claude-kit/scripts/user-config-inventory.py`); read its stdout (redirect long output to the `audit-scratch` folder). Report each `errors` entry as unread.
5. `## Reading`: the sentence `Never read \`.claude/settings.json\`, \`.claude/settings.local.json\` or \`.claude.json\` in full:` followed by "read only the line ranges the inventory cites, and never an `env` or `headers` block." Then: read in full every hook command's target script (the kit's, skills-dir plugins' and installed plugins'), the `statusLine` command's target script, skill files, scheduled-task files and every `instructions` file; for an item with `manifest_hooks: true`, read its `.claude-plugin/plugin.json` in full and every hooks file it names. The hook-resolution rule from the plan-level answer, verbatim in substance.
6. `## Checks`: section 4 of `rules.md`, both halves, on every item; plus the spec's six extra checks (permission rules broader than their apparent purpose and auto-approve modes; hooks that run on every tool call or prompt, or that fetch or run remote code; MCP servers with unpinned packages (`npx` or `uvx` without a version), remote URLs, or wide scope; plugins without a pinned commit; scheduled tasks that read untrusted content (web, inbox, vault ingest) with no human in the loop; untrusted text paths into a tool-using model across the whole setup). For a project-scope plugin, say that its project's settings decide whether it is enabled and that they were not read.
7. `## Output`: write `~/.claude/claude-kit/audit/user-config.md` (create the folder), never inside a repo, because it holds private paths and settings. Header: date, home directory written as `~`, the `version` in the kit's `plugin.json` (`../../.claude-plugin/plugin.json` from this directory), production bar, and what was not read. Sections: `## Inventory` (tables), `## Permissions`, `## Hooks`, `## MCP servers`, `## Plugins`, `## Skills`, `## Scheduled tasks`, `## Instructions`, `## Fix first`. Never copy a secret or an env or header value.
8. `## Self-check`: run `python <dir of rules.md>/../../scripts/check-findings.py <home> <report>` until it exits 0. In chat: counts by severity, the top five from Fix first, the checker's summary line and the report path; open the report (`Invoke-Item` on Windows, `open` on macOS, `xdg-open` on Linux).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_audit_skills.py tests/test_skill_size.py -v`
Expected: all PASS (including `test_audit_frontmatter` with the longer description).

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/audit/user-mode.md plugin/skills/audit/SKILL.md tests/test_audit_skills.py
git commit -m "Add audit --user mode for the user-scope setup"
```

### Task 4: ADR, README, version bump and spec index

**Files:**
- Create: `knowledge/decisions/0047-user-config-audit.md` (number per Global Constraints)
- Modify: `knowledge/decisions/README.md`
- Modify: `README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `tests/test_plugin_manifest.py`
- Modify: `docs/superpowers/README.md`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: nothing code consumes.

- [ ] **Step 1: Pin the new version in the test (failing)**

Run `git fetch origin` and read `origin/main`'s version (`git show origin/main:plugin/.claude-plugin/plugin.json`); the new version is the next minor (`0.31.1` → `0.32.0` today). In `tests/test_plugin_manifest.py`, `test_version_is_0_30_0` asserts `data["version"] == "0.31.1"`; change it to the new version.

Run: `pytest tests/test_plugin_manifest.py -v -k version_is`
Expected: FAIL (`0.31.1 != 0.32.0`).

- [ ] **Step 2: Bump `plugin.json`**

Set `"version"` in `plugin/.claude-plugin/plugin.json` to the new version; change nothing else in it.

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: all PASS.

- [ ] **Step 3: Write the ADR and its index row**

Take the number from `git ls-tree --name-only origin/main knowledge/decisions/` (highest + 1; rename the file if it is not 0047). Format of `knowledge/decisions/0000-template.md`: `# ADR 0047: User-config audit is a mode of audit, reports outside repos, never reads secrets`, Status `accepted`, Date the implementation date. Context: the repo audit covers one repo's config; most exposure (user settings, MCP servers in `~/.claude.json`, plugin hooks, skills, scheduled tasks) is outside any repo; idea from ECC's AgentShield, ideas only. Decision: one sentence each on reason and rejected option for D1 (a `--user` mode of `audit` reusing `rules.md` and `check-findings.py`; rejected a separate `config-audit` skill and the inventory script alone), D3 (report under `~/.claude/claude-kit/audit/`, never in a repo, because it holds private paths and settings; rejected `<repo>/docs/audit/`) and D4 (key names only, settings files and `.claude.json` read only at cited lines; rejected reading them in full, which would load secrets into context). Consequences: reuse and safety vs. a manual-only behavioural check. Add the row `| [0047](0047-user-config-audit.md) | User-config audit is a mode of audit, reports outside repos, never reads secrets | accepted | <date> |` at the end of the table in `knowledge/decisions/README.md`.

- [ ] **Step 4: README sentence**

In `README.md`, in the `plugin/` bullet, after `compares them by domain` and before its closing `)`, add: `; \`audit --user\` audits the user-scope setup outside any repo (settings, MCP servers, plugins and their hooks, skills, scheduled tasks) from \`user-config-inventory.py\` and writes its report to \`~/.claude/claude-kit/audit/\``. Keep the sentence inside the existing parenthesis.

- [ ] **Step 5: Regenerate the spec index and run the docs tests**

Run: `python plugin/scripts/spec-index.py docs/superpowers; pytest tests/test_docs.py tests/test_plugin_manifest.py -v`
Expected: `docs/superpowers/README.md` gains rows for `2026-11-15-user-config-audit-design.md` and `2026-11-16-user-config-audit.md` (`git diff --stat` shows it changed, unless the Stop hook already added them); all tests PASS.

- [ ] **Step 6: Check for private names and commit**

Run: `git diff main | grep -i -E "<username>|<private-repo-names>"`, filling in this machine's username (`$env:USERNAME` / `whoami`) and the private repo names under the workspace folder.
Expected: the grep prints nothing.

```bash
git add knowledge/decisions/0047-user-config-audit.md knowledge/decisions/README.md README.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py docs/superpowers/README.md
git commit -m "ADR, README and version bump for audit --user"
```

### Task 5: Verify the success criteria

**Files:** none (the report is written outside the repo; scratch files go to the `audit-scratch` temp folder and are deleted)

**Depends on:** Task 1, Task 2, Task 3, Task 4

**Interfaces:**
- Consumes: everything above.
- Produces: the counts by severity for the PR description (not the report).

- [ ] **Step 1: Suite green (criterion 1)**

Run: `pytest; ruff check plugin tests; ruff format --check plugin tests`
Expected: pytest reports all passed with no failures or errors; ruff prints `All checks passed!` and no files would be reformatted.

- [ ] **Step 2: Run the user audit (criterion 2)**

If `~/.claude/claude-kit/audit/user-config.md` already exists, stop and ask the user before overwriting it (user-mode.md's rule). Otherwise follow this worktree's `plugin/skills/audit/user-mode.md` from start to finish, running this worktree's `plugin/scripts/user-config-inventory.py` and `plugin/scripts/check-findings.py` (not the installed kit's copies).

Run: `python plugin/scripts/check-findings.py ~ ~/.claude/claude-kit/audit/user-config.md`
Expected: exit 0 and a summary line with no rejected findings.

- [ ] **Step 3: Inventory coverage check**

Run: `python plugin/scripts/user-config-inventory.py` and compare against the report's `## Inventory` tables.
Expected: every plugin listed under any settings item's `enabledPlugins`, every skills item with `plugin: true`, and every hook `command` (settings, installed plugins, skills-dir plugins) appears in the report's inventory.

- [ ] **Step 4: Secret search without reading values**

Write this snippet to `<temp>/audit-scratch/secret_check.py` (outside the repo) and run it with `python -I`; never print the values:

```python
import json, pathlib, sys
home = pathlib.Path.home()
report = (home / ".claude/claude-kit/audit/user-config.md").read_text("utf-8")
values = []
for name in (".claude/settings.json", ".claude/settings.local.json"):
    p = home / name
    if p.is_file():
        env = json.loads(p.read_text("utf-8-sig")).get("env") or {}
        values += [(name, k, str(v)) for k, v in env.items()]
cj = home / ".claude.json"
if cj.is_file():
    data = json.loads(cj.read_text("utf-8-sig"))
    servers = [("user", data.get("mcpServers") or {})]
    servers += [(p, (v or {}).get("mcpServers") or {}) for p, v in (data.get("projects") or {}).items()]
    for scope, group in servers:
        for sname, s in group.items():
            for field in ("env", "headers"):
                values += [(f"{scope}:{sname}", f"{field}.{k}", str(v)) for k, v in (s.get(field) or {}).items()]
hits = [(where, key) for where, key, v in values if v and v in report]
print(f"checked {len(values)} values, found {len(hits)}")
for where, key in hits:
    print("hit:", key)
sys.exit(1 if hits else 0)
```

Run: `python -I <temp>/audit-scratch/secret_check.py`
Expected: `checked <n> values, found 0` and exit 0. Then delete the `audit-scratch` folder.

- [ ] **Step 5: Record the counts**

Note the counts by severity from the report (Critical, High, Medium, Low) for the PR description; do not paste the report or any path from it into the PR. No commit (this task changes no repo file).
