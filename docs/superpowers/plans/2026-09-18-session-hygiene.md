# Session Hygiene Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

- **Status:** approved
- **Date:** 2026-09-18

**Goal:** Make ending and restarting a Claude Code session nearly free (a per-branch
handoff file, injected on the next start), make context growth visible (status line
plus a threshold nudge), and give Claude an exploration discipline (`lean-context`
skill), so sessions stay short and every turn stays cheap.

**Architecture:** Everything is Python scripts and Markdown inside the existing
`plugin/` folder of the kit. `plugin/scripts/handoff.py` owns the handoff file
(path, generated State section, snapshot merge). Three hooks in `plugin/hooks/`
wrap it and the transcript: `handoff_snapshot.py` (SessionEnd), `handoff_inject.py`
(SessionStart), `context_nudge.py` (UserPromptSubmit), sharing a tiny
`_transcript.py` helper. `statusline.py` renders the meter; `install-statusline.py`
wires it into user settings from `install.ps1`. `token-report.py` reproduces the
measurement that motivated the spec. Docs, templates, a command, a skill and two
ADRs complete it.

**Tech Stack:** Python 3.11+ standard library only (no new dependencies), pytest,
ruff, PowerShell 5.1 for the installer, git and optional `gh` on PATH.

**Spec:** `docs/superpowers/specs/2026-09-18-session-hygiene-design.md`. Read it
first; this plan argues from it. Workspace rules: `CLAUDE.md` at the repo root.

## Why this exists (for an executor with no context)

A measurement of 67 sessions showed the token cost is **context size times turn
count**: sessions run 200 to 700 turns with 300k to 850k tokens of context by the
end, and every turn re-sends all of it. Sessions run long because starting fresh
loses everything except `CLAUDE.md`. Simulating "restart with a 45k-token handoff
when context passes 300k" cut input tokens by 42%. The kit's job here is to make
that restart cheap, visible and habitual, without any hook ever hiding tool output
from Claude (that was an explicit quality decision).

Decisions already made (do not relitigate):

- Handoff is **gitignored, per branch, per work tree**, never committed. Rejected:
  committed on the feature branch (pollutes PR diffs, needs a cleanup step).
- Hooks are **conservative**: they add context and write files; none truncates or
  filters tool output. Rejected: aggressive output filtering.
- First nudge at **300k**, then every 100k; both configurable by env var.
- Status line is **added by the installer when absent**, never overwritten.
- Session hygiene is the **sixth convention** document, not a section elsewhere.
- **No service-backed memory** (knowledge graph, vector store). Rejected because
  same-file re-reads are rare; the real loss is carry-over between sessions.
- The subagent-first **exploration convention is deferred**; only the skill ships.

## Global Constraints

- Python `>=3.11`; scripts and hooks use only the standard library
  (`pyproject.toml` lists `markdown` for the renderer only). No new dependencies.
- `ruff check plugin tests` and `ruff format --check plugin tests` must pass;
  line length 88; lint rules `E, F, I, UP, B` (see `pyproject.toml`).
- Every hook: reads event JSON from stdin, catches every exception, reports on
  stderr prefixed `[claude-kit]`, **always exits 0**, never deletes (ADR 0007).
- Files written by scripts use UTF-8 and LF newlines (`newline="\n"`).
- Status line output is ASCII plus ANSI color codes; no Unicode glyphs.
- No private repo names and no Windows username in any tracked file. Tests use
  `tmp_path`; scripts derive every path from arguments, `Path.home()` or git.
- The handoff file target is under 80 lines; the skill under 60 lines.
- Work happens on a feature branch in a worktree (see Task 0) and lands by PR.

## File structure

Create:

```
plugin/scripts/handoff.py               path / state / snapshot for the handoff file
plugin/scripts/statusline.py            status line renderer (stdin JSON -> one line)
plugin/scripts/install-statusline.py    adds statusLine to user settings if absent
plugin/scripts/token-report.py          transcript measurement + cap simulation
plugin/hooks/_transcript.py             read_tail / last_usage_tokens / recent_prompts
plugin/hooks/handoff_snapshot.py        SessionEnd  -> handoff.snapshot
plugin/hooks/handoff_inject.py          SessionStart (startup|clear) -> print handoff
plugin/hooks/context_nudge.py           UserPromptSubmit -> threshold nudge
plugin/commands/handoff.md              /handoff
plugin/skills/lean-context/SKILL.md     exploration discipline
conventions/session-hygiene.md          sixth convention
knowledge/decisions/0008-handoff-is-gitignored-per-branch.md
knowledge/decisions/0009-no-service-backed-memory.md
tests/test_handoff.py
tests/test_handoff_snapshot.py
tests/test_handoff_inject.py
tests/test_context_nudge.py
tests/test_statusline.py
tests/test_install_statusline.py
tests/test_token_report.py
```

Modify:

```
plugin/hooks/hooks.json                 register the three hooks
plugin/install.ps1                      -Settings param; call install-statusline.py
plugin/.claude-plugin/plugin.json       version 0.2.0, description
plugin/templates/project/.gitignore     .claude/handoffs/
plugin/templates/project/CLAUDE.md      Pointers line
plugin/scripts/scaffold.py:185-186      adopt reminder mentions .claude/handoffs/
conventions/README.md                   sixth row + paragraph
CLAUDE.md                               sixth bullet + Token discipline section
README.md                               sixth playbook + plugin paragraph
knowledge/decisions/README.md           rows 0008, 0009
tests/test_plugin_manifest.py           new hooks, command, skill
tests/test_templates.py                 unchanged file list (no new template files)
tests/test_scaffold.py                  adopt reminder + gitignore content
tests/test_install.py                   pass -Settings to a temp file
```

---

### Task 0: Pre-flight and worktree

**Files:** none changed.

- [ ] **Step 1: Pre-flight on `main`** (workspace rule)

```powershell
git branch --show-current          # must print: main
git fetch
git status -sb                     # must print: ## main...origin/main (no ahead/behind)
```

If not on `main` or not in sync, stop and ask the user.

- [ ] **Step 2: Create the worktree** with the `superpowers:using-git-worktrees`
skill, branch `feat/session-hygiene`. Work in that worktree for every task below.

- [ ] **Step 3: Confirm the suite is green before changing anything**

```powershell
pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"
pytest
ruff check plugin tests; ruff format --check plugin tests
```

Expected: all pass. (Do not skip: it proves the environment, not the code.)

---

### Task 1: `handoff.py` (path, state, snapshot)

**Files:**
- Create: `plugin/scripts/handoff.py`
- Test: `tests/test_handoff.py`

**Interfaces:**
- Produces (imported by Tasks 2 and 3 via `sys.path`):
  - `work_tree(cwd: Path) -> Path | None`
  - `branch_name(cwd: Path) -> str` (e.g. `feature/foo`, or `detached-<sha7>`)
  - `safe_name(branch: str) -> str`
  - `handoff_path(cwd: Path) -> Path` (`<work_tree>/.claude/handoffs/<safe>.md`)
  - `state_section(cwd: Path) -> str` (starts with `## State`, ends with `\n`)
  - `written_line(by: str) -> str` (`- **Written:** YYYY-MM-DDTHH:MM by <by>`)
  - `replace_state(text: str, state: str) -> str`
  - `snapshot(cwd: Path, prompts: list[str]) -> Path`
  - CLI: `handoff.py path|state|snapshot [--cwd DIR] [--prompts FILE]`,
    exit 1 outside a git work tree.

- [ ] **Step 1: Write the failing tests**

`tests/test_handoff.py`:

