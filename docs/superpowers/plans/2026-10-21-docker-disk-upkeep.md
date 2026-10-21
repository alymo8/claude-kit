# Docker Desktop disk upkeep on Windows Implementation Plan

- **Status:** implemented
- **Date:** 2026-10-21

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a read-only status script for Docker Desktop's virtual disk on Windows, report its line in `/ship` and `/ship-fast` clean-up, add an on-demand user-only `/docker-compact` command, and document the one-time sparse fix.

**Architecture:** One standard-library script, `plugin/scripts/docker-disk.py`, prints a single status line (file size, used space inside the disk, Docker total, sparse state, verdict) and always exits 0. Commands are Markdown prompts whose text tests pin with string assertions: a new `plugin/commands/docker-compact.md`, and one added sentence each in `ship.md` and `ship-fast.md`. Docs, ADR 0038 and a minor version bump (0.26.0 → 0.27.0) finish the change.

**Tech Stack:** Python 3.11+ standard library (pytest, ruff), Markdown, JSON, PowerShell 5.1 and `diskpart` (only inside the command text; never run in this change).

**Spec:** `docs/superpowers/specs/2026-10-21-docker-disk-upkeep-design.md`

Spec gate record: docs/superpowers/gates/2026-10-21-docker-disk-upkeep-design.md

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/`, workspace
conventions under `conventions/`, ADRs under `knowledge/decisions/`.
`tests/helpers.py` exports `PLUGIN` (`REPO / "plugin"`), `REPO`,
`load_module(path, name)` (imports a hyphenated script) and
`run_script(script, *args, env=...)` (returns a `CompletedProcess` with text
`stdout`). Scripts follow `plugin/scripts/open-spec.py`: a module docstring with
usage, `from __future__ import annotations`, `main()` returning the exit code,
`if __name__ == "__main__": sys.exit(main())`.

In `tests/test_ship_command.py`, `_step(n)` returns step `n` of `ship.md` with
whitespace collapsed; step markers (`11.`) start at column 0 and their continuation lines are indented 4 spaces for steps 10–12 (keep that indent for inserted lines). In `ship-fast.md` the
clean-up is the section after `## Cleanup (on request)`.

