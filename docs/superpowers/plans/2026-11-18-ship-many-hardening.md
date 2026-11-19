# `/ship-many` hardening Implementation Plan

- **Status:** approved
- **Date:** 2026-11-18
- **Frozen:** none (spec D7: nothing is frozen)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/ship-many` children survive the failures of the first real run: a new runner script, `plugin/scripts/ship-child.py`, gives each child a real 2-hour limit per attempt, `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`, keep-awake and at most one resume, and writes a status file that `/ship-many` reads.

**Architecture:** `ship-child.py` (standard library only) runs `claude -p "/claude-kit:ship <rel>" ...` in its own process group, kills the whole tree on timeout, then decides once whether to resume from three pieces of evidence: the merged-PR state from `gh`, a stop-rule handoff in the child's `feat/<slug>` worktree, and whether that worktree existed before the run. `/ship` step 2 pins the `<slug>` rule both sides rely on. `/ship-many` launches the runner per spec and reads `<log-name>.status.json`. An ADR, three gotcha bullets, a README sentence and a minor version bump finish the change.

**Tech Stack:** Python 3.11 standard library (`argparse`, `ctypes`, `datetime`, `json`, `re`, `shutil`, `signal`, `subprocess`, `time`), pytest, ruff, Markdown.

**Spec:** `docs/superpowers/specs/2026-11-18-ship-many-hardening-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-18-ship-many-hardening-design.md`

## Context for the executor

This repo is claude-kit, a Claude Code plugin under `plugin/`. Setup once:
`pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks: `pytest`,
`ruff check plugin tests`, `ruff format --check plugin tests`. Run plain
`pytest` (not `-q`) to see the pass count.

`tests/helpers.py` exports `PLUGIN`, `REPO`, `load_module(path, name)` (imports
a hyphenated script), `clean_env(**extra)` (os.environ without `CLAUDE_KIT_*`,
plus `extra`) and `run_script(script, *args, cwd=None, env=None)` (runs
`sys.executable script args` with a 60-second timeout and returns a
`CompletedProcess` with UTF-8 `stdout`/`stderr`). Scripts follow
`plugin/scripts/docker-disk.py`: `#!/usr/bin/env python3`, a module docstring
with usage, `from __future__ import annotations`, `argparse`,
`main(argv: list[str] | None = None) -> int`,
`if __name__ == "__main__": sys.exit(main())`, and
`sys.stdout.reconfigure(encoding="utf-8")` guarded by `hasattr`.

Facts the runner relies on (checked in the repo):
- `plugin/scripts/handoff.py` writes a handoff at
  `<work-tree>/.claude/handoffs/<safe branch>.md`, where `safe_name` replaces
  every character outside `[A-Za-z0-9._-]` with `_`, so `feat/demo` gives
  `feat_demo.md`. `/handoff` (`plugin/commands/handoff.md`) writes
  `- **Written:** <YYYY-MM-DDTHH:MM> by /handoff`; the SessionEnd snapshot
  writes `- **Written:** ... by session-end snapshot` and
  `- **State refreshed:** ... by session-end snapshot`.
- `/ship` (`plugin/commands/ship.md`) writes its handoff through the
  `claude-kit:handoff` skill only when a stop rule fires, and from step 2 on
  it works inside the `feat/<slug>` worktree.
- `git worktree list --porcelain` prints blocks of `worktree <path>` then
  `HEAD <sha>` then `branch refs/heads/<name>` (or `detached`), separated by
  blank lines; on Windows the path uses `/` separators.

Gotchas (`knowledge/kit-dev-gotchas.md`): lines fit ruff's 88 characters;
edit test files with the Edit/Write tools, not bash heredocs. Commands must
stay under 20,000 bytes (`tests/test_skill_size.py`). The installed kit is
loaded through a junction to the main checkout, not this worktree, so the
manual dry run in Task 5 follows the worktree's command file directly.

## Global Constraints

- Runner: standard library only, Python 3.11, `sys.stdout.reconfigure(encoding="utf-8")`.
- Runner CLI, verbatim: `python ship-child.py --spec <rel> --main <main checkout> --log <log dir> --name <log-name> [--timeout 7200] [--resume-wait 60] [--claude claude] [--gh gh] [--git git]`.
- Exit 2 on bad usage, when `--main` is not a directory, or when an executable is not found by `shutil.which` (the message names it). Otherwise the exit code is the last attempt's exit code, 124 when it timed out.
- Child command, verbatim: `claude -p "/claude-kit:ship <rel>" --permission-mode auto --permission-prompts none --output-format json`, with the environment plus `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`.
- Log files: `<log>/<name>.json`, `<log>/<name>.err`, resume `<log>/<name>.resume.json`, `<log>/<name>.resume.err`, status `<log>/<name>.status.json`.
- `resume` values, verbatim: `resumed`, `merged`, `stop rule`, `timed out`, `gh failed`, `no worktree`.
- Slug: the spec's file name without `.md`, a leading `YYYY-MM-DD-` and a trailing `-design`; branch `feat/<slug>`.
- ADR number: one above the highest in `knowledge/decisions/` on `origin/main` at implementation time (today `0048`, so `0049`). Version: one minor above `origin/main`'s `plugin/.claude-plugin/plugin.json` at implementation time (today `0.33.0`, so `0.34.0`).
- Public repo: no machine username or private repo names in tracked files.