```python
import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "handoff.py"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout.strip()


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


@pytest.fixture
def mod():
    return load_module(SCRIPT, "handoff")


def test_safe_name_replaces_slashes_and_odd_chars(mod):
    assert mod.safe_name("feature/foo") == "feature_foo"
    assert mod.safe_name("a b:c") == "a_b_c"
    assert mod.safe_name("v1.2-rc") == "v1.2-rc"


def test_path_is_under_dot_claude_handoffs(repo, mod):
    git("checkout", "-q", "-b", "feature/foo", cwd=repo)
    expected = repo / ".claude" / "handoffs" / "feature_foo.md"
    assert mod.handoff_path(repo).resolve() == expected.resolve()


def test_detached_head_gets_sha_name(repo, mod):
    sha = git("rev-parse", "--short=7", "HEAD", cwd=repo)
    git("checkout", "-q", "--detach", cwd=repo)
    assert mod.branch_name(repo) == f"detached-{sha}"


def test_state_lists_dirty_files_and_commits(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    (repo / "b.txt").write_text("b\n", encoding="utf-8")
    state = mod.state_section(repo)
    assert state.startswith("## State\n<!-- generated; do not edit -->\n")
    assert "- branch: main" in state
    assert "- dirty: b.txt" in state
    assert "init" in state  # last commit subject
    assert "- upstream: none" in state
    assert "- PR: none" in state
    assert state.endswith("\n")


def test_state_reports_ahead_behind_when_upstream_exists(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    git("branch", "base", cwd=repo)
    git("checkout", "-q", "-b", "feat", cwd=repo)
    git("branch", "--set-upstream-to=base", cwd=repo)
    (repo / "c.txt").write_text("c\n", encoding="utf-8")
    git("add", "c.txt", cwd=repo)
    git("commit", "-q", "-m", "c", cwd=repo)
    assert "- upstream: base, ahead 1, behind 0" in mod.state_section(repo)


def test_replace_state_keeps_every_other_byte(mod):
    before = (
        "# Handoff: x\n\n- **Written:** 2026-09-18T10:00 by /handoff\n\n"
        "## Task\nBuild it.\n\n## State\n<!-- generated; do not edit -->\n"
        "- branch: old\n\n## Done this session\n- a\n"
    )
    new_state = "## State\n<!-- generated; do not edit -->\n- branch: new\n"
    after = mod.replace_state(before, new_state)
    assert after == (
        "# Handoff: x\n\n- **Written:** 2026-09-18T10:00 by /handoff\n\n"
        "## Task\nBuild it.\n\n## State\n<!-- generated; do not edit -->\n"
        "- branch: new\n\n## Done this session\n- a\n"
    )


def test_replace_state_when_state_is_last_section(mod):
    before = "# H\n\n## State\n- branch: old\n"
    assert mod.replace_state(before, "## State\n- branch: new\n") == (
        "# H\n\n## State\n- branch: new\n"
    )


def test_snapshot_creates_file_with_state_and_prompts(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    path = mod.snapshot(repo, ["first prompt", "second prompt"])
    text = path.read_text(encoding="utf-8")
    assert path.resolve() == (repo / ".claude" / "handoffs" / "main.md").resolve()
    assert text.startswith("# Handoff: main\n\n- **Written:** ")
    assert "by session-end snapshot" in text
    assert "## State\n" in text
    assert "## Recent prompts\n- first prompt\n- second prompt\n" in text
    assert b"\r\n" not in path.read_bytes()


def test_snapshot_refreshes_only_state_and_written(repo, mod, monkeypatch):
    monkeypatch.setattr(mod, "pr_url", lambda cwd: None)
    path = mod.handoff_path(repo)
    path.parent.mkdir(parents=True)
    path.write_text(
        "# Handoff: main\n\n- **Written:** 2026-01-01T00:00 by /handoff\n"
        "- **Spec / plan:** none\n\n## Task\nKeep me.\n\n"
        "## State\n- branch: stale\n\n## Next\n1. Keep me too.\n",
        encoding="utf-8",
    )
    mod.snapshot(repo, ["ignored when file exists"])
    text = path.read_text(encoding="utf-8")
    assert "Keep me." in text and "Keep me too." in text
    assert "- branch: stale" not in text
    assert "- branch: main" in text
    assert "2026-01-01T00:00" not in text
    assert "by session-end snapshot" in text
    assert "ignored when file exists" not in text


def test_cli_path_and_state(repo):
    out = run_script(SCRIPT, "path", "--cwd", str(repo))
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip().endswith("main.md")
    out = run_script(SCRIPT, "state", "--cwd", str(repo))
    assert out.returncode == 0, out.stderr
    assert out.stdout.startswith("## State")


def test_cli_snapshot_reads_prompts_file(repo, tmp_path):
    prompts = tmp_path / "p.txt"
    prompts.write_text("one\ntwo\n", encoding="utf-8")
    out = run_script(SCRIPT, "snapshot", "--cwd", str(repo), "--prompts", str(prompts))
    assert out.returncode == 0, out.stderr
    text = (repo / ".claude" / "handoffs" / "main.md").read_text(encoding="utf-8")
    assert "- one\n- two\n" in text


def test_cli_outside_git_exits_1_and_writes_nothing(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    for sub in ("path", "state", "snapshot"):
        out = run_script(SCRIPT, sub, "--cwd", str(plain))
        assert out.returncode == 1, sub
        assert "git" in out.stderr
    assert not (plain / ".claude").exists()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_handoff.py -v`
Expected: every test errors with `FileNotFoundError` or `AssertionError` (script
missing).

- [ ] **Step 3: Write `plugin/scripts/handoff.py`**

```python
#!/usr/bin/env python3
"""Per-branch session handoff file: path, generated State section, snapshot.

Usage:
  handoff.py path     [--cwd DIR]                  print the handoff path
  handoff.py state    [--cwd DIR]                  print the generated State section
  handoff.py snapshot [--cwd DIR] [--prompts FILE]  create or refresh the file

The file lives at ``<work-tree>/.claude/handoffs/<branch>.md`` (gitignored). The
``/handoff`` command writes the whole file; ``snapshot`` (run by the SessionEnd
hook) creates it if missing and otherwise replaces only the ``## State`` section
and the ``**Written:**`` line, leaving every other byte untouched. Exit 1 outside a
git work tree.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SAFE_RE = re.compile(r"[^A-Za-z0-9._-]")
STATE_HEADER = "## State"
STATE_NOTE = "<!-- generated; do not edit -->"
WRITTEN_RE = re.compile(r"^- \*\*Written:\*\* .*$", re.M)


def git(*args: str, cwd: Path, timeout: int = 30) -> str | None:
    """Run git; return stripped stdout on success, None on any failure."""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def work_tree(cwd: Path) -> Path | None:
    top = git("rev-parse", "--show-toplevel", cwd=cwd)
    return Path(top) if top else None


def branch_name(cwd: Path) -> str:
    name = git("branch", "--show-current", cwd=cwd)
    if name:
        return name
    sha = git("rev-parse", "--short=7", "HEAD", cwd=cwd) or "unknown"
    return f"detached-{sha}"


def safe_name(branch: str) -> str:
    return SAFE_RE.sub("_", branch)


def handoff_path(cwd: Path) -> Path:
    top = work_tree(cwd)
    if top is None:
        raise RuntimeError("not inside a git work tree")
    return top / ".claude" / "handoffs" / f"{safe_name(branch_name(cwd))}.md"


def pr_url(cwd: Path) -> str | None:
    """URL of the open PR for the current branch via gh, or None."""
    if not shutil.which("gh"):
        return None
    try:
        result = subprocess.run(
            ["gh", "pr", "view", "--json", "url", "-q", ".url"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    url = result.stdout.strip()
    return url if result.returncode == 0 and url.startswith("http") else None


def state_section(cwd: Path) -> str:
    top = work_tree(cwd)
    if top is None:
        raise RuntimeError("not inside a git work tree")
    lines = [STATE_HEADER, STATE_NOTE]
    lines.append(f"- branch: {branch_name(cwd)}  (worktree: {top.as_posix()})")
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", cwd=cwd)
    if upstream:
        counts = git("rev-list", "--left-right", "--count", "@{u}...HEAD", cwd=cwd)
        behind, _, ahead = (counts or "0\t0").partition("\t")
        lines.append(
            f"- upstream: {upstream}, ahead {ahead.strip()}, behind {behind.strip()}"
        )
    else:
        lines.append("- upstream: none")
    porcelain = git("status", "--porcelain", cwd=cwd) or ""
    dirty = [line[3:].strip() for line in porcelain.splitlines() if line.strip()]
    lines.append("- dirty: " + (", ".join(dirty) if dirty else "clean"))
    log = git("log", "--oneline", "-5", cwd=cwd) or ""
    commits = [line.strip() for line in log.splitlines() if line.strip()]
    lines.append("- last commits: " + ("; ".join(commits) if commits else "none"))
    lines.append(f"- PR: {pr_url(cwd) or 'none'}")
    return "\n".join(lines) + "\n"


def written_line(by: str) -> str:
    return f"- **Written:** {datetime.now():%Y-%m-%dT%H:%M} by {by}"


def replace_state(text: str, state: str) -> str:
    """Replace the ``## State`` section (up to the next ``## ``) with ``state``."""
    start = text.find(STATE_HEADER)
    if start == -1:
        return text.rstrip("\n") + "\n\n" + state
    end = text.find("\n## ", start + len(STATE_HEADER))
    if end == -1:
        end = len(text)
    return text[:start] + state.rstrip("\n") + "\n" + text[end:]


def new_file_text(branch: str, state: str, prompts: list[str]) -> str:
    parts = [
        f"# Handoff: {branch}",
        "",
        written_line("session-end snapshot"),
        "- **Spec / plan:** none",
        "",
        state.rstrip("\n"),
    ]
    if prompts:
        parts += ["", "## Recent prompts", *[f"- {p}" for p in prompts]]
    return "\n".join(parts) + "\n"


def snapshot(cwd: Path, prompts: list[str]) -> Path:
    path = handoff_path(cwd)
    state = state_section(cwd)
    if path.exists():
        text = replace_state(path.read_text(encoding="utf-8"), state)
        text = WRITTEN_RE.sub(written_line("session-end snapshot"), text, count=1)
    else:
        text = new_file_text(branch_name(cwd), state, prompts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("subcommand", choices=("path", "state", "snapshot"))
    parser.add_argument("--cwd", default=".", help="a directory inside the repo")
    parser.add_argument("--prompts", help="file with one recent prompt per line")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cwd = Path(args.cwd).resolve()
    if work_tree(cwd) is None:
        print("[claude-kit] handoff: not inside a git work tree", file=sys.stderr)
        return 1
    if args.subcommand == "path":
        print(handoff_path(cwd).as_posix())
    elif args.subcommand == "state":
        sys.stdout.write(state_section(cwd))
    else:
        prompts: list[str] = []
        if args.prompts:
            raw = Path(args.prompts).read_text(encoding="utf-8")
            prompts = [line.strip() for line in raw.splitlines() if line.strip()]
        print(snapshot(cwd, prompts).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_handoff.py -v`
Expected: all PASS. If `test_state_reports_ahead_behind_when_upstream_exists`
fails on the count order, note that `--left-right --count @{u}...HEAD` prints
`<behind>\t<ahead>`; the code already reads it that way.

- [ ] **Step 5: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/scripts/handoff.py tests/test_handoff.py
git commit -m "Add handoff.py: per-branch handoff path, State section, snapshot"
```

---

### Task 2: `_transcript.py` helper and the SessionEnd snapshot hook

**Files:**
- Create: `plugin/hooks/_transcript.py`, `plugin/hooks/handoff_snapshot.py`
- Modify: `plugin/hooks/hooks.json`
- Test: `tests/test_handoff_snapshot.py`, `tests/test_plugin_manifest.py`

**Interfaces:**
- Consumes: `handoff.snapshot(cwd, prompts)` from Task 1.
- Produces (used by Task 4): in `_transcript.py`
  - `read_tail(path: Path, size: int = 262144) -> str` (last `size` bytes,
    decoded UTF-8 with `errors="replace"`, from the first full line)
  - `iter_records(text: str) -> Iterator[dict]` (one parsed JSON object per
    parseable line)
  - `last_usage_tokens(text: str) -> int | None` (input + cache_creation +
    cache_read of the last `assistant` record with a `usage` block)
  - `recent_prompts(text: str, limit: int = 5) -> list[str]` (last `limit`
    user prompts whose `message.content` is a string, not `isMeta`, not
    starting with `<`; first line only, cut at 120 chars)

- [ ] **Step 1: Write the failing tests**

`tests/test_handoff_snapshot.py`:

```python
import json
import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "handoff_snapshot.py"
HELPER = PLUGIN / "hooks" / "_transcript.py"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


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