Setup: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks:
`pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.

Why (from the spec): Docker Desktop's `docker_data.vhdx` grows and never shrinks
unless the WSL distro is sparse (38.7 GB file for ~9.7 GB data on 2026-10-21).
Compaction stops Docker and needs UAC, so it stays out of `/ship`'s
no-check-in clean-up (D5); the clean-up only reports.

## Decisions already made (do not relitigate)

- D1: suggest compaction only when used is known and `file > 1.5 × used` and
  `file − used > 2 GiB`. Exactly 1.5× is not suggested.
- D2: no live compaction in this change.
- D4: used = `df` inside the `docker-desktop` distro, not `docker system df`;
  the Docker total is shown for context only.
- D6: sparse bit from `os.stat(...).st_file_attributes`, not `fsutil`.
- D7: the script never starts the distro; if it is not running, used is `?`.
- The kit never edits Docker Desktop or WSL settings; the existing Docker rule
  sentences (label filter on every prune, baseline) stay word for word.

Plan-level answers to the spec gate's plan questions:

- **Disk path for `/docker-compact`:** the script gets a `--path` flag that
  prints only the chosen disk path (nothing when none is found or not
  Windows) and exits 0. The command uses it, so the two default paths live in
  one place. (Task 1, Task 2)
- **No disk found:** `/docker-compact` stops after step 1 when the line says
  `skipped`; there is nothing to compact. (Task 2)
- **`compact.txt` encoding:** written by PowerShell
  `Set-Content -Encoding ascii` (ASCII, no BOM). If the disk path contains a
  non-ASCII character, the command stops before writing it and tells the user
  to run diskpart by hand. (Task 2)
- **diskpart outcome:** `Start-Process ... -Verb RunAs -Wait -PassThru`
  inside `try`/`catch`; a caught error means the UAC prompt was declined
  (nothing compacted); `ExitCode` 0 is success, anything else is a failure;
  the size before/after is reported in every case. (Task 2)
- **`docker system df` parsing:** a regex per row over the plain table output
  (no `--format`, so the allow-list stays exactly `docker system df`). Size
  tokens are a decimal number followed by one of `B`, `kB`, `MB`, `GB`, `TB`
  (factors of 1000). The total is known only when all four rows (Images,
  Containers, Local Volumes, Build Cache) parse; a missing row or any other
  unit means "does not parse" and `docker ?`. (Task 1)
- **Criterion 3 when Docker Desktop is not running:** not a stop rule; the PR
  records criterion 3 as not run, with the script's output pasted and the
  reason. (Task 5)
- **CLAUDE.md size:** the added sentence is at most 200 characters;
  `tests/test_workspace_rules_inject.py::test_size_cap` (≤ 9,500; 9,136 before
  this change) must still pass. (Task 4)

## Global Constraints

- Python standard library only; `requires-python >= 3.11`; ruff target `py311`.
- The script always exits 0 and runs no subprocess other than
  `wsl -l --running -q`, `wsl -d docker-desktop -- df -B1 /mnt/docker-desktop-disk`
  and `docker system df`, each with a 15-second timeout.
- Sizes print in GiB (bytes / 2^30) with one decimal, e.g. `9.5 GiB`; an unknown
  value prints as `<label> ?` (e.g. `used ?`).
- The public repo rule: no machine username or private repo names in tracked
  files; use `%LOCALAPPDATA%`, `%TEMP%`, `<repo-root>` in prose.
- Existing sentences stay verbatim: in `ship.md` "Never run a prune without a"
  and "never remove anything in the baseline"; in `ship-fast.md` "never run a
  prune without a"; the Docker paragraph of `CLAUDE.md`.
- Version 0.27.0.

## Review Focus

- `wsl -l --running -q` output with a BOM, CRLF line ends, or UTF-8 instead of
  UTF-16-LE (`WSL_UTF8=1`) must still find `docker-desktop`, and a distro named
  `docker-desktop-data` alone must not count as `docker-desktop`. (Task 1 test
  `test_running_distros_variants`)
- `df -B1` output that is empty, has only the header, or has a non-numeric
  `Used` column gives `used ?`, never a crash. (Task 1 test
  `test_df_used_bad_output`)
- `docker system df` output with an unknown unit (`PB`) or a missing row gives
  `docker ?`, not a partial sum. (Task 1 test `test_docker_total_unparseable`)
- `LOCALAPPDATA` unset on Windows gives the no-disk line, not a crash. (Task 1
  test `test_localappdata_unset`)
- A `subprocess.run` that raises `OSError` (not just `FileNotFoundError`) is
  treated as unknown, and the script still exits 0. (Task 1 test
  `test_oserror_is_unknown`)

---

### Task 1: `docker-disk.py` status script

**Files:**
- Create: `plugin/scripts/docker-disk.py`
- Test: `tests/test_docker_disk.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces (all in `plugin/scripts/docker-disk.py`; tests load it with
  `load_module(PLUGIN / "scripts" / "docker-disk.py", "docker_disk")`):
  - `GIB = 2**30`, `TIMEOUT = 15`
  - `DISTRO_CMD = ["wsl", "-l", "--running", "-q"]`
  - `DF_CMD = ["wsl", "-d", "docker-desktop", "--", "df", "-B1", "/mnt/docker-desktop-disk"]`
  - `DOCKER_CMD = ["docker", "system", "df"]`
  - `find_disk(localappdata: str | None) -> Path | None` — first existing of
    `<localappdata>/Docker/wsl/disk/docker_data.vhdx`,
    `<localappdata>/Docker/wsl/data/ext4.vhdx`; `None` when unset/empty or neither exists.
  - `read_disk(path: Path) -> tuple[int, bool]` — `(st_size, sparse)` from one
    `_stat(path)` call, where module-level `_stat = os.stat` (tests patch `mod._stat`, never `os.stat`); sparse is `getattr(st, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_SPARSE_FILE != 0`.
  - `run(cmd: list[str]) -> bytes | None` — the only `subprocess.run` call:
    `capture_output=True, timeout=TIMEOUT, check=False`; returns stdout bytes on
    exit 0, `None` on non-zero exit, `OSError` (includes `FileNotFoundError`) or
    `subprocess.TimeoutExpired`.
  - `running_distros(out: bytes) -> list[str]` — decode as UTF-16-LE when the
    bytes contain `b"\x00"`, else UTF-8 (`errors="ignore"` both); remove
    `"\x00"` and `"\ufeff"` (the BOM; write it as that escape in the source); return stripped non-empty lines.
  - `parse_df_used(text: str) -> int | None` — the `Used` column (index 2) of the
    first data row after the header, as int; `None` if absent/non-numeric.
  - `parse_docker_total(text: str) -> int | None` — sum per the regex below.
  - `used_bytes() -> int | None` — `run(DISTRO_CMD)`; only if `"docker-desktop"`
    is in `running_distros(...)`, `run(DF_CMD)` and `parse_df_used`. Any `run`
    returning `None` makes the result `None` (do not pass `None` on).
  - `docker_bytes() -> int | None` — `run(DOCKER_CMD)` then `parse_docker_total`;
    `None` when `run` returns `None`.
  - `verdict(file: int, used: int | None, sparse: bool) -> str`
  - `gib(n: int | None) -> str` — `f"{n / GIB:.1f} GiB"` or `"?"`.
  - `status_line(file: int, used: int | None, docker: int | None, sparse: bool) -> str`
  - `main(argv: list[str] | None = None) -> int` — always 0. With `--path`:
    on Windows with a disk, print the disk path; otherwise print nothing.
    Without it: `sys.platform != "win32"` → `docker disk: skipped (not Windows)`;
    no disk → `docker disk: skipped (no Docker Desktop disk found)`; else
    `status_line(...)`, calling `read_disk`, then `used_bytes()`, then `docker_bytes()`. Reads `os.environ.get("LOCALAPPDATA")`.

