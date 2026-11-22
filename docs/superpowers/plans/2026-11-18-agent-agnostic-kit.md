# Agent-agnostic kit Implementation Plan

- **Status:** approved
- **Date:** 2026-11-18
- **Frozen:** none (spec D10: nothing is frozen)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the kit run in Mistral Vibe, Codex and Cursor (rules, kit map, vault pointer, handoff, skills, gates) while Claude Code sees exactly what it sees today.

**Architecture:** The kit root's rules move to `AGENTS.md` with `CLAUDE.md` as an `@AGENTS.md` stub. A new hook runner, `plugin/hooks/run.py`, reads the existing `plugin/hooks/hooks.json`, runs the portable hooks for a non-Claude agent and prints their context in that agent's JSON shape, prefixed by a tool-mapping reference. `plugin/install.py --agent` links the kit skills, generated command-wrapper skills and a vendored superpowers copy into `~/.agents/skills/` and merges the runner into the agent's user hook file.

**Tech Stack:** Python 3.11 standard library (`argparse`, `json`, `re`, `shlex`, `shutil`, `subprocess`, `tomllib` in tests only), pytest, ruff, PowerShell 5.1 wrapper, Markdown.

**Spec:** `docs/superpowers/specs/2026-11-18-agent-agnostic-kit-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-18-agent-agnostic-kit-design.md`

## Context for the executor

This repo is claude-kit, a Claude Code plugin under `plugin/`. Setup once:
`pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks: `pytest`,
`ruff check plugin tests`, `ruff format --check plugin tests`. Run plain
`pytest` (not `-q`; `pyproject.toml` already adds `-q`) to see the pass count.
Read `knowledge/kit-dev-gotchas.md` before editing tests (88-character lines,
edit test files with the Edit tool, never through a bash heredoc).

`tests/helpers.py` exports `PLUGIN`, `REPO`, `load_module(path, name)` (imports
a hyphenated script), `clean_env(**extra)` (os.environ without `CLAUDE_KIT_*`)
and `run_script(script, *args, stdin="", cwd=None, env=None)` (runs
`sys.executable script args`, 60-second timeout, UTF-8 text). Scripts follow
`plugin/scripts/docker-disk.py`: `#!/usr/bin/env python3`, module docstring
with usage, `from __future__ import annotations`, `argparse`,
`main(argv: list[str] | None = None) -> int`, `sys.stdout.reconfigure(encoding="utf-8")`
guarded by `hasattr`. Hooks always exit 0 and print errors to stderr prefixed
`[claude-kit]` (ADR 0007).

Facts checked in the repo:
- `plugin/hooks/hooks.json` registers, under `SessionStart` in this order:
  `worktree_audit.py`, `lean_context_inject.py`, `kit_map_inject.py`,
  `workspace_rules_inject.py`, `vault_inject.py`, `grill_inject.py`, and
  `handoff_inject.py` (group `"matcher": "startup|clear"`); under `Stop`:
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py" "${CLAUDE_PROJECT_DIR}/docs/superpowers"`.
  Every command starts with `python "${CLAUDE_PLUGIN_ROOT}/...`.
  `worktree_audit.py` reads `Path.cwd()`; `handoff_inject.py` reads the event
  `cwd`; `worktree_audit.py` and `handoff_inject.py` print plain text, the
  other SessionStart hooks print `{"hookSpecificOutput": {...,
  "additionalContext": ...}}`; `spec-index.py` prints nothing on stdout.
- `kit_map_inject.py` output starts `Kit map (claude-kit). Kit root: ...`.
- `plugin/install.py` has `PLUGIN`, `is_link(path)`, `points_at_plugin(link)`,
  `make_link(link)` (junction via `cmd /c mklink /J` on Windows, symlink
  elsewhere), `install_link`, `install_statusline`, `check_python`,
  `warn_missing_tools`, `main`. Keep it parseable by Python 3.8.
