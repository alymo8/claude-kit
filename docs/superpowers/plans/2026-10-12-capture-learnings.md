# Capture learnings at feature finish Implementation Plan

- **Status:** draft
- **Date:** 2026-10-12

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `capture-learnings` skill to the claude-kit plugin and wire it into `/ship` step 7, `/ship-fast` step 7 and the workspace rule for manual finishes, so each feature's learnings land in its own PR.

**Architecture:** One flow-invoked skill (`plugin/skills/capture-learnings/SKILL.md`) holds the whole procedure: collect, filter, route by kind, write, commit, return a summary. The commands only call it at the start of their PR step and add its summary to their report. The convention, the workspace `CLAUDE.md`, an ADR, the README and the plugin manifest describe it. Every change is Markdown or JSON, checked by structure tests in `tests/`.

**Tech Stack:** Markdown skill and command files, Python 3 + pytest structure tests, ruff.

**Spec:** `docs/superpowers/specs/2026-10-12-capture-learnings-design.md`

## Context for the executor

This repo is claude-kit, a Claude Code plugin under `plugin/` plus workspace
conventions under `conventions/`. Commands (`plugin/commands/*.md`) and skills
(`plugin/skills/<name>/SKILL.md`) are prompts that Claude follows; tests in
`tests/` check their text with plain string and regex assertions.
`tests/helpers.py` exports `PLUGIN` (the `plugin/` path) and `REPO` (the repo root).

Setup, once per machine: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`.
Before every commit run the full suite and lint:

```bash
pytest -q
ruff check plugin tests
ruff format --check plugin tests
```

Decisions already made (do not reopen):
- Learnings are captured when a feature finishes, not at session end; no hook.
- They are committed on the feature branch before the PR is created, so they ride in the PR.
- No approval pause; the calling flow's report lists them.
- One flow-invoked skill, not copies in each command (commands run in other repos, which can only reach `plugin/`).
- Route by kind to existing homes: repo `CLAUDE.md`, `knowledge/`, an ADR, or auto-memory.
- `/handoff`, `/ship-many` and `superpowers:finishing-a-development-branch` stay unchanged.

Answers to the spec gate's plan questions (built into the tasks below):
- `tests/test_ship_fast_command.py` gets its own `_step` helper, like `tests/test_ship_command.py` (Task 3).
- The skill also mines subagent/task reports and CI fix-loop history for candidates (Task 1, step 1 of the skill).
- `/ship` runs the full test suite and lint after a learnings commit and before pushing; `/ship-fast` relies on CI from its existing push (Tasks 2, 3).
- When an existing `CLAUDE.md` lacks the matching heading, the skill appends that heading at the end of the file (Task 1).
- The skill adds an index row to `knowledge/decisions/README.md` for every ADR it writes when that index exists; this change's own ADR 0031 gets its row (Tasks 1, 5).
- The skill re-reads `MEMORY.md` right before adding its pointer line and adds one line instead of rewriting the file, so concurrent `/ship-many` children do not overwrite each other (Task 1).
- On a `/ship-fast` resume at step 7, the "already recorded at its destination" filter means nothing new is written and no second commit is made (Task 1).

## Global Constraints

- Skill frontmatter `name: capture-learnings`; `description` starts with "Use when"; no `disable-model-invocation`.
- Commit subject of the skill's own commit: `Capture learnings`.
- `CLAUDE.md` limit: an entry goes to `knowledge/` when `CLAUDE.md` would have more than 100 lines after the addition.
- Never write secrets, credentials, connection strings, personal data, or names of other private repos or of user accounts, in any repo.
- `plugin/.claude-plugin/plugin.json` version goes from `0.21.0` to `0.22.0`.
- Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Private-name check before every commit (the kit repo is public): run `gh repo list --visibility private --limit 200 --json name -q '.[].name'`, then for each name `git diff origin/main -U0 | grep -i -w -F "<name>"` plus the same on `git diff --cached -U0` → no output. Never write those names themselves into a tracked file.

## Review Focus

- A repo with no `knowledge/` or no `knowledge/decisions/` (an unscaffolded repo): the skill must fall back, not create a half-formed decision log. Pinned by `test_missing_homes_have_fallbacks` (Task 1).
- A rerun or resume after a learnings commit: no duplicate entries, no second commit. Pinned by `test_rerun_writes_nothing_new` (Task 1).
- Concurrent `/ship-many` children editing the same `MEMORY.md`: re-read before adding one line. Pinned by `test_memory_index_is_reread_before_adding` (Task 1).
- An ADR written by the skill without its index row: pinned by `test_adr_gets_an_index_row` (Task 1).
- A `/ship` learnings commit pushed untested: pinned by `test_learnings_commit_is_tested_before_push` (Task 2).

---

### Task 1: The `capture-learnings` skill

**Files:**
- Create: `plugin/skills/capture-learnings/SKILL.md`
- Test: `tests/test_capture_learnings_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the skill name `claude-kit:capture-learnings` and a returned "Learnings summary" that Tasks 2 and 3 tell their report steps to include.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_capture_learnings_skill.py`:

```python
"""Structure tests for the capture-learnings skill."""