`parse_docker_total` row regex (multiline, per row):

```python
ROW = re.compile(
    r"^(Images|Containers|Local Volumes|Build Cache)\s+\S+\s+\S+\s+"
    r"(\d+(?:\.\d+)?)(B|kB|MB|GB|TB)\s",
    re.M,
)
UNITS = {"B": 1, "kB": 10**3, "MB": 10**6, "GB": 10**9, "TB": 10**12}
```

Known only when all four row names matched (append `"\n"` to the text before
matching so a last row still has trailing whitespace); else `None`. Round each
row to int bytes.

Line format (copy exactly):
`docker disk: file {gib(file)}, used {gib(used)}, docker {gib(docker)}, sparse {yes|no} -> {verdict}`

`verdict`: flags in order `not sparse` (when not sparse) and
`compact suggested (/docker-compact)` (when `used is not None and file > 1.5 * used and file - used > 2 * GIB`),
joined with `"; "`, or `"ok"` when none.

- [ ] **Step 1: Write the failing tests** in `tests/test_docker_disk.py`.

Fixtures: `mod` (the loaded module); a `fake_run(monkeypatch, responses)`
helper that sets `mod.subprocess.run` to a function recording `cmd` into a
list and returning `subprocess.CompletedProcess(cmd, rc, stdout=bytes)` from a
dict keyed by `tuple(cmd)`, or raising an exception instance stored there;
default for an unknown command is to fail the test. Use
`monkeypatch.setattr(mod.sys, "platform", "win32")` and
`monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))` for the Windows cases, and
`monkeypatch.setattr(mod, "read_disk", lambda p: (size, sparse))` for sizes. For Windows cases with a disk, create an empty file at `tmp_path / "Docker" / "wsl" / "disk" / "docker_data.vhdx"` so `find_disk` finds it.

Sample outputs to use:

```python
G = 2**30
DISTROS = "docker-desktop\r\nUbuntu\r\n".encode("utf-16-le")
DF = (b"Filesystem        1B-blocks       Used   Available Use% Mounted on\n"
      b"/dev/sde     1081101176832 3435973837 1022473838592   1% /mnt/docker-desktop-disk\n")
DOCKER = (b"TYPE            TOTAL     ACTIVE    SIZE      RECLAIMABLE\n"
          b"Images          5         2         1.2GB     800MB (66%)\n"
          b"Containers      2         0         212B      212B (100%)\n"
          b"Local Volumes   2         1         500MB     0B (0%)\n"
          b"Build Cache     10        0         45.5kB    45.5kB\n")
```

Tests and their assertions:

```python
def test_not_windows_skips(mod, monkeypatch, capsys):
    # platform "linux"; any subprocess call fails the test
    assert mod.main([]) == 0
    assert capsys.readouterr().out.strip() == "docker disk: skipped (not Windows)"

def test_no_disk(mod, monkeypatch, tmp_path, capsys):
    assert mod.main([]) == 0
    assert capsys.readouterr().out.strip() == "docker disk: skipped (no Docker Desktop disk found)"

def test_localappdata_unset(...):  # delenv LOCALAPPDATA -> same no-disk line, exit 0

def test_find_disk_prefers_docker_data_then_ext4(mod, tmp_path):
    # only wsl/data/ext4.vhdx exists -> that path; add wsl/disk/docker_data.vhdx -> it wins
    # find_disk(None) is None and find_disk("") is None

def test_read_disk_size_from_real_file(mod, tmp_path):
    # 1234-byte file -> read_disk(p)[0] == 1234

def test_sparse_bit(mod, monkeypatch):
    # monkeypatch.setattr(mod, "_stat", lambda p: SimpleNamespace(st_size=5, st_file_attributes=0x200))
    # -> (5, True); st_file_attributes=0 -> (5, False); attribute missing -> (5, False)

def test_full_line_suggests_compact(mod, ...):
    # read_disk -> (int(9.5*G), False); runs DISTROS, DF, DOCKER
    assert out == ("docker disk: file 9.5 GiB, used 3.2 GiB, docker 1.6 GiB, sparse no"
                   " -> not sparse; compact suggested (/docker-compact)")
    # (1.2e9 + 212 + 5e8 + 45500) / 2**30 = 1.58... -> "1.6 GiB"

def test_parse_docker_total_units(mod):
    assert mod.parse_docker_total(DOCKER.decode()) == 1_200_000_000 + 212 + 500_000_000 + 45_500
    # a variant with "2.5TB" for Images adds 2_500_000_000_000

def test_docker_total_unparseable(mod):
    # Images size "1.2PB" -> None; Build Cache row removed -> None; "" -> None

def test_df_used(mod):
    assert mod.parse_df_used(DF.decode()) == 3435973837

def test_df_used_bad_output(mod):
    # "" -> None; header only -> None; Used column "abc" -> None

def test_running_distros_variants(mod):
    # UTF-16-LE with BOM b"\xff\xfe" + CRLF -> includes "docker-desktop"
    # plain UTF-8 "docker-desktop\nUbuntu\n" -> includes "docker-desktop"
    # "docker-desktop-data\n" -> "docker-desktop" not in result

def test_distro_not_running_skips_df(mod, ...):
    # DISTROS without docker-desktop -> calls == [DISTRO_CMD, DOCKER_CMD]; line has "used ?"
    # and no "compact suggested"

def test_docker_missing_down_timeout(mod, ...):
    # parametrize DOCKER_CMD response: FileNotFoundError(), rc=1 empty stdout,
    # subprocess.TimeoutExpired(DOCKER_CMD, 15) -> line has "docker ?", main returns 0

def test_oserror_is_unknown(mod, ...):
    # DISTRO_CMD raises OSError("boom") -> "used ?", exit 0

def test_only_allowed_commands(mod, ...):
    # run every scenario above through one recorder; every recorded cmd is one of
    # DISTRO_CMD, DF_CMD, DOCKER_CMD (compare as lists, exactly)

def test_threshold_edges(mod):
    v = mod.verdict
    assert v(int(9.5 * G), int(3.2 * G), True) == "compact suggested (/docker-compact)"
    assert v(4 * G, 2 * G, True) == "ok"            # 2x but gap exactly 2 GiB
    assert v(3 * G, int(1.9 * G), True) == "ok"     # over 1.5x, gap 1.1 GiB
    assert v(9 * G, 6 * G, True) == "ok"            # exactly 1.5x, gap 3 GiB
    assert v(40 * G, None, True) == "ok"            # used unknown
    assert v(G, G, False) == "not sparse"

def test_status_line_sparse_yes_no(mod):
    assert mod.status_line(int(9.5 * G), int(3.2 * G), None, True) == (
        "docker disk: file 9.5 GiB, used 3.2 GiB, docker ?, sparse yes"
        " -> compact suggested (/docker-compact)")
    assert "sparse no -> not sparse; " in mod.status_line(int(9.5 * G), int(3.2 * G), None, False)

def test_gib_and_unknown(mod):
    assert mod.gib(int(9.5 * G)) == "9.5 GiB" and mod.gib(None) == "?"

def test_path_flag(mod, ...):
    # Windows with docker_data.vhdx -> main(["--path"]) prints exactly that path; no subprocess runs
    # no disk -> prints nothing; not Windows -> prints nothing; all exit 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_docker_disk.py -q`