## Plan-level answers to the spec gate's plan questions

- **Stop-rule handoff written outside the feature worktree:** no `/ship` note
  or test is added; one extra attempt is accepted. The handoff skill writes to
  the work tree of its current directory, and every `/ship` stop rule after
  step 2 fires inside the `feat/<slug>` worktree, so its handoff lands there.
  Only the two stop rules that fire before step 2 (fetch failure in step 1,
  spec gate in step 0) write elsewhere, and spec D3 retries those on purpose.
  (Task 2)
- **Creating the worktree after the snapshot in tests:** the fake `claude`
  creates it. Its per-attempt config has `"worktree": true`, which runs
  `git -C <main> worktree add <fake dir>/wt -b feat/demo` during the attempt,
  after the runner took its pre-attempt `worktree list` snapshot; the config's
  `"handoff"` text is then written to
  `<fake dir>/wt/.claude/handoffs/feat_demo.md`. (Task 2)
- **Missing `--log` directory:** the runner creates it
  (`mkdir(parents=True, exist_ok=True)`); it is not a usage error. `/ship-many`
  step 4 creates it anyway, so this only matters for a hand run. (Task 2)
- **Prompt intact through a `claude.cmd` shim:** the runner passes argv as a
  list to `subprocess.Popen` with the `shutil.which`-resolved path, never a
  shell string; Python quotes the prompt (it holds a space) and `cmd.exe`
  hands it to the shim's `%*` unchanged. The fake launcher on Windows is a
  `.cmd` file, and `test_child_command_env_and_logs` asserts the fake received
  exactly the expected argv list. (Task 2)

## Review Focus

- **Main checkout path with a space** (a Windows user folder such as
  `C:\Users\First Last`): `--main`, the child's working directory and the
  worktree paths must work. Task 2's rig names the main checkout folder
  `main checkout`, so every Task 2 test runs with a space.
- **Handoff with CRLF line endings** (a handoff written on Windows): the
  `Written` line must still be recognised. Task 1 test
  `test_stop_rule_handoff_crlf`.
- **`gh` exits 0 but prints something that is not a JSON list** (a warning
  banner, an empty string): treat it as `gh failed`, never as "no PR". Task 2
  test `test_gh_bad_json_is_gh_failed`.
- **Empty child stdout or a JSON array** (a crashed child): `cost` is `null`,
  not an error. Task 1 test `test_read_cost`.
- **`--log` directory that does not exist yet:** created, not an error. Task 2
  test `test_child_command_env_and_logs` points `--log` at a missing folder.

---

### Task 1: Runner helpers in `ship-child.py`

**Files:**
- Create: `plugin/scripts/ship-child.py`
- Test: `tests/test_ship_child.py`

**Depends on:** none

**Interfaces:**
- Produces (all in `plugin/scripts/ship-child.py`, loaded in tests as
  `load_module(PLUGIN / "scripts" / "ship-child.py", "ship_child")`):
  - `branch_slug(spec: str) -> str`: slug of the spec's file name (accepts a
    relative path with `/`).
  - `worktree_on(porcelain: str, branch: str) -> Path | None`: the path of the
    first worktree whose `branch refs/heads/<branch>` line matches, else `None`.
  - `stop_rule_handoff(worktree: Path, slug: str) -> bool`: `True` when
    `<worktree>/.claude/handoffs/feat_<slug>.md` exists and has a
    `- **Written:** ... by <by>` line with `<by>` (stripped, `\r` removed)
    other than `session-end snapshot`. Missing file or no `Written` line:
    `False`. `State refreshed` lines are ignored.
  - `read_cost(path: Path) -> float | None`: `total_cost_usd` when the file
    parses as a JSON object holding a number there, else `None` (missing
    file, empty file, invalid JSON, non-object).
  - `class KeepAwake` with attribute `active: bool` and method
    `release() -> None` (idempotent); `keep_awake(platform: str) -> KeepAwake`.

- [ ] **Step 1: Write the failing tests** in `tests/test_ship_child.py`
  (module fixture `mod` loads the script as above):