from __future__ import annotations

from helpers import PLUGIN

SKILL = PLUGIN / "skills" / "capture-learnings" / "SKILL.md"


def body():
    return SKILL.read_text(encoding="utf-8")


def flat():
    """The body with all whitespace runs collapsed, so wrapped phrases match."""
    return " ".join(body().split())


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(body())
    assert front["name"] == "capture-learnings"
    assert front["description"].startswith("Use when")
    assert "/ship" in front["description"]
    assert "/ship-fast" in front["description"]
    assert "disable-model-invocation" not in front


def test_routes_every_kind():
    text = flat()
    for needle in ("CLAUDE.md", "knowledge/", "knowledge/decisions/", "MEMORY.md"):
        assert needle in text, needle


def test_none_is_a_valid_result():
    text = flat()
    assert "`none`" in text
    assert "write nothing" in text
    assert "dropped candidate" in text
    assert "rule that dropped it" in text


def test_never_writes_secrets():
    text = flat().lower()
    for needle in ("secrets", "personal data", "private repos"):
        assert needle in text, needle


def test_commits_on_the_feature_branch():
    text = flat()
    assert "`Capture learnings`" in text
    assert "feature branch" in text
    assert "Auto-memory writes are not committed" in text


def test_missing_homes_have_fallbacks():
    text = flat()
    assert "0000-template.md" in text
    assert "no `knowledge/` folder" in text
    assert "no `knowledge/decisions/` folder" in text
    assert "`poc/`" in text


def test_claude_md_limit_is_exact():
    text = flat()
    assert "more than 100 lines" in text


def test_rerun_writes_nothing_new():
    text = flat()
    assert "already recorded at its destination" in text
    assert "no commit" in text


def test_memory_index_is_reread_before_adding():
    text = flat()
    assert "re-read `MEMORY.md`" in text


def test_adr_gets_an_index_row():
    text = flat()
    assert "knowledge/decisions/README.md" in text
    assert "index row" in text


def test_mines_subagent_reports_and_handoff():
    text = flat()
    assert "subagent" in text
    assert ".claude/handoffs/" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_capture_learnings_skill.py -q`
Expected: 11 failed, each with `FileNotFoundError` for `SKILL.md`.

- [ ] **Step 3: Write the skill**

Create `plugin/skills/capture-learnings/SKILL.md` with exactly this content:

````markdown
---
name: capture-learnings
description: Use when /ship or /ship-fast reaches its PR step, or when a feature or change is finished by hand before its branch merges. Writes the session's learnings (gotchas, commands that work, conventions, decisions, the user's corrections) to the repo's CLAUDE.md, knowledge/, an ADR or auto-memory, as one commit on the feature branch, and returns a Learnings summary for the caller's report.
---

# Capture learnings

Runs once per feature, on its feature branch, before the PR is opened (or,
for a manual finish, before the branch merges). The learnings ride in the
feature's PR and are visible in its diff, so there is no approval pause: do
not ask the user to confirm them.

## Steps

1. **Collect candidates** from the work on this feature: the user's
   corrections and stated preferences; commands that failed before one
   worked; surprises (CI failures with a non-obvious cause, platform
   quirks, things that look wrong but are intentional); conventions the
   user set. Include what reached this session through subagent and task
   reports and the CI fix loop, not only what happened in this context.
   Also read the branch's handoff file when present
   (`.claude/handoffs/<branch>.md`, with `/` in the branch written as `_`),
   because a feature may span sessions.
2. **Filter.** Keep a candidate only if a competent newcomer to the repo
   would otherwise waste time on it or get it wrong. Drop anything the
   commit messages, the diff, the spec, the plan or an existing ADR already
   says. Drop anything already recorded at its destination: read the
   destination first, and update an existing entry instead of adding a
   duplicate. On a rerun or resume this drops what an earlier run wrote,
   so nothing new means no commit. Zero learnings is a valid result: write
   nothing and return `none`.
3. **Route** each kept learning by kind:

   | Kind | Destination |
   |---|---|
   | Repo command, gotcha, or convention | The repo's root `CLAUDE.md`, under the matching heading of the kit's project template: Setup / prerequisites; Build, run, test; Conventions; Gotchas. If the file lacks that heading, append it at the end of the file. |
   | Durable finding about the domain or the code | `knowledge/<topic>.md` (the existing file on the topic, else a new one), linked from `CLAUDE.md` only if every session needs it. |
   | A decision with alternatives that a later change could reopen | A new ADR under `knowledge/decisions/`, in the format of the repo's `knowledge/decisions/0000-template.md` (else its `knowledge/decisions/README.md`, else its newest ADR), with the repo's next number. If `knowledge/decisions/README.md` has an index table, add the ADR's index row. |
   | A preference about how Claude should work that holds beyond this repo | Auto-memory: the session's memory directory and its `MEMORY.md` index, following the session's memory instructions. Never a tracked file. |

   Fallbacks:
   - No root `CLAUDE.md`: create it holding only the new entries under
     their headings.
   - `CLAUDE.md` would have more than 100 lines after the addition (a file
     already over that limit always qualifies): put the entry in
     `knowledge/` and link it from `CLAUDE.md` instead.
   - The repo has no `knowledge/` folder: put durable findings in
     `CLAUDE.md` under `## Gotchas`.
   - The repo has no `knowledge/decisions/` folder, or the branch is a
     `poc/` branch (a `/ship-fast` POC, where ADRs are not required): write
     no ADR; list the decision in the summary as `not written:`.
   - The session has no auto-memory directory: list preference learnings
     in the summary as `not written:`.