Expected: errors loading `plugin/scripts/docker-disk.py` (file not found).

- [ ] **Step 3: Implement `plugin/scripts/docker-disk.py`** with the interface
above. Module docstring: usage `docker-disk.py [--path]`, what the line means,
that it always exits 0, runs only the three commands, and never starts the
`docker-desktop` distro. Parse `--path` with `argparse`. Decode `df` and
`docker` output as UTF-8 with `errors="replace"`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_docker_disk.py -q` → all pass.
Run: `ruff check plugin tests` and `ruff format --check plugin tests` → clean.

- [ ] **Step 5: Commit**

```bash
git add plugin/scripts/docker-disk.py tests/test_docker_disk.py
git commit -m "Add read-only Docker Desktop disk status script"
```

---

### Task 2: `/docker-compact` command

**Files:**
- Create: `plugin/commands/docker-compact.md`
- Test: `tests/test_docker_compact_command.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: `docker-disk.py` (no flag → the status line; `--path` → the disk
  path only).
- Produces: `plugin/commands/docker-compact.md` with frontmatter
  `description:` and `disable-model-invocation: true` (Task 4's manifest tests
  read it).

- [ ] **Step 1: Write the failing tests** in
`tests/test_docker_compact_command.py`, reading the file as `TEXT` and
`" ".join(TEXT.split())` as `FLAT`:

```python
def test_frontmatter_user_only():
    front = TEXT.split("---", 2)[1]
    assert TEXT.startswith("---\n") and "description:" in front
    assert "disable-model-invocation: true" in front

def test_runs_status_script_and_path_flag():
    assert '"${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"' in TEXT
    assert "~/.claude/skills/claude-kit/scripts/docker-disk.py" in TEXT
    assert "--path" in TEXT and "skipped" in TEXT

def test_asks_before_stopping_docker():
    ask = FLAT.index("Ask the user before anything else")
    assert ask < FLAT.index("fstrim") < FLAT.index("wsl --shutdown")
    assert "UAC" in FLAT and "clear yes" in FLAT

def test_steps_and_diskpart_script():
    for needle in ("fstrim -v /mnt/docker-desktop-disk", "wsl --shutdown",
                   "wsl --manage docker-desktop --set-sparse true",
                   r"%TEMP%\dcompact", 'select vdisk file="', "attach vdisk readonly",
                   "compact vdisk", "detach vdisk", "-Encoding ascii",
                   "-Verb RunAs", "-Wait", "-PassThru", "ExitCode"):
        assert needle in FLAT, needle

def test_temp_folder_deleted_and_no_prune():
    assert "Remove-Item" in FLAT and "whether or not diskpart succeeded" in FLAT
    assert "prune" not in TEXT.lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_docker_compact_command.py -q` → fails (file missing).

- [ ] **Step 3: Write `plugin/commands/docker-compact.md`.** It follows the
spec's nine steps (Design, `/docker-compact`) with these plan choices folded
in; keep each needle above verbatim:

- Frontmatter description: "Reclaim unused space in Docker Desktop's
  virtual disk on Windows (asks first; stops Docker; one UAC prompt)".
- Opening: on a system that is not Windows, say the command does not apply
  and stop. Commands run in PowerShell.
- Step 1: run `python "${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"`
  (fallback `~/.claude/skills/claude-kit/scripts/docker-disk.py`) and show the
  line. If it says `skipped`, report it and stop: nothing to compact. If the
  verdict lacks `compact suggested`, say so (when it shows `used ?`, say the
  `docker-desktop` distro was not running, so used space is unknown), then go
  on to step 2: the user decides. Run the script again with `--path` and keep
  the printed disk path.
- Step 2: "**Ask the user before anything else.**" Compacting stops Docker
  Desktop and every container and needs one UAC prompt; wait for a clear yes.
  A no ends the command with nothing changed.
- Step 3: if the distro is running (`wsl -l --running -q` lists
  `docker-desktop`), `wsl -d docker-desktop -- fstrim -v /mnt/docker-desktop-disk`;
  report a failure and continue.
- Step 4: ask the user to quit Docker Desktop from its tray icon and confirm;
  then `wsl --shutdown`.
- Step 5: if the line said `not sparse`, ask a separate yes/no; on yes run
  `wsl --manage docker-desktop --set-sparse true`.