def record(kind: str, **extra) -> str:
    return json.dumps({"type": kind, **extra})


def user(text: str, **extra) -> str:
    return record("user", message={"role": "user", "content": text}, **extra)


def tool_result() -> str:
    content = [{"type": "tool_result", "tool_use_id": "x", "content": "..."}]
    return record("user", message={"role": "user", "content": content})


@pytest.fixture
def transcript(tmp_path: Path) -> Path:
    lines = [
        user("<command-name>/clear</command-name>"),
        user("meta line", isMeta=True),
        user("first real prompt\nsecond line ignored"),
        tool_result(),
        user("x" * 200),
        user("last prompt"),
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_recent_prompts_filters_and_truncates(transcript):
    helper = load_module(HELPER, "_transcript")
    prompts = helper.recent_prompts(transcript.read_text(encoding="utf-8"))
    assert prompts == ["first real prompt", "x" * 120, "last prompt"]


def test_recent_prompts_limit(transcript):
    helper = load_module(HELPER, "_transcript")
    text = transcript.read_text(encoding="utf-8")
    assert helper.recent_prompts(text, limit=1) == ["last prompt"]


def test_read_tail_returns_whole_small_file_and_only_tail_of_big(tmp_path):
    helper = load_module(HELPER, "_transcript")
    small = tmp_path / "s.txt"
    small.write_text("a\nb\n", encoding="utf-8")
    assert helper.read_tail(small) == "a\nb\n"
    big = tmp_path / "b.txt"
    big.write_bytes(b"0123456789\n" * 100_000 + b"tail-line\n")
    tail = helper.read_tail(big, size=1024)
    assert tail.endswith("tail-line\n")
    assert len(tail.encode()) <= 1024
    assert tail.startswith("0123456789\n")  # starts at a line boundary


def test_read_tail_missing_file_is_empty(tmp_path):
    helper = load_module(HELPER, "_transcript")
    assert helper.read_tail(tmp_path / "nope.jsonl") == ""


def test_hook_writes_handoff_with_recent_prompts(repo, transcript):
    event = json.dumps(
        {
            "hook_event_name": "SessionEnd",
            "reason": "clear",
            "cwd": str(repo),
            "transcript_path": str(transcript),
        }
    )
    result = run_script(HOOK, stdin=event, cwd=repo)
    assert result.returncode == 0, result.stderr
    text = (repo / ".claude" / "handoffs" / "main.md").read_text(encoding="utf-8")
    assert "## State" in text
    assert "- last prompt" in text
    assert "meta line" not in text


def test_hook_is_silent_outside_git(tmp_path, transcript):
    plain = tmp_path / "plain"
    plain.mkdir()
    event = json.dumps({"cwd": str(plain), "transcript_path": str(transcript)})
    result = run_script(HOOK, stdin=event, cwd=plain)
    assert result.returncode == 0
    assert not (plain / ".claude").exists()


def test_hook_survives_malformed_stdin(repo):
    result = run_script(HOOK, stdin="{not json", cwd=repo)
    assert result.returncode == 0
    assert not (repo / ".claude").exists()


def test_hook_survives_missing_transcript(repo):
    event = json.dumps({"cwd": str(repo), "transcript_path": str(repo / "none")})
    result = run_script(HOOK, stdin=event, cwd=repo)
    assert result.returncode == 0
    assert (repo / ".claude" / "handoffs" / "main.md").exists()
```

Add to `tests/test_plugin_manifest.py` (replace the existing
`test_commands_exist_with_frontmatter` body's tuple to include `"handoff"` in
Task 8; here add the hook-registration test):

```python
def test_hooks_json_registers_session_hygiene_hooks():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    events = hooks["hooks"]
    assert any(
        "handoff_snapshot.py" in h["command"]
        for g in events["SessionEnd"]
        for h in g["hooks"]
    )
    starts = [g for g in events["SessionStart"] if g.get("matcher") == "startup|clear"]
    assert starts and "handoff_inject.py" in starts[0]["hooks"][0]["command"]
    assert any(
        "context_nudge.py" in h["command"]
        for g in events["UserPromptSubmit"]
        for h in g["hooks"]
    )
```

(This test also covers Tasks 3 and 4; it fails until those files exist, which is
expected. Register all three hooks in `hooks.json` now.)

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_handoff_snapshot.py tests/test_plugin_manifest.py -v`
Expected: snapshot tests fail with missing files; the manifest test fails on
`KeyError: 'SessionEnd'`.

- [ ] **Step 3: Write `plugin/hooks/_transcript.py`**

```python
"""Helpers for reading the tail of a Claude Code transcript (JSONL).

Transcripts grow to tens of MB; hooks read only the last chunk.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

TAIL_BYTES = 256 * 1024
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def read_tail(path: Path, size: int = TAIL_BYTES) -> str:
    """Last ``size`` bytes of ``path`` from the first full line; '' if unreadable."""
    try:
        total = path.stat().st_size
        with path.open("rb") as fh:
            if total > size:
                fh.seek(total - size)
                data = fh.read()
                cut = data.find(b"\n")
                data = data[cut + 1 :] if cut != -1 else data
            else:
                data = fh.read()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def iter_records(text: str) -> Iterator[dict]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            yield record


def last_usage_tokens(text: str) -> int | None:
    """Context size after the last API call: input + cache creation + cache read."""
    found: int | None = None
    for record in iter_records(text):
        if record.get("type") != "assistant":
            continue
        usage = (record.get("message") or {}).get("usage")
        if isinstance(usage, dict):
            found = sum(int(usage.get(k) or 0) for k in USAGE_KEYS)
    return found


def recent_prompts(text: str, limit: int = 5) -> list[str]:
    """Last ``limit`` typed user prompts, first line only, at most 120 chars."""
    prompts: list[str] = []
    for record in iter_records(text):
        if record.get("type") != "user" or record.get("isMeta"):
            continue
        content = (record.get("message") or {}).get("content")
        if not isinstance(content, str):
            continue
        first = content.strip().splitlines()[0] if content.strip() else ""
        if not first or first.startswith("<"):
            continue
        prompts.append(first[:120])
    return prompts[-limit:]
```

- [ ] **Step 4: Write `plugin/hooks/handoff_snapshot.py`**

```python
#!/usr/bin/env python3
"""SessionEnd hook: refresh the branch's handoff file with the current git State.

Creates ``.claude/handoffs/<branch>.md`` (with the last few user prompts) when
none exists; otherwise replaces only its State section and Written line. Outside
a git repo it does nothing. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "scripts"))

import _transcript  # noqa: E402
import handoff  # noqa: E402


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            return 0
        cwd = Path(event.get("cwd") or Path.cwd())
        if handoff.work_tree(cwd) is None:
            return 0
        prompts: list[str] = []
        transcript = event.get("transcript_path")
        if isinstance(transcript, str):
            prompts = _transcript.recent_prompts(_transcript.read_tail(Path(transcript)))
        handoff.snapshot(cwd, prompts)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] handoff snapshot error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Register all three hooks in `plugin/hooks/hooks.json`**

Replace the file with:

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
      },
      {
        "matcher": "startup|clear",
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/handoff_inject.py\""
          }
        ]
      }
    ],
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/handoff_snapshot.py\""
          }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/context_nudge.py\""
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 6: Run the tests**

Run: `pytest tests/test_handoff_snapshot.py -v`
Expected: all PASS. `tests/test_plugin_manifest.py::test_hook_commands_reference_existing_scripts`
will FAIL until Tasks 3 and 4 create the other two hook files; that is expected
at this point.

- [ ] **Step 7: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/hooks/_transcript.py plugin/hooks/handoff_snapshot.py plugin/hooks/hooks.json tests/test_handoff_snapshot.py tests/test_plugin_manifest.py
git commit -m "Add SessionEnd handoff snapshot hook and transcript tail helper"
```

---

### Task 3: SessionStart inject hook

**Files:**
- Create: `plugin/hooks/handoff_inject.py`
- Test: `tests/test_handoff_inject.py`

**Interfaces:**
- Consumes: `handoff.work_tree`, `handoff.handoff_path`, `handoff.branch_name`,
  `handoff.safe_name` (Task 1).
- Produces: `render(cwd: Path, now: datetime) -> str` (plain text for stdout,
  `""` when nothing to say); constants `MAX_AGE_DAYS = 7`.

- [ ] **Step 1: Write the failing tests**

`tests/test_handoff_inject.py`:

```python
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "handoff_inject.py"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


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


def write_handoff(repo: Path, name: str, written: datetime, body: str = "") -> Path:
    path = repo / ".claude" / "handoffs" / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"# Handoff: {name}\n\n- **Written:** {written:%Y-%m-%dT%H:%M} by /handoff\n\n"
        f"## Task\n{body or 'Do the thing.'}\n",
        encoding="utf-8",
    )
    return path


NOW = datetime(2026, 9, 18, 12, 0)


def test_injects_fresh_handoff_for_current_branch(repo):
    write_handoff(repo, "main", NOW - timedelta(hours=3), "Resume here.")
    text = load_module(HOOK, "inject").render(repo, NOW)
    assert text.startswith('<handoff age="3h" path=".claude/handoffs/main.md">')
    assert "verify it against git" in text
    assert "Resume here." in text
    assert text.rstrip().endswith("</handoff>")


def test_skips_stale_handoff(repo):
    write_handoff(repo, "main", NOW - timedelta(days=8))
    assert load_module(HOOK, "inject").render(repo, NOW) == ""


def test_mentions_other_branch_handoffs_in_one_line(repo):
    write_handoff(repo, "feature_bar", NOW - timedelta(days=2))
    text = load_module(HOOK, "inject").render(repo, NOW)
    assert text == "[claude-kit] Handoffs exist for other branches: feature_bar (2d)"


def test_other_branch_stale_handoff_is_not_mentioned(repo):
    write_handoff(repo, "feature_old", NOW - timedelta(days=30))
    assert load_module(HOOK, "inject").render(repo, NOW) == ""


def test_age_falls_back_to_mtime_without_written_line(repo):
    path = repo / ".claude" / "handoffs" / "main.md"
    path.parent.mkdir(parents=True)
    path.write_text("# Handoff: main\n\n## Task\nNo written line.\n", encoding="utf-8")
    text = load_module(HOOK, "inject").render(repo, datetime.now())
    assert "No written line." in text


def test_non_git_dir_renders_nothing(tmp_path):
    assert load_module(HOOK, "inject").render(tmp_path, NOW) == ""


def test_script_exit_zero_and_prints_to_stdout(repo, tmp_path):
    write_handoff(repo, "main", datetime.now() - timedelta(minutes=5))
    event = json.dumps({"hook_event_name": "SessionStart", "cwd": str(repo)})
    result = run_script(HOOK, stdin=event, cwd=repo)
    assert result.returncode == 0, result.stderr
    assert "<handoff " in result.stdout
    assert run_script(HOOK, stdin="{bad", cwd=tmp_path).returncode == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_handoff_inject.py -v`
Expected: FAIL, file missing.

- [ ] **Step 3: Write `plugin/hooks/handoff_inject.py`**

```python
#!/usr/bin/env python3
"""SessionStart hook (startup|clear): inject the branch's recent handoff file.

Prints the handoff for the current branch when it is younger than seven days,
wrapped in a short header. Otherwise prints one line naming fresh handoffs for
other branches, or nothing. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "scripts"))

import handoff  # noqa: E402

MAX_AGE_DAYS = 7
WRITTEN_RE = re.compile(r"^- \*\*Written:\*\* (\d{4}-\d{2}-\d{2}T\d{2}:\d{2})", re.M)
HEADER = (
    "Handoff from the previous session on this branch. Read it before exploring.\n"
    "The State section was generated at session end; verify it against git before\n"
    "trusting it."
)


def written_at(path: Path) -> datetime:
    match = WRITTEN_RE.search(path.read_text(encoding="utf-8"))
    if match:
        return datetime.strptime(match.group(1), "%Y-%m-%dT%H:%M")
    return datetime.fromtimestamp(path.stat().st_mtime)


def age_text(delta: timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f"{max(minutes, 0)}m"
    if minutes < 60 * 24:
        return f"{minutes // 60}h"
    return f"{minutes // (60 * 24)}d"


def render(cwd: Path, now: datetime) -> str:
    top = handoff.work_tree(cwd)
    if top is None:
        return ""
    folder = top / ".claude" / "handoffs"
    if not folder.is_dir():
        return ""
    limit = timedelta(days=MAX_AGE_DAYS)
    current = handoff.handoff_path(cwd)
    if current.exists() and now - written_at(current) <= limit:
        age = age_text(now - written_at(current))
        rel = current.relative_to(top).as_posix()
        body = current.read_text(encoding="utf-8").rstrip("\n")
        return f'<handoff age="{age}" path="{rel}">\n{HEADER}\n\n{body}\n</handoff>'
    others = []
    for path in sorted(folder.glob("*.md")):
        if path == current:
            continue
        delta = now - written_at(path)
        if delta <= limit:
            others.append(f"{path.stem} ({age_text(delta)})")
    if others:
        return "[claude-kit] Handoffs exist for other branches: " + ", ".join(others)
    return ""


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        cwd = Path(event.get("cwd") or Path.cwd()) if isinstance(event, dict) else Path.cwd()
        text = render(cwd, datetime.now())
        if text:
            print(text)
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] handoff inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_handoff_inject.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/hooks/handoff_inject.py tests/test_handoff_inject.py
git commit -m "Add SessionStart hook that injects the branch handoff"
```

---

### Task 4: UserPromptSubmit context nudge hook

**Files:**
- Create: `plugin/hooks/context_nudge.py`
- Test: `tests/test_context_nudge.py`

**Interfaces:**
- Consumes: `_transcript.read_tail`, `_transcript.last_usage_tokens` (Task 2).
- Produces: `next_level(tokens: int, fired: int, at: int, step: int) -> int | None`,
  `message(tokens: int) -> str`, env vars `CLAUDE_KIT_NUDGE_AT` (default
  `300000`), `CLAUDE_KIT_NUDGE_STEP` (default `100000`); state file
  `<scratchpad_dir>/claude-kit/nudge-level`.

- [ ] **Step 1: Write the failing tests**

`tests/test_context_nudge.py`:

```python
import json
import os
import subprocess
import sys
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "context_nudge.py"


def transcript_with(path: Path, tokens: int, padding_bytes: int = 0) -> Path:
    usage = {
        "input_tokens": 100,
        "cache_creation_input_tokens": 900,
        "cache_read_input_tokens": tokens - 1000,
    }
    lines = []
    if padding_bytes:
        filler = json.dumps({"type": "user", "message": {"content": "x" * 1000}})
        lines += [filler] * (padding_bytes // (len(filler) + 1))
    lines.append(json.dumps({"type": "assistant", "message": {"usage": usage}}))
    lines.append(json.dumps({"type": "user", "message": {"content": "next"}}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(tmp_path: Path, tokens: int, env: dict | None = None, padding: int = 0):
    transcript = transcript_with(tmp_path / "t.jsonl", tokens, padding)
    event = json.dumps(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "cwd": str(tmp_path),
            "scratchpad_dir": str(tmp_path / "scratch"),
            "transcript_path": str(transcript),
        }
    )
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=event,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **(env or {})},
        timeout=60,
    )


def test_next_level_math():
    mod = load_module(HOOK, "nudge")
    assert mod.next_level(100_000, 0, 300_000, 100_000) is None
    assert mod.next_level(310_000, 0, 300_000, 100_000) == 300_000
    assert mod.next_level(350_000, 300_000, 300_000, 100_000) is None
    assert mod.next_level(420_000, 300_000, 300_000, 100_000) == 400_000
    assert mod.next_level(650_000, 300_000, 300_000, 100_000) == 600_000


def test_fires_once_per_threshold(tmp_path):
    assert run(tmp_path, 100_000).stdout == ""
    first = run(tmp_path, 310_000)
    out = json.loads(first.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "310k tokens" in out["hookSpecificOutput"]["additionalContext"]
    assert "/handoff" in out["systemMessage"]
    assert run(tmp_path, 350_000).stdout == ""
    again = json.loads(run(tmp_path, 420_000).stdout)
    assert "420k tokens" in again["hookSpecificOutput"]["additionalContext"]


def test_env_vars_change_thresholds(tmp_path):
    env = {"CLAUDE_KIT_NUDGE_AT": "20000", "CLAUDE_KIT_NUDGE_STEP": "5000"}
    assert run(tmp_path, 19_000, env).stdout == ""
    assert "21k tokens" in run(tmp_path, 21_000, env).stdout
    assert run(tmp_path, 24_000, env).stdout == ""
    assert "26k tokens" in run(tmp_path, 26_000, env).stdout


def test_reads_only_the_tail_of_a_large_transcript(tmp_path):
    result = run(tmp_path, 310_000, padding=5 * 1024 * 1024)
    assert result.returncode == 0, result.stderr
    assert "310k tokens" in result.stdout


def test_missing_transcript_or_bad_stdin_is_silent(tmp_path):
    event = json.dumps({"transcript_path": str(tmp_path / "none.jsonl")})
    assert run_script(HOOK, stdin=event).returncode == 0
    assert run_script(HOOK, stdin=event).stdout == ""
    assert run_script(HOOK, stdin="{bad").returncode == 0
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_context_nudge.py -v`
Expected: FAIL, file missing.

- [ ] **Step 3: Write `plugin/hooks/context_nudge.py`**

```python
#!/usr/bin/env python3
"""UserPromptSubmit hook: nudge once per context threshold crossed.

Reads the tail of the transcript, computes the context size after the last API
call (input + cache creation + cache read), and when it first passes
CLAUDE_KIT_NUDGE_AT (default 300000) and then every CLAUDE_KIT_NUDGE_STEP
(default 100000), prints a one-sentence nudge as additionalContext (for Claude)
and systemMessage (for the user). The highest threshold already fired is kept
in <scratchpad_dir>/claude-kit/nudge-level. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import _transcript  # noqa: E402

DEFAULT_AT = 300_000
DEFAULT_STEP = 100_000


def next_level(tokens: int, fired: int, at: int, step: int) -> int | None:
    """Highest threshold at or below ``tokens`` that is above ``fired``, or None."""
    if tokens < at:
        return None
    level = at + ((tokens - at) // step) * step
    return level if level > fired else None


def message(tokens: int) -> str:
    return (
        f"Context is at {tokens // 1000}k tokens; every turn now re-sends all of "
        "it. At the next natural boundary, run /handoff and then /clear. "
        "(claude-kit session hygiene)"
    )


def level_file(event: dict) -> Path:
    scratch = event.get("scratchpad_dir")
    if isinstance(scratch, str) and scratch:
        return Path(scratch) / "claude-kit" / "nudge-level"
    session = str(event.get("session_id") or "unknown")
    return Path(tempfile.gettempdir()) / f"claude-kit-nudge-{session}"


def env_int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def main() -> int:
    try:
        event = json.loads(sys.stdin.read() or "{}")
        if not isinstance(event, dict):
            return 0
        transcript = event.get("transcript_path")
        if not isinstance(transcript, str):
            return 0
        tokens = _transcript.last_usage_tokens(_transcript.read_tail(Path(transcript)))
        if not tokens:
            return 0
        marker = level_file(event)
        fired = 0
        if marker.exists():
            try:
                fired = int(marker.read_text(encoding="utf-8").strip() or 0)
            except ValueError:
                fired = 0
        level = next_level(
            tokens, fired, env_int("CLAUDE_KIT_NUDGE_AT", DEFAULT_AT),
            env_int("CLAUDE_KIT_NUDGE_STEP", DEFAULT_STEP),
        )
        if level is None:
            return 0
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(str(level), encoding="utf-8")
        text = message(tokens)
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "hookEventName": "UserPromptSubmit",
                        "additionalContext": text,
                    },
                    "systemMessage": text,
                }
            )
        )
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] context nudge error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_context_nudge.py tests/test_plugin_manifest.py -v`
Expected: all PASS (the manifest test now finds all three hook files).

- [ ] **Step 5: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/hooks/context_nudge.py tests/test_context_nudge.py
git commit -m "Add UserPromptSubmit hook that nudges once per context threshold"
```

---

### Task 5: Status line renderer

**Files:**
- Create: `plugin/scripts/statusline.py`
- Test: `tests/test_statusline.py`

**Interfaces:**
- Produces: `render(data: dict, branch: str) -> str`, `current_branch(cwd: str) -> str`;
  CLI reads the status line JSON on stdin and prints one line. Used by Task 6.

- [ ] **Step 1: Write the failing tests**

`tests/test_statusline.py`:

```python
import json
import re

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "statusline.py"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

SAMPLE = {
    "model": {"id": "claude-opus-5", "display_name": "Opus"},
    "workspace": {"current_dir": "C:/anywhere"},
    "cost": {"total_cost_usd": 14.2},
    "context_window": {
        "total_input_tokens": 312_000,
        "context_window_size": 1_000_000,
        "used_percentage": 31.2,
    },
}


def plain(text: str) -> str:
    return ANSI.sub("", text)


def test_renders_documented_fields():
    mod = load_module(SCRIPT, "statusline")
    assert plain(mod.render(SAMPLE, "feature/foo")) == (
        "ctx 312k/1M 31% | $14.20 | feature/foo"
    )


def test_small_window_and_missing_branch():
    mod = load_module(SCRIPT, "statusline")
    data = {**SAMPLE, "context_window": {**SAMPLE["context_window"]}}
    data["context_window"]["context_window_size"] = 200_000
    assert plain(mod.render(data, "")) == "ctx 312k/200k 31% | $14.20"


def test_nulls_before_first_call():
    mod = load_module(SCRIPT, "statusline")
    data = {"context_window": {"total_input_tokens": 0, "used_percentage": None}}
    assert plain(mod.render(data, "main")) == "ctx - | $0.00 | main"


def test_color_by_percentage():
    mod = load_module(SCRIPT, "statusline")
    low = {"context_window": {"total_input_tokens": 10_000, "used_percentage": 10}}
    mid = {"context_window": {"total_input_tokens": 10_000, "used_percentage": 45}}
    high = {"context_window": {"total_input_tokens": 10_000, "used_percentage": 75}}
    assert "\x1b[" not in mod.render(low, "")
    assert "\x1b[33m" in mod.render(mid, "")
    assert "\x1b[31m" in mod.render(high, "")


def test_output_is_ascii():
    mod = load_module(SCRIPT, "statusline")
    mod.render(SAMPLE, "main").encode("ascii")


def test_cli_reads_stdin_and_survives_garbage():
    result = run_script(SCRIPT, stdin=json.dumps(SAMPLE))
    assert result.returncode == 0, result.stderr
    assert plain(result.stdout).startswith("ctx 312k/1M 31% | $14.20")
    bad = run_script(SCRIPT, stdin="not json")
    assert bad.returncode == 0
    assert bad.stdout == "\n"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_statusline.py -v`
Expected: FAIL, file missing.

- [ ] **Step 3: Write `plugin/scripts/statusline.py`**

```python
#!/usr/bin/env python3
"""Claude Code status line: context tokens, percentage, cost and branch.

Reads the status line JSON on stdin and prints one ASCII line, e.g.
``ctx 312k/1M 31% | $14.20 | feature/foo``. The percentage is yellow from 30%
and red from 60%. Prints an empty line on malformed input; never raises.
"""

from __future__ import annotations

import json
import subprocess
import sys

YELLOW = "\x1b[33m"
RED = "\x1b[31m"
RESET = "\x1b[0m"


def _k(n: int) -> str:
    return "1M" if n >= 1_000_000 else f"{round(n / 1000)}k"


def current_branch(cwd: str) -> str:
    if not cwd:
        return ""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def render(data: dict, branch: str) -> str:
    ctx = data.get("context_window") or {}
    used = ctx.get("total_input_tokens") or 0
    size = ctx.get("context_window_size") or 0
    pct = ctx.get("used_percentage")
    if used and pct is not None:
        pct_int = int(round(float(pct)))
        color = RED if pct_int >= 60 else YELLOW if pct_int >= 30 else ""
        pct_text = f"{color}{pct_int}%{RESET if color else ''}"
        ctx_text = f"ctx {_k(int(used))}/{_k(int(size))} {pct_text}" if size else (
            f"ctx {_k(int(used))} {pct_text}"
        )
    else:
        ctx_text = "ctx -"
    cost = float((data.get("cost") or {}).get("total_cost_usd") or 0)
    parts = [ctx_text, f"${cost:.2f}"]
    if branch:
        parts.append(branch)
    return " | ".join(parts)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        if not isinstance(data, dict):
            raise ValueError("not an object")
        cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd") or ""
        print(render(data, current_branch(str(cwd))))
    except Exception:
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_statusline.py -v`
Expected: all PASS.

- [ ] **Step 5: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/scripts/statusline.py tests/test_statusline.py
git commit -m "Add status line script showing context, cost and branch"
```

---

### Task 6: Status line installer and `install.ps1` integration

**Files:**
- Create: `plugin/scripts/install-statusline.py`
- Modify: `plugin/install.ps1`
- Test: `tests/test_install_statusline.py`, `tests/test_install.py`

**Interfaces:**
- Produces: CLI `install-statusline.py [--settings PATH] [--skills-dir PATH]`;
  function `install(settings: Path, skills_dir: Path) -> str` returning
  `"added"` or `"unchanged"`. `install.ps1` gains `-Settings <path>` (default
  `~\.claude\settings.json`) and calls the script after the junction is in place.

- [ ] **Step 1: Write the failing tests**

`tests/test_install_statusline.py`:

```python
import json
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "install-statusline.py"


def test_adds_statusline_and_preserves_everything_else(tmp_path: Path):
    settings = tmp_path / "settings.json"
    original = {
        "model": "x",
        "permissions": {"allow": ["WebSearch"]},
        "nested": {"deep": [1, {"a": "b"}]},
        "unicode": "عربي",
    }
    settings.write_text(json.dumps(original), encoding="utf-8")
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills") == "added"
    data = json.loads(settings.read_text(encoding="utf-8"))
    for key, value in original.items():
        assert data[key] == value
    assert data["statusLine"]["type"] == "command"
    command = data["statusLine"]["command"]
    assert command.startswith('python "')
    assert command.endswith('/claude-kit/scripts/statusline.py"')
    assert "\\" not in command
    assert "عربي" in settings.read_text(encoding="utf-8")  # ensure_ascii=False


def test_existing_statusline_is_left_untouched(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text('{"statusLine": {"type": "command", "command": "mine"}}')
    before = settings.read_bytes()
    mod = load_module(SCRIPT, "install_statusline")
    assert mod.install(settings, tmp_path / "skills") == "unchanged"
    assert settings.read_bytes() == before


def test_creates_missing_settings_file(tmp_path: Path):
    settings = tmp_path / "sub" / "settings.json"
    result = run_script(
        SCRIPT, "--settings", str(settings), "--skills-dir", str(tmp_path / "skills")
    )
    assert result.returncode == 0, result.stderr
    assert "statusLine added" in result.stdout
    assert "statusLine" in json.loads(settings.read_text(encoding="utf-8"))


def test_unparseable_settings_is_refused_without_writing(tmp_path: Path):
    settings = tmp_path / "settings.json"
    settings.write_text("{oops", encoding="utf-8")
    result = run_script(SCRIPT, "--settings", str(settings))
    assert result.returncode == 1
    assert settings.read_text(encoding="utf-8") == "{oops"
```

In `tests/test_install.py`, change `run_install` so every test passes a temp
settings path and never touches the real one:

```python
def run_install(skills_dir):
    settings = skills_dir.parent / "settings.json"
    return subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(INSTALL),
            "-SkillsDir",
            str(skills_dir),
            "-Settings",
            str(settings),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
```

and add:

```python
def test_install_adds_statusline_to_given_settings(tmp_path):
    skills = tmp_path / "skills"
    result = run_install(skills)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "statusLine added" in result.stdout
    text = (tmp_path / "settings.json").read_text(encoding="utf-8")
    assert "statusline.py" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_install_statusline.py tests/test_install.py -v`
Expected: the new tests FAIL (script missing; `-Settings` unknown parameter).

- [ ] **Step 3: Write `plugin/scripts/install-statusline.py`**

```python
#!/usr/bin/env python3
"""Add the claude-kit status line to Claude Code user settings if none is set.

Usage: install-statusline.py [--settings PATH] [--skills-dir PATH]

Reads ``settings.json`` (default ``~/.claude/settings.json``; created as ``{}``
if missing). If it has no ``statusLine`` key, adds one pointing at
``<skills-dir>/claude-kit/scripts/statusline.py`` (the junction path, so it stays
valid if the checkout moves) and rewrites the file with two-space indentation.
Never overwrites an existing status line. Exit 1 if the file is not valid JSON.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def install(settings: Path, skills_dir: Path) -> str:
    data: dict = {}
    if settings.exists():
        data = json.loads(settings.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("settings.json is not a JSON object")
    if "statusLine" in data:
        return "unchanged"
    script = (skills_dir / "claude-kit" / "scripts" / "statusline.py").as_posix()
    data["statusLine"] = {"type": "command", "command": f'python "{script}"'}
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return "added"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--settings", default=str(Path.home() / ".claude" / "settings.json"))
    parser.add_argument("--skills-dir", default=str(Path.home() / ".claude" / "skills"))
    args = parser.parse_args(argv)
    settings = Path(args.settings)
    try:
        outcome = install(settings, Path(args.skills_dir))
    except ValueError as exc:
        print(f"[claude-kit] {settings}: {exc}; left unchanged", file=sys.stderr)
        return 1
    if outcome == "added":
        print(f"statusLine added to {settings}")
    else:
        print("statusLine already configured; left unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Update `plugin/install.ps1`**

Add the parameter and a helper, and call it on both success paths. The `param`
block becomes:

```powershell
param(
  [string]$SkillsDir = (Join-Path $HOME ".claude\skills"),
  [string]$Settings = (Join-Path $HOME ".claude\settings.json")
)
```

Add after `$link = ...`:

```powershell
function Install-StatusLine {
  $script = Join-Path $PSScriptRoot "scripts\install-statusline.py"
  try {
    $out = & python $script --settings $Settings --skills-dir $SkillsDir 2>&1
    Write-Host ($out -join "`n")
  } catch {
    Write-Host "WARNING: could not configure the status line (is python on PATH?): $_"
  }
}
```

Replace the "already installed" branch's `exit 0` with:

```powershell
    Write-Host "claude-kit already installed: $link -> $target"
    Install-StatusLine
    exit 0
```

and after `Write-Host "Installed: $link -> $target"` insert `Install-StatusLine`
before the final hints. Also update the `.SYNOPSIS/.DESCRIPTION` comment: "Also
adds the kit's status line to user settings when none is configured."

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_install_statusline.py tests/test_install.py -v`
Expected: all PASS on Windows (`test_install.py` is skipped on Linux).

- [ ] **Step 6: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/scripts/install-statusline.py plugin/install.ps1 tests/test_install_statusline.py tests/test_install.py
git commit -m "Install the status line into user settings when absent"
```

---

### Task 7: `token-report.py`

**Files:**
- Create: `plugin/scripts/token-report.py`
- Test: `tests/test_token_report.py`

**Interfaces:**
- Produces: `encode_project(path: Path) -> str`, `scan(files: list[Path]) -> Report`,
  `simulate(contexts: list[list[int]], cap: int, restart: int = 45_000) -> int`,
  `render(report: Report, caps: list[int]) -> str`; CLI
  `token-report.py [--project DIR | --all] [--root DIR] [--cap N ...]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_token_report.py`:

```python
import json
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "token-report.py"


def assistant(ctx: int, tool: dict | None = None) -> str:
    content = [tool] if tool else []
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 0,
             "cache_read_input_tokens": ctx - 10}
    return json.dumps({"type": "assistant", "message": {"usage": usage, "content": content}})