4. **Write and commit.** Entries are terse and imperative, with exact
   commands in code spans or fences. Never write secrets, credentials,
   connection strings or personal data, and no names of other private
   repos or of user accounts, in any repo (visibility can change). For
   auto-memory, re-read `MEMORY.md` right before adding the pointer line,
   and add one line rather than rewriting the file: parallel runs may
   write it at the same time. Commit the repo files on the feature branch
   as one commit with the subject `Capture learnings` and the session's
   attribution line. Auto-memory writes are not committed. If no repo file
   changed, make no commit.
5. **Return** the Learnings summary for the caller's report:
   - one line per written learning: `<destination>: <learning>`;
   - one line per decision or preference listed instead of written,
     starting `not written:`;
   - when nothing was written: `none`, then each dropped candidate with
     the step-2 rule that dropped it.
````

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_capture_learnings_skill.py -q`
Expected: `11 passed`.

- [ ] **Step 5: Full suite, lint, commit**

Run: `pytest -q` → all pass; `ruff check plugin tests` → `All checks passed!`; `ruff format --check plugin tests` → already formatted.
Run the private-name check from Global Constraints → no output.

```bash
git add plugin/skills/capture-learnings/SKILL.md tests/test_capture_learnings_skill.py
git commit -m "capture-learnings skill

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: Wire the skill into `/ship`

**Files:**
- Modify: `plugin/commands/ship.md`
- Test: `tests/test_ship_command.py`

**Depends on:** none

**Interfaces:**
- Consumes: the skill name `claude-kit:capture-learnings` (Task 1) and its "Learnings summary".
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_ship_command.py` (it already defines `_step(n)`, which returns step `n`'s text with whitespace collapsed):

```python
def test_learnings_are_captured_before_the_pr():
    step = _step(7)
    assert "claude-kit:capture-learnings" in step
    assert step.index("claude-kit:capture-learnings") < step.index("gh pr create")


def test_learnings_commit_is_tested_before_push():
    step = _step(7)
    learn = step.index("claude-kit:capture-learnings")
    assert learn < step.index("full test suite") < step.index("git push")
    assert step.index("git push") < step.index("gh pr create")


def test_report_lists_learnings():
    assert "Learnings summary from step 7" in _step(12)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ship_command.py -q`
Expected: 3 failed (`ValueError: substring not found` / `AssertionError`), the rest pass.

- [ ] **Step 3: Edit `plugin/commands/ship.md`**

In step 7, replace the opening line

```
7. **PR.** The PR title is the spec's **title**: the first line outside code
```

with

```
7. **PR.** First run the `claude-kit:capture-learnings` skill. If it made a
   commit, run the full test suite and lint from `CLAUDE.md`, then
   `git push`. The PR title is the spec's **title**: the first line outside code
