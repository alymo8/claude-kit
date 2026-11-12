# Two-axis review, surgical diffs, frozen evaluators, Merge Danger and a hardening retro Implementation Plan

- **Status:** approved
- **Date:** 2026-11-10

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a frozen-file diff check (`frozen-check.py`), a two-axis `claude-kit:review` skill run on every `/ship` step 6, surgical-diff rules, Merge Danger PR bodies and a Harden step in `capture-learnings`, with ADRs 0041–0045 and a minor version bump to 0.28.0.

**Architecture:** One standard-library script, `plugin/scripts/frozen-check.py`, decides whether any file named by a spec's or plan's `- **Frozen:**` bullet changed since its snapshot commit. Everything else is Markdown read by Claude: a new skill folder `plugin/skills/review/` (SKILL.md plus two reviewer prompt files), a new reference `plugin/references/pr-body.md`, and edits to `ship.md`, `ship-finish.md`, `ship-fast.md`, `ship-fast-finish.md`, `capture-learnings`, the spec-gate rubric, three conventions and both PR templates. Structure tests pin the Markdown with string assertions.

**Tech Stack:** Python 3.11+ standard library (`argparse`, `re`, `subprocess`), git, pytest, ruff, Markdown, JSON.

**Spec:** `docs/superpowers/specs/2026-11-10-review-and-guardrails-design.md`

Spec gate record: docs/superpowers/gates/2026-11-10-review-and-guardrails-design.md

## Context for the executor

This repo is claude-kit: a Claude Code plugin under `plugin/`, workspace
conventions under `conventions/`, ADRs under `knowledge/decisions/`.
`tests/helpers.py` exports `REPO`, `PLUGIN` (`REPO / "plugin"`),
`load_module(path, name)` (imports a hyphenated script), `run_script(script,
*args, cwd=None, env=None)` (runs it with `sys.executable`, returns a
`CompletedProcess` with text `stdout`/`stderr`, UTF-8) and
`command_text(name)` (a command's text with each reference file named by a
`${CLAUDE_PLUGIN_ROOT}/references/<file>.md` pointer in that command file
inlined after the paragraph holding the pointer; references named only
inside another reference are not inlined). `tests/test_worktree_audit.py`
has a `git(*args, cwd)` helper and a temporary-repo fixture to copy.

Scripts follow `plugin/scripts/docker-disk.py` and `parallel-plan.py`: a
module docstring with usage and exit codes, `from __future__ import
annotations`, `main(argv: list[str] | None = None) -> int`, and
`if __name__ == "__main__": sys.exit(main())`; a script that prints paths
calls `sys.stdout.reconfigure(encoding="utf-8")` first.

Gotchas (from `knowledge/kit-dev-gotchas.md`):
- `pyproject.toml` sets `addopts = "-q"`; run plain `pytest` for the count.
- Test code must fit ruff's 88-character line limit; split long strings by hand.
- In `tests/test_ship_command.py`, `_step(n)` splits `command_text("ship")`
  on every line that starts at column 0 with `<digits>. `. Prose added inside a
  `ship.md` step stays indented 3 spaces (4 for steps 10–12 in
  `plugin/references/ship-finish.md`). No file inlined into the ship text
  (`pr-body.md`, `ship-finish.md`) may have a column-0 numbered line except
  `ship-finish.md`'s own step markers. `_stops()` returns the raw text from
  `## Stop rules` to `## Steps` (so it includes `## Git lock retry` and the new
  `## Frozen check`); normalise whitespace before matching phrases.
- `test_relative_markdown_links_resolve` checks every tracked `.md`: write ADR
  numbers in conventions as plain text ("ADR 0042"), not as links, and never put
  a link-shaped example in prose.
- `ship.md`, `ship-fast.md` and the PR templates have CRLF line endings in the
  working tree; edit them with the Edit tool, never a bash heredoc. Run
  `ruff format <file>` on any Python file you touched with a shell.
- Edit test files with the Edit tool (heredocs break `\n` escapes).

Setup: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks:
`pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.

## Global Constraints

- `frozen-check.py`: standard library only, Python 3.11; exit 0 ok or none declared, 1 violations, 2 bad usage / unreadable file / git failure.
- Output lines exactly: `frozen: none declared`, `frozen: ok (<n> files)`, `frozen: changed <path> since <short snapshot>`, `frozen: warning: no file matches <pattern>`.
- Approval trailer, exactly: `Frozen-change-approved: <path>`; written only by `/ship`'s (or `/ship-fast`'s) main session after the user approves; implementers and subagents never write it.
- Every SKILL.md and command stays under 20,000 bytes; `plugin/commands/ship.md` at most 18,500 bytes (`wc -c`, working-tree bytes). If it would exceed that, move step 6's text to `plugin/references/ship-review.md` with the pointer pattern `${CLAUDE_PLUGIN_ROOT}/references/ship-review.md` plus the `~/.claude/skills/claude-kit/references/ship-review.md` fallback in the same paragraph.
- Reviewers run as new general-purpose subagents on the session's model, no `model` override, no conversation context (D9).
- Nothing is frozen in this change (D10): this plan has no `**Frozen:**` bullet.
- No third-party plugin is installed; no superpowers skill is edited.
- Version: `plugin/.claude-plugin/plugin.json` goes from `0.27.1` to `0.28.0` (on a rebase conflict, the next minor above `origin/main`'s).
- ADR numbers 0041–0045; before writing them run `git ls-tree --name-only origin/main knowledge/decisions/`; if any is taken, use the next free numbers and update every reference in this change (conventions text and tests).
- This repo is public: no machine username or private repo name in any tracked file.
- For `/ship`'s main session: before step 10, reread the "After merge" section at the end of this plan (it may have been compacted away), then run that check in step 10 and report its counts in step 12 (spec Success criterion 5).
- ADR 0037's Status line and index row are left as they are (the spec's Scope In does not list them); ADR 0041's text says it amends ADR 0037.

## Review Focus

- A frozen file created on the branch by renaming an unfrozen file, then edited: git's rename detection would hide the add; the script uses `--no-renames` so it is still an add and the edit is caught (test in Task 1).
- A frozen path with non-ASCII characters (`tests/é.txt`): git quotes it by default; the script runs git with `-c core.quotepath=off` and prints the path as is (test in Task 1).
- The script run with `--root` pointing at a subdirectory of the repo: `ls-tree` must list repo-relative paths (`--full-tree`), so `tests/a.py` still matches (test in Task 1).
- A `- **Frozen:**` bullet wrapped onto an indented continuation line: patterns on the continuation line count (test in Task 1).
- A base ref that does not resolve (`--base nosuch`, or a clone without `origin/main`): exit 2 with a stderr message, never a false `ok` (test in Task 1).

## Answers to the spec gate's Plan questions

- **`*` and `**/`:** a single `*` stays inside one path segment (never matches `/`); `?` matches one non-`/` character; `**/` matches zero or more whole directories; a trailing `**` matches anything. Tests in Task 1 (`test_single_star_stays_in_one_segment`, `test_double_star_slash_matches_zero_dirs`).
- **Several trailers for one path:** the last one wins: the snapshot is the latest commit in `base..HEAD` (in commit order) that carries `Frozen-change-approved: <path>` and comes after the path's starting snapshot. Task 1 (`test_last_trailer_wins`).
- **Exit 2 under `/ship` and `/ship-fast`:** debug with `superpowers:systematic-debugging` and rerun before pushing; it is not a stop rule. Task 5 (`## Frozen check` in `ship.md`) and Task 6 (`ship-fast-finish.md`).
- **Approval commit:** yes, the main session makes `git commit --allow-empty` after the change commit, with one `Frozen-change-approved: <path>` trailer line per approved path. Task 5 and Task 6 stop rules.
- **Step 7 push and step 8 fix loop:** yes, the check runs before every `git push` in steps 5 to 9, step 7's push and step 8's fix loop included. Task 5.
- **`claude-kit:review` and `frozen-check.py`:** it runs `python <this skill's directory>/../../scripts/frozen-check.py <spec> [<plan>] --base <base>` (fallback `~/.claude/skills/claude-kit/scripts/frozen-check.py`), the same relative pattern as `spec-gate` uses for `spec-lint.py`; with no spec and no plan found, the check is skipped, the standards reviewer is told `Frozen: skipped (no spec or plan)` and the report says so. Task 2.
- **Capture learnings files as process files:** yes, files changed by the branch's `Capture learnings` commit (`CLAUDE.md`, `knowledge/` entries, an ADR) are process files and never scope creep. Task 2.
- **`pr-body.md` and the `_step(7)` assertions:** `pr-body.md` uses only `#`/`##` headings and `- ` bullets (no column-0 numbered lines), so inlined after step 7's paragraph it stays inside `_step(7)` and does not split later steps; it keeps the verbatim strings the existing step-7 assertions need (`Plan decisions (auto-approved)`, `- **Approved by:** /ship (auto)`, `` `Plan decisions` otherwise ``, `docs/superpowers/gates/plans/`). `ship-fast-finish.md` names `pr-body.md` but `command_text("ship-fast")` does not inline it, so the ship-fast test reads `plugin/references/pr-body.md` directly for its `/ship-fast` list and checks only that `pr-body.md` is named in the ship-fast text. Tasks 5 and 6.
- **Hand run versus a run under a command:** an argument. `/ship` step 7 and `/ship-fast` step 7 invoke the skill with the argument `--auto` (so `/ship-many` children, which run `/ship`, pass it too); no argument means a hand run. Task 4 (skill), Tasks 5 and 6 (callers).
- **Post-merge live check:** in step 10's detached `<tmp>` worktree at the squash commit, after its tests and before `git worktree remove`; when the loaded plugin has no `review` skill yet, follow `<tmp>/plugin/skills/review/SKILL.md` from the file. See "After merge" at the end of this plan.
- **Rubric check:** yes, a new numbered item `9. **Frozen evaluator.**` under "What to check", after item 8. Task 3.