- In PowerShell a parameter named `$Home` fails ("Cannot overwrite variable
  Home because it is read-only or constant"); declare
  `[Alias("Home")][string]$HomeDir` instead.
- `tests/test_install.py` removes the links it creates in a fixture: a
  recursive delete of `tmp_path` could follow a junction into `plugin/`.
  Every new installer test must leave no link behind (Task 5 fixture).
- `tests/test_skill_size.py::test_every_reference_file_is_read_by_a_command`
  fails for a `plugin/references/*.md` that no command or skill names.
- `tests/test_docs.py::test_relative_markdown_links_resolve` checks every
  tracked `.md` outside `SKIP_DIRS`; upstream superpowers'
  `writing-skills/references/anthropic-best-practices.md` has link-shaped
  examples that do not resolve.
- `tests/test_docs.py::test_setup_guide_lists_every_env_switch` requires
  every `CLAUDE_KIT_[A-Z_]*` name in tracked `plugin/` text to appear in
  `docs/setup.md`.
- Upstream superpowers 7.0.2 lives on this machine at
  `~/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.2`
  (`skills/`, `LICENSE`, `package.json` with `"version"`). The kit references
  11 superpowers skills; their closure adds `writing-skills`.

## Global Constraints

- Claude's behaviour must not change: `plugin/hooks/hooks.json`, every
  `plugin/skills/*/SKILL.md` frontmatter, and every hook's output with
  `CLAUDE_KIT_AGENT` unset stay as on `origin/main`, apart from the
  workspace-rules header naming `AGENTS.md`.
- Standard library only, Python 3.11, in `run.py` and the new scripts.
- Never run `plugin/install.py` or `install.ps1` from a test without a
  temporary `--skills-dir`/`--home` under `tmp_path`.
- This repo is public: no machine username, private repo name or absolute
  machine path in tracked files (`VERSION` included).
- Every linked skill folder's `SKILL.md` `name` equals the folder name and
  matches `^[a-z0-9-]+$`.
- Claude-only hook set: `{context_nudge.py, handoff_snapshot.py, precompact_keep.py, on_spec_edit.py}`.

## Review Focus

- An agent's user hook file that is malformed JSON: the installer exits 1 and changes nothing (Task 5 test `test_malformed_hook_file_changes_nothing`).
- Empty or non-JSON stdin to `run.py`: treated as `{}`, the current directory is the cwd, hooks still run (Task 2 test `test_empty_or_bad_stdin`).
- A project `CLAUDE.md` with an `@` import of a missing file: the line is kept as written, no error (Task 2 test `test_project_claude_md_injected_when_no_agents_md`).
- A kit skill renamed or removed after an earlier install: its dangling link in `~/.agents/skills/` is removed on rerun (Task 5 test `test_dangling_kit_link_removed`).
- An agent started in a subfolder of a git repo, or in a folder outside any repo: the project directory is the git top level, else the folder itself (Task 2 test `test_project_dir_is_git_top_level`).

## Decisions this plan makes (answers to the spec gate's plan questions)

- **Commands are parsed, not shelled.** `run.py` splits each `hooks.json`
  command with `shlex.split` (POSIX mode), then replaces `${CLAUDE_PLUGIN_ROOT}`
  and `${CLAUDE_PROJECT_DIR}` inside each token with forward-slash paths, and
  swaps a leading `python` or `python3` token for `sys.executable` (the
  interpreter running `run.py`, which is the installer's `--python`, since the
  installed hook command starts with it). (Task 2)
- **Script cwd.** Each script runs with its process cwd set to the event's
  `cwd` (else `run.py`'s own cwd), which lies in the project. (Task 2)
- **Project directory** is `git -C <cwd> rev-parse --show-toplevel` when that
  succeeds, else the cwd; it feeds `CLAUDE_PROJECT_DIR`,
  `${CLAUDE_PROJECT_DIR}` and the project `CLAUDE.md`/`AGENTS.md` lookup.
  (Task 2)
- **Missing `source`** becomes `startup` for every agent. (Task 2)
- **No cap** on the joined context; each script keeps its own size limit.
  (Task 2)
- **Extra pieces only at SessionStart.** The tool mapping and project
  `CLAUDE.md` are added for `--event SessionStart` only, so `Stop` prints
  nothing unless a Stop script prints. (Task 2)
- **Workspace-rules header for non-Claude agents** (any repo it injects in):
  `Workspace rules (claude-kit, from <root>/<file>). Your agent did not load them for this repo; follow them as you would an AGENTS.md. Relative links resolve against <root>.`
  Claude's header is today's with `CLAUDE.md` replaced by the file read.
  (Task 1)
- **`make_link` gains `target: Path = PLUGIN`.** (Task 5)
- **`--home`** (default `Path.home()`) is the base of every default:
  `--agent claude` uses `<home>/.claude/skills` and `<home>/.claude/settings.json`,
  the others `<home>/.agents/skills`; an explicit `--skills-dir` or
  `--settings` wins. (Task 5)
- **Dangling kit links are removed** on rerun: a link in the skills dir
  whose target lies under the kit's `plugin/skills/`, `plugin/agent-skills/`
  or `vendor/superpowers/skills/` and no longer exists. A link whose existing
  target lies under those roots but is another folder (a skill that moved
  between roots) is relinked and reported as `Relinked <name>`. (Task 5)
- **Managed blocks.** `~/.vibe/hooks.toml` holds the kit entries between
  `# >>> claude-kit hooks (managed by plugin/install.py) >>>` and
  `# <<< claude-kit hooks <<<`; the user `AGENTS.md` block sits between
  `<!-- claude-kit:begin (managed by plugin/install.py) -->` and
  `<!-- claude-kit:end -->`. In the JSON hook files a kit entry is one whose
  command contains `/plugin/hooks/run.py"` and `--agent `. All new file
  contents are computed before anything is written; a malformed JSON hook
  file aborts the install with exit 1 and no change. (Task 5)
- **SC1 captures** use the same environment and, for each checkout, the
  checkout itself as the kit-repo project and one shared temporary repo
  outside the kit as the other project; both checkout roots are replaced by
  `<kit>` in both captures. (Task 8)

---

### Task 1: Rules move to `AGENTS.md`; workspace-rules hook reads it and serves non-Claude agents

**Files:**
- Create: `AGENTS.md` (via `git mv CLAUDE.md AGENTS.md`)
- Modify: `CLAUDE.md` (recreated as the one line `@AGENTS.md`)
- Modify: `plugin/hooks/workspace_rules_inject.py`
- Modify: `docs/setup.md` (one sentence under `## Switches`)
- Test: `tests/test_workspace_rules_inject.py`
- Test: `tests/test_docs.py`, `tests/test_ship_many_command.py`, `tests/test_spec_gate_skill.py`

**Depends on:** none

**Interfaces:**
- Produces: `workspace_rules_inject.rules_file(root: Path) -> Path` (`root/"AGENTS.md"` if it is a file, else `root/"CLAUDE.md"`); `build(root: Path, agent: str = "") -> str`; `toplevel(project: Path) -> Path | None`; `child_repo(project: Path, root: Path) -> bool`. Env var `CLAUDE_KIT_AGENT` (`vibe`, `codex`, `cursor`, or unset).

- [ ] **Step 1: Move the rules**

Run: `git mv CLAUDE.md AGENTS.md`, then write `CLAUDE.md` containing exactly `@AGENTS.md` and one newline.
Then `git add CLAUDE.md`.
Expected: `git status` shows staged `new file: AGENTS.md` and `modified: CLAUDE.md` (git reports no rename because `CLAUDE.md` still exists), and the moved text is unchanged: `python -c "import pathlib,subprocess; old=subprocess.run(['git','show','HEAD:CLAUDE.md'],capture_output=True,text=True,encoding='utf-8').stdout; print(old==pathlib.Path('AGENTS.md').read_text(encoding='utf-8'))"` prints `True` (text-mode reads, so a CRLF working copy compares equal).

- [ ] **Step 2: Point the existing doc tests at `AGENTS.md`**

In `tests/test_docs.py` replace every read of `REPO / "CLAUDE.md"` with `REPO / "AGENTS.md"` (in `test_claude_md_script_paths_exist`, `_claude_md_section`, `test_learnings_capture_is_part_of_finishing`, `test_claude_md_has_rules_moved_from_memory`) and `"CLAUDE.md"` with `"AGENTS.md"` in the name tuples of `test_docs_wire_ship_fast` and `test_docs_wire_ship_fast_interview`. Same in `tests/test_ship_many_command.py::test_docs_wire_ship_many` and `tests/test_spec_gate_skill.py::test_docs_wire_the_gate` (`text("AGENTS.md")`). Add to `tests/test_docs.py`:

```python
def test_claude_md_is_the_agents_stub():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.strip() == "@AGENTS.md"
    assert len(text.splitlines()) == 1
```

- [ ] **Step 3: Write the failing workspace-rules tests**

In `tests/test_workspace_rules_inject.py`: change `test_outside_the_kit_injects_rules_without_kit_dev` to assert `f"{REPO.as_posix()}/AGENTS.md" in text`; give `make_kit` a keyword `agents_md=None` that writes `kit/AGENTS.md` when not `None`; add:

```python
AGENTS = ("vibe", "codex", "cursor")
RULES = "# Rules\n\n## How we work\n\nx\n"


def git_repo(path):
    subprocess.run(GIT + ["init", "-q", str(path)], check=True)
    subprocess.run(GIT + ["-C", str(path), "add", "-A"], check=True)
    subprocess.run(GIT + ["-C", str(path), "commit", "-qm", "i"], check=True)


def test_rules_come_from_agents_md(tmp_path):
    kit = make_kit(tmp_path, "@AGENTS.md\n", agents_md=RULES)
    other = tmp_path / "other"
    other.mkdir()
    hook = kit / "plugin" / "hooks" / HOOK.name
    text = context(run(hook, CLAUDE_PROJECT_DIR=str(other)))
    assert f"{kit.as_posix()}/AGENTS.md)" in text
    assert "as you would a CLAUDE.md" in text
    assert "## How we work" in text


def test_stub_gives_same_rules_as_full_claude_md(tmp_path):
    stub = make_kit(tmp_path / "a", "@AGENTS.md\n", agents_md=RULES)
    full = make_kit(tmp_path / "b", RULES)
    other = tmp_path / "other"
    other.mkdir()
    texts = []
    for kit in (stub, full):
        hook = kit / "plugin" / "hooks" / HOOK.name
        texts.append(context(run(hook, CLAUDE_PROJECT_DIR=str(other))))
    assert texts[0].split("\n\n", 1)[1] == texts[1].split("\n\n", 1)[1]


def test_agent_gets_rules_in_child_repo_inside_kit(tmp_path):
    kit = make_kit(tmp_path, "@AGENTS.md\n", agents_md=RULES)
    git_repo(kit)
    child = kit / "child"
    child.mkdir()
    (child / "README.md").write_text("c\n", encoding="utf-8")
    git_repo(child)
    hook = kit / "plugin" / "hooks" / HOOK.name
    assert run(hook, CLAUDE_PROJECT_DIR=str(child)).stdout == ""
    for agent in AGENTS:
        env = {"CLAUDE_PROJECT_DIR": str(child), "CLAUDE_KIT_AGENT": agent}
        text = context(run(hook, **env))
        assert "## How we work" in text
        assert "follow them as you would an AGENTS.md" in text


def test_agent_silent_in_kit_root_subfolder_and_worktree(tmp_path):
    kit = make_kit(tmp_path, "@AGENTS.md\n", agents_md=RULES)
    git_repo(kit)
    worktree = tmp_path / "wt"
    subprocess.run(
        GIT + ["-C", str(kit), "worktree", "add", "-q", str(worktree)], check=True
    )
    hook = kit / "plugin" / "hooks" / HOOK.name
    for agent in AGENTS:
        for project in (kit, kit / "plugin", worktree):
            env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_KIT_AGENT": agent}
            assert run(hook, **env).stdout == "", (agent, project)
    for agent in AGENTS:
        for project in (REPO, REPO / "plugin"):
            env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_KIT_AGENT": agent}
            assert run(**env).stdout == "", (agent, project)
```

- [ ] **Step 4: Run the tests to see them fail**

Run: `pytest tests/test_workspace_rules_inject.py tests/test_docs.py tests/test_ship_many_command.py tests/test_spec_gate_skill.py -o addopts=""`
Expected: FAIL in `test_outside_the_kit_injects_rules_without_kit_dev`, `test_project_dir_from_stdin`, `test_rules_come_from_agents_md`, `test_stub_gives_same_rules_as_full_claude_md`, `test_agent_gets_rules_in_child_repo_inside_kit` (the hook still reads the one-line stub `CLAUDE.md`, no agent mode); the doc tests pass.

- [ ] **Step 5: Implement in `plugin/hooks/workspace_rules_inject.py`**

`kit_root()` is unchanged (it still checks `CLAUDE.md`). `rules(root)` reads `rules_file(root)`. `build(root, agent)` uses the file's name in the header: with `agent == ""` only the path changes, to `f"from {where}/{rules_file(root).name})"`; the rest of Claude's header stays byte-identical, including "as you would a CLAUDE.md"; with an agent it is the non-Claude header from "Decisions this plan makes". `toplevel()` runs `git -C <project> rev-parse --show-toplevel` (10-second timeout, `None` on failure). `child_repo(project, root)` is true when `toplevel(project)` is not `None`, is not `root` (compare with `same`), is inside `root`, and `in_kit_worktree(project, root)` is false. In `main()`, with `agent = os.environ.get("CLAUDE_KIT_AGENT", "")`:

```python
if inside(project, root):
    inject = bool(agent) and child_repo(project, root)
else:
    inject = not in_kit_worktree(project, root)
```

Update the module docstring: rules come from `AGENTS.md` when present; with `CLAUDE_KIT_AGENT` set (by `plugin/hooks/run.py`) child repos inside the kit folder get them too (ADR 0050).

- [ ] **Step 6: Document `CLAUDE_KIT_AGENT`**

Add under `## Switches` in `docs/setup.md` one sentence: `CLAUDE_KIT_AGENT` is not a switch to set by hand; `plugin/hooks/run.py` sets it to `vibe`, `codex` or `cursor` for the hooks it runs.

- [ ] **Step 7: Run the tests to see them pass**

Run: `pytest tests/test_workspace_rules_inject.py tests/test_docs.py tests/test_ship_many_command.py tests/test_spec_gate_skill.py -o addopts=""`
Expected: all PASS, including `test_size_cap` (the header length is unchanged).

- [ ] **Step 8: Commit**

```bash
git add AGENTS.md CLAUDE.md plugin/hooks/workspace_rules_inject.py docs/setup.md tests/test_workspace_rules_inject.py tests/test_docs.py tests/test_ship_many_command.py tests/test_spec_gate_skill.py
git commit -m "feat: workspace rules live in AGENTS.md; CLAUDE.md imports it"
```

### Task 2: Tool mapping and the cross-agent hook runner

**Files:**
- Create: `plugin/references/agent-tools.md`
- Create: `plugin/hooks/run.py`
- Modify: `tests/test_skill_size.py` (reference files may be read by a hook)
- Test: `tests/test_run_hooks.py`

**Depends on:** none

**Interfaces:**
- Produces (module `plugin/hooks/run.py`): `PLUGIN: Path` (`Path(__file__).resolve().parents[1]`); `TOOLS = "references/agent-tools.md"`; `CLAUDE_ONLY: frozenset[str]` (Global Constraints set); `TIMEOUT = 10`; `normalise(raw: str, event: str) -> dict` (keys `cwd`, `source`, `hook_event_name`); `project_dir(cwd: Path) -> Path`; `commands(hooks: dict, event: str, source: str, plugin: Path, project: Path) -> list[list[str]]`; `run_one(argv: list[str], stdin: str, env: dict[str, str], cwd: Path, timeout: float = TIMEOUT) -> str`; `contribution(stdout: str) -> str`; `tool_mapping(plugin: Path) -> str`; `project_instructions(project: Path) -> str`; `render(agent: str, event: str, text: str) -> str`; `main(argv: list[str] | None = None) -> int`. CLI: `run.py --agent {vibe,codex,cursor} --event {SessionStart,Stop}`.

- [ ] **Step 1: Write the failing tests in `tests/test_run_hooks.py`**

```python
import json
import shutil
import subprocess
import sys

import pytest
from helpers import PLUGIN, clean_env, load_module

RUN = PLUGIN / "hooks" / "run.py"
TOOLS = PLUGIN / "references" / "agent-tools.md"
AGENTS = ("vibe", "codex", "cursor")
SCRIPTS = {
    "json_ctx.py": (
        "import json, os, sys\n"
        "e = json.load(sys.stdin)\n"
        "t = f\"json src={e['source']} agent={os.environ['CLAUDE_KIT_AGENT']}\"\n"
        "print(json.dumps({'hookSpecificOutput': {'additionalContext': t}}))\n"
    ),
    "plain.py": "import os\nprint('plain cwd=' + os.path.basename(os.getcwd()))\n",
    "context_nudge.py": "print('CLAUDE ONLY')\n",
    "fails.py": "import sys\nprint('partial')\nsys.exit(3)\n",
    "matched.py": "print('matched')\n",
    "argv.py": "import sys\nprint('stop ' + sys.argv[1])\n",
}


def group(script, matcher=None, arg=""):
    command = f'python "${{CLAUDE_PLUGIN_ROOT}}/hooks/{script}"{arg}'
    out = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        out["matcher"] = matcher
    return out


def make_kit(tmp_path, session=None):
    plugin = tmp_path / "kit" / "plugin"
    (plugin / "hooks").mkdir(parents=True)
    (plugin / "references").mkdir()
    shutil.copy(RUN, plugin / "hooks" / "run.py")
    shutil.copy(TOOLS, plugin / "references" / "agent-tools.md")
    for name, body in SCRIPTS.items():
        (plugin / "hooks" / name).write_text(body, encoding="utf-8")
    if session is None:
        session = [
            group("json_ctx.py"),
            group("plain.py"),
            group("context_nudge.py"),
            group("fails.py"),
            group("matched.py", "startup|clear"),
        ]
    stop = [group("argv.py", arg=' "${CLAUDE_PROJECT_DIR}/docs"')]
    hooks = {"hooks": {"SessionStart": session, "Stop": stop}}
    (plugin / "hooks" / "hooks.json").write_text(json.dumps(hooks), "utf-8")
    return plugin


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "proj"
    path.mkdir()
    return path


def run(plugin, agent, project, event="SessionStart", stdin=None, cwd=None):
    if stdin is None:
        stdin = json.dumps({"cwd": str(project), "source": "startup"})
    env = clean_env()
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(
        [sys.executable, str(plugin / "hooks" / "run.py")]
        + ["--agent", agent, "--event", event],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd or project,
        env=env,
        timeout=60,
    )


def context(result, agent, event="SessionStart"):
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    if agent == "vibe":
        return data["hook_specific_output"]["additional_context"]
    if agent == "codex":
        assert data["hookSpecificOutput"]["hookEventName"] == event
        return data["hookSpecificOutput"]["additionalContext"]
    return data["additional_context"]


@pytest.mark.parametrize("agent", AGENTS)
def test_each_agent_gets_its_shape(tmp_path, project, agent):
    text = context(run(make_kit(tmp_path), agent, project), agent)
    assert f"json src=startup agent={agent}" in text
    assert "plain cwd=proj" in text
    assert "matched" in text
    assert "CLAUDE ONLY" not in text
    assert "partial" not in text


def test_matcher_applies_to_source(tmp_path, project):
    plugin = make_kit(tmp_path)
    for source, seen in (("resume", False), ("clear", True)):
        stdin = json.dumps({"cwd": str(project), "source": source})
        text = context(run(plugin, "vibe", project, stdin=stdin), "vibe")
        assert ("matched" in text) is seen, source


@pytest.mark.parametrize("agent", AGENTS)
def test_missing_source_becomes_startup(tmp_path, project, agent):
    stdin = json.dumps({"cwd": str(project)})
    result = run(make_kit(tmp_path), agent, project, stdin=stdin)
    text = context(result, agent)
    assert "json src=startup" in text and "matched" in text


def test_failing_script_is_skipped_with_stderr(tmp_path, project):
    result = run(make_kit(tmp_path), "codex", project)
    assert result.returncode == 0
    assert "[claude-kit]" in result.stderr and "fails.py" in result.stderr


def test_slow_script_times_out(tmp_path, capsys):
    mod = load_module(RUN, "kit_run_hooks")
    argv = [sys.executable, "-c", "import time; time.sleep(5)"]
    assert mod.run_one(argv, "{}", clean_env(), tmp_path, timeout=1) == ""
    assert "[claude-kit]" in capsys.readouterr().err


def test_stop_expands_project_dir_and_adds_no_extras(tmp_path, project):
    result = run(make_kit(tmp_path), "codex", project, event="Stop")
    text = context(result, "codex", event="Stop")
    assert f"stop {project.resolve().as_posix()}/docs" in text
    assert "claude-kit agent tools" not in text


def test_mapping_injected_with_plugin_path(tmp_path, project):
    plugin = make_kit(tmp_path)
    text = context(run(plugin, "cursor", project), "cursor")
    assert text.startswith("# claude-kit agent tools")
    assert plugin.resolve().as_posix() in text
    assert "<plugin>" not in text
    assert "~/.claude/skills/claude-kit" in text
    assert "`code-review`" in text and "requesting-code-review" in text


def test_project_claude_md_injected_when_no_agents_md(tmp_path, project):
    (project / "CLAUDE.md").write_text(
        "proj rules\n@extra.md\n@missing.md\n", encoding="utf-8"
    )
    (project / "extra.md").write_text("extra text\n", encoding="utf-8")
    text = context(run(make_kit(tmp_path), "vibe", project), "vibe")
    assert "proj rules" in text and "extra text" in text
    assert "@missing.md" in text
    order = [text.index(s) for s in ("agent tools", "proj rules", "json src")]
    assert order == sorted(order)


def test_project_with_agents_md_not_injected(tmp_path, project):
    (project / "CLAUDE.md").write_text("proj rules\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("agents rules\n", encoding="utf-8")
    text = context(run(make_kit(tmp_path), "vibe", project), "vibe")
    assert "proj rules" not in text and "agents rules" not in text


@pytest.mark.parametrize("stdin", ["", "not json"])
def test_empty_or_bad_stdin(tmp_path, project, stdin):
    result = run(make_kit(tmp_path), "vibe", project, stdin=stdin)
    assert "plain cwd=proj" in context(result, "vibe")


def test_project_dir_is_git_top_level(tmp_path, project):
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    sub = project / "sub"
    sub.mkdir()
    stdin = json.dumps({"cwd": str(sub)})
    result = run(make_kit(tmp_path), "vibe", sub, event="Stop", stdin=stdin)
    text = context(result, "vibe", event="Stop")
    assert f"stop {project.resolve().as_posix()}/docs" in text


def test_nothing_collected_prints_nothing(tmp_path, project):
    plugin = make_kit(tmp_path)
    (plugin / "hooks" / "argv.py").write_text("pass\n", encoding="utf-8")
    result = run(plugin, "vibe", project, event="Stop")
    assert result.returncode == 0 and result.stdout == ""


def test_claude_only_set():
    mod = load_module(RUN, "kit_run_hooks")
    assert mod.CLAUDE_ONLY == {
        "context_nudge.py",
        "handoff_snapshot.py",
        "precompact_keep.py",
        "on_spec_edit.py",
    }


def test_real_hooks_json_commands(tmp_path):
    mod = load_module(RUN, "kit_run_hooks")
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text("utf-8"))
    session = mod.commands(hooks, "SessionStart", "startup", PLUGIN, tmp_path)
    assert len(session) == 7
    for argv in session:
        assert argv[0] == sys.executable
        assert (PLUGIN / "hooks").as_posix() in argv[1]
    (stop,) = mod.commands(hooks, "Stop", "startup", PLUGIN, tmp_path)
    assert stop[-1] == f"{tmp_path.as_posix()}/docs/superpowers"
```

In `tests/test_skill_size.py::test_every_reference_file_is_read_by_a_command`, add the text of `PLUGIN.glob("hooks/*.py")` to `texts`, so a reference read by a hook counts.

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_run_hooks.py tests/test_skill_size.py -o addopts=""`
Expected: FAIL (`run.py` and `agent-tools.md` do not exist).

- [ ] **Step 3: Write `plugin/references/agent-tools.md`**

It must start with the line `# claude-kit agent tools` and hold, as short sections in the style of superpowers' per-agent tool references, every rule in the spec's "Tool mapping" list, using `<plugin>` for the plugin path:
- `superpowers:<name>` and `claude-kit:<name>` mean the skill `<name>`.
- "Dispatch a subagent" / the Agent tool: the agent's subagent feature when it has one (Vibe documents subagents); with none, do the step inline as a separate pass that rereads its inputs from disk and does not rely on the conversation.
- AskUserQuestion and the app's wrap-up box: ask in chat.
- TodoWrite / the task list: the agent's own plan or todo feature, or a short checklist in chat.
- Slash commands such as `/ship`: the wrapper skill of the same name.
- `${CLAUDE_PLUGIN_ROOT}` means `<plugin>`; every `~/.claude/skills/claude-kit` path in any kit command, skill or reference also means `<plugin>`.
- The Claude Code built-in `code-review` skill (named by `ship-fast.md`): run the bundled `requesting-code-review` skill on the branch diff, then fix the findings it reports.
- Not available in this agent: `/ship-many`, the status line, `token-report.py`, `audit --user`, Claude auto-memory, and the transcript, precompact and spec-edit hooks; `/ship` and `/ship-fast` run in one session with no headless child sessions, and the Stop-time `spec-index.py` keeps the specs index current.
- One line stating the plugin path: `The kit's plugin folder is <plugin>.`

No Markdown links (the link checker would resolve them). The file must not contain the test sentinels `matched`, `partial`, `CLAUDE ONLY`, `proj rules`, `agents rules`, `json src` or `plain cwd`, which `tests/test_run_hooks.py` checks for by substring.

- [ ] **Step 4: Implement `plugin/hooks/run.py`**

Order of work in `main`: parse args (`--agent` choices `vibe codex cursor`, `--event` choices `SessionStart Stop`); read stdin (empty or non-JSON or non-object → `{}`); `normalise` → `cwd` = event `cwd` resolved, else `Path.cwd()`; `source` = event `source` if it is a non-empty string, else `"startup"`; `hook_event_name` = `--event`. `project = project_dir(cwd)` (git top level, else `cwd`). Read `PLUGIN / "hooks" / "hooks.json"`; `commands()` walks `hooks["hooks"][event]` groups in file order, skips a group whose `matcher` does not `re.fullmatch` the source, and for each hook command: `shlex.split`, skip it when any token's basename is in `CLAUDE_ONLY`, replace `${CLAUDE_PLUGIN_ROOT}` with `plugin.as_posix()` and `${CLAUDE_PROJECT_DIR}` with `project.as_posix()` in each token, swap a first token `python`/`python3` for `sys.executable`. Each command runs through `run_one` with stdin = the normalised event as JSON, env = `os.environ` plus `CLAUDE_PROJECT_DIR=str(project)` and `CLAUDE_KIT_AGENT=<agent>`, cwd = `cwd`, `encoding="utf-8"`, `errors="replace"`. `run_one` returns `contribution(stdout)` on exit 0; on a non-zero exit, timeout or `OSError` it prints `[claude-kit] run.py: <script basename> <reason>` to stderr and returns `""`. `contribution`: a JSON object with a string at `hookSpecificOutput.additionalContext` gives that string; otherwise the stripped stdout. For `SessionStart` only, the pieces start with `tool_mapping(PLUGIN)` (the file text with every `<plugin>` replaced by `PLUGIN.as_posix()`) and then `project_instructions(project)`: `""` when `project/"AGENTS.md"` exists or `project/"CLAUDE.md"` does not; otherwise the header `Project instructions (from <project>/CLAUDE.md; this repo has no AGENTS.md, so your agent did not load them). Follow them as you would an AGENTS.md.`, a blank line, and the file text where each line that is `@<path>` after stripping is replaced by the text of `project/<path>` when that file exists (one level, no recursion) and kept as written otherwise. Non-empty pieces are joined with `"\n\n"`; `render` prints the agent shape from the spec (Vibe `{"hook_specific_output": {"additional_context": T}}`, Codex `{"hookSpecificOutput": {"hookEventName": E, "additionalContext": T}}`, Cursor `{"additional_context": T}`); nothing collected prints nothing. Wrap `main`'s body in `try/except Exception` printing `[claude-kit] run.py error: ...`; always return 0. Docstring names the spec and ADR 0050 and says Claude never calls this file.

- [ ] **Step 5: Run the tests to see them pass**

Run: `pytest tests/test_run_hooks.py tests/test_skill_size.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add plugin/references/agent-tools.md plugin/hooks/run.py tests/test_run_hooks.py tests/test_skill_size.py
git commit -m "feat: cross-agent hook runner and tool mapping"
```

### Task 3: Vendored superpowers bundle

**Files:**
- Create: `plugin/scripts/vendor-superpowers.py`
- Create: `vendor/superpowers/` (`skills/<name>/` folders, `LICENSE`, `VERSION`)
- Modify: `tests/test_docs.py` (`SKIP_DIRS` gains `"vendor/"`)
- Test: `tests/test_vendor_superpowers.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: `AGENTS.md` at the repo root (Task 1), part of the scan set.
- Produces (module `plugin/scripts/vendor-superpowers.py`): `REF_RE = re.compile(r"superpowers:([a-z0-9-]+)")`; `kit_references(repo: Path) -> set[str]` (scans `repo.glob("plugin/**/*.md")`, `repo/"AGENTS.md"` when present, `repo.glob("conventions/*.md")`; nothing under `docs/`); `closure(start: set[str], skills_dir: Path) -> set[str]` (adds every `superpowers:<name>` found in any `*.md` under `skills_dir/<name>/` for names already in the set whose folder exists, until stable; names without a folder stay in the result); `main(argv) -> int` with `--from DIR` (required; upstream root holding `skills/`, `LICENSE`, `package.json`), `--repo DIR` (default: the kit root, `Path(__file__).resolve().parents[2]`), `--source TEXT` (default `https://github.com/obra/superpowers`).

- [ ] **Step 1: Write the failing tests in `tests/test_vendor_superpowers.py`**

```python
import json
import subprocess

from helpers import PLUGIN, REPO, load_module

VENDOR = REPO / "vendor" / "superpowers"
mod = load_module(PLUGIN / "scripts" / "vendor-superpowers.py", "vendor_sp")


def names(folder):
    if not folder.is_dir():
        return set()
    return {p.name for p in folder.iterdir() if (p / "SKILL.md").is_file()}


def test_bundle_holds_the_closure():
    start = mod.kit_references(REPO)
    assert {"brainstorming", "writing-plans", "systematic-debugging"} <= start
    want = mod.closure(start, VENDOR / "skills")
    assert names(VENDOR / "skills") == want
    assert "writing-skills" in want


def test_license_and_version():
    assert "MIT License" in (VENDOR / "LICENSE").read_text(encoding="utf-8")
    version = (VENDOR / "VERSION").read_text(encoding="utf-8")
    assert version.startswith("version: ")
    assert "source: " in version


def test_no_name_collision_with_kit_skills_or_wrappers():
    kit = names(PLUGIN / "skills") | names(PLUGIN / "agent-skills")
    assert not names(VENDOR / "skills") & kit


def test_bundle_is_outside_plugin_skills():
    assert PLUGIN not in VENDOR.resolve().parents


def test_shebang_scripts_are_executable_in_git():
    listed = subprocess.run(
        ["git", "ls-files", "-s", "vendor/superpowers"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    scripts = 0
    for line in listed:
        mode, rest = line.split(" ", 1)
        path = REPO / rest.split("\t", 1)[1]
        if path.read_bytes().startswith(b"#!"):
            scripts += 1
            assert mode == "100755", path
    assert scripts > 0


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_kit_references_scan_set(tmp_path):
    write(tmp_path / "plugin" / "a" / "x.md", "superpowers:aaa")
    write(tmp_path / "docs" / "y.md", "superpowers:bbb")
    write(tmp_path / "AGENTS.md", "superpowers:ccc")
    write(tmp_path / "conventions" / "z.md", "superpowers:ddd")
    assert mod.kit_references(tmp_path) == {"aaa", "ccc", "ddd"}


def upstream(tmp_path):
    up = tmp_path / "up"
    write(up / "skills" / "a" / "SKILL.md", "use superpowers:b")
    write(up / "skills" / "b" / "SKILL.md", "b")
    write(up / "skills" / "c" / "SKILL.md", "c")
    write(up / "LICENSE", "MIT License\n")
    write(up / "package.json", json.dumps({"version": "9.9.9"}))
    return up


def test_script_copies_the_closure(tmp_path):
    repo = tmp_path / "repo"
    write(repo / "plugin" / "x.md", "superpowers:a")
    args = ["--from", str(upstream(tmp_path)), "--repo", str(repo)]
    assert mod.main(args) == 0
    bundle = repo / "vendor" / "superpowers"
    assert names(bundle / "skills") == {"a", "b"}
    assert "version: 9.9.9" in (bundle / "VERSION").read_text(encoding="utf-8")
    assert (bundle / "LICENSE").is_file()


def test_script_fails_on_unknown_skill(tmp_path):
    repo = tmp_path / "repo"
    write(repo / "plugin" / "x.md", "superpowers:nope")
    args = ["--from", str(upstream(tmp_path)), "--repo", str(repo)]
    assert mod.main(args) == 1
    assert not (repo / "vendor").exists()
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_vendor_superpowers.py -o addopts=""`
Expected: FAIL (script missing).

- [ ] **Step 3: Implement `plugin/scripts/vendor-superpowers.py`**

`main`: compute `kit_references(repo)` then `closure(..., upstream/"skills")`; if any name lacks an upstream folder, print `ERROR: unknown superpowers skill(s): <names>` and return 1 before writing. Otherwise delete `repo/vendor/superpowers/skills` if present, `shutil.copytree` each skill folder whole, copy `LICENSE`, and write `VERSION` (newline `"\n"`) as `version: <package.json version>` then `source: <--source>`. Print one line per copied skill. Never write a machine path.

- [ ] **Step 4: Generate the bundle and skip it in the link check**

Run: `python plugin/scripts/vendor-superpowers.py --from "$HOME/.claude/plugins/cache/claude-plugins-official/superpowers/7.0.2"` (use the highest version folder present there).
Expected: 12 skill folders under `vendor/superpowers/skills/` (the 11 the kit references plus `writing-skills`), plus `LICENSE` and `VERSION` with `version: 7.0.2`.

Add `"vendor/"` to `SKIP_DIRS` in `tests/test_docs.py`, with the comment line `# vendor/ is an unchanged upstream copy.`

- [ ] **Step 5: Run the tests to see them pass**

Run: `pytest tests/test_vendor_superpowers.py tests/test_docs.py -o addopts=""`
Expected: all PASS except `test_shebang_scripts_are_executable_in_git` (the bundle is not staged yet; Step 6 makes it pass).

- [ ] **Step 6: Commit, keeping upstream scripts executable**

`git add vendor` on Windows records every file as `100644`, but upstream skills run shebang scripts directly (`executing-plans/SKILL.md` runs `../subagent-driven-development/scripts/sdd-workspace`). After staging, mark each vendored file whose first two bytes are `#!` executable, then re-run the vendor tests.

Run (in the Bash tool, not PowerShell): `git add vendor && python -c "import pathlib,subprocess; fs=[p.as_posix() for p in pathlib.Path('vendor/superpowers').rglob('*') if p.is_file() and p.read_bytes()[:2]==b'#!']; subprocess.run(['git','update-index','--chmod=+x',*fs],check=True); print(len(fs))"` then `pytest tests/test_vendor_superpowers.py -o addopts=""`
Expected: a count above 0 is printed; `test_shebang_scripts_are_executable_in_git` and the other vendor tests PASS.

```bash
git add plugin/scripts/vendor-superpowers.py tests/test_vendor_superpowers.py tests/test_docs.py
git commit -m "feat: vendor the superpowers skills the kit uses"
```

### Task 4: Generated command-wrapper skills

**Files:**
- Create: `plugin/scripts/agent-skills.py`
- Create: `plugin/agent-skills/<name>/SKILL.md` (one per command except `ship-many`; generated)
- Test: `tests/test_agent_skills.py`

**Depends on:** Task 3

**Interfaces:**
- Consumes: `vendor/superpowers/skills/` (Task 3), read by the linked-folder name test.
- Produces (module `plugin/scripts/agent-skills.py`): `SKIP = {"ship-many"}`; `description(text: str) -> str` (the raw value of the `description:` line in the command's frontmatter); `render(name: str, desc: str) -> str`; `wrappers(commands_dir: Path) -> dict[str, str]` (name → SKILL.md text); `main(argv) -> int` with `--check` and `--out DIR` (default `Path(__file__).resolve().parents[1] / "agent-skills"`, independent of the cwd). Write mode writes every wrapper with `newline="\n"` and deletes wrapper folders no command produces; `--check` prints each missing, stale or differing wrapper and returns 1, else prints `ok` and returns 0.

- [ ] **Step 1: Write the failing tests in `tests/test_agent_skills.py`**

```python
import json
import re

from helpers import PLUGIN, REPO, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "agent-skills.py"
WRAPPERS = PLUGIN / "agent-skills"
NAME_RE = re.compile(r"^[a-z0-9-]+$")
MACHINE_RE = re.compile(r"[A-Za-z]:[\\/]|/home/|/Users/")
mod = load_module(SCRIPT, "agent_skills")


def front(path):
    head = path.read_text(encoding="utf-8").split("---", 2)[1]
    pairs = (line.split(":", 1) for line in head.strip().splitlines())
    return {k.strip(): v.strip() for k, v in pairs}


def test_check_passes_on_committed_wrappers():
    result = run_script(SCRIPT, "--check")
    assert result.returncode == 0, result.stdout + result.stderr


def test_one_wrapper_per_command_except_ship_many():
    commands = {p.stem for p in (PLUGIN / "commands").glob("*.md")}
    wrappers = {p.name for p in WRAPPERS.iterdir() if p.is_dir()}
    assert wrappers == commands - {"ship-many"}


def test_wrapper_frontmatter_and_body():
    for folder in WRAPPERS.iterdir():
        skill = folder / "SKILL.md"
        meta = front(skill)
        assert meta["name"] == folder.name
        assert meta["disable-model-invocation"] == "true"
        command = PLUGIN / "commands" / f"{folder.name}.md"
        assert json.loads(meta["description"]) == front(command)["description"]
        text = skill.read_text(encoding="utf-8")
        assert f"`<plugin>/commands/{folder.name}.md`" in text
        assert not MACHINE_RE.search(text), folder.name


def test_check_accepts_crlf_working_copy(tmp_path):
    out = tmp_path / "out"
    assert mod.main(["--out", str(out)]) == 0
    skill = out / "ship" / "SKILL.md"
    skill.write_bytes(skill.read_bytes().replace(b"\n", b"\r\n"))
    assert mod.main(["--check", "--out", str(out)]) == 0


def test_check_fails_then_write_fixes(tmp_path):
    out = tmp_path / "out"
    (out / "stale").mkdir(parents=True)
    assert mod.main(["--check", "--out", str(out)]) == 1
    assert mod.main(["--out", str(out)]) == 0
    assert not (out / "stale").exists()
    assert mod.main(["--check", "--out", str(out)]) == 0


def test_every_linked_folder_has_a_valid_name():
    roots = [
        PLUGIN / "skills",
        WRAPPERS,
        REPO / "vendor" / "superpowers" / "skills",
    ]
    folders = [p for root in roots for p in root.iterdir() if p.is_dir()]
    assert len(folders) > 30
    for folder in folders:
        name = front(folder / "SKILL.md")["name"]
        assert name == folder.name and NAME_RE.match(name), folder
```

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_agent_skills.py -o addopts=""`
Expected: FAIL (script missing).

- [ ] **Step 3: Implement `plugin/scripts/agent-skills.py`**

`--check` reads each existing `SKILL.md` with `Path.read_text(encoding="utf-8")` (universal newlines, so a CRLF working copy on Windows matches) and compares it with the rendered string. `render` returns exactly this, with `{desc_json}` = `json.dumps(desc, ensure_ascii=False)`:

```
---
name: {name}
description: {desc_json}
disable-model-invocation: true
---

# /{name} (claude-kit command)

Follow `<plugin>/commands/{name}.md`, where `<plugin>` is the absolute
`plugin/` path stated in the injected claude-kit tool mapping. Pass the
user's text after the skill name as the command's `$ARGUMENTS`, read the
command through the tool mapping, and report each step that needs a
Claude-only feature as skipped.
```

- [ ] **Step 4: Generate the wrappers**

Run: `python plugin/scripts/agent-skills.py`
Expected: 8 folders under `plugin/agent-skills/`: `adopt-conventions`, `docker-compact`, `handoff`, `new-project`, `ship`, `ship-fast`, `spec-html`, `vault-init`.

- [ ] **Step 5: Run the tests to see them pass**

Run: `pytest tests/test_agent_skills.py tests/test_vendor_superpowers.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add plugin/scripts/agent-skills.py plugin/agent-skills tests/test_agent_skills.py
git commit -m "feat: wrapper skills for the kit commands in other agents"
```

### Task 5: Installer `--agent` and the PowerShell wrapper

**Files:**
- Modify: `plugin/install.py`
- Modify: `plugin/install.ps1`
- Test: `tests/test_install.py`

**Depends on:** Task 2, Task 3, Task 4

**Interfaces:**
- Consumes: `plugin/hooks/run.py` CLI `--agent <a> --event {SessionStart,Stop}` (Task 2); skill folders in `plugin/skills/`, `plugin/agent-skills/` (Task 4) and `vendor/superpowers/skills/` (Task 3).
- Produces (module `plugin/install.py`): `AGENTS = ("claude", "vibe", "codex", "cursor")`; `KIT = PLUGIN.parent`; `RUNNER = PLUGIN / "hooks" / "run.py"`; `make_link(link: Path, target: Path = PLUGIN) -> None`; `skill_sources(kit: Path = KIT) -> list[Path]` (every folder holding a `SKILL.md` under the three roots, sorted per root, missing roots skipped); `hook_command(python: str, agent: str, event: str) -> str` (`<python> "<RUNNER as posix>" --agent <a> --event <E>`, `<python>` wrapped in double quotes when it contains a space); `link_skills(skills_dir: Path, sources: list[Path]) -> None`; `vibe_hooks(text: str, python: str) -> str`; `json_hooks(text: str, agent: str, python: str) -> str` (raises `ValueError` on malformed JSON); `agents_block(text: str, python: str, agent: str) -> str`; `install_agent(agent: str, home: Path, skills_dir: Path, python: str) -> int`. CLI adds `--agent` (default `claude`) and `--home` (default `Path.home()`); `--skills-dir`/`--settings` default to `None` and derive from `--home` and `--agent` per "Decisions this plan makes".

- [ ] **Step 1: Write the failing tests in `tests/test_install.py`**

Replace the `drop_kit_link` fixture with one that removes every link under `tmp_path` without following it, and give `run_install` an `extra=()` parameter appended to its argv:

```python
def drop_links(root):
    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames) + filenames:
            path = os.path.join(dirpath, name)
            if is_link(path):
                remove_link(path)
                if name in dirnames:
                    dirnames.remove(name)


@pytest.fixture(autouse=True)
def drop_kit_links(tmp_path):
    yield
    drop_links(tmp_path)
```

Then add `import tomllib` and `from pathlib import Path` to the imports, and:

```python
AGENTS = ("vibe", "codex", "cursor")
VENDOR = PLUGIN.parent / "vendor" / "superpowers" / "skills"


def run_agent(tmp_path, agent, *extra):
    home = tmp_path / "home"
    args = ["--agent", agent, "--home", str(home), "--python", sys.executable]
    return subprocess.run(
        [sys.executable, str(INSTALL), *args, *extra],
        capture_output=True,
        text=True,
        timeout=120,
    )


def skills(tmp_path):
    return tmp_path / "home" / ".agents" / "skills"


def snapshot(root):
    found = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for name in list(dirnames) + filenames:
            path = os.path.join(dirpath, name)
            if is_link(path):
                found[path] = "link:" + os.readlink(path)
                if name in dirnames:
                    dirnames.remove(name)
            elif name in filenames:
                with open(path, "rb") as handle:
                    found[path] = handle.read()
    return found


@pytest.mark.parametrize("agent", AGENTS)
def test_agent_links_every_skill(tmp_path, agent):
    result = run_agent(tmp_path, agent)
    assert result.returncode == 0, out(result)
    expected = {
        "spec-gate": PLUGIN / "skills" / "spec-gate",
        "ship": PLUGIN / "agent-skills" / "ship",
        "brainstorming": VENDOR / "brainstorming",
    }
    for name, target in expected.items():
        link = skills(tmp_path) / name
        assert is_link(link) and os.path.samefile(link, target), name
    assert not (tmp_path / "home" / ".claude").exists()


def test_foreign_entry_left_alone(tmp_path):
    foreign = skills(tmp_path) / "spec-gate"
    foreign.mkdir(parents=True)
    (foreign / "keep.txt").write_text("mine", encoding="utf-8")
    result = run_agent(tmp_path, "vibe")
    assert result.returncode == 0, out(result)
    assert not is_link(foreign) and (foreign / "keep.txt").is_file()
    assert "Skipped" in result.stdout and "spec-gate" in result.stdout


def test_dangling_kit_link_removed(tmp_path):
    skills(tmp_path).mkdir(parents=True)
    old = skills(tmp_path) / "old-skill"
    try:
        make_dir_link(old, PLUGIN / "skills" / "no-such-skill")
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("cannot create a dangling link here")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 0, out(result)
    assert not os.path.lexists(old)


def test_vibe_hooks_toml_keeps_other_entries(tmp_path):
    path = tmp_path / "home" / ".vibe" / "hooks.toml"
    path.parent.mkdir(parents=True)
    path.write_text(
        '[[hooks]]\nname = "mine"\ntype = "session_start"\ncommand = "echo hi"\n',
        encoding="utf-8",
    )
    assert run_agent(tmp_path, "vibe").returncode == 0
    hooks = tomllib.loads(path.read_text(encoding="utf-8"))["hooks"]
    assert [h["name"] for h in hooks] == [
        "mine",
        "claude-kit-session-start",
        "claude-kit-stop",
    ]
    assert hooks[1]["type"] == "session_start"
    assert hooks[1]["command"].endswith('run.py" --agent vibe --event SessionStart')
    assert hooks[2]["type"] == "post_agent" and hooks[2]["match"] == "main"
    assert hooks[2]["command"].endswith('run.py" --agent vibe --event Stop')


def test_codex_hooks_json(tmp_path):
    path = tmp_path / "home" / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    mine = {"hooks": [{"type": "command", "command": "echo mine"}]}
    path.write_text(json.dumps({"hooks": {"SessionStart": [mine]}, "x": 1}), "utf-8")
    assert run_agent(tmp_path, "codex").returncode == 0
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["x"] == 1
    start = data["hooks"]["SessionStart"]
    assert start[0] == mine and len(start) == 2
    command = start[1]["hooks"][0]["command"]
    assert command.endswith('run.py" --agent codex --event SessionStart')
    stop = data["hooks"]["Stop"][0]["hooks"][0]["command"]
    assert stop.endswith('run.py" --agent codex --event Stop')


def test_cursor_hooks_json(tmp_path):
    path = tmp_path / "home" / ".cursor" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps({"version": 1, "hooks": {"stop": [{"command": "echo mine"}]}}),
        encoding="utf-8",
    )
    result = run_agent(tmp_path, "cursor")
    assert result.returncode == 0, out(result)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["version"] == 1
    assert data["hooks"]["stop"][0] == {"command": "echo mine"}
    assert data["hooks"]["stop"][1]["command"].endswith("--event Stop")
    start = data["hooks"]["sessionStart"][0]["command"]
    assert start.endswith('run.py" --agent cursor --event SessionStart')
    assert "user rules" in result.stdout and "run.py" in result.stdout
    assert not (tmp_path / "home" / ".cursor" / "AGENTS.md").exists()


@pytest.mark.parametrize("agent", ["vibe", "codex"])
def test_agents_md_block(tmp_path, agent):
    path = tmp_path / "home" / f".{agent}" / "AGENTS.md"
    path.parent.mkdir(parents=True)
    path.write_text("my rules\n", encoding="utf-8")
    run_agent(tmp_path, agent)
    run_agent(tmp_path, agent)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("my rules\n")
    assert text.count("<!-- claude-kit:begin") == 1
    assert "Kit map (claude-kit)" in text
    assert f'run.py" --agent {agent} --event SessionStart' in text


@pytest.mark.parametrize("agent", AGENTS)
def test_second_run_changes_no_byte(tmp_path, agent):
    assert run_agent(tmp_path, agent).returncode == 0
    before = snapshot(tmp_path / "home")
    assert run_agent(tmp_path, agent).returncode == 0
    assert snapshot(tmp_path / "home") == before


def test_malformed_hook_file_changes_nothing(tmp_path):
    path = tmp_path / "home" / ".codex" / "hooks.json"
    path.parent.mkdir(parents=True)
    path.write_text("{oops", encoding="utf-8")
    result = run_agent(tmp_path, "codex")
    assert result.returncode == 1 and "ERROR" in result.stdout
    assert path.read_text(encoding="utf-8") == "{oops"
    assert not skills(tmp_path).exists()


@pytest.mark.parametrize(
    ("agent", "step"),
    [
        ("codex", "/hooks"),
        ("vibe", "new Vibe session"),
        ("cursor", "new Cursor agent chat"),
    ],
)
def test_report_names_next_step(tmp_path, agent, step):
    assert step in run_agent(tmp_path, agent).stdout


# The existing test_install.py cases stay unedited (apart from the fixture and
# run_install's extra parameter): they are the guard for today's behaviour.
def test_agent_claude_matches_default(tmp_path):
    results = []
    for name, extra in (("a", ()), ("b", ("--agent", "claude"))):
        root = tmp_path / name
        result = run_install(root, extra=extra)
        assert result.returncode == 0, out(result)
        results.append((result.stdout.replace(str(root), "<t>"), root))
    assert results[0][0] == results[1][0]
    assert sorted(os.listdir(results[0][1])) == sorted(os.listdir(results[1][1]))


POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


@pytest.mark.skipif(POWERSHELL is None, reason="PowerShell not on PATH")
def test_powershell_wrapper_agent_vibe(tmp_path):
    env = dict(os.environ, HOME=str(tmp_path), USERPROFILE=str(tmp_path))
    command = [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass"]
    command += ["-File", str(WRAPPER), "-Agent", "vibe", "-Home", str(tmp_path)]
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=120, env=env
    )
    assert result.returncode == 0, out(result)
    assert os.path.samefile(
        tmp_path / ".agents" / "skills" / "spec-gate", PLUGIN / "skills" / "spec-gate"
    )
    assert (tmp_path / ".vibe" / "hooks.toml").is_file()
    assert not (tmp_path / ".claude" / "skills").exists()
    lines = result.stdout.splitlines()
    written = {
        Path(line.split(" ", 1)[1]).resolve()
        for line in lines
        if line.startswith(("Wrote ", "Unchanged "))
    }
    vibe = (tmp_path / ".vibe").resolve()
    assert {vibe / "hooks.toml", vibe / "AGENTS.md"} <= written
    for path in written:
        assert path.is_relative_to(tmp_path.resolve()), path
    linked = sum(1 for line in lines if line.startswith("Linked "))
    assert linked == len(os.listdir(tmp_path / ".agents" / "skills"))
```

(`run_install(root, extra=...)` passes `--skills-dir root/skills --settings root/settings.json`; the existing tests keep calling it without `extra`.)

- [ ] **Step 2: Run the tests to see them fail**

Run: `pytest tests/test_install.py -o addopts=""`
Expected: the new tests FAIL (`--agent` unknown); the existing ones PASS.

- [ ] **Step 3: Implement `--agent` in `plugin/install.py`**

`main`: `--agent claude` runs today's flow unchanged, with `--skills-dir`/`--settings` defaulting to `<home>/.claude/skills` and `<home>/.claude/settings.json`. For the other agents: `check_python(args.python)` (exit 1 on failure), `warn_missing_tools()`, then `install_agent`. No status line and no superpowers warning. `install_agent` first computes the new text of every file it will write (`<home>/.vibe/hooks.toml` and `<home>/.vibe/AGENTS.md` for Vibe; `<home>/.codex/hooks.json` and `<home>/.codex/AGENTS.md` for Codex; `<home>/.cursor/hooks.json` for Cursor; a missing file reads as `""`); a `ValueError` prints `ERROR: <path> is not valid JSON; nothing changed.` and returns 1. Then `link_skills`, then each file is written (parents created, `newline="\n"`) only when its text changed, printing `Wrote <path>` or `Unchanged <path>`. `link_skills` per source folder: no entry → `make_link(link, folder)` and print `Linked <name>`; a link that resolves to `folder` → print nothing; a link whose existing target lies under one of the three kit roots but is another folder (a skill that moved between roots) → remove the link, `make_link(link, folder)` and print `Relinked <name>`; anything else → print `Skipped <name>: <path> exists and is not this kit's link`. It then removes each link in the skills dir whose `os.readlink` target (with a leading `\\?\` stripped) lies under one of the three kit roots and does not exist, printing `Removed <name> (dangling)`. Hook content:
- `vibe_hooks`: strip any existing managed block (markers in "Decisions this plan makes"), `rstrip("\n")` the rest, then append (after one blank line when the rest is not empty) the block with two `[[hooks]]` tables: `name = "claude-kit-session-start"`, `type = "session_start"`, `command = '<hook_command(..., "SessionStart")>'`; and `name = "claude-kit-stop"`, `type = "post_agent"`, `match = "main"`, `command = '<hook_command(..., "Stop")>'` (TOML literal strings). Ends with one newline.
- `json_hooks` (`""` reads as `{}`): Codex removes from `hooks.SessionStart`/`hooks.Stop` every group with a kit command, then appends `{"hooks": [{"type": "command", "command": <cmd>}]}` to each; Cursor sets `version` to 1, removes kit entries from `hooks.sessionStart`/`hooks.stop`, appends `{"command": <cmd>}`. Output `json.dumps(data, indent=2) + "\n"`.
- `agents_block`: same strip-and-append as `vibe_hooks` with the HTML-comment markers around one line: `If your context has no "Kit map (claude-kit)" text, run \`<hook_command(python, agent, "SessionStart")>\` and follow what it prints.`

Report, last lines: Codex `Next: in Codex, run /hooks and trust the claude-kit hooks.`; Vibe `Next: start a new Vibe session.`; Cursor `Next: start a new Cursor agent chat. If the kit map does not reach the model, paste this into Cursor's user rules:` followed by the same fallback line. Update the module docstring's usage line with `[--agent {claude,vibe,codex,cursor}] [--home DIR]`.

- [ ] **Step 4: Update `plugin/install.ps1`**

```powershell
param(
  [string]$SkillsDir,
  [string]$Settings,
  [ValidateSet("claude", "vibe", "codex", "cursor")][string]$Agent = "claude",
  [Alias("Home")][string]$HomeDir
)
```

Keep the python check. Build the argument list: `(Join-Path $PSScriptRoot "install.py")` (as today, so the wrapper works from any cwd), `--agent $Agent`; `--home $HomeDir` when given. For `claude`, default `$SkillsDir` and `$Settings` to `<base>\.claude\skills` and `<base>\.claude\settings.json` where `<base>` is `$HomeDir` if given else `$HOME`, and always pass both (today's behaviour). For other agents pass `--skills-dir`/`--settings` only when given. Run `& python @arguments; exit $LASTEXITCODE`. Document `-Agent` and `-Home` in the help block.

- [ ] **Step 5: Run the tests to see them pass**

Run: `pytest tests/test_install.py -o addopts=""`
Expected: all PASS (the PowerShell tests are skipped where PowerShell is missing).

- [ ] **Step 6: Commit**

```bash
git add plugin/install.py plugin/install.ps1 tests/test_install.py
git commit -m "feat: install.py --agent for Vibe, Codex and Cursor"
```

### Task 6: capture-learnings follows the `@AGENTS.md` stub

**Files:**
- Modify: `plugin/skills/capture-learnings/SKILL.md` (body only)
- Test: `tests/test_capture_learnings_skill.py`

**Depends on:** none

- [ ] **Step 1: Write the failing test**

```python
def test_stub_claude_md_routes_to_agents_md():
    text = flat()
    assert "is only `@AGENTS.md`" in text
    assert "write to the root `AGENTS.md` instead" in text
```

- [ ] **Step 2: Run it to see it fail**

Run: `pytest tests/test_capture_learnings_skill.py::test_stub_claude_md_routes_to_agents_md -o addopts=""`
Expected: FAIL.

- [ ] **Step 3: Add the rule**

Add a bullet to the edge-case list after the routing table (beside "No root `CLAUDE.md`"): `- Root \`CLAUDE.md\` is only \`@AGENTS.md\`: every rule here that names the root \`CLAUDE.md\` (routing, line limit, links) applies to the root \`AGENTS.md\`; write to the root \`AGENTS.md\` instead and leave the stub unchanged.` Frontmatter unchanged.

- [ ] **Step 4: Run the skill tests to see them pass**

Run: `pytest tests/test_capture_learnings_skill.py tests/test_skill_size.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/capture-learnings/SKILL.md tests/test_capture_learnings_skill.py
git commit -m "feat: capture-learnings writes to AGENTS.md behind a stub"
```

### Task 7: ADR, docs, version bump and spec index

**Files:**
- Create: `knowledge/decisions/0050-agent-agnostic-kit.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `knowledge/decisions/0034-workspace-rules-inject.md`
- Modify: `knowledge/decisions/0035-process-rules-in-claude-md.md`
- Modify: `docs/setup.md`
- Modify: `README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `docs/superpowers/README.md`
- Test: `tests/test_docs.py`, `tests/test_plugin_manifest.py`

**Depends on:** Task 5

**Interfaces:**
- Consumes: the installer flags and next steps from Task 5, the scripts from Tasks 3 and 4.

Numbering: `0050` and `0.35.0` are one above `origin/main` today. Before starting, run `git fetch origin` then `git ls-tree --name-only origin/main knowledge/decisions/` and `git show origin/main:plugin/.claude-plugin/plugin.json`; if either moved, use the next number and version everywhere in this task, and also replace `ADR 0050` in the docstrings Tasks 1 and 2 wrote (`grep -rn "ADR 0050" plugin` lists them).

- [ ] **Step 1: Write the failing tests**

In `tests/test_docs.py`:

```python
def test_agent_agnostic_adr_amends_0034_and_0035():
    decisions = REPO / "knowledge" / "decisions"
    adr = "0050-agent-agnostic-kit.md"
    assert (decisions / adr).is_file()
    index = (decisions / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
    for old in ("0034-workspace-rules-inject.md", "0035-process-rules-in-claude-md.md"):
        row = next(line for line in index.splitlines() if old in line)
        assert "amended by 0050" in row, old
        assert "amended by 0050" in (decisions / old).read_text("utf-8"), old


def test_docs_cover_other_agents():
    guide = (REPO / "docs" / "setup.md").read_text(encoding="utf-8")
    section = guide.split("## Using the kit with Vibe, Codex or Cursor", 1)[1]
    section = section.split("\n## ", 1)[0]
    for needle in ("--agent vibe", "--agent codex", "--agent cursor", "/hooks"):
        assert needle in section, needle
    for needle in ("vendor-superpowers.py", "agent-skills.py", "/ship-many"):
        assert needle in section, needle
    readme = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    para = readme.split("Mistral Vibe", 1)[1][:400]
    assert "Codex" in para and "Cursor" in para and "docs/setup.md" in para
```

In `tests/test_plugin_manifest.py` rename `test_version_is_0_34_0` to `test_version_is_0_35_0` and assert `"0.35.0"`.

- [ ] **Step 2: Run them to see them fail**

Run: `pytest tests/test_docs.py tests/test_plugin_manifest.py -o addopts=""`
Expected: the two new docs tests and the version test FAIL.

- [ ] **Step 3: Write the ADR and mark the amended ones**

`knowledge/decisions/0050-agent-agnostic-kit.md`, in the format of ADR 0049 (`# ADR 0050: The kit runs in Mistral Vibe, Codex and Cursor from one source`, `- **Status:** accepted`, `- **Date:** <today>`, then `## Context`, `## Decision`, `## Consequences`). Context: the kit worked only in Claude Code; the three agents share `AGENTS.md`, `~/.agents/skills/` and hook files (cite the spec path). Decision: one bullet each for spec D1 to D11. Consequences: Claude output unchanged apart from the rules header; a new hook in `hooks.json` reaches every agent; command edits need `python plugin/scripts/agent-skills.py`; superpowers updates need `vendor-superpowers.py`; Cursor's fire-and-forget `sessionStart` may need the user-rules fallback. Add its index row (`accepted`, today's date). In ADRs 0034 and 0035 and their index rows, set the status to `accepted; amended by 0050` and, in the ADR files, append ` ([ADR 0050](0050-agent-agnostic-kit.md): rules now live in AGENTS.md; non-Claude agents also get them in child repos inside the kit folder)` for 0034 and ` ([ADR 0050](0050-agent-agnostic-kit.md): the rules now live in AGENTS.md, which CLAUDE.md imports)` for 0035.

- [ ] **Step 4: Write the setup section and the README paragraph**

`docs/setup.md`: a `## Using the kit with Vibe, Codex or Cursor` section right after `## Install`, covering: `python plugin/install.py --agent vibe` (and `--agent codex`, `--agent cursor`; `plugin\install.ps1 -Agent vibe` on Windows); what it does (links kit skills, command wrappers and the bundled superpowers skills into `~/.agents/skills/`, adds the runner to the agent's user hook file, adds a fallback line to `~/.vibe/AGENTS.md` or `~/.codex/AGENTS.md`); next steps (Codex `/hooks` to trust the hooks; Vibe and Cursor a new session; Cursor's user-rules fallback); what stays Claude-only (`/ship-many`, status line, token report, `audit --user`, the transcript, precompact and spec-edit hooks); for kit developers, `python plugin/scripts/agent-skills.py` after editing a command and `python plugin/scripts/vendor-superpowers.py --from <superpowers checkout or plugin cache>` to refresh the bundle. `README.md`: one paragraph after the install bullet saying the kit also runs in Mistral Vibe, Codex and Cursor through `install.py --agent`, pointing at the [setup guide](docs/setup.md).

- [ ] **Step 5: Bump the version and regenerate the spec index**

Set `"version": "0.35.0"` in `plugin/.claude-plugin/plugin.json`. Run: `python plugin/scripts/spec-index.py docs/superpowers`
Expected: `docs/superpowers/README.md` gains rows for `2026-11-18-agent-agnostic-kit-design.md` and `2026-11-18-agent-agnostic-kit.md`.

- [ ] **Step 6: Run the tests to see them pass**

Run: `pytest tests/test_docs.py tests/test_plugin_manifest.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add knowledge/decisions docs/setup.md README.md plugin/.claude-plugin/plugin.json docs/superpowers/README.md tests/test_docs.py tests/test_plugin_manifest.py
git commit -m "docs: ADR 0050, setup for Vibe, Codex and Cursor; v0.35.0"
```

### Task 8: Verify the success criteria

**Files:**
- Create (scratch, outside the repo): `<scratch>/capture.py`, `<scratch>/main.txt`, `<scratch>/branch.txt`, `<scratch>/pr-notes.md`
- Test: `tests/` (full suite)

**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6, Task 7

`<scratch>` is the session scratchpad or a temporary directory outside the repo; nothing in this task is tracked.

- [ ] **Step 1: SC3, suite green**

Run: `pytest -o addopts=""` then `ruff check plugin tests` then `ruff format --check plugin tests`
Expected: all tests pass (PowerShell tests may skip); both ruff commands report no issues.

- [ ] **Step 2: SC2, Claude skills unchanged**

Run: `git diff origin/main -- plugin/skills/*/SKILL.md`
Expected: only the body change in `plugin/skills/capture-learnings/SKILL.md` (Task 6); no line between the `---` frontmatter markers changes in any file, and `ls plugin/skills` still lists the same 15 folders. Also `git diff origin/main --stat -- plugin/hooks/hooks.json` prints nothing.

- [ ] **Step 3: SC1, Claude context unchanged**

Create two detached checkouts outside the kit folder: `git worktree add --detach <scratch>/kit-main origin/main` and `git worktree add --detach <scratch>/kit-branch HEAD`, and one project `git init -q <scratch>/outside`. Write `<scratch>/capture.py` that takes `<checkout> <out-file> <other-checkout>` and, with `CLAUDE_KIT_AGENT` removed from the environment and every other variable as the shell has it, for each project in (`<checkout>`, `<scratch>/outside`): for each `SessionStart` group of `<checkout>/plugin/hooks/hooks.json` whose matcher (if any) matches `startup`, runs `[sys.executable, <checkout>/plugin/hooks/<script>]` with cwd = project, `CLAUDE_PROJECT_DIR` = project, stdin `{"cwd": project, "source": "startup", "hook_event_name": "SessionStart"}`, and appends `== <script> @ <project label> ==` plus its stdout; then appends `<checkout>/CLAUDE.md` with each line that is exactly `@<path>` replaced by `<checkout>/<path>`'s text. Before writing, it replaces both checkout roots (native and forward-slash forms) with `<kit>`.

Run: `python <scratch>/capture.py <scratch>/kit-main <scratch>/main.txt <scratch>/kit-branch`, `python <scratch>/capture.py <scratch>/kit-branch <scratch>/branch.txt <scratch>/kit-main`, then `git diff --no-index <scratch>/main.txt <scratch>/branch.txt`
Expected: the only changed lines are the workspace-rules header for the `outside` project, `from <kit>/CLAUDE.md)` becoming `from <kit>/AGENTS.md)`. If another hook's output differs, check that hook's file is identical between checkouts (`git diff origin/main HEAD -- plugin/hooks/<file>` prints nothing) and that the difference comes from the checkout setup; otherwise fix the change before going on. Then `git worktree remove <scratch>/kit-main` and `git worktree remove <scratch>/kit-branch`.

- [ ] **Step 4: SC8, publishable plugin**

Run: `pytest tests/test_plugin_manifest.py tests/test_vendor_superpowers.py -o addopts=""`
Expected: PASS; `plugin/.claude-plugin/plugin.json`, `plugin/hooks/hooks.json`, `plugin/skills/` and `plugin/commands/` exist.

- [ ] **Step 5: Run the live checks SC4 to SC6 and write the PR notes**

SC4 to SC6 need a live Claude, Vibe or Cursor session that this executor cannot drive from the branch, so stop here and ask the user to run them, giving these exact steps from the spec: SC4 (one `/ship-fast` run in Claude on `ship-fast-toy` reaching its PR, its parallel tasks or reviewers running as subagents; result = the PR link and a transcript excerpt), SC5 (Vibe: `python plugin/install.py --agent vibe`, a new session in a project repo outside the kit folder, the model quotes the kit map and a workspace rule, Vibe's skill list shows the kit skills, the bundled superpowers skills and the wrappers, and `spec-gate` runs on a sample spec to a gate record; result = a transcript excerpt), SC6 (Cursor: `python plugin/install.py --agent cursor`, a new agent chat in the same repo, the model quotes the kit map and `/` lists `spec-gate`; if the `sessionStart` context does not reach the model, SC6 fails as stated: record that, try the installer's paste-into-user-rules fallback and record its result). Then write `<scratch>/pr-notes.md` with: the SC1 diff summary with `<kit>` paths and no machine path; the SC2, SC3 and SC8 results; the SC4, SC5 and SC6 results and transcript excerpts the user returned (no machine paths); and SC7 as the only pending item (Codex live check: kit map quoted, `/skills` lists the kit skills, pending until Codex is installed). The PR body is built from this file, and the branch does not merge until SC4, SC5 and SC6 each have a recorded result (for SC6, a recorded failure with the fallback result counts).
Expected: the file exists, holds a result for each of SC4, SC5 and SC6, and `grep -c "pending" <scratch>/pr-notes.md` prints 1 (SC7 only).

- [ ] **Step 6: Commit any fixes**

Run: `git status --short`
Expected: clean. If Steps 1 to 4 needed fixes, commit them with `git commit -m "fix: <what>"`; there is nothing else to commit.