```python
def test_branch_slug(mod):
    name = "2026-11-15-user-config-audit-design.md"
    assert mod.branch_slug(name) == "user-config-audit"
    assert mod.branch_slug("docs/specs/2026-11-18-demo-design.md") == "demo"
    assert mod.branch_slug("notes.md") == "notes"


def test_worktree_on(mod):
    porcelain = (
        "worktree C:/r/main\nHEAD 1\nbranch refs/heads/main\n\n"
        "worktree C:/r/wt x\nHEAD 2\nbranch refs/heads/feat/demo\n\n"
        "worktree C:/r/d\nHEAD 3\ndetached\n"
    )
    assert mod.worktree_on(porcelain, "feat/demo") == Path("C:/r/wt x")
    assert mod.worktree_on(porcelain, "feat/other") is None
```

  - `test_stop_rule_handoff` (parametrized over handoff text → expected):
    `"- **Written:** 2026-11-18T10:00 by /handoff\n"` → `True`;
    `"- **Written:** 2026-11-18T10:00 by session-end snapshot\n"` → `False`;
    that snapshot `Written` line plus
    `"- **State refreshed:** 2026-11-18T11:00 by session-end snapshot\n"` →
    `False`; no file → `False`. The file goes at
    `tmp_path / ".claude" / "handoffs" / "feat_demo.md"`; call
    `mod.stop_rule_handoff(tmp_path, "demo")`.
  - `test_stop_rule_handoff_crlf`: the `/handoff` line written as bytes ending
    `by /handoff\r\n` → `True`.
  - `test_read_cost`: `{"total_cost_usd": 4.12}` → `4.12`; `""` → `None`;
    `"not json"` → `None`; `"[1]"` → `None`; missing file → `None`.
  - Keep-awake tests monkeypatch `mod.subprocess.Popen` with a recorder that
    returns a fake process (`wait(timeout=1)` raises
    `subprocess.TimeoutExpired`, any other `wait` returns `0`; `terminate()`
    and `kill()` recorded) and `mod.shutil.which`:
    - `test_keep_awake_darwin`: starts
      `["caffeinate", "-i", "-w", str(os.getpid())]`, `active is True`, and
      `release()` calls `terminate()`.
    - `test_keep_awake_linux`: with `which` returning a path, starts
      `["systemd-inhibit", "--what=sleep", "--mode=block", "sleep", "infinity"]`
      with `start_new_session=True`, `active is True`; `release()` with
      `monkeypatch.setattr(mod.os, "killpg", recorder, raising=False)` (it
      does not exist on Windows) sends `signal.SIGTERM` to the fake's `pid`
      attribute.
    - `test_keep_awake_linux_without_inhibit`: `which` returns `None` → Popen
      never called, `active is False`.
    - `test_keep_awake_popen_fails`: Popen raises `OSError` → `active is False`.
    - `test_keep_awake_exits_early`: the fake process's `wait(timeout=1)`
      returns `1` → `active is False`.
    - `test_keep_awake_other_platform`: `keep_awake("sunos").active is False`.
  - `test_keep_awake_windows` (`skipif sys.platform != "win32"`): with
    `k = mod.keep_awake("win32")`, `k.active is True`; then
    `prev = SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)` (via
    `ctypes.windll.kernel32`, `restype = ctypes.c_uint32`) has the
    `ES_SYSTEM_REQUIRED` bit set; after `k.release()`,
    `SetThreadExecutionState(ES_CONTINUOUS)` returns a value without that bit.
    Constants: `ES_CONTINUOUS = 0x80000000`, `ES_SYSTEM_REQUIRED = 0x00000001`.

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_ship_child.py -v`
Expected: FAIL (the script does not exist).

- [ ] **Step 3: Implement the helpers in `plugin/scripts/ship-child.py`**

  Module docstring: the usage line from Global Constraints and a summary of
  the spec's "Child runner" points 1 to 5. `branch_slug`: take the file name,
  drop `.md`, `re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)`, then strip one
  trailing `-design`. `stop_rule_handoff`: regex
  `^- \*\*Written:\*\* .* by (.+?)\s*$` with `re.M`, on text read with
  `encoding="utf-8"`. `keep_awake`:
  - `win32`: `ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)`
    (`restype = ctypes.c_uint32`); non-zero → active; `release()` calls it
    with `ES_CONTINUOUS`. Runs on the caller's thread (the runner calls it
    from its main thread, Task 2).
  - `darwin`: Popen `caffeinate -i -w <os.getpid()>`; a platform starting with
    `linux`: Popen the `systemd-inhibit` command when
    `shutil.which("systemd-inhibit")` finds it. Both with
    stdin/stdout/stderr `DEVNULL`. After starting, `proc.wait(timeout=1)`: if
    it returns, the request failed (`active False`); `TimeoutExpired` means it
    holds. `OSError` → `active False`. The `systemd-inhibit` process starts
    with `start_new_session=True`, so its `sleep infinity` child goes with
    it. `release()` stops the process (`caffeinate`: `terminate()`;
    `systemd-inhibit`: `os.killpg(proc.pid, signal.SIGTERM)`), then
    `wait(5)`, and on `TimeoutExpired` calls `kill()`; `OSError` and
    `ProcessLookupError` are ignored throughout.
  - Any other platform: `active False`.

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_ship_child.py -v`
Expected: all PASS (`test_keep_awake_windows` skipped off Windows).