- Step 6: if the disk path has a character outside ASCII, stop here and tell
  the user to run diskpart by hand with the four lines below (diskpart reads
  the script as ASCII). Otherwise create `%TEMP%\dcompact`
  (`New-Item -ItemType Directory -Force "$env:TEMP\dcompact"`) and write
  `compact.txt` with `Set-Content -Encoding ascii` (ASCII, no BOM), lines:
  `select vdisk file="<disk path>"`, `attach vdisk readonly`,
  `compact vdisk`, `detach vdisk`. Keep the spec's reason: a short fixed path,
  because writing under the session scratchpad failed on a long-path error on
  2026-10-21, and it avoids quoting problems with diskpart's `/s`.
- Step 7: note `(Get-Item <disk path>).Length`, then in one PowerShell call:
  `try { $p = Start-Process diskpart -ArgumentList '/s', "$env:TEMP\dcompact\compact.txt" -Verb RunAs -Wait -PassThru -ErrorAction Stop; $p.ExitCode } catch { 'declined' }`.
  A `declined` result means the UAC prompt was declined and nothing was
  compacted; `ExitCode` 0 is success; any other code, or an empty result,
  is a failure.
- Step 8: `Remove-Item -Recurse -Force "$env:TEMP\dcompact"`, whether or not
  diskpart succeeded.
- Step 9: report the outcome from step 7 and the file size before and after
  in GiB. Tell the user to start Docker Desktop again, then run the script
  once more for the full line.