---

### Task 1: `frozen-check.py`

**Files:**
- Create: `plugin/scripts/frozen-check.py`
- Test: `tests/test_frozen_check.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: CLI `python plugin/scripts/frozen-check.py FILE.md [FILE.md ...] [--base REF] [--root DIR]`; functions `parse_patterns(text: str) -> list[str]` and `pattern_regex(pattern: str) -> re.Pattern[str]`; output lines and exit codes as in Global Constraints. Tasks 2, 5 and 6 call the CLI and read its lines.

Behaviour (from spec Design §4, with the Plan-question answers):
- `parse_patterns`: walk lines, toggling a fence flag on lines whose `lstrip()` starts with three backticks; outside fences, a line matching `^\s*- \*\*Frozen:\*\*` starts a bullet; following lines that are non-blank, start with whitespace and whose stripped text does not start with `- ` continue it. Return the backticked spans (`` `([^`]+)` ``) of all bullets in order, a leading `./` stripped.
- `main`: union of patterns over all files, first-seen order, duplicates dropped. Files are resolved against the current directory and read with `encoding="utf-8"`. An unreadable file prints `frozen-check: cannot read <file>` to stderr and returns 2. No pattern → print `frozen: none declared`, return 0.
- All git calls: `["git", "-c", "core.quotepath=off", "-C", top, ...]`, where `top` is the output of `git -C <--root or the current directory> rev-parse --show-toplevel`, resolved first (so repo-relative pathspecs such as `-- tests/a.py` resolve from the repo root even when `--root` is a subdirectory), `check=True`, text UTF-8; a `CalledProcessError` or `OSError` prints `frozen-check: git failed: <command>: <stderr>` and returns 2.
- Base: `git merge-base <REF> HEAD`, `REF` = `--base` or `origin/main`.
- Commits: `git rev-list --reverse <base>..HEAD` (index order = commit order).
- Candidate paths: `git ls-tree -r --full-tree --name-only <base>` ∪ same for `HEAD` ∪ `git log --no-renames --diff-filter=A --name-only --format= <base>..HEAD`.
- Frozen set: candidates whose path `pattern_regex(p).fullmatch(path)` for some pattern, sorted. Each pattern matching no candidate prints `frozen: warning: no file matches <pattern>` (warnings first).
- Snapshot per path: start = the base (index -1) if the path is in the base tree, else the index of the first commit of `git log --no-renames --diff-filter=A --reverse --format=%H <base>..HEAD -- <path>`. Trailers: parse `git log --format=%H%x00%B%x1e <base>..HEAD` once; a commit approves the paths of its lines matching `^Frozen-change-approved:[ \t]*(\S+)[ \t]*$` (multiline). The snapshot is the last commit with index > start approving the path, else the start.
- Violation: `git diff --quiet <snapshot> HEAD -- <path>` returns 1 (run without `check`; any return other than 0 or 1 is a git failure → 2). Print `frozen: changed <path> since <snapshot[:7]>` per violation and return 1; else print `frozen: ok (<n> files)` (n = size of the frozen set) and return 0.

- [ ] **Step 1: Write the failing tests in `tests/test_frozen_check.py`**

Fixture and helpers (copy the `git` helper from `tests/test_worktree_audit.py`):

```python
import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "frozen-check.py"
fc = load_module(SCRIPT, "frozen_check")


def git(*args: str, cwd: Path) -> str: ...  # as in test_worktree_audit.py


def commit(root: Path, msg: str, files: dict[str, str | None]) -> None:
    """Write (str) or delete (None) each file, then commit everything."""
    for rel, content in files.items():
        path = root / rel
        if content is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-q", "--allow-empty", "-m", msg, cwd=root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """`main` holds tests/a.py and src/x.py; HEAD is branch `feat` at main."""
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    commit(root, "base", {"tests/a.py": "a\n", "src/x.py": "x\n"})
    git("checkout", "-q", "-b", "feat", cwd=root)
    return root


def spec(tmp_path: Path, bullet: str, name: str = "spec.md") -> Path:
    path = tmp_path / name
    path.write_text(f"# S\n\n- **Status:** approved\n{bullet}\n", encoding="utf-8")
    return path


def check(repo: Path, *specs: Path, base: str = "main"):
    args = [str(s) for s in specs]
    return run_script(SCRIPT, *args, "--base", base, "--root", str(repo))
```

Tests (name: setup → assertions), each spec file in `tmp_path`, outside the repo:

- `test_no_bullet_is_none_declared`: spec with bullet `- **Date:** 2026-11-10` → `returncode == 0`, `stdout.strip() == "frozen: none declared"`.
- `test_untouched_base_file_is_ok`: `` - **Frozen:** `tests/a.py` `` → 0, `"frozen: ok (1 files)" in stdout`.
- `test_modified_base_file_is_a_violation`: commit `tests/a.py` = `"b\n"` → 1, `"frozen: changed tests/a.py since " in stdout`.
- `test_deleted_base_file_is_a_violation`: commit deleting `tests/a.py` → 1.
- `test_created_file_never_edited_is_ok`: pattern `tests/new.py`; commit creating it → 0, `"ok (1 files)"`.
- `test_created_file_edited_later_is_a_violation`: create, then a second commit edits it → 1.
- `test_created_file_deleted_later_is_a_violation`: create, then delete → 1.
- `test_approval_trailer_moves_the_snapshot`: edit `tests/a.py`; then `git commit -q --allow-empty -m approve -m "Frozen-change-approved: tests/a.py"` → 0; then another edit commit → 1.
- `test_last_trailer_wins`: edit + approval commit, edit + approval commit → 0; assert the stdout says `ok`.
- `test_glob_matches_nested_files`: pattern `tests/acceptance/**`; a commit on `feat` creates `tests/acceptance/x/y.txt` → 0 with `"ok (1 files)"`; a second commit edits it → 1, `"tests/acceptance/x/y.txt" in stdout`.
- `test_unmatched_pattern_warns_and_passes`: `` `tests/nothing/*.py` `` → 0, `"frozen: warning: no file matches tests/nothing/*.py" in stdout`, `"ok (0 files)" in stdout`.
- `test_single_star_stays_in_one_segment`: pattern `tests/*.py`; commit creating `tests/sub/b.py`, then a commit editing it → 0 and `"ok (1 files)"` (only `tests/a.py` matches).
- `test_double_star_slash_matches_zero_dirs`: pattern `tests/**/a.py`; edit `tests/a.py` → 1.
- `test_bullets_in_two_files_are_united`: spec with `` `tests/a.py` ``, plan (`name="plan.md"`) with `` `src/x.py` ``; first, with no commit on `feat`, → 0 with `"ok (2 files)"`; then a commit edits `src/x.py` → 1, `"src/x.py" in stdout`.
- `test_bullet_in_code_fence_is_ignored`: spec text with the bullet inside a three-backtick fence → 0, `"none declared"`.
- `test_missing_input_file_exits_2`: path `tmp_path / "nope.md"` → 2, `"cannot read" in stderr`.
- `test_unknown_base_exits_2`: `base="nosuch"` → 2, `stderr != ""`.
- `test_renamed_then_edited_created_file_is_a_violation`: pattern `tests/frozen.py`; `git mv src/x.py tests/frozen.py` + commit, then edit commit → 1.
- `test_non_ascii_path_is_reported_as_is`: pattern `tests/é.txt`; a commit on `feat` creates it, a second commit edits it → 1, `"tests/é.txt" in stdout`.
- `test_root_may_be_a_subdirectory`: `--root` = `repo / "src"` (call `run_script` directly), edit `tests/a.py` → 1.
- `test_wrapped_bullet_continuation_counts`: bullet text `` "- **Frozen:** `src/x.py`,\n  `tests/a.py`" ``; edit `tests/a.py` → 1.
- `test_parse_patterns_unit`: `fc.parse_patterns("- **Frozen:** `./a/b.py`, `c/**`\n")` == `["a/b.py", "c/**"]`.
- `test_pattern_regex_unit`: `fc.pattern_regex("a/*.py").fullmatch("a/b/c.py") is None`; `fc.pattern_regex("a/**/c.py").fullmatch("a/c.py")`; `fc.pattern_regex("a/**").fullmatch("a/b/c")`; `fc.pattern_regex("a/?.py").fullmatch("a/bc.py") is None`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_frozen_check.py -o addopts=""`
Expected: FAIL (collection error: `frozen-check.py` does not exist).

- [ ] **Step 3: Implement `plugin/scripts/frozen-check.py`**

`parse_patterns(text: str) -> list[str]`, `pattern_regex(pattern: str) -> re.Pattern[str]`, `main(argv: list[str] | None = None) -> int`, per the Behaviour list above. `argparse` with `files` (`nargs="+"`), `--base`, `--root`; argparse's own usage errors exit 2. The docstring states usage, the output lines and the exit codes. `pattern_regex` (the one algorithm the tests do not pin alone):

```python
def pattern_regex(pattern: str) -> re.Pattern[str]:
    out, i = [], 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            out.append(".*")
            i += 2
        elif pattern[i] == "*":
            out.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(pattern[i]))
            i += 1
    return re.compile("".join(out))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_frozen_check.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Full suite and lint**

Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`
Expected: no failures; ruff prints no errors.

- [ ] **Step 6: Commit**

```bash
git add plugin/scripts/frozen-check.py tests/test_frozen_check.py
git commit -m "Add frozen-check.py: frozen-file diff check"
```

### Task 2: `claude-kit:review` skill

**Files:**
- Create: `plugin/skills/review/SKILL.md`
- Create: `plugin/skills/review/standards-reviewer.md`
- Create: `plugin/skills/review/spec-reviewer.md`
- Test: `tests/test_review_skill.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: Task 1's CLI and its output lines (`frozen: changed <path> since <sha>` etc.).
- Produces: skill `claude-kit:review`, arguments `[base-ref] [spec.md] [plan.md]`; report with `## Standards` and `## Spec` sections; standards findings tagged `hard` or `judgement`; spec findings of kind (a) missing or partial, (b) scope creep, (c) implemented but wrong. Task 5 relies on these names. The constant `SURGICAL_RULES` in `tests/test_review_skill.py` (Task 3 reuses it):

```python
SURGICAL_RULES = (
    "Trace every line",
    "Mention unrelated dead code",
    "Remove only your own leftovers",
    "Nothing speculative",
    "Deleting is a win",
    "Ask during design",
)
```

These six names map, in order, to the six bullets of spec Design §3.

Content of `SKILL.md` (spec Design §2), in the kit's wording:
- Frontmatter: `name: review`; `description:` starting `Use when /ship reaches step 6, or when the user asks for a review of a branch or diff against its spec and the repo's rules.` then `Runs a standards reviewer and a spec reviewer as two parallel fresh-context subagents and reports them side by side.`; `argument-hint: [base-ref] [spec.md] [plan.md]`.
- Step 1 **Pin the diff**: base = first argument else `origin/main`; `git rev-parse <base>` must resolve and `git diff <base>...HEAD` must be non-empty, otherwise report that and stop; record `git log <base>..HEAD --oneline`.
- Step 2 **Find the spec**: arguments; else a plan under `docs/superpowers/plans/` changed on the branch whose `**Spec:**` line names a spec; else the newest (by file name) spec in `git diff --name-only <base>...HEAD -- docs/superpowers/specs/`. None: skip the spec reviewer and report `Spec: no spec found`.
- Step 3 **Find the standards**: root `CLAUDE.md`, `knowledge/review-standards.md`, `CONTRIBUTING.md`, any `CODING_STANDARDS.md`, and the engineering-practices playbook (the repo's `conventions/engineering-practices.md`, else the path from the kit map); only files that exist.
- Step 4 **Frozen check**: run `python <this skill's directory>/../../scripts/frozen-check.py <spec> [<plan>] --base <base>` (fallback: `~/.claude/skills/claude-kit/scripts/frozen-check.py`); keep its whole output for the standards reviewer. With no spec and no plan: skip it and use `Frozen: skipped (no spec or plan)`. Exit 2: report the stderr in the output line given to the reviewer; it is not a finding.
- Step 5 **Dispatch both reviewers in one message**, as new general-purpose subagents, no `model` override, no conversation context. Each prompt is its file's content with the placeholders filled: `<repo root>`, `<diff command>` (`git diff <base>...HEAD`), `<commit list>`, and for the standards reviewer `<standards files>` and `<frozen-check output>`, for the spec reviewer `<spec path>` and `<plan path or none>`. State that process files are never scope creep: the spec, the plan, gate records, ADRs, `docs/superpowers/README.md`, and files changed by the branch's `Capture learnings` commit.
- Step 6 **Report**: `## Standards` then `## Spec`, each the reviewer's findings lightly cleaned, never merged or reranked across axes; then the frozen line; then one line `Findings: standards <n> (worst: <finding>), spec <n> (worst: <finding>)`.

Content of `standards-reviewer.md`: read `<standards files>` and run `<diff command>` in `<repo root>` (commits: `<commit list>`); report each finding as `- <file> <hunk header> | <rule: standards file and quoted rule, or the baseline item> | hard or judgement | fix: <one line>`. `hard` = breach of a written repo rule; baseline findings are always `judgement`; a written repo rule that endorses something wins over the baseline (suppress the finding); skip what a linter or formatter in the repo already enforces. Baseline: the 12 smells by exact name (Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest), each with one line on how it shows in a diff and one on the usual fix; the six `SURGICAL_RULES` by name, one line each; the frozen rule: each `frozen: changed <path>` line in `<frozen-check output>` is a `hard` finding, and nothing else about frozen paths is (never judge a frozen path from the raw diff). Ends: `Under 400 words.`

Content of `spec-reviewer.md`: read `<spec path>` (and `<plan path or none>`) and run `<diff command>` in `<repo root>`; report (a) requirements missing or partial; (b) behaviour or files in the diff the spec did not ask for (scope creep); (c) requirements that look implemented but wrong. Process files (same list as SKILL.md step 5) are never scope creep. Each finding: `- (a|b|c) <file or requirement> | "<quoted spec line>" | <problem and fix in one line>`; the sentence `Quote the spec line for every finding.` Ends: `Under 400 words.`

- [ ] **Step 1: Write the failing tests in `tests/test_review_skill.py`**

```python
from helpers import PLUGIN

REVIEW = PLUGIN / "skills" / "review"
SMELLS = (
    "Mysterious Name", "Duplicated Code", "Feature Envy", "Data Clumps",
    "Primitive Obsession", "Repeated Switches", "Shotgun Surgery",
    "Divergent Change", "Speculative Generality", "Message Chains",
    "Middle Man", "Refused Bequest",
)
SURGICAL_RULES = (...)  # as in Interfaces


def read(name):
    return (REVIEW / name).read_text(encoding="utf-8")


def flat(name):
    return " ".join(read(name).split())
```

(`ruff format` puts one smell per line; keep it that way.) Plus the `frontmatter(text)` helper from `tests/test_capture_learnings_skill.py`. Tests:

- `test_frontmatter`: `name == "review"`; description starts with `"Use when"`, contains `"/ship"`, length ≤ 1024; `argument-hint == "[base-ref] [spec.md] [plan.md]"`; no `disable-model-invocation`.
- `test_skill_dispatches_both_reviewers_in_one_message`: in `flat("SKILL.md")`: `"standards-reviewer.md"`, `"spec-reviewer.md"`, `"in one message"`, `"general-purpose"`, `"## Standards"`, `"## Spec"`, `"git diff <base>...HEAD"`, `"origin/main"`, `"Spec: no spec found"`, `"never merged or reranked"`.
- `test_skill_runs_frozen_check_before_dispatch`: `"frozen-check.py"`, `"--base <base>"`, `"~/.claude/skills/claude-kit/scripts/frozen-check.py"`, `"Frozen: skipped (no spec or plan)"` in the text; `text.index("frozen-check.py") < text.index("in one message")`.
- `test_process_files_are_never_scope_creep`: `"never scope creep"`, `"gate records"`, `"ADRs"`, `"docs/superpowers/README.md"`, `"Capture learnings"` in `flat("SKILL.md")`, and `"never scope creep"` in `flat("spec-reviewer.md")`.
- `test_standards_reviewer_baseline`: every smell and every `SURGICAL_RULES` name in `flat("standards-reviewer.md")`; also `"`hard`"`, `"`judgement`"`, `"wins over the baseline"`, `"linter or formatter"`, `"frozen: changed"`, `"<frozen-check output>"`, `"Under 400 words"`.
- `test_spec_reviewer_axes`: in `flat("spec-reviewer.md")`: `"missing or partial"`, `"scope creep"`, `"implemented but wrong"`, `"Quote the spec line"`, `"Under 400 words"`, `"<spec path>"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_review_skill.py -o addopts=""`
Expected: FAIL (`FileNotFoundError` for `SKILL.md`).

- [ ] **Step 3: Write the three Markdown files** with the content above.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_review_skill.py tests/test_skill_size.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Full suite and lint**

Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`
Expected: no failures; ruff clean.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/review tests/test_review_skill.py
git commit -m "Add claude-kit:review: standards and spec reviewers side by side"
```

### Task 3: Conventions, PR templates and the spec-gate rubric

**Files:**
- Modify: `conventions/engineering-practices.md`
- Modify: `conventions/spec-driven-development.md`
- Modify: `conventions/knowledge-layer.md`
- Modify: `.github/PULL_REQUEST_TEMPLATE.md`
- Modify: `plugin/templates/project/.github/PULL_REQUEST_TEMPLATE.md`
- Modify: `plugin/skills/spec-gate/rubric.md`
- Test: `tests/test_review_skill.py`, `tests/test_templates.py`, `tests/test_spec_gate_skill.py`

**Depends on:** Task 2

**Interfaces:**
- Consumes: `SURGICAL_RULES` from `tests/test_review_skill.py` (Task 2).
- Produces: the convention text the standards reviewer cites; the `- **Frozen:**` field documented under `## Frozen files` in `conventions/spec-driven-development.md`.

Content:
- `engineering-practices.md`: in §2, the bullet `- No dead or commented-out code.` becomes `- No dead or commented-out code introduced by the change.`; after §2's last paragraph (before `## 3. Code review`) add `### Surgical diffs and simplicity` with six bullets, each starting with a bold `SURGICAL_RULES` name followed by a period (`- **Trace every line.** ...`), carrying spec Design §3's six rules in order (the last one names ADR 0018 and ADR 0036 as plain text), and a closing line `The standards reviewer of claude-kit:review checks these rules (ADR 0044).` Definition of done: `no dead code` becomes `no dead code introduced by the change`, and a new bullet `- The diff is surgical: every changed line traces to the spec or task.`
- `spec-driven-development.md`: in `## Spec anatomy`, a bullet `- **Frozen** (optional) — see [Frozen files](#frozen-files).`; a new section `## Frozen files` after `## Plan gate`'s section ends (before `## Parallel plan tasks`): a spec or plan may carry a `- **Frozen:**` header bullet of backticked repo-relative paths or globs (acceptance tests, eval harness, fixtures whose results decide "done"); once approved, implementers never edit those files to make them pass; a frozen file that does not exist yet is created once, exactly as the plan gives it, and never changed after; a needed change goes back to the user as a spec decision; `plugin/scripts/frozen-check.py` enforces it before each push in `/ship` and `/ship-fast`, and only the main session writes a `Frozen-change-approved: <path>` trailer after the user approves (ADR 0042, plain text).
- `knowledge-layer.md`: under `## Conventions`, one bullet: `- **Reviewer-only standards:** \`knowledge/review-standards.md\` holds judgement-call review rules. The standards reviewer of \`claude-kit:review\` reads it; implementers do not, so never link it from \`CLAUDE.md\` or any file loaded at session start. \`claude-kit:capture-learnings\` creates it on first need.`
- Both PR templates, identical, exactly:

```markdown
## What

<!-- one paragraph: what changes and why; link the spec / ADR if there is one -->

<!-- then the smallest visual that shows the change: pseudocode, a call tree, a file tree, a Mermaid diagram or a diff sketch; for a text-only change, a short before/after quote -->

## Merge danger

**Door:** one-way | two-way
<!-- one-way when reverting the PR cannot undo what merging does (data deleted, overwritten or migrated, published history rewritten, something outside the repo changed); otherwise two-way -->

**Blast radius:**
<!-- one word (none, docs, one-command, all-sessions, consumers), then one line on what could break -->

## Definition of done

- [ ] Behaviour is covered by tests (test-first, or the divergence is a named carve-out)
- [ ] Formatter and linter clean; no dead or commented-out code introduced by the change
- [ ] The diff is surgical: every changed line traces to the spec or task
- [ ] CI green
- [ ] Spec status / ADR updated if a decision changed or the work is now implemented
- [ ] `CLAUDE.md` updated if a command, layout, or convention it documents changed
```

- `rubric.md`: after item 8 and before `## Severity`, add:

```markdown
9. **Frozen evaluator.** If the Success criteria name a test or eval file, or
   a test suite the change adds, and the spec has neither a `- **Frozen:**`
   header bullet nor a Decisions entry saying why nothing is frozen, raise a
   `minor` finding. Its fix is to add the bullet with those paths, or a
   Decisions entry saying why nothing is frozen.
```

- [ ] **Step 1: Write the failing tests**

In `tests/test_review_skill.py` (add `REPO` to the helpers import):
- `test_engineering_practices_name_the_surgical_rules`: in the whitespace-collapsed `conventions/engineering-practices.md`: `"### Surgical diffs and simplicity"`, `f"**{name}.**"` for each `SURGICAL_RULES` name, `"The diff is surgical: every changed line traces to the spec or task."`, `"No dead or commented-out code introduced by the change."`, `"no dead code introduced by the change"`, `"ADR 0044"`.
- `test_knowledge_layer_names_the_reviewer_only_file`: `"knowledge/review-standards.md"` and `"never link it from `CLAUDE.md`"` in collapsed `conventions/knowledge-layer.md`.

In `tests/test_templates.py`:
- `test_pr_templates_state_merge_danger_and_surgical_diffs`: read `PLUGIN.parent / ".github" / "PULL_REQUEST_TEMPLATE.md"` and `PROJECT / ".github" / "PULL_REQUEST_TEMPLATE.md"`; assert equal; assert `"## Merge danger"`, `"**Door:** one-way | two-way"`, `"**Blast radius:**"`, `"smallest visual"`, `"The diff is surgical: every changed line traces to the spec or task"`, `"introduced by the change"` in it.

In `tests/test_spec_gate_skill.py`:
- `test_rubric_checks_frozen_bullet`: `rubric.index("8. **ADR triggers.**") < rubric.index("9. **Frozen evaluator.**") < rubric.index("## Severity")`; `"- **Frozen:**"` in the rubric; `"`minor`"` in the item-9 slice.
- `test_frozen_field_is_documented`: the `## Frozen files` section of `conventions/spec-driven-development.md` (split on `"## Frozen files"`, then on `"\n## "`) contains `"- **Frozen:**"`, `"frozen-check.py"`, `"Frozen-change-approved: <path>"`, `"created once"`, `"ADR 0042"`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_review_skill.py tests/test_templates.py tests/test_spec_gate_skill.py -o addopts=""`
Expected: FAIL on the five new tests only.

- [ ] **Step 3: Make the edits** listed under Content (Edit tool; the PR templates are CRLF in the working tree, Write them whole).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_review_skill.py tests/test_templates.py tests/test_spec_gate_skill.py tests/test_docs.py -o addopts=""`
Expected: all PASS (`test_docs.py` covers relative links).

- [ ] **Step 5: Full suite and lint**

Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`
Expected: no failures; ruff clean.

- [ ] **Step 6: Commit**

```bash
git add conventions .github/PULL_REQUEST_TEMPLATE.md plugin/templates/project/.github/PULL_REQUEST_TEMPLATE.md plugin/skills/spec-gate/rubric.md tests
git commit -m "Surgical-diff rules, Frozen field, Merge danger in PR templates"
```

### Task 4: Harden step in `capture-learnings`

**Files:**
- Modify: `plugin/skills/capture-learnings/SKILL.md`
- Test: `tests/test_capture_learnings_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the skill takes an optional argument `--auto` (passed by `/ship` and `/ship-fast`; absent on a hand run); its Learnings summary gains a `Hardening:` block (`Hardening: none` when empty) whose lines start `harden (mechanical):`, `harden (steering):` or `harden (navigation):`. Tasks 5 and 6 pass `--auto` and copy the `Hardening:` lines into the PR body.

Content (spec Design §1):
- Frontmatter gains `argument-hint: [--auto]`.
- A short `## Mode` paragraph before `## Steps`: with the argument `--auto` (passed by `/ship` and `/ship-fast`, so `/ship-many` children pass it too), never build a mechanical proposal; without it (a hand run), after returning the summary, offer once to build the mechanical proposals and build them only on a yes, as a separate commit with its tests.
- New step `4. **Harden.**` between `3. **Route**` and the renumbered `5. **Write and commit.**`; `Return` becomes `6. **Return**`. Its inputs: step 1's candidates plus every review finding fixed in this feature (from the review reports that reached the session) and every CI failure's cause; step 2's filter still applies. Each mistake (done wrong, then corrected by a review, CI, a failed command or the user) is classified:
  - `**Mechanical:**` a fixed pattern a tool could detect without judgement (banned API or import, file-location or naming rule, forbidden string, missing file, format) → line `harden (mechanical): <mistake> → <lint rule | hook | test | CI check> in <file>: <the rule>`; prefer extending an existing check (read the lint config, test layout and `.github/workflows/` first); an existing check not wired into CI or a pre-commit/pre-push hook is itself the proposal.
  - `**Judgement call:**` needs reading the code in context → one terse imperative bullet under `## Rules` in `knowledge/review-standards.md`, in the same `Capture learnings` commit. If the file is missing, create it with frontmatter `title: Review standards`, `status: stable`, `last_updated: <today>`, `sources: []`, one line saying it is read by the standards reviewer of `claude-kit:review` and not by implementers, then `## Rules`; if `knowledge/README.md` exists, add a row for it in its map. The sentence `Never link this file from `CLAUDE.md` or any file an implementer loads at session start.`
  - `**Steering bloat:**` (report only) read root and nested `CLAUDE.md`; flag no-op, duplicate, to-check or to-standards rules → `harden (steering): <file>:<line> <no-op | duplicate | to-check | to-standards>: <why>`. The sentence `Do not edit these files for this scan.`
  - `**Navigation and information access:**` (report only) → `harden (navigation): <what was hard to find> → <pointer to add, where>`.
- Step 5 (Write and commit) also writes `knowledge/review-standards.md` in the same commit.
- Step 6 (Return) gains: after the learnings lines, a `Hardening:` block, one line per harden line, or `Hardening: none`; a rule written to the standards file appears among the learnings as `knowledge/review-standards.md: <rule>`.

- [ ] **Step 1: Write the failing tests** in `tests/test_capture_learnings_skill.py`:

- `test_harden_step_sits_between_route_and_commit`: in `flat()`: `index("3. **Route**") < index("4. **Harden.**") < index("5. **Write and commit.**") < index("6. **Return**")`.
- `test_harden_classifies_mistakes`: `"**Mechanical:**"`, `"**Judgement call:**"`, `"harden (mechanical):"`, `"harden (steering):"`, `"harden (navigation):"`, `"knowledge/review-standards.md"`, `"## Rules"`, `"status: stable"`, `"Hardening:"`, `"Hardening: none"`, `"CI failure"` in `flat()`.
- `test_steering_scan_does_not_edit`: `"Do not edit these files for this scan."` in `flat()`.
- `test_standards_file_is_never_linked_from_claude_md`: `"Never link this file from `CLAUDE.md`"` in `flat()`.
- `test_mechanical_proposals_are_built_only_on_a_hand_run`: `frontmatter(body())["argument-hint"] == "[--auto]"`; `"## Mode"`, `"--auto"`, `"/ship-many"`, `"only on a yes"`, `"separate commit"` in `flat()`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_capture_learnings_skill.py -o addopts=""`
Expected: FAIL on the five new tests; the existing ones pass.

- [ ] **Step 3: Edit `plugin/skills/capture-learnings/SKILL.md`** per Content.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_capture_learnings_skill.py tests/test_skill_size.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Full suite and lint**

Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`
Expected: no failures; ruff clean.

- [ ] **Step 6: Commit**

```bash
git add plugin/skills/capture-learnings/SKILL.md tests/test_capture_learnings_skill.py
git commit -m "capture-learnings: Harden step and Hardening summary"
```

### Task 5: `/ship`: frozen check, two-axis review and the PR body reference

**Files:**
- Create: `plugin/references/pr-body.md`
- Modify: `plugin/commands/ship.md`
- Modify: `plugin/references/ship-finish.md`
- Test: `tests/test_ship_command.py`

**Depends on:** Task 1, Task 2, Task 4

**Interfaces:**
- Consumes: Task 1's CLI (exit codes 0/1/2); Task 2's `claude-kit:review` (arguments, `hard`/`judgement`, kinds (a)/(b)/(c), `## Standards`/`## Spec`); Task 4's `--auto` argument and `Hardening:` block.
- Produces: `plugin/references/pr-body.md` with `## Shared parts`, `## /ship body, in this order`, `## /ship-fast body, in this order`; Task 6 points to it.

Content of `plugin/references/pr-body.md` (headings and `- ` bullets only; no column-0 numbered lines; no `$(`):
- Title `# PR body for /ship and /ship-fast` and one line: read by `commands/ship.md` step 7 and `references/ship-fast-finish.md` step 7 when they write the PR body file.
- `## Shared parts`: **Summary** (two to five lines, then the smallest visual that shows the change: pseudocode, a call tree, a file tree, a Mermaid diagram, or a `diff` sketch of one of those; one visual, two at most; a text-only change gets none and quotes a short before and after instead). **Merge danger**: `**Door:** one-way | two-way` with one line why: one-way when merging does something reverting the PR cannot undo, by the irreversible test of `/ship` step 3a (deletes, overwrites or migrates data not regenerable from the repo, rewrites published git history, or changes something outside the repository); otherwise two-way. `**Blast radius:** <one word>` (for example `none`, `docs`, `one-command`, `all-sessions`, `consumers`) with one line on what could break. **Hardening proposals**: the `Hardening:` lines from the capture-learnings summary, verbatim; omitted when `Hardening: none`.
- `## /ship body, in this order`: Summary; links to the spec, the plan and the plan gate record (`docs/superpowers/gates/plans/<plan file name>`); a section listing verbatim each entry of the plan record's `## Plan-introduced decisions` (omitted when that list is `none`), titled `Plan decisions (auto-approved)` when the record has `- **Approved by:** /ship (auto)` and `Plan decisions` otherwise; Merge danger; Review (per `claude-kit:review` axis, Standards and Spec, one line on the findings fixed and one on the `judgement` findings left, plus the findings the final whole-branch review fixed); Hardening proposals; Verification (the exact commands and their results); the attribution line the session requires.
- `## /ship-fast body, in this order`: Summary; Acceptance criteria, each with its evidence (the test name or the smoke-run output); Decisions (every question the user answered, then the product choices "assumed (not asked)"); Assumptions (engineering choices taken without asking); Cut (what the POC leaves out); Merge danger; Hardening proposals; links to the spec and the task list; Verification (the exact commands and their results); the attribution line the session requires.

Edits to `plugin/commands/ship.md` (3-space indent inside steps):
- Stop rules, new bullet after the PR-title bullet: `` `frozen-check.py` exits 1 (see Frozen check). Report each changed path. The user answers by approving the change or by revising the spec. On approval, and only then, the main session runs `git commit --allow-empty` after the change commit, with one `Frozen-change-approved: <path>` trailer line per approved path, and continues from the push it stopped before. Implementers and subagents never write that trailer. ``
- New section `## Frozen check` between `## Git lock retry` and `## Steps` (no word "pre-flight" in it): before every `git push` in steps 5 to 9 (step 7's push, step 8's fix loop and step 9's rebase included), run `python "${CLAUDE_PLUGIN_ROOT}/scripts/frozen-check.py" <spec> <plan>` (fallback if the variable is not expanded: `~/.claude/skills/claude-kit/scripts/frozen-check.py`) in the feature worktree. Exit 0: push. Exit 1: the frozen stop rule. Exit 2 (bad usage, unreadable file, git failure): debug it with `superpowers:systematic-debugging` and rerun before pushing; it is not a stop rule.
- Step 3's quoted prompt: after the sentence ending `(none if the section is missing).`, add (as `   > ` lines) `Copy the spec's `**Frozen:**` bullet into the plan header, adding any test or eval file whose full content the plan writes and that a success criterion depends on.`
- Step 4: after the sentence ending `before the next task.`, add: `Pass each implementer and task reviewer this global constraint, with <list> the plan's `**Frozen:**` paths (skip it when the plan has none): "Files under Frozen (`<list>`) that exist are read-only. One that does not exist yet is created once, exactly as the plan gives it, and never changed after that commit. Report any other needed change as a blocker."`
- Step 5: `` `git push -u origin feat/<slug>`. `` becomes `` Run the frozen check, then `git push -u origin feat/<slug>`. ``; its fix loop's `fix, commit, push` becomes `fix, commit, run the frozen check, push`.
- Step 6 rewritten: if this session did not receive, during step 4 of this run, the report of the final whole-branch review that step 4's skill runs (SDD's final review or `parallel-tasks`' final review), for example on a run resumed in another session, first use `superpowers:requesting-code-review` on `origin/main..HEAD`, then `superpowers:receiving-code-review`, and fix every finding you can verify. Then, on every run, run the `claude-kit:review` skill with base `origin/main`, the spec and the plan. Fix every `hard` standards finding and every spec finding of kind (a) or (c) you can verify; remove scope creep (b) unless removing it breaks a requirement. Fix a `judgement` finding when the fix is small and clearly better; keep the rest for the PR body and the report. Commit, re-run the full test suite and lint, run the frozen check, push. A finding from any of these reviews that needs a scope, product or behaviour decision the spec does not settle is a stop rule.
- Step 7: `First run the `claude-kit:capture-learnings` skill.` becomes `First run the `claude-kit:capture-learnings` skill with the argument `--auto`.`; `then `git push`` becomes `then run the frozen check and `git push``; the sentence from `The body has:` through `the attribution line the session requires.` is replaced by `Write the body by `${CLAUDE_PLUGIN_ROOT}/references/pr-body.md` (fallback if the variable is not expanded: `~/.claude/skills/claude-kit/references/pr-body.md`): its shared parts and its `/ship` list.` Keep the title rules, the Bash-tool rule and the title comparison unchanged.

Edits to `plugin/references/ship-finish.md` (4-space indent for steps 10–12):
- Header line: `That command's Stop rules and Git lock retry apply here.` → `That command's Stop rules, Git lock retry and Frozen check apply here.`
- Step 9: `re-run tests, `git push --force-with-lease`` → `re-run tests, run the frozen check, `git push --force-with-lease``.
- Step 12: `the review findings you fixed (from whichever review ran in step 4 or step 6)` → `the review findings you fixed (from the review in step 4 or step 6) and, per `claude-kit:review` axis (Standards, Spec), the findings fixed and the `judgement` findings left`.

- [ ] **Step 1: Write the failing tests** in `tests/test_ship_command.py` (import `PLUGIN` from helpers too):

```python
def _frozen():
    rule = SHIP.split("## Frozen check", 1)[1].split("## Steps", 1)[0]
    return " ".join(rule.split())
```

- `test_frozen_check_runs_before_every_push`: in `_frozen()`: `'frozen-check.py" <spec> <plan>'`, `"~/.claude/skills/claude-kit/scripts/frozen-check.py"`, `"superpowers:systematic-debugging"`, `"not a stop rule"`, `"step 8's fix loop"`; and `"frozen check" in _step(n)` for each `n` in `(5, 6, 7, 9)`.
- `test_frozen_violation_is_a_stop_rule`: in `" ".join(_stops().split())`: `"`frozen-check.py` exits 1"`, `"git commit --allow-empty"`, `"Frozen-change-approved: <path>"`, `"Implementers and subagents never write that trailer"`.
- `test_plan_prompt_copies_the_frozen_bullet`: `"**Frozen:**" in _quoted(3)`.
- `test_step_four_passes_the_frozen_constraint`: `"Files under Frozen (`<list>`) that exist are read-only" in _step(4)` and `"created once, exactly as the plan gives it" in _step(4)`.
- `test_step_six_runs_the_two_axis_review_every_run`: `step = _step(6)`; `"on every run, run the `claude-kit:review` skill" in step`; `"`hard`"`, `"`judgement`"`, `"scope creep"` in step; `step.index("superpowers:requesting-code-review") < step.index("claude-kit:review")`.
- `test_pr_body_follows_the_reference`: `step = _step(7)`; `"references/pr-body.md"`, `"~/.claude/skills/claude-kit/references/pr-body.md"`, `"**Door:**"`, `"**Blast radius:**"`, `"Merge danger"`, `"Hardening proposals"` in step.
- `test_capture_learnings_runs_in_auto_mode`: `"`claude-kit:capture-learnings` skill with the argument `--auto`" in _step(7)`.
- `test_report_lists_review_axes`: `"claude-kit:review"` and `"`judgement`"` in `_step(12)`.
- `test_ship_md_stays_under_its_size_budget`: `len((PLUGIN / "commands" / "ship.md").read_bytes()) <= 18_500`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ship_command.py -o addopts=""`
Expected: FAIL on the new tests (except the size test, which passes today); existing tests pass.

- [ ] **Step 3: Create `plugin/references/pr-body.md` and edit `ship.md` and `ship-finish.md`** per Content.

- [ ] **Step 4: Check the size**

Run: `wc -c plugin/commands/ship.md`
Expected: at most 18500. If larger, move step 6's body to `plugin/references/ship-review.md` (headings and bullets only, no column-0 numbered lines), leaving `6. **Review.** Read ...ship-review.md (fallback ...) and follow it.` in `ship.md`, and rerun.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_ship_command.py tests/test_skill_size.py tests/test_ship_many_command.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 6: Full suite and lint**

Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`
Expected: no failures; ruff clean.

- [ ] **Step 7: Commit**

```bash
git add plugin/references/pr-body.md plugin/commands/ship.md plugin/references/ship-finish.md tests/test_ship_command.py
git commit -m "/ship: frozen check, two-axis review, Merge Danger PR body"
```

### Task 6: `/ship-fast`: frozen check and the PR body reference

**Files:**
- Modify: `plugin/commands/ship-fast.md`
- Modify: `plugin/references/ship-fast-finish.md`
- Test: `tests/test_ship_fast_command.py`

**Depends on:** Task 1, Task 4, Task 5

**Interfaces:**
- Consumes: Task 1's CLI; Task 4's `--auto`; Task 5's `plugin/references/pr-body.md` (`## /ship-fast body, in this order`).
- Produces: nothing later tasks use.

Content:
- `ship-fast.md` Stop rules: new bullet after `PR CI is red after 2 fix attempts. Report the open PR link.`: `` `frozen-check.py` exits 1 before a push in step 7. Report each changed path (and the open PR link, if any). The user approves the change, and only then the main session runs `git commit --allow-empty`, after the change commit, with one `Frozen-change-approved: <path>` trailer line per approved path; or the user revises the spec. ``
- `ship-fast-finish.md` step 7 (3-space indent): `First run the `claude-kit:capture-learnings` skill, then` → `First run the `claude-kit:capture-learnings` skill with the argument `--auto`, then run the frozen check and`; replace the sentence `The body has: ... the attribution line the session requires.` with `Write the body by `${CLAUDE_PLUGIN_ROOT}/references/pr-body.md` (fallback if the variable is not expanded: `~/.claude/skills/claude-kit/references/pr-body.md`): its shared parts and its `/ship-fast` list.`; in the CI loop, `commit, push, count one attempt` → `commit, run the frozen check, push, count one attempt`; and add one sentence at the end of the step: `**Frozen check:** before each push in this step, run `python "${CLAUDE_PLUGIN_ROOT}/scripts/frozen-check.py" <spec>` (fallback `~/.claude/skills/claude-kit/scripts/frozen-check.py`; the task list carries no Frozen bullet). Exit 0: push. Exit 1: a stop rule. Exit 2: debug it with `superpowers:systematic-debugging` and rerun before pushing.` Do not name `spec-gate`, `plan-gate` or `requesting-code-review` anywhere.

- [ ] **Step 1: Write the failing tests** in `tests/test_ship_fast_command.py` (import `PLUGIN` from helpers):

- `test_frozen_check_before_each_push`: `step = _step(7)`; `'frozen-check.py" <spec>'`, `"~/.claude/skills/claude-kit/scripts/frozen-check.py"`, `"superpowers:systematic-debugging"` in step; `step.index("frozen check") < step.index("git push -u origin poc/<slug>")`.
- `test_frozen_violation_is_a_stop_rule`: stops = whitespace-collapsed `SHIP_FAST.split("## Stop rules", 1)[1].split("\n## ", 1)[0]`; `"`frozen-check.py` exits 1"` and `"Frozen-change-approved: <path>"` in stops.
- `test_pr_body_follows_the_reference`: `"references/pr-body.md"` and `"--auto"` in `_step(7)`; body = `(PLUGIN / "references" / "pr-body.md").read_text(encoding="utf-8")`; its `/ship-fast` part (`body.split("## /ship-fast body", 1)[1]`) contains `"Acceptance criteria"`, `"Merge danger"`, `"Hardening proposals"`, `"Cut"`, `"Assumptions"`.
- `test_quick_review_is_still_code_review`: `"code-review" in _step(6)` and `"claude-kit:review" not in SHIP_FAST`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ship_fast_command.py -o addopts=""`
Expected: FAIL on the first three new tests; `test_quick_review_is_still_code_review` and the existing tests pass.

- [ ] **Step 3: Edit `ship-fast.md` and `ship-fast-finish.md`** per Content (Edit tool; CRLF).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ship_fast_command.py tests/test_skill_size.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Full suite and lint**

Run: `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`
Expected: no failures; ruff clean.

- [ ] **Step 6: Commit**

```bash
git add plugin/commands/ship-fast.md plugin/references/ship-fast-finish.md tests/test_ship_fast_command.py
git commit -m "/ship-fast: frozen check and Merge Danger PR body"
```

### Task 7: ADRs, README, version bump and final checks

**Files:**
- Create: `knowledge/decisions/0041-two-axis-review-in-ship.md`
- Create: `knowledge/decisions/0042-frozen-evaluator-diff-check.md`
- Create: `knowledge/decisions/0043-harden-in-capture-learnings.md`
- Create: `knowledge/decisions/0044-surgical-diffs-and-simplicity.md`
- Create: `knowledge/decisions/0045-merge-danger-in-pr-bodies.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Modify: `docs/superpowers/README.md`
- Test: `tests/test_plugin_manifest.py`, `tests/test_review_skill.py`

**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5, Task 6

**Interfaces:**
- Consumes: the names every earlier task introduced (for the README and ADR text).
- Produces: nothing.

Content:
- First run `git fetch origin` and `git ls-tree --name-only origin/main knowledge/decisions/`; if any of 0041–0045 is taken, use the next free numbers here and update every place the numbers appear: the ADR file names, the index rows, the `ADRS` tuple in `tests/test_review_skill.py`, "ADR 0042"/"ADR 0044" in `conventions/` and the tests from Task 3, and every other "ADR 004x" mention in this change (`git diff origin/main | grep -n "004[1-5]"`).
- Each ADR in the format of `knowledge/decisions/0039-handoff-ages-by-written.md` (`# ADR NNNN: <title>`, `- **Status:** accepted`, `- **Date:** 2026-11-10`, `## Context`, `## Decision` with the rejected alternatives, `## Consequences`), from spec "ADRs" and Decisions D1–D10:
  - 0041 "Two-axis review in `/ship`": step 6 always runs `claude-kit:review` besides the superpowers final review; axes reported apart; amends ADR 0037 (two diff-only reviewer subagents per run, shifting the token baseline). Rejected: replace the final review; run only when it did not run.
  - 0042 "Frozen evaluator as a diff check and a stop rule": the `Frozen:` field, snapshot rule, `Frozen-change-approved:` trailer by the main session only (D7). Rejected: a PreToolUse hook (ADR 0007: hooks exit 0); editing the Frozen bullet to unfreeze (re-gates spec and plan).
  - 0043 "Harden step in capture-learnings": mechanical mistakes proposed, not built, under `/ship`, `/ship-fast` and `/ship-many` children (`--auto`); judgement calls to `knowledge/review-standards.md`; steering scan report-only. Rejected: a separate `/retro` skill; `/ship`'s clean-up.
  - 0044 "Surgical diffs and simplicity": Design §3 rules as a workspace convention and in the Definition of done, checked by the standards reviewer; "ask" limited to design. Rejected: installing the karpathy-guidelines plugin.
  - 0045 "Merge Danger in PR bodies": door, blast radius, smallest visual in `/ship`/`/ship-fast` bodies and the PR template; one-way by step 3a's irreversible test. Rejected: keep the PR body as it is.
- `knowledge/decisions/README.md`: five index rows in the existing table format, e.g. `| [0041](0041-two-axis-review-in-ship.md) | Two-axis review in `/ship` | accepted | 2026-11-10 |`.
- `README.md`: in the `plugin/` bullet, the skills list becomes `` `audit-deep`, `pr-review-respond`, `capture-learnings` and `review` skills `` (with `review` described in a parenthesis: a standards reviewer and a spec reviewer side by side, run by `/ship`'s review step); after the `/ship <spec.md>` sentence add: `A spec or plan can freeze its acceptance tests with a `- **Frozen:**` bullet; `frozen-check.py` checks them before every push and a changed frozen file stops the run.`
- `plugin.json`: `"version": "0.28.0"`; description gains, before the final period: `, and a review skill that runs a standards reviewer and a spec reviewer side by side in /ship's review step, with a frozen-file check before each push`.
- `docs/superpowers/README.md`: regenerate with `python plugin/scripts/spec-index.py docs/superpowers` (never by hand).

- [ ] **Step 1: Write the failing tests**

In `tests/test_plugin_manifest.py`: rename `test_version_is_0_27_1` to `test_version_is_0_28_0` asserting `data["version"] == "0.28.0"`; add `test_description_mentions_review`: `"review skill"` and `"frozen-file check"` in `data["description"]`.

In `tests/test_review_skill.py`, add:

```python
ADRS = (
    "0041-two-axis-review-in-ship.md",
    "0042-frozen-evaluator-diff-check.md",
    "0043-harden-in-capture-learnings.md",
    "0044-surgical-diffs-and-simplicity.md",
    "0045-merge-danger-in-pr-bodies.md",
)


def test_adrs_exist_and_are_indexed():
    decisions = REPO / "knowledge" / "decisions"
    index = (decisions / "README.md").read_text(encoding="utf-8")
    for adr in ADRS:
        assert (decisions / adr).is_file(), adr
        assert f"]({adr})" in index, adr
    assert "0037" in (decisions / ADRS[0]).read_text(encoding="utf-8")


def test_readme_names_the_review_skill_and_frozen_check():
    readme = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    assert "`review`" in readme and "frozen-check.py" in readme
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_plugin_manifest.py tests/test_review_skill.py -o addopts=""`
Expected: FAIL on the four new or renamed tests.

- [ ] **Step 3: Write the ADRs, index rows, README and manifest edits; regenerate the spec index**

Run: `python plugin/scripts/spec-index.py docs/superpowers`
Expected: exit 0; `docs/superpowers/README.md` lists this spec and this plan.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_plugin_manifest.py tests/test_review_skill.py tests/test_docs.py -o addopts=""`
Expected: all PASS.

- [ ] **Step 5: Final checks (spec Success criteria 1–4 and 6)**

Run: `pytest -o addopts=""` → all pass. `ruff check plugin tests` and `ruff format --check plugin tests` → clean. `wc -c plugin/commands/ship.md` → at most 18500. `python plugin/scripts/frozen-check.py docs/superpowers/specs/2026-11-10-review-and-guardrails-design.md docs/superpowers/plans/2026-11-10-review-and-guardrails.md` → `frozen: none declared`, exit 0. Build `<pattern>` from the machine's username (`whoami`, without the domain) and every name from `gh repo list --visibility private --json name -q ".[].name"`, joined with `|`, then `git diff origin/main | grep -i -E "<pattern>"` → no output.
Expected: every check as stated; fix and rerun any that is not.

- [ ] **Step 6: Commit**

```bash
git add knowledge/decisions README.md plugin/.claude-plugin/plugin.json docs/superpowers/README.md tests/test_plugin_manifest.py tests/test_review_skill.py
git commit -m "ADRs 0041-0045, README, version 0.28.0"
```

## After merge (for `/ship` step 10; spec Success criterion 5)

In step 10's detached `<tmp>` worktree at `<squash-commit>`, after its test suite, lint and `main` CI watch and before `git worktree remove --force <tmp>`: run `claude-kit:review` with base `<squash-commit>~1`, this spec and this plan (paths inside `<tmp>`). If the loaded plugin has no `review` skill yet (the installed plugin is a junction to the main checkout, which may be behind), read and follow `<tmp>/plugin/skills/review/SKILL.md` from the file. Record the finding counts per axis (the report's `Findings:` line) in `/ship`'s step 12 report message. This check changes nothing; its findings are not a stop rule.