- [ ] **Step 5: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` — expected clean.

```bash
git add plugin/scripts/ship-child.py tests/test_ship_child.py
git commit -m "ship-child.py: slug, worktree, handoff, cost and keep-awake helpers"
```

### Task 2: Runner attempts, timeout, resume and status

**Files:**
- Modify: `plugin/scripts/ship-child.py`
- Test: `tests/test_ship_child.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: Task 1's `branch_slug`, `worktree_on`, `stop_rule_handoff`,
  `read_cost`, `keep_awake`.
- Produces: `main(argv: list[str] | None = None) -> int` and the status file
  `<log>/<name>.status.json` with exactly the spec's keys: `spec`, `branch`,
  `keep_awake`, `attempts` (each `cwd`, `start`, `end`, `exit`, `timed_out`,
  `cost`), `resume`, `timed_out`, `exit`, `cost`. Task 3's `/ship-many` text
  reads these keys. Internal helpers (names free): one attempt runner, a
  process-tree killer, a merged-PR check returning `True`/`False`/`None`
  (`None` = `gh failed`), and the resume decision.

**Test rig** (in `tests/test_ship_child.py`, fixture `rig(tmp_path)`;
`SHIP_CHILD = PLUGIN / "scripts" / "ship-child.py"`):
- `main = tmp_path / "main checkout"` (a space on purpose): `git init -b main`,
  commit `docs/superpowers/specs/2026-11-18-demo-design.md` (any text) with
  `git -c user.name=t -c user.email=t@example.com commit`. `rel` is that path
  with `/`.