- Closing rule: the command never removes Docker objects, never touches
  volumes, and never empties anything; compaction only gives back unused blocks
  of the disk file. (Do not use the word "prune" anywhere in the file; the
  test forbids it.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_docker_compact_command.py -q` → all pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/commands/docker-compact.md tests/test_docker_compact_command.py
git commit -m "Add /docker-compact command"
```

---

### Task 3: Status line in `/ship` and `/ship-fast` clean-up

**Files:**
- Modify: `plugin/commands/ship.md` (step 11 Docker sentences; step 12)
- Modify: `plugin/commands/ship-fast.md` (`## Cleanup (on request)` Docker sentence)
- Test: `tests/test_ship_command.py`, `tests/test_ship_fast_command.py`

**Depends on:** none

**Interfaces:**
- Consumes: the script path `scripts/docker-disk.py` (text only; the tests do
  not run it).
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing tests.**

In `tests/test_ship_command.py`:

```python
def test_cleanup_reports_docker_disk_line():
    step = _step(11)
    assert "scripts/docker-disk.py" in step
    assert step.index("docker buildx rm <slug>") < step.index("docker-disk.py")
    assert "its verdict is not a stop rule" in step
    assert "If the task used Docker, then run" in step
    assert "Never run a prune without a" in step
    assert "never remove anything in the baseline" in step
    assert "docker disk:" in _step(12)
```

In `tests/test_ship_fast_command.py`:

```python
def test_cleanup_reports_docker_disk_line():
    cleanup = " ".join(SHIP_FAST.split("## Cleanup (on request)", 1)[1].split())
    assert "scripts/docker-disk.py" in cleanup
    assert cleanup.index("docker buildx rm <slug>") < cleanup.index("docker-disk.py")
    assert "never run a prune without a" in cleanup
    assert "If the task used Docker" in cleanup[cleanup.index("never run a prune"):]
```

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_ship_command.py tests/test_ship_fast_command.py -q`
Expected: the two new tests fail on `docker-disk.py`.

- [ ] **Step 3: Edit the commands; do not change any existing word.**

`ship.md` step 11: after the sentence ending "never remove anything in the
baseline." insert (4-space indent, rewrap to the file's width):

> If the task used Docker, then run
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"` (fallback
> `~/.claude/skills/claude-kit/scripts/docker-disk.py`) and keep its
> `docker disk:` line for the report; it changes nothing and never prompts,
> and its verdict is not a stop rule.

`ship.md` step 12: after "the Learnings summary from step 7," insert
"the `docker disk:` line from step 11 if the task used Docker,".

`ship-fast.md` clean-up: after "`label=claude-kit.task=<slug>` filter." and
before "Then `git -C <main-checkout> worktree remove`" insert:

> If the task used Docker, then run
> `python "${CLAUDE_PLUGIN_ROOT}/scripts/docker-disk.py"` (fallback
> `~/.claude/skills/claude-kit/scripts/docker-disk.py`) and put its
> `docker disk:` line in your clean-up reply; it changes nothing and never
> prompts.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ship_command.py tests/test_ship_fast_command.py -q` → all pass.
Run: `git diff -- plugin/commands/ship.md plugin/commands/ship-fast.md` → only
added lines plus rewrapped lines whose words are unchanged.

- [ ] **Step 5: Commit**

```bash
git add plugin/commands/ship.md plugin/commands/ship-fast.md tests/test_ship_command.py tests/test_ship_fast_command.py
git commit -m "Report the Docker disk line in /ship and /ship-fast clean-up"
```

---

### Task 4: Docs, ADR 0038, manifest and version 0.27.0

**Files:**
- Modify: `docs/setup.md` (new section after `## Switches`)
- Modify: `CLAUDE.md` (Docker paragraph)
- Modify: `README.md` (commands paragraph)
- Create: `knowledge/decisions/0038-docker-disk-upkeep-outside-cleanup.md`
- Modify: `knowledge/decisions/README.md` (row for 0038)
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `tests/test_plugin_manifest.py`
- Test: `tests/test_docs.py` (existing), `tests/test_workspace_rules_inject.py` (existing)

**Depends on:** Task 2

**Interfaces:**
- Consumes: `plugin/commands/docker-compact.md` from Task 2 (frontmatter with
  `disable-model-invocation: true`, text containing `scripts/docker-disk.py`).
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing manifest tests** in
`tests/test_plugin_manifest.py`:
  - in `test_commands_exist_with_frontmatter`, add
    `"docker-compact": "scripts/docker-disk.py"` to `expected`;
  - in `test_side_effecting_commands_are_user_only`, add `"docker-compact"` to
    `user_only`;
  - rename `test_version_is_0_26_0` to `test_version_is_0_27_0` asserting
    `"0.27.0"`;
  - add `test_description_mentions_docker_compact`: `"/docker-compact" in data["description"]`.

- [ ] **Step 2: Run them to verify they fail**

Run: `pytest tests/test_plugin_manifest.py -q` → the version and description
tests fail.

- [ ] **Step 3: Bump `plugin/.claude-plugin/plugin.json`** to `"version": "0.27.0"`
and append to the description, before its final period:
", and /docker-compact to reclaim unused space in Docker Desktop's disk on Windows, with a read-only status line in the /ship and /ship-fast clean-up".

- [ ] **Step 4: Write the docs.**

`docs/setup.md`: after the `## Switches` table, before `## How changes ship`,
add `## Docker Desktop on Windows` saying: Docker Desktop keeps its data in
`%LOCALAPPDATA%\Docker\wsl\disk\docker_data.vhdx`, which grows as Docker writes
and does not shrink when data is deleted unless the distro is sparse; the
one-time fix is to quit Docker Desktop, then run
`wsl --manage docker-desktop --set-sparse true`; an optional build-cache cap in
Docker Desktop → Settings → Docker Engine:
`"builder": {"gc": {"enabled": true, "defaultKeepStorage": "5GB"}}`; the kit
never changes these settings itself; `python plugin/scripts/docker-disk.py`
shows the state (and `/ship`'s clean-up prints it when a task used Docker), and
`/docker-compact` reclaims space that has already built up (it asks first,
stops Docker and needs one UAC prompt).

`CLAUDE.md`: append to the Docker paragraph, directly after the sentence
ending "and never remove anything in the baseline.", this sentence (≤ 200
characters, nothing else changes):

> The clean-up also runs `plugin/scripts/docker-disk.py` (it reports only on
> Windows) and reports its line; compaction is only on demand, via
> `/docker-compact` (ADR 0038).

`README.md`: in the commands paragraph, after the `/spec-html [path]` sentence
("... opens its HTML view."), add: "`/docker-compact` reclaims unused space in
Docker Desktop's virtual disk on Windows, after asking (see
[`docs/setup.md`](docs/setup.md#docker-desktop-on-windows))."

ADR `knowledge/decisions/0038-docker-disk-upkeep-outside-cleanup.md`, in the
format of ADR 0037 (`# ADR 0038: Docker disk upkeep runs outside the
per-feature clean-up`, Status accepted, Date 2026-10-21, `## Context`,
`## Decision`, `## Consequences`). Context: the vhdx grows and does not shrink
unless sparse (38.7 GB for ~9.7 GB of data on 2026-10-21; diskpart got it to
9.5 GB); the bloat is machine-wide; compacting stops Docker and needs UAC,
which conflicts with `/ship`'s no-check-in run. Decision: the clean-up only
reports `docker-disk.py`'s line; compaction is the user-only `/docker-compact`;
the sparse flag is the prevention and compaction the repair, both applied by
the user; the threshold (file > 1.5 × used and file − used > 2 GiB) is measured
against the space used inside the disk, not `docker system df`, which counted
1.6 GiB against 3.2 GiB used. Consequences: growth is noticed at each
Docker-using `/ship`; nothing is reclaimed without the user; macOS, Linux and
moved disks get a skipped line.

`knowledge/decisions/README.md`: append
`| [0038](0038-docker-disk-upkeep-outside-cleanup.md) | Docker disk upkeep runs outside the per-feature clean-up | accepted | 2026-10-21 |`.

- [ ] **Step 5: Run the checks**

Run: `pytest tests/test_plugin_manifest.py tests/test_docs.py tests/test_workspace_rules_inject.py -q`
Expected: all pass, including `test_size_cap` (≤ 9,500 characters). If
`test_size_cap` fails, shorten the new `CLAUDE.md` sentence; do not trim other
text.

- [ ] **Step 6: Commit**

```bash
git add docs/setup.md CLAUDE.md README.md knowledge/decisions plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "Docs, ADR 0038 and 0.27.0 for Docker disk upkeep"
```

---

### Task 5: Index, statuses and acceptance checks

**Files:**
- Modify: `docs/superpowers/README.md` (regenerated)
- Modify: `docs/superpowers/specs/2026-10-21-docker-disk-upkeep-design.md` (Status only)
- Modify: `docs/superpowers/plans/2026-10-21-docker-disk-upkeep.md` (Status only)

**Depends on:** Task 1, Task 2, Task 3, Task 4

**Interfaces:**
- Consumes: everything above.
- Produces: the evidence for the PR body.

- [ ] **Step 1: Set statuses and regenerate the index.** Set `**Status:**` to
`implemented` in the spec and this plan (the convention sets it in the merging
PR). Run `python plugin/scripts/spec-index.py docs/superpowers`; expect rows
for this spec and plan in `docs/superpowers/README.md`.

- [ ] **Step 2: Criteria 1, 2, 4.**

Run: `pytest`, then `ruff check plugin tests` and `ruff format --check plugin tests`
Expected: all tests pass (including `tests/test_docker_disk.py::test_only_allowed_commands`); both ruff commands report no issues.

- [ ] **Step 3: Criterion 5.** `git diff main -- CLAUDE.md plugin/commands` →
no removed line that holds a rule sentence (only rewraps in `ship.md` /
`ship-fast.md` whose words are unchanged).

- [ ] **Step 4: Criterion 6.** In PowerShell, build the pattern from
`$env:USERNAME` plus every name from
`gh repo list --visibility private --json name -q ".[].name"`, joined with `|`,
then `git diff main | Select-String -Pattern <pattern>` (case-insensitive).
Expected: no match except the public GitHub owner in existing URLs.

- [ ] **Step 5: Criterion 3 (dry run, Windows only).** With Docker Desktop
running: `python plugin/scripts/docker-disk.py`, then the manual readings
`(Get-Item "$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx").Length/1GB`,
`wsl -d docker-desktop -- df -B1 /mnt/docker-desktop-disk` (Used / 2^30),
`docker system df` (sum the four SIZE values in decimal units, / 2^30) and
`fsutil sparse queryflag "$env:LOCALAPPDATA\Docker\wsl\disk\docker_data.vhdx"`.
Expected: each number within 0.1 GiB of the script's, and the sparse state
matches. Paste both outputs into the PR body. If Docker Desktop is not running
(or the machine is not Windows), this is not a stop: paste the script's output
and record criterion 3 as "not run" with the reason.

Criterion 7 (PR open with green CI, squash-merged) is delivered by `/ship`'s PR, CI and merge steps after this plan; paste the evidence from Steps 2–5 into the PR body.

- [ ] **Step 6: Commit**

```bash
git add docs/superpowers
git commit -m "Mark Docker disk upkeep spec and plan implemented; regenerate index"
```