def result(tool_use_id: str, text: str) -> str:
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
    return json.dumps({"type": "user", "message": {"content": [block]}})


def make_project(root: Path) -> Path:
    folder = root / "C--proj"
    folder.mkdir(parents=True)
    bash = {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "cat x"}}
    read = {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "f"}}
    s1 = [assistant(50_000, bash), result("t1", "a" * 20_000), assistant(80_000, read),
          result("t2", "b" * 100), assistant(120_000)]
    s2 = [assistant(10_000), assistant(400_000)]
    (folder / "s1.jsonl").write_text("\n".join(s1) + "\n", encoding="utf-8")
    (folder / "s2.jsonl").write_text("\n".join(s2) + "\n", encoding="utf-8")
    return folder


def test_encode_project_matches_claude_code_scheme():
    mod = load_module(SCRIPT, "token_report")
    assert mod.encode_project(Path("C:/Users/x/Desktop/Github")) == (
        "C--Users-x-Desktop-Github"
    )


def test_scan_counts_turns_tokens_and_tool_output(tmp_path):
    mod = load_module(SCRIPT, "token_report")
    folder = make_project(tmp_path)
    report = mod.scan(sorted(folder.glob("*.jsonl")))
    assert report.sessions == 2
    assert report.turns == 5
    assert report.input_tokens == 50_000 + 80_000 + 120_000 + 10_000 + 400_000
    assert report.tool_chars["Bash"] == 20_000
    assert report.tool_chars["Read"] == 100
    assert report.families["cat"] == 20_000
    assert [b[0] for b in report.big_results] == [20_000]