- `fake = tmp_path / "fake"`, `bin = tmp_path / "bin"`. Two fake programs,
  `claude` and `gh`, each a Python file in `fake/` plus a launcher in `bin/`:
  on Windows `bin/<name>.cmd` holding `@"<sys.executable>" "<fake/name.py>" %*`;
  elsewhere `bin/<name>` holding `#!<sys.executable>` followed by the Python
  source, mode 0o755. The rig's env is `clean_env(PATH=str(bin) + os.pathsep
  + os.environ["PATH"], FAKE_DIR=str(fake))`, so the runner finds them with
  the defaults `--claude claude --gh gh` and finds the real `git`.
- Fake `claude` reads `fake/claude.json` = `{"main": <str>, "rel": <str>,
  "attempts": [...]}`; the attempt index is the number of lines already in
  `fake/calls.jsonl`. It appends `{"argv": sys.argv[1:], "cwd": os.getcwd(),
  "env": os.environ.get("CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS")}`, then
  applies the attempt's keys in this order: `"worktree": true` →
  `git -C <main> worktree add <fake>/wt -b feat/demo`; `"handoff": <text>` →
  write it to `<fake>/wt/.claude/handoffs/feat_demo.md` (creating folders);
  `"delete_spec": true` → delete `<main>/<rel>`; `"grandchild": true` → start
  `[sys.executable, "-c", "import time; time.sleep(60)"]`, write its pid to
  `fake/grandchild.pid` and its own pid to `fake/child.pid`; `"sleep": <s>`;
  then print `"stdout"` to stdout and `"stderr"` to stderr (both default
  empty) and exit with `"exit"` (default 0).
- Fake `gh` reads `fake/gh.json` = `{"exit": int, "stdout": str}`, appends
  `{"argv": sys.argv[1:], "cwd": os.getcwd()}` to `fake/gh_calls.jsonl`,
  prints `stdout`, exits `exit`. Default `gh.json`:
  `{"exit": 0, "stdout": "[]"}`.
- `rig.run(attempts, *extra, gh=None, log=None)` writes the configs, runs
  `run_script(SHIP_CHILD, "--spec", rel, "--main", str(main), "--log",
  str(log or tmp_path / "logs"), "--name", "demo", "--resume-wait", "0",
  *extra, env=rig.env)` and returns `(proc, status)`, where `status` is the
  parsed status file or `None` when it is missing.
- `alive(pid) -> bool` helper: on Windows, `str(pid)` in the stdout of
  `["tasklist", "/FI", f"PID eq {pid}", "/NH"]`; elsewhere `os.kill(pid, 0)`
  succeeds (`ProcessLookupError` → `False`). Tests poll it for up to 5
  seconds.

- [ ] **Step 1: Write the failing tests** (all through `rig.run` unless noted;
  compare paths with `os.path.samefile`):
  - `test_child_command_env_and_logs`: `log=tmp_path / "new" / "logs"`
    (missing); one attempt `{"exit": 0, "stdout": "{\"total_cost_usd\": 1}",
    "stderr": "warn"}`; gh stdout
    `[{"number": 7, "createdAt": "2999-01-01T00:00:00Z"}]`. Assert
    `calls[0]["argv"] == ["-p", f"/claude-kit:ship {rel}",
    "--permission-mode", "auto", "--permission-prompts", "none",
    "--output-format", "json"]`, `calls[0]["env"] == "0"`, its cwd is `main`;
    `demo.json` holds the stdout and `demo.err` holds `warn`; status
    `resume == "merged"`, one attempt, `exit == 0`; proc exit 0. The gh call's
    argv `== ["pr", "list", "--head", "feat/demo", "--state", "merged",
    "--json", "number,createdAt"]` with cwd `main`.
  - `test_timeout_kills_tree`: extra `--timeout 2`, attempt
    `{"grandchild": true, "sleep": 60}`. Elapsed (measured around `rig.run`)
    `< 30`; proc exit 124; `alive` is false for both pids within 5 seconds;
    status `timed_out is True`, `exit == 124`, `resume == "timed out"`, one
    attempt; `calls.jsonl` has one line.
  - `test_failure_resumes_once_in_worktree`: attempts
    `[{"exit": 1, "worktree": true, "stdout": "{\"total_cost_usd\": 1.5}"},
    {"exit": 0, "stdout": "{\"total_cost_usd\": 2.25}"}]`. Status
    `resume == "resumed"`, two attempts, `attempts[1]["cwd"]` is `fake/wt`,
    `cost == 3.75`, `exit == 0`; `demo.resume.json` and `demo.resume.err`
    exist.
  - `test_second_failure_not_resumed`: attempts `[{"exit": 1, "worktree":
    true}, {"exit": 1}, {"exit": 0}]` (the third must never run). Two lines in
    `calls.jsonl`; status `exit == 1`; proc exit 1.
  - `test_handoff_by_handoff_is_stop_rule`: attempt `{"exit": 0, "worktree":
    true, "handoff": "- **Written:** 2026-11-18T10:00 by /handoff\n"}` →
    `resume == "stop rule"`, one attempt.
  - `test_snapshot_handoff_does_not_block` (parametrized: the snapshot
    `Written` line alone; plus a `State refreshed ... by session-end snapshot`
    line), first attempt `{"exit": 1, "worktree": true, "handoff": ...}`, then
    `{"exit": 0}` → `resume == "resumed"`, two attempts.
  - `test_merged_before_start_does_not_count`: gh stdout
    `[{"number": 1, "createdAt": "2000-01-01T00:00:00Z"}]`, attempts
    `[{"exit": 1, "worktree": true}, {"exit": 0}]` → `resume == "resumed"`.
  - `test_gh_failure_blocks_resume`: gh `{"exit": 1, "stdout": ""}`, attempt
    `{"exit": 1, "worktree": true}` → `resume == "gh failed"`, one attempt.
  - `test_gh_bad_json_is_gh_failed`: gh `{"exit": 0, "stdout": "warning: x"}`,
    attempt `{"exit": 1, "worktree": true}` → `resume == "gh failed"`, one
    attempt.
  - `test_preexisting_worktree_blocks_resume`: before `rig.run`, run
    `git -C <main> worktree add <tmp_path>/old -b feat/demo`; attempt
    `{"exit": 1}` → `resume == "no worktree"`, one attempt.
  - `test_no_worktree_resumes_in_main_checkout`: attempts `[{"exit": 1},
    {"exit": 0}]` → `resume == "resumed"`, `attempts[1]["cwd"]` is `main`.
  - `test_no_worktree_and_no_spec`: attempt `{"exit": 1, "delete_spec": true}`
    → `resume == "no worktree"`, one attempt.
  - `test_non_json_stdout_cost_null`: attempt `{"exit": 0, "stdout": "oops"}`,
    gh lists a PR created `2999-01-01T00:00:00Z` → attempt `cost is None` and
    top-level `cost is None`.
  - `test_missing_claude_exits_2`: extra `--claude no-such-claude-xyz` → proc
    exit 2, `"no-such-claude-xyz"` in stderr, no status file.
  - `test_bad_usage_exits_2`: `run_script(SHIP_CHILD, "--main", str(main))`
    (no `--spec`) → exit 2; a full argument set with `--main` pointing at
    `tmp_path / "missing"` → exit 2.
  - `test_status_records_keep_awake`: a single-attempt run's status has a
    boolean `keep_awake`; on Windows it is `True`.

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_ship_child.py -v`
Expected: the Task 2 tests FAIL (`main` missing); Task 1 tests still pass.