```

In step 12, replace these two lines

```
    (and why not, if not), the review findings you fixed, and anything left out
    and why.
```

with

```
    (and why not, if not), the review findings you fixed, the Learnings
    summary from step 7, and anything left out and why.
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ship_command.py -q`
Expected: all pass.

- [ ] **Step 5: Full suite, lint, commit**

Run: `pytest -q` → all pass; `ruff check plugin tests` → `All checks passed!`; `ruff format --check plugin tests` → already formatted.
Run the private-name check from Global Constraints → no output.

```bash
git add plugin/commands/ship.md tests/test_ship_command.py
git commit -m "/ship: capture learnings before the PR

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: Wire the skill into `/ship-fast`

**Files:**
- Modify: `plugin/commands/ship-fast.md`
- Test: `tests/test_ship_fast_command.py`

**Depends on:** none

**Interfaces:**
- Consumes: the skill name `claude-kit:capture-learnings` (Task 1) and its "Learnings summary".
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing tests**

In `tests/test_ship_fast_command.py`, add `import re` to the imports (above `from helpers import PLUGIN`, keeping ruff's import order), and append:

```python
def _step(n):
    match = re.search(rf"^{n}\. (.*?)(?=^\d+\. |^## |\Z)", SHIP_FAST, re.M | re.S)
    assert match, n
    return " ".join(match.group(1).split())


def test_learnings_are_captured_before_the_push():
    step = _step(7)
    assert "claude-kit:capture-learnings" in step
    learn = step.index("claude-kit:capture-learnings")
    assert learn < step.index("git push -u origin poc/<slug>")


def test_report_lists_learnings():
    assert "Learnings summary from step 7" in _step(9)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_ship_fast_command.py -q`
Expected: 2 failed, the rest pass.

- [ ] **Step 3: Edit `plugin/commands/ship-fast.md`**

In step 7, replace

```
7. **PR.** `git push -u origin poc/<slug>`. (Each CI fix commit restarts
```

with

```
7. **PR.** First run the `claude-kit:capture-learnings` skill, then
   `git push -u origin poc/<slug>` (it carries any learnings commit, which
   changes no app code and needs no restart). (Each CI fix commit restarts
```

Then re-wrap that paragraph's first lines to the file's usual width (about 75 characters) without changing any other words.

In step 9 (Report), replace

```
   fixes; the CI result
```

with

```
   fixes; the Learnings summary from step 7; the CI result
```

and re-wrap the paragraph the same way.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_ship_fast_command.py -q`
Expected: all pass (including `test_no_gates_no_review_round_no_merge`, which forbids `spec-gate`, `plan-gate`, `gh pr merge` and `requesting-code-review` in this file).

- [ ] **Step 5: Full suite, lint, commit**

Run: `pytest -q` → all pass; `ruff check plugin tests` → `All checks passed!`; `ruff format --check plugin tests` → already formatted.
Run the private-name check from Global Constraints → no output.

```bash
git add plugin/commands/ship-fast.md tests/test_ship_fast_command.py
git commit -m "/ship-fast: capture learnings before the push

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: Workspace rule and convention

**Files:**
- Modify: `CLAUDE.md`
- Modify: `conventions/project-memory.md`
- Test: `tests/test_docs.py`

**Depends on:** none

**Interfaces:**
- Consumes: the skill name `claude-kit:capture-learnings` (Task 1).
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_docs.py` (`REPO` is already imported from `helpers`):

```python
def test_learnings_capture_is_part_of_finishing():
    claude = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    para = claude.split("**A feature is not finished until its workspace is gone.**", 1)[1]
    para = para.split("\n\n", 1)[0]
    assert "claude-kit:capture-learnings" in para
    convention = (REPO / "conventions" / "project-memory.md").read_text(
        encoding="utf-8"
    )
    assert "## Capturing learnings" in convention
    assert "capture-learnings" in convention.split("## Capturing learnings", 1)[1]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_docs.py::test_learnings_capture_is_part_of_finishing -q`
Expected: FAIL with `AssertionError`.

- [ ] **Step 3: Edit the workspace `CLAUDE.md`**

In the paragraph starting `**A feature is not finished until its workspace is gone.** When the work is merged`, insert directly after the bold sentence:

```
Before the branch merges, run the `claude-kit:capture-learnings` skill so the
feature's learnings land in its PR.
```

so the paragraph reads "**A feature is not finished until its workspace is gone.** Before the branch merges, run the `claude-kit:capture-learnings` skill so the feature's learnings land in its PR. When the work is merged ...". Re-wrap only those lines (the file wraps near 84 characters).

- [ ] **Step 4: Edit `conventions/project-memory.md`**

Insert this section directly before `## Definition of done`:

```markdown
## Capturing learnings

A memory file improves only if what a feature taught gets written down. When
a feature or change finishes, before its branch merges, the
`claude-kit:capture-learnings` skill collects the session's learnings and
writes each to its home: repo commands, gotchas and conventions to this file
(or to `knowledge/` once this file would pass 100 lines); durable findings to
the [knowledge layer](knowledge-layer.md); decisions to an ADR in the
[decision log](decision-log.md); the user's preferences about how Claude
works to auto-memory, never a tracked file. The learnings land in the
feature's PR. `/ship` and `/ship-fast` run the skill at their PR step; for a
manual finish, run it yourself. The skill holds the full routing rules.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_docs.py -q`
Expected: all pass (including `test_relative_markdown_links_resolve`, which checks the two new relative links).

- [ ] **Step 6: Full suite, lint, commit**

Run: `pytest -q` → all pass; `ruff check plugin tests` → `All checks passed!`; `ruff format --check plugin tests` → already formatted.
Run the private-name check from Global Constraints → no output.

```bash
git add CLAUDE.md conventions/project-memory.md tests/test_docs.py
git commit -m "Workspace rule and convention: capture learnings when a feature finishes

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 5: ADR, README, plugin manifest

**Files:**
- Create: `knowledge/decisions/0031-capture-learnings-at-feature-finish.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `README.md`
- Modify: `plugin/.claude-plugin/plugin.json`
- Test: `tests/test_plugin_manifest.py`

**Depends on:** none

**Interfaces:**
- Consumes: the skill name `capture-learnings` (Task 1).
- Produces: nothing other tasks use.

- [ ] **Step 1: Write the failing test**

In `tests/test_plugin_manifest.py` (it already imports `json` and `PLUGIN`), replace the existing test at the end of the file

```python
def test_version_is_0_21_0():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "0.21.0"
```

with

```python
def test_version_is_0_22_0():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "0.22.0"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_plugin_manifest.py -q`
Expected: 1 failed (`test_version_is_0_22_0`), the rest pass.

- [ ] **Step 3: Edit `plugin/.claude-plugin/plugin.json`**

Set `"version": "0.22.0"`. Leave `description` unchanged (the spec scopes this file to the version bump only).

- [ ] **Step 4: Write the ADR**

Create `knowledge/decisions/0031-capture-learnings-at-feature-finish.md`:

```markdown
# ADR 0031: Capture learnings when a feature finishes, in its PR

- **Status:** accepted
- **Date:** 2026-10-12

## Context
Sessions learn things later sessions rediscover or get wrong: gotchas,
commands that work, conventions, the user's corrections. `/handoff` moves
findings and decisions at a session's end, but no flow recorded operational
learnings when a feature finished. A `SessionEnd` hook cannot run the model,
and a headless `claude -p` over every transcript costs tokens each session
and writes files nobody reviews.

## Decision
- Learnings are captured when a feature or change finishes, by the
  `capture-learnings` skill: `/ship` and `/ship-fast` run it at the start of
  their PR step; the workspace rule runs it before a manual finish merges.
- It commits on the feature branch, so the learnings land in the feature's
  PR and are reviewable in its diff. No approval pause; the flow's report
  lists them.
- One flow-invoked skill instead of text copied into each command, because
  commands run in other repos and can reach only `plugin/`.
- Each learning goes to an existing home by kind: the repo's `CLAUDE.md`
  (or `knowledge/` once it would pass 100 lines), `knowledge/`, an ADR, or
  auto-memory for preferences. No separate learnings file.
- `/handoff` and `/ship-many` are unchanged; no back-filling of past work.

## Consequences
- In this repo, whose `CLAUDE.md` is already over 100 lines, repo learnings
  go to `knowledge/`.
- `/ship-fast` POC branches and repos without `knowledge/decisions/` get no
  ADRs; decisions are listed in the report instead.
- The learnings commit lands after the step-6 review; `/ship` runs the
  tests and lint on it before pushing, and the PR diff shows it.
```

- [ ] **Step 5: Add the ADR's index row**

In `knowledge/decisions/README.md`, append after the `0030` row:

```
| [0031](0031-capture-learnings-at-feature-finish.md) | Capture learnings when a feature finishes, in its PR | accepted | 2026-10-12 |
```

- [ ] **Step 6: Edit `README.md`**

In the `plugin/` bullet, replace

```
  `audit-deep` and `pr-review-respond` skills (the audits share a citation
```

with

```
  `audit-deep`, `pr-review-respond` and `capture-learnings` skills (the
  audits share a citation
```

That is the README's only change (the spec asks for one line naming the skill where the other skills are listed).

- [ ] **Step 7: Run the tests to verify they pass**

Run: `pytest tests/test_plugin_manifest.py tests/test_docs.py -q`
Expected: all pass (the docs test checks the ADR index link resolves).

- [ ] **Step 8: Full suite, lint, private-name check, commit**

Run: `pytest -q` → all pass; `ruff check plugin tests` → `All checks passed!`; `ruff format --check plugin tests` → already formatted.
Run: `gh repo list --visibility private --limit 200 --json name -q '.[].name'`, then for each name `git diff origin/main -U0 | grep -i -w -F "<name>"` → no output. The kit repo is public; never write those names themselves into a tracked file.

```bash
git add knowledge/decisions/0031-capture-learnings-at-feature-finish.md knowledge/decisions/README.md README.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "ADR 0031, README and manifest for capture-learnings (v0.22.0)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 6: Live check — capture this feature's own learnings

The kit loads commands and skills from the main checkout, so the `/ship` run
that lands this plan still reads the old `ship.md`, whose step 7 has no
learnings step. This task runs the new skill by hand, from this worktree,
before the PR is created. It is executed in the main session (not by a
subagent), because the learnings come from that session's context.

**Files:**
- Create or modify: whatever the skill routes this feature's learnings to. In this repo the root `CLAUDE.md` already has more than 100 lines, so repo learnings go to a file under `knowledge/` (an existing topic file, else a new one) and decisions to a new ADR with its index row in `knowledge/decisions/README.md`.

**Depends on:** Task 1, Task 2, Task 3, Task 4, Task 5

**Interfaces:**
- Consumes: `plugin/skills/capture-learnings/SKILL.md` as written by Task 1, read from this worktree.
- Produces: the Learnings summary that `/ship`'s report (step 12) includes.

- [ ] **Step 1: Follow the skill**

Read `plugin/skills/capture-learnings/SKILL.md` in this worktree and follow
its five steps on the current session and branch `feat/capture-learnings`,
including the handoff file `.claude/handoffs/feat_capture-learnings.md` if
present. Before the skill's commit (its step 4), run the private-name check
from Global Constraints on `git diff --cached -U0` → no output.

- [ ] **Step 2: Check the result**

Run: `git log -1 --format=%s`
Expected: `Capture learnings` if the skill wrote repo files; otherwise any subject other than `Capture learnings` (a merge commit is possible if tasks were merged back with `--no-ff`), and the summary reads `none` followed by each dropped candidate with the rule that dropped it.
For a `Capture learnings` commit, run `git show --stat HEAD` and confirm every changed file is a routed destination (a `knowledge/` file, an ADR plus its `knowledge/decisions/README.md` row; never `CLAUDE.md` in this repo).

- [ ] **Step 3: Full suite, lint, private-name check, then confirm the skill's commit**

Run: `pytest -q` → all pass; `ruff check plugin tests` → `All checks passed!`; `ruff format --check plugin tests` → already formatted.
Run the private-name check from Global Constraints → no output.
The skill made the commit itself in Step 1 (subject `Capture learnings`); if a check fails, fix the file and commit the fix with `git commit --amend --no-edit` only while that commit is still unpushed.

- [ ] **Step 4: Carry the summary into the report**

Keep the summary the skill returned and include it as a `Learnings:` line in
the final `/ship` report (step 12), even though the loaded `ship.md` does not
yet ask for it.

## Verification (whole branch)

1. `pytest -q` exits 0; `ruff check plugin tests` and `ruff format --check plugin tests` pass.
2. All tests named in Tasks 1–5 exist and pass:
   `pytest tests/test_capture_learnings_skill.py tests/test_ship_command.py tests/test_ship_fast_command.py tests/test_docs.py tests/test_plugin_manifest.py -q` exits 0.
3. Live check (Task 6): the PR contains a `Capture learnings` commit whose
   entries are each in their routed destination, or the report says
   `Learnings: none` with the dropped candidates and why. Either way the
   report has the Learnings line.
4. The branch diff adds no private repo name (checked against `gh repo list --visibility private`) to a tracked file.