def test_simulate_restarts_at_cap():
    mod = load_module(SCRIPT, "token_report")
    contexts = [[100, 200, 300]]
    assert mod.simulate(contexts, cap=1_000, restart=45) == 600
    # cap 250: turn 3 (300) restarts -> counted as 45, later turns offset by 255
    assert mod.simulate([[100, 200, 300, 320]], cap=250, restart=45) == 100 + 200 + 45 + 65


def test_cli_prints_report_and_simulation(tmp_path):
    make_project(tmp_path)
    out = run_script(SCRIPT, "--all", "--root", str(tmp_path), "--cap", "100000")
    assert out.returncode == 0, out.stderr
    assert "sessions: 2" in out.stdout
    assert "avg context per call" in out.stdout
    assert "cap 100,000" in out.stdout
    assert "Bash" in out.stdout and "cat" in out.stdout


def test_cli_empty_root_is_graceful(tmp_path):
    out = run_script(SCRIPT, "--all", "--root", str(tmp_path / "missing"))
    assert out.returncode == 0
    assert "no transcripts found" in out.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_token_report.py -v`
Expected: FAIL, file missing.

- [ ] **Step 3: Write `plugin/scripts/token-report.py`**

```python
#!/usr/bin/env python3
"""Where do the tokens go? Measure Claude Code transcripts and simulate restarts.

Usage:
  token-report.py [--project DIR] [--root DIR] [--cap N ...]   one project (default: cwd)
  token-report.py --all [--root DIR] [--cap N ...]              every project folder

Transcripts live under ``~/.claude/projects/<encoded cwd>/*.jsonl``. Prints
sessions, turns, total input tokens, average context per call, the largest
sessions, tool output by tool and by Bash command family, results over 15k
characters, and total input tokens under a "restart with a 45k handoff at N
tokens" policy for each ``--cap``. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RESTART_COST = 45_000
BIG_RESULT = 15_000
SUBCOMMAND_WORDS = {"git", "gh", "npm", "npx", "pnpm", "yarn", "python", "pytest", "ruff", "node"}
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
FAMILY_RE = re.compile(r"(?:cd\s+\S+\s*(?:&&|;)\s*)*(\S+)")


def encode_project(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


@dataclass
class Report:
    sessions: int = 0
    turns: int = 0
    input_tokens: int = 0
    contexts: list[list[int]] = field(default_factory=list)
    per_session: list[tuple[str, int, int, float | None]] = field(default_factory=list)
    tool_chars: Counter = field(default_factory=Counter)
    tool_calls: Counter = field(default_factory=Counter)
    families: Counter = field(default_factory=Counter)
    big_results: list[tuple[int, str, str]] = field(default_factory=list)


def family(command: str) -> str:
    match = FAMILY_RE.match(command.strip())
    word = match.group(1) if match else "?"
    if word in SUBCOMMAND_WORDS:
        sub = re.search(re.escape(word) + r"\s+(\S+)", command)
        word = f"{word} {sub.group(1)}" if sub else word
    return word


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        return "".join(x.get("text", "") for x in content if isinstance(x, dict))
    return content if isinstance(content, str) else ""


def scan(files: list[Path]) -> Report:
    report = Report()
    for path in files:
        report.sessions += 1
        tools: dict[str, tuple[str, dict]] = {}
        contexts: list[int] = []
        cost: float | None = None
        for line in path.open(encoding="utf-8", errors="replace"):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            kind = record.get("type")
            message = record.get("message") or {}
            if kind == "cost-state":
                cost = record.get("totalCostUSD")
            elif kind == "assistant":
                usage = message.get("usage")
                if isinstance(usage, dict):
                    ctx = sum(int(usage.get(k) or 0) for k in USAGE_KEYS)
                    contexts.append(ctx)
                    report.turns += 1
                    report.input_tokens += ctx
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tools[block.get("id", "")] = (block.get("name", "?"), block.get("input") or {})
                        report.tool_calls[block.get("name", "?")] += 1
            elif kind == "user" and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                        continue
                    text = result_text(block)
                    name, inp = tools.get(block.get("tool_use_id", ""), ("?", {}))
                    report.tool_chars[name] += len(text)
                    if name in ("Bash", "PowerShell"):
                        report.families[family(str(inp.get("command", "")))] += len(text)
                    if len(text) > BIG_RESULT:
                        what = inp.get("command") or inp.get("file_path") or inp.get("pattern") or ""
                        report.big_results.append((len(text), name, str(what)[:80]))
        if contexts:
            report.contexts.append(contexts)
            report.per_session.append((path.stem[:8], len(contexts), contexts[-1], cost))
    return report


def simulate(contexts: list[list[int]], cap: int, restart: int = RESTART_COST) -> int:
    total = 0
    for session in contexts:
        offset = 0
        for ctx in session:
            effective = ctx - offset
            if effective > cap:
                offset = ctx - restart
                effective = restart
            total += effective
    return total


def render(report: Report, caps: list[int]) -> str:
    out: list[str] = []
    out.append(f"sessions: {report.sessions}   turns: {report.turns:,}")
    out.append(f"total input tokens (all turns): {report.input_tokens:,}")
    avg = report.input_tokens // report.turns if report.turns else 0
    out.append(f"avg context per call: {avg:,}")
    out.append("")
    out.append("largest sessions by end context (id, turns, end ctx, cost):")
    for sid, turns, end, cost in sorted(report.per_session, key=lambda r: -r[2])[:10]:
        cost_text = f"${cost:.2f}" if isinstance(cost, int | float) else "-"
        out.append(f"  {sid}  {turns:>5}  {end:>9,}  {cost_text}")
    out.append("")
    total_chars = sum(report.tool_chars.values()) or 1
    out.append("tool output by tool (chars, calls, share):")
    for name, chars in report.tool_chars.most_common(10):
        out.append(f"  {name:22s} {chars:>12,} {report.tool_calls[name]:>6}  {100 * chars // total_chars}%")
    out.append("")
    out.append("Bash output by command family (chars):")
    for name, chars in report.families.most_common(15):
        out.append(f"  {chars:>12,}  {name}")
    out.append("")
    out.append(f"results over {BIG_RESULT:,} chars: {len(report.big_results)}")
    for chars, name, what in sorted(report.big_results, reverse=True)[:10]:
        out.append(f"  {chars:>9,}  {name:10s} {what}")
    out.append("")
    out.append(f"restart simulation ({RESTART_COST:,}-token restart):")
    for cap in caps:
        simulated = simulate(report.contexts, cap)
        saved = 100 * (1 - simulated / report.input_tokens) if report.input_tokens else 0
        out.append(f"  cap {cap:>9,}: {simulated:>15,}  ({saved:.0f}% fewer)")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--project", default=".", help="project directory (default: cwd)")
    parser.add_argument("--all", action="store_true", help="scan every project folder")
    parser.add_argument("--root", default=str(Path.home() / ".claude" / "projects"))
    parser.add_argument("--cap", type=int, nargs="*", default=[150_000, 200_000, 300_000])
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.all:
        files = sorted(root.glob("*/*.jsonl")) if root.is_dir() else []
    else:
        folder = root / encode_project(Path(args.project).resolve())
        files = sorted(folder.glob("*.jsonl")) if folder.is_dir() else []
    if not files:
        print("no transcripts found")
        return 0
    print(render(scan(files), args.cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_token_report.py -v`
Expected: all PASS. Then run it for real and compare with the spec's Purpose
table (rounding differences are fine):

```powershell
python plugin/scripts/token-report.py --all
```

- [ ] **Step 5: Lint, format, commit**

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/scripts/token-report.py tests/test_token_report.py
git commit -m "Add token-report.py: transcript measurement and restart simulation"
```

---

### Task 8: `/handoff` command, `lean-context` skill, manifest

**Files:**
- Create: `plugin/commands/handoff.md`, `plugin/skills/lean-context/SKILL.md`
- Modify: `plugin/.claude-plugin/plugin.json`, `tests/test_plugin_manifest.py`

- [ ] **Step 1: Extend the manifest tests**

In `tests/test_plugin_manifest.py`, change `test_commands_exist_with_frontmatter`
to:

```python
def test_commands_exist_with_frontmatter():
    expected = {
        "new-project": "scripts/scaffold.py",
        "adopt-conventions": "scripts/scaffold.py",
        "handoff": "scripts/handoff.py",
    }
    for name, script in expected.items():
        text = (PLUGIN / "commands" / f"{name}.md").read_text(encoding="utf-8")
        assert text.startswith("---\n"), name
        assert "description:" in text.split("---", 2)[1], name
        assert script in text, name


def test_lean_context_skill_exists_and_is_short():
    text = (PLUGIN / "skills" / "lean-context" / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert "name: lean-context" in front
    assert "description:" in front
    assert len(text.splitlines()) <= 60


def test_plugin_version_bumped():
    data = json.loads(
        (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert data["version"] == "0.2.0"
    assert "handoff" in data["description"]
```

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: the three touched tests FAIL.

- [ ] **Step 2: Write `plugin/commands/handoff.md`**

```markdown
---
description: Write the per-branch handoff file (task, git state, done, next, files, commands, open questions) so the next session can continue from it after /clear
---

Write the handoff for the current branch. It is gitignored, per work tree, and
the next session on this branch loads it automatically on start.

1. Durable first. Ask: did this session produce something that outlives it? A
   finding belongs in `knowledge/`, a locked decision in an ADR under
   `knowledge/decisions/`, a change of approach in the plan under
   `docs/superpowers/plans/`. Write those now; the handoff only links to them.
2. Get the path and the generated State section:

   python "${CLAUDE_PLUGIN_ROOT}/scripts/handoff.py" path
   python "${CLAUDE_PLUGIN_ROOT}/scripts/handoff.py" state

   (Fallback if the variable is not expanded:
   `~/.claude/skills/claude-kit/scripts/handoff.py`.)
3. Write the file at that path with exactly these sections, in this order:

   # Handoff: <branch>

   - **Written:** <YYYY-MM-DDTHH:MM> by /handoff
   - **Spec / plan:** <path or "none">

   ## Task
   One paragraph: what is being built and why. No references to this chat.

   <paste the State section verbatim>

   ## Done this session
   ## Next
   Ordered, concrete steps in the voice of a plan: exact paths and commands.
   ## Files that matter
   `path`: why.
   ## Commands that work
   Exact commands verified this session, in a fenced block.
   ## Open questions
   ## Moved to durable homes
   Links from step 1, or "nothing".

   Keep it under 80 lines. If Next has more than 8 steps, they belong in the plan
   file; link it and keep the first 3 here.
4. End your reply with the path and this sentence: "Run `/clear` to start fresh;
   the next session loads this handoff automatically."
```

- [ ] **Step 3: Write `plugin/skills/lean-context/SKILL.md`**

```markdown
---
name: lean-context
description: Use before exploring a codebase, reading files, or running anything with long output (tests, builds, logs, git). Keeps the main context small so every later turn stays cheap.
---

# Lean context

The cost of a session is context size times turn count. Everything a tool
returns stays in context for every later turn. Exploration output that was
needed once is the biggest avoidable cost, so read narrowly and keep the main
thread for conclusions.

## Rules

1. **Decide what you need before reading.** A symbol, a line range, or the
   shape of a file. For an unknown file, check its line count first, then read
   a range. Read a file whole only when it is under about 200 lines.
   Example: `wc -l src/app.ts`, then `sed -n '120,180p' src/app.ts`.
2. **Search, don't sweep.** `grep -n` with two or three lines of context and a
   cap; never chain `cat` over several files to "get an overview".
   Example: `grep -n -C2 'createUser' -r src | head -40`.
3. **Broad questions go to an Explore subagent.** "Every caller of X", "how does
   subsystem Y fit together": ask for conclusions plus `file:line` pointers,
   not dumps. The subagent's context is discarded; yours stays lean.
4. **Long output goes to a file first.** Redirect tests, builds and logs to the
   scratchpad, then `tail` and `grep` for failures. The full log stays on disk
   if it is needed later.
   Example: `pnpm test > "$SCRATCH/test.log" 2>&1; tail -40 "$SCRATCH/test.log"`.
5. **Never echo what you just wrote**, and never re-read a file to confirm an
   edit; the tool result already confirmed it.
6. **Write down what you learned** in the plan or the handoff instead of
   re-deriving it later in this session or the next one.
7. **Watch the meter.** The status line shows context size; a nudge appears at
   300k tokens and every 100k after. Finish the current step, run `/handoff`,
   then `/clear`.

## Why

Measured across 67 sessions: Bash was 82% of tool output, and cat, sed, grep,
ls and find sweeps were most of that. Re-reads of the same file were rare; the
waste was whole files read into a context that then lived for hundreds of
turns. Details: `conventions/session-hygiene.md` in the kit.
```

- [ ] **Step 4: Update `plugin/.claude-plugin/plugin.json`**

```json
{
  "name": "claude-kit",
  "version": "0.2.0",
  "license": "MIT",
  "description": "Workspace conventions as a plugin: /new-project and /adopt-conventions scaffolding, /handoff with session-start injection, context nudge and status line, lean-context skill, token report, spec renderer + index hook, worktree audit, supabase-cli skill."
}
```

- [ ] **Step 5: Run the tests, commit**

Run: `pytest tests/test_plugin_manifest.py -v` → all PASS.

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/commands/handoff.md plugin/skills/lean-context/SKILL.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "Add /handoff command, lean-context skill; bump plugin to 0.2.0"
```

---

### Task 9: Templates and scaffolder

**Files:**
- Modify: `plugin/templates/project/.gitignore`, `plugin/templates/project/CLAUDE.md`,
  `plugin/scripts/scaffold.py` (the adopt reminder near line 185)
- Test: `tests/test_scaffold.py`

- [ ] **Step 1: Write the failing tests** (append to `tests/test_scaffold.py`)

```python
def test_new_project_ignores_handoffs_and_points_at_session_hygiene(tmp_path):
    result = run_script(SCRIPT, "--name", "demo", "--stack", "node", "--parent", str(tmp_path))
    assert result.returncode == 0, result.stderr
    gitignore = (tmp_path / "demo" / ".gitignore").read_text("utf-8")
    assert ".claude/handoffs/" in gitignore
    claude_md = (tmp_path / "demo" / "CLAUDE.md").read_text("utf-8")
    assert "lean-context" in claude_md and "/handoff" in claude_md


def test_adopt_reminder_mentions_handoffs(repo):
    result = run_script(SCRIPT, "--adopt", "--stack", "node", "--dest", str(repo))
    assert result.returncode == 0, result.stderr
    assert ".claude/handoffs/" in result.stdout
```

(`repo` fixture in that file already has a pre-existing `.gitignore`, so the
reminder line is printed.)

Run: `pytest tests/test_scaffold.py -v` → the two new tests FAIL.

- [ ] **Step 2: Edit the templates**

`plugin/templates/project/.gitignore`: after the `.claude/worktrees/` line add:

```
# Session handoff files (claude-kit): per branch, never committed
.claude/handoffs/
```

`plugin/templates/project/CLAUDE.md`, under `## Pointers`, add a fourth bullet:

```
- Session hygiene: use `claude-kit:lean-context` when exploring; `/handoff` before `/clear`.
```

- [ ] **Step 3: Edit `plugin/scripts/scaffold.py`**

Replace the reminder line:

```python
    if Path(".gitignore") in skipped:
        print(
            "check .gitignore contains: docs/superpowers/**/*.html, .env* "
            "and .claude/handoffs/"
        )
```

- [ ] **Step 4: Run tests, commit**

Run: `pytest tests/test_scaffold.py tests/test_templates.py -v` → all PASS
(`test_adopt_creates_only_missing_files_and_never_commits` still finds
`docs/superpowers/**/*.html` in the output).

```powershell
ruff check plugin tests; ruff format plugin tests
git add plugin/templates plugin/scripts/scaffold.py tests/test_scaffold.py
git commit -m "Templates: ignore .claude/handoffs and point at session hygiene"
```

---

### Task 10: Convention, ADRs, README and CLAUDE.md

**Files:**
- Create: `conventions/session-hygiene.md`,
  `knowledge/decisions/0008-handoff-is-gitignored-per-branch.md`,
  `knowledge/decisions/0009-no-service-backed-memory.md`
- Modify: `conventions/README.md`, `CLAUDE.md`, `README.md`,
  `knowledge/decisions/README.md`
- Test: `tests/test_docs.py` (existing link check; no new test code)

- [ ] **Step 1: Write `conventions/session-hygiene.md`**

```markdown
# Session hygiene

How a working session starts, how long it runs, and how it ends, so that every
turn stays cheap without losing anything a later session needs.

## The cost model

A session's cost is **context size times turn count**. Every turn re-sends the
whole context, and everything a tool returns stays in it. Measured across 67
sessions in five repos before this convention existed:

| Observation | Value |
|---|---|
| Average context per API call | 260k tokens |
| Median assistant turns per session | 181 (max 704) |
| Context at the end of the longest sessions | 300k to 850k tokens |
| Share of tool output from Bash | 82%, mostly cat / sed / grep / ls / find |
| Same-file re-reads within a session | 7 in total |

Sessions ran long because starting fresh lost everything except `CLAUDE.md`.
Simulating "restart with a 45k-token handoff at 300k" cut input tokens by 42%;
at 150k, by 65%.

## Principles

1. **A session is a unit of work, not a day.** End it at a natural boundary: a
   task done, a plan step complete, a decision made.
2. **Restarting must be cheap.** A handoff file carries the in-flight state; the
   knowledge layer, ADRs and plans carry everything durable. Nothing important
   lives only in the conversation.
3. **Keep the main context for conclusions.** Explore narrowly, delegate sweeps,
   send long output to disk first (the `claude-kit:lean-context` skill).
4. **Make growth visible.** The status line shows context size at zero cost; a
   nudge at 300k tokens (then every 100k) says when to hand off.

## The handoff file

`<work-tree>/.claude/handoffs/<branch>.md`, gitignored, under 80 lines. Written
by `/handoff`; its State section is refreshed automatically at session end; it is
injected automatically on the next `startup` or `clear` on the same branch while
younger than seven days. Sections: Task, State (generated), Done this session,
Next, Files that matter, Commands that work, Open questions, Moved to durable
homes.

What does **not** belong in it: findings (go to `knowledge/`), decisions (go to
an ADR), changes of plan (go to the plan). The `/handoff` command asks about
these first. `.claude/handoffs/` may be emptied at any time; a removed worktree
takes its handoffs with it.

## The routine

1. Start: read the injected handoff, verify its State against `git status`.
2. Work with the `lean-context` skill; keep an eye on the status line.
3. When the nudge appears, finish the current step.
4. `/handoff`, then `/clear`. Repeat.

## Re-measuring

`python <kit>/plugin/scripts/token-report.py --all` prints the numbers above for
every project on this machine, plus the restart simulation. Run it after a few
weeks of use and compare with the table at the top.

## Definition of done

- A handoff exists whenever a branch is mid-flight at the end of a session.
- No session ends above the nudge threshold without a handoff.
- A fresh session on the branch can continue from the handoff alone.
- Findings, decisions and plan changes made during the session are in their
  durable homes, not only in the handoff.
```

- [ ] **Step 2: Write the two ADRs**

`knowledge/decisions/0008-handoff-is-gitignored-per-branch.md`:

```markdown
# ADR 0008: Session handoff files are gitignored, per branch, per work tree

- **Status:** accepted
- **Date:** 2026-09-18

## Context
Sessions restart cheaply only if in-flight state carries over. That state is
fast-moving and branch-specific: exactly what the project memory convention keeps
out of `CLAUDE.md`. It could be committed on the feature branch or kept local.

## Decision
The handoff lives at `<work-tree>/.claude/handoffs/<branch>.md` and is
gitignored. `/handoff` writes it; the SessionEnd hook refreshes its State; the
SessionStart hook injects it for seven days. Durable content goes to
`knowledge/`, ADRs or the plan, never only to the handoff.

## Consequences
No PR diff noise and no cleanup step at merge; a removed worktree takes its
handoffs with it. A machine switch mid-feature loses the handoff (the plan and
git history remain). Rejected: committing it on the feature branch.
```

`knowledge/decisions/0009-no-service-backed-memory.md`:

```markdown
# ADR 0009: No service-backed memory in the kit

- **Status:** accepted
- **Date:** 2026-09-18

## Context
Token spend was attributed to rediscovery, and a knowledge-graph memory
(database plus an extraction model on every write) was considered. Measurement
showed same-file re-reads are rare; the loss is carry-over between sessions and
context that grows for hundreds of turns.

## Decision
The kit stays files plus Python hooks: a handoff file for carry-over, the
knowledge layer for durable facts, no daemon, no index service, no ingestion
cost.

## Consequences
Zero setup on a new machine and nothing to keep running. Recall across projects
relies on the knowledge layer and Claude Code's own memory directory. Revisit
only if a re-measurement shows recall, not carry-over, as the dominant cost.
```

Add both rows to `knowledge/decisions/README.md`:

```
| [0008](0008-handoff-is-gitignored-per-branch.md) | Session handoff files are gitignored, per branch, per work tree | accepted | 2026-09-18 |
| [0009](0009-no-service-backed-memory.md) | No service-backed memory in the kit | accepted | 2026-09-18 |
```

- [ ] **Step 3: Update `conventions/README.md`**

Add a sixth table row:

```
| [Session hygiene](session-hygiene.md) | How sessions start, how long they run, and how they end: handoff files, the context meter, lean exploration. |
```

Append to the "How they fit together" paragraph: "Session hygiene is the
**cadence**: it keeps each working session short and cheap while the other five
keep the work correct, and it decides what a session leaves behind (a handoff)
versus what goes into the knowledge base, the decision log, or the plan."

- [ ] **Step 4: Update the workspace `CLAUDE.md`**

In the conventions bullet list add, after the project memory bullet:

```
- **[Session hygiene](conventions/session-hygiene.md)** — sessions are units of
  work: a gitignored per-branch handoff file (`/handoff`, injected on the next
  start), a context meter with a nudge at 300k tokens, and lean exploration.
```

Add a new section after "## Environment":

```
## Token discipline

The cost of a session is context size times turn count. Before exploring or
running anything with long output, use the `claude-kit:lean-context` skill. When
the context nudge appears, finish the current step, run `/handoff`, then `/clear`.
Details: [conventions/session-hygiene.md](conventions/session-hygiene.md).
```

In the "Building a new feature" section, after the paragraph on cleaning up,
add one sentence: "The normal end of a working session on a feature is
`/handoff` then `/clear`; the next session on the branch starts from the handoff."

- [ ] **Step 5: Update `README.md`**

Add the sixth playbook bullet under "conventions/":

```
  - [Session hygiene](conventions/session-hygiene.md) — short sessions, a
    per-branch handoff file, a context meter, lean exploration.
```

Rewrite the `plugin/` bullet's list of contents: "a Claude Code plugin: the
`supabase-cli` and `lean-context` skills, the spec → HTML renderer, the
`token-report.py` measurement script, a status line, and five hooks (auto-render
specs/plans after edits; report leftover worktrees, inject the branch handoff and
nudge past a context threshold at the right moments; snapshot git state at
session end)." Add to the commands sentence: "`/handoff` writes the per-branch
handoff file before you `/clear`." Add to the installer sentence: "It also adds
the kit's status line to `~/.claude/settings.json` when none is configured."

- [ ] **Step 6: Run the docs test and the whole suite, commit**

```powershell
pytest tests/test_docs.py -v     # link check covers the new docs
pytest
ruff check plugin tests; ruff format --check plugin tests
git add conventions CLAUDE.md README.md knowledge/decisions
git commit -m "Add session hygiene convention, ADRs 0008-0009, README and CLAUDE.md pointers"
```

---

### Task 11: Verification, PR, cleanup

**Files:** none new.

- [ ] **Step 1: Full automated verification**

```powershell
ruff check plugin tests
ruff format --check plugin tests
pytest
```

Expected: all green. Paste the summary line in the PR.

- [ ] **Step 2: Private-name scan** (workspace rule; the kit is public)

```powershell
git grep -n -i -E "$env:USERNAME" -- . ':!*.html' ':!LICENSE'
```

Expected: no output. Fix any hit before continuing.

Also grep for the names of the private project folders that sit beside this checkout under `Github/`; do not write those names into this file.

- [ ] **Step 3: Manual checks in a real project repo** (spec success criteria 2)

The plugin is loaded from the junction, so the worktree's files are not live.
Either merge first and re-check, or temporarily run
`plugin\install.ps1` from the worktree path (it refuses if the junction points
elsewhere; remove and re-create the junction, then restore it afterwards). Then,
in any project repo:

1. Start a session, run `/handoff`. Confirm `.claude/handoffs/<branch>.md` exists
   with all sections and is under 80 lines.
2. Run `/clear`. Confirm the new session's context begins with the `<handoff>`
   block (ask Claude "what does the handoff say?").
3. Start a session with `CLAUDE_KIT_NUDGE_AT=20000` in the environment, do
   enough work to pass 20k tokens, and confirm exactly one nudge appears in the
   conversation and one system message; the next prompt shows none.
4. Confirm the status line shows `ctx …k/1M …% | $… | <branch>` after the first
   reply. If the `systemMessage` key placement (top level) turns out not to
   display, move it inside `hookSpecificOutput` and rerun
   `tests/test_context_nudge.py` after updating its assertion.
5. Run `python plugin/scripts/token-report.py --all` and confirm the numbers
   match the spec's Purpose table within rounding.

Record the outcome of each check in the PR description.

- [ ] **Step 4: Update the spec and plan status, open the PR**

Set `- **Status:** implemented` in
`docs/superpowers/specs/2026-09-18-session-hygiene-design.md` and in this plan;
commit ("Mark the session hygiene spec and plan implemented"). Push the branch
and open the PR with `gh pr create`, body: summary, the verification evidence
from Steps 1 to 3, and the attribution line from the session reminder.

- [ ] **Step 5: Finish the branch**

After merge, use `superpowers:finishing-a-development-branch`: remove and prune
the worktree, delete the branch locally and on the remote, run
`plugin\install.ps1` once from the `main` checkout so the junction and the status
line are in place, and start a new session to confirm the session-start hooks
load (the worktree audit should report nothing).
```