- [ ] **Step 3: Implement `main` in `plugin/scripts/ship-child.py`**

  Follow the spec's "Child runner" points 1 to 5. Specifics the spec leaves
  to the plan:
  - Resolve `--claude`, `--gh`, `--git` with `shutil.which` first; a `None`
    prints `ship-child.py: executable not found: <name>` to stderr and returns
    2. `--main` not a directory: a message and 2. Then create `--log`.
  - Call `keep_awake(sys.platform)` on the main thread and `release()` in a
    `finally`. The runner prints nothing on success.
  - Record `git -C <main> worktree list --porcelain` (stdout text) before the
    first attempt.
  - One attempt: `subprocess.Popen([claude, "-p", f"/claude-kit:ship {rel}",
    "--permission-mode", "auto", "--permission-prompts", "none",
    "--output-format", "json"], cwd=<main for the first attempt, the chosen
    resume directory for the second>, env={**os.environ,
    "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"}, stdout=<file>,
    stderr=<file>, stdin=subprocess.DEVNULL)` plus `start_new_session=True`
    on POSIX or `creationflags=subprocess.CREATE_NEW_PROCESS_GROUP` on
    Windows; `proc.wait(timeout=args.timeout)`; on `TimeoutExpired` kill the
    tree (Windows `taskkill /PID <pid> /T /F`; POSIX `os.killpg(pid,
    SIGTERM)`, `wait(10)`, then `os.killpg(pid, SIGKILL)` if still running,
    ignoring `ProcessLookupError`), `wait()`, and set `exit` 124 and
    `timed_out` true. Times are `datetime.now(timezone.utc)`, stored as
    `isoformat(timespec="seconds")`. `cost` from `read_cost` on the attempt's
    JSON file.
  - Merged check: run `[gh, "pr", "list", "--head", f"feat/{slug}",
    "--state", "merged", "--json", "number,createdAt"]` with `cwd=main`,
    `capture_output=True`, `text=True`, `encoding="utf-8"`. Non-zero exit, or
    stdout that is not a JSON list of objects → `None` (`gh failed`).
    Otherwise `True` when any `createdAt`, parsed with
    `datetime.fromisoformat(s.replace("Z", "+00:00"))`, is after the first
    attempt's start; an entry without a parsable `createdAt` is skipped.
  - Resume decision after the first attempt only, in the spec's order:
    timed out → `timed out`; merged check `None` → `gh failed`; `True` →
    `merged`; `worktree_on(before, f"feat/{slug}")` not `None` →
    `no worktree`; `worktree_on(now, ...)` found and `stop_rule_handoff` →
    `stop rule`; found → resume there; else `(main / rel).is_file()` → resume
    in `main`; else `no worktree`. A resume sleeps `--resume-wait`, runs one
    attempt with the `.resume.json` / `.resume.err` files, and sets `resume`
    to `resumed`. No further attempts.
  - Status as the spec's point 5; top-level `cost` is the sum of non-null
    attempt costs (`round(x, 6)`), `null` when all are null. Write with
    `json.dumps(..., indent=2)` and `encoding="utf-8"`. Return the last
    attempt's `exit`.

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_ship_child.py -v`
Expected: all PASS (Windows-only test skipped elsewhere).

- [ ] **Step 5: Lint and commit**

Run: `ruff check plugin tests; ruff format --check plugin tests` — expected clean.

```bash
git add plugin/scripts/ship-child.py tests/test_ship_child.py
git commit -m "ship-child.py: time limit, one resume and status file"
```

### Task 3: `/ship` slug rule and `/ship-many` using the runner

**Files:**
- Modify: `plugin/commands/ship.md` (step 2)
- Modify: `plugin/commands/ship-many.md` (steps 2 to 6)
- Test: `tests/test_ship_command.py`, `tests/test_ship_many_command.py`

**Depends on:** Task 2

**Interfaces:**
- Consumes: Task 2's CLI (Global Constraints), its argv literals in
  `ship-child.py`, and its status keys (`attempts`, `resume`, `timed_out`,
  `exit`, `cost`).

- [ ] **Step 1: Write the failing tests**

  In `tests/test_ship_command.py`:

```python
def test_step_2_defines_the_slug():
    step = _step(2)
    assert "2026-11-15-user-config-audit-design.md" in step
    assert "user-config-audit" in step and "`-design`" in step
```

  In `tests/test_ship_many_command.py`, add
  `SHIP_CHILD = (PLUGIN / "scripts" / "ship-child.py").read_text(encoding="utf-8")`
  and a helper `step(n)` returning the text from `f"{n}. **"` to
  `f"{n + 1}. **"` (or the end). Replace `test_child_command_and_defaults`
  with a version that asserts each of these in `SHIP_CHILD`:
  `"/claude-kit:ship `, `"--permission-mode"`, `"auto"`,
  `"--permission-prompts"`, `"none"`, `"--output-format"`, `"json"` (each
  with its double quotes, as the list literals Task 2 writes) and
  `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`; keep its `default 3`,
  `limits concurrent specs only` and `2.1.259` assertions on `SHIP_MANY`.
  Add:
  - `test_step_4_launches_the_runner`: `step(4)` contains `ship-child.py`,
    `--spec`, `--main`, `--log`, `--name` and `not enforced`, and not
    `` `-2` ``.
  - `test_step_2_excludes_duplicate_slugs`: `` `duplicate slug` `` in `step(2)`.
  - `test_step_5_reads_status_file`: `step(5)` contains `status.json`,
    `attempts` and `timed_out`.
  - `test_step_6_drops_timed_out_recheck`: `step(6)` contains neither
    `may still be running` nor `look up its PR once more`, and contains
    `attempts` and `2 (resumed)`.
  In `test_collect_and_status_order`, delete the `look up its PR once more`
  assertion and the two `finish` lines; keep the rest. The first backticked
  `merged` must still come before the first backticked `timed out`, so do not
  write `` `timed out` `` in steps 1 to 4.

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_ship_command.py tests/test_ship_many_command.py -v`
Expected: the four new step tests and `test_step_2_defines_the_slug` FAIL;
the rewritten `test_child_command_and_defaults` and the edited
`test_collect_and_status_order` pass.

- [ ] **Step 3: Edit `plugin/commands/ship.md` step 2**

  After the sentence that starts ``Branch `feat/<slug>` from `origin/main` ``
  (it ends after the git fallback in parentheses), add:
  "`<slug>` is the spec's file name without `.md`, a leading `YYYY-MM-DD-`
  and a trailing `-design` (`2026-11-15-user-config-audit-design.md` →
  `user-config-audit`); `/ship-many`'s runner finds the branch by this rule."

- [ ] **Step 4: Edit `plugin/commands/ship-many.md`**

  - **Step 2:** after the `duplicate title` sentence add: "Then compute each
    remaining spec's slug as `/ship` step 2 defines it; a spec whose slug
    repeats an earlier spec's is excluded as `duplicate slug` (with
    `--dry-run`, it is only reported)."
  - **Step 3:** "the exact child command for each spec" becomes "the exact
    `ship-child.py` command for each spec".
  - **Step 4:** replace "and a 2-hour timeout", the fenced `claude -p ...`
    command and the `<log-name>` sentence, so the step says each spec runs
    as one background Bash command from the main checkout:

    ```
    python "${CLAUDE_PLUGIN_ROOT}/scripts/ship-child.py" --spec <spec> --main <main checkout> --log <log> --name <log-name>
    ```

    followed by: "`<spec>` is the path relative to the main checkout and
    `<log-name>` the spec's file name without `.md`. The runner gives each
    attempt 2 hours and kills the child's whole process tree when they pass,
    resumes once when the child ended with no merged PR, stop-rule handoff
    or timeout, and keeps the machine awake. The limit is the runner's, not
    the Bash tool's: a background Bash command's timeout is not enforced."
    Keep the wave and "One child failing never stops the others" sentences.
    The scripts fallback in the command's intro covers this path.
  - **Step 5:** replace the exit-code bullet with: "Its exit code, cost
    (`cost`), attempts (`attempts`) and `resume` come from
    `<log>/<log-name>.status.json` when the file holds a JSON object;
    otherwise the exit code is the background command's, cost and attempts
    are unknown, and `timed_out` counts as false. Its `result` text comes
    from its last attempt's JSON file (`<log-name>.resume.json` when it has
    two attempts, else `<log-name>.json`)." In the status bullet, the
    `timed out` reason becomes "(the status file's `timed_out` is true)".
  - **Step 6:** delete the first two sentences (the timed-out PR recheck and
    "may still be running"). The table becomes "(spec, wave, status,
    attempts, exit code, PR, merge commit, cost, log file)", followed by
    "attempts is `1`, or `2 (resumed)`; the total cost sums the status
    files' `cost`."

- [ ] **Step 5: Run to verify they pass**

Run: `pytest tests/test_ship_command.py tests/test_ship_many_command.py tests/test_skill_size.py -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add plugin/commands/ship.md plugin/commands/ship-many.md tests/test_ship_command.py tests/test_ship_many_command.py
git commit -m "/ship-many: run each child through ship-child.py; /ship defines the slug"
```

### Task 4: ADR, gotchas, README, version and index

**Files:**
- Create: `knowledge/decisions/0049-ship-many-child-runner.md` (number per Global Constraints)
- Modify: `knowledge/decisions/README.md`, `knowledge/kit-dev-gotchas.md`, `README.md`, `plugin/.claude-plugin/plugin.json`, `tests/test_plugin_manifest.py`, `docs/superpowers/README.md`

**Depends on:** none

- [ ] **Step 1: Write the failing test** — in `tests/test_plugin_manifest.py`
  rename `test_version_is_0_33_0` to `test_version_is_0_34_0` and expect
  `"0.34.0"` (or the version Global Constraints gives at implementation time).

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: `test_version_is_0_34_0` FAILS.

- [ ] **Step 3: Bump `version` in `plugin/.claude-plugin/plugin.json`** to that
  version. Re-run Step 2's command: expected PASS.

- [ ] **Step 4: Write the ADR** in the format of
  `knowledge/decisions/0000-template.md`: title "`/ship-many` children run
  through a runner with a time limit, one resume and keep-awake", Status
  `accepted`, Date `2026-11-18`. Context: the five failures of the spec's
  Purpose, with a link to ADR 0018
  (`0018-ship-many-headless-children.md`). Decision: D1 to D6, one sentence
  each on the reason and one on the rejected option; for D6 say the slug
  rule is now a contract between `/ship` and `ship-child.py` and that
  `/ship` printing its branch was rejected. Consequences: worst case 4 hours
  per child; a closed laptop lid still sleeps; a rerun over an existing
  `feat/<slug>` branch stays a hand step. Add the row
  ``| [0049](0049-ship-many-child-runner.md) | `/ship-many` children run through a runner with a time limit, one resume and keep-awake | accepted | 2026-11-18 |``
  at the end of the table in `knowledge/decisions/README.md`.

- [ ] **Step 5: Gotchas** — under "## Why `/ship` and `/ship-fast` say what
  they say" in `knowledge/kit-dev-gotchas.md`, add three bullets:
  - **Print-mode wait ceiling:** `claude -p` ends a `run_in_background`
    command after 10 minutes (`CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`), so
    `ship-child.py` sets it to `0` for `/ship-many` children.
  - **Background Bash timeout is not enforced:** a `run_in_background`
    command ignores its timeout (one child ran about 7 hours), so the 2-hour
    limit lives in `ship-child.py`, which kills the whole process tree.
  - **Why a resume skips a child that wrote a handoff:** `/ship` writes a
    `Written ... by /handoff` line only when a stop rule fires, which needs
    the user; the SessionEnd snapshot also writes the file but marks its
    lines `by session-end snapshot`, so only the `Written` line's author,
    not the file's existence or time, tells a stop rule apart.

- [ ] **Step 6: README** — in `README.md`, after the `/ship-many` sentence
  ending "`--dry-run` shows the waves first.", add: "Each child gets 2 hours
  per attempt and one automatic resume when it ends without a merged PR or
  a stop rule, and the run keeps the machine awake (a closed laptop lid
  still sleeps it)."

- [ ] **Step 7: Regenerate the spec index**

Run: `python plugin/scripts/spec-index.py`
Expected: `docs/superpowers/README.md` holds rows for the spec and this plan
(`grep -c ship-many-hardening docs/superpowers/README.md` prints `2`).

- [ ] **Step 8: Run the touched tests**

Run: `pytest tests/test_plugin_manifest.py tests/test_docs.py -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add knowledge/decisions/0049-ship-many-child-runner.md knowledge/decisions/README.md knowledge/kit-dev-gotchas.md README.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py docs/superpowers/README.md
git commit -m "ADR 0049, gotchas, README and v0.34.0 for the ship-many runner"
```

### Task 5: Full verification and manual checks (success criteria 1 to 3)

**Files:** none (verification; results go in the PR description)

**Depends on:** Task 3, Task 4

- [ ] **Step 0: Full suite (criterion 1)** — on the branch with Tasks 1 to 4
  merged.

Run: `pytest; ruff check plugin tests; ruff format --check plugin tests`
Expected: all tests pass (platform skips only), ruff clean. Then grep
`git diff origin/main` for the machine's username and any private repo
name: no hits. CI on the PR runs the same on Windows, Linux and macOS.

- [ ] **Step 1: Dry run (criterion 2).** The installed kit reads the main
  checkout's command, so follow this worktree's
  `plugin/commands/ship-many.md` steps 1 to 3 by hand (or in a session told
  to follow that file) with `--dry-run` on
  `docs/superpowers/specs/2026-11-15-user-config-audit-design.md` and
  `docs/superpowers/specs/2026-11-15-untrusted-vault-content-design.md`.
  Expected: per spec, the `python ".../ship-child.py" --spec <spec> --main
  <main checkout> --log <log> --name <log-name>` command and the log
  directory, and nothing launched (no new `feat/` branch, no log directory
  created).

- [ ] **Step 2: Runner smoke (criterion 3).** In a real terminal, write a fake
  `claude` that sleeps 60 seconds in a scratch folder (`fake.py`:
  `import time; time.sleep(60)`, with a `claude.cmd` launcher
  `@"<python>" "<scratch>\fake.py" %*` on Windows), then run the runner.

Run: `python plugin/scripts/ship-child.py --spec docs/superpowers/specs/2026-11-18-ship-many-hardening-design.md --main . --log <scratch>/logs --name smoke --timeout 5 --resume-wait 0 --claude <scratch>/claude.cmd`
Expected: it ends within 30 seconds with exit 124, and
`<scratch>/logs/smoke.status.json` shows `"timed_out": true` and
`"keep_awake": true`. Delete the scratch folder afterwards.

- [ ] **Step 3: Criterion 4 as a follow-up.** Criterion 4 (the next real
  `/ship-many` run checked for unresumed children and children past 4 hours,
  recorded in project memory) is post-merge and not blocking; list it under
  follow-ups in the PR description.
