# Spec Grill Implementation Plan

- **Status:** approved
- **Date:** 2026-10-01

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the opt-in `claude-kit:grill` skill (interview after the design
summary, before the spec), its coverage checklist, a SessionStart hook that
injects the grill rule when `CLAUDE_KIT_GRILL=1`, and lint rule `L9-coverage`
in `spec-lint.py`.

**Architecture:** The skill lives in `plugin/skills/grill/` (`SKILL.md` plus
`coverage.md`, the single list of coverage areas). `grill_inject.py` copies
the shape of `lean_context_inject.py`. `spec-lint.py` gains `check_coverage`,
called from `lint()` (specs only), which reads the area names from
`coverage.md` through a module constant and applies only when the env var is
`1` and the spec's Date is on or after 2026-10-01. Docs: `CLAUDE.md`, the
spec-driven convention, `README.md`, ADR 0019, plugin 0.11.0.

**Tech Stack:** Python 3.11+ standard library, pytest, ruff, Markdown skill
files.

**Spec:** `docs/superpowers/specs/2026-10-01-spec-grill-design.md`

## Context for a cold start

- Work in the feature worktree on branch `feat/spec-grill`, rebased onto
  `origin/main` at `4c76d88` (#25, which added the `teach` skill and set the
  plugin to 0.10.0). The spec and its gate record are already committed on
  the branch.
- Full suite: `pytest` (a few minutes). Lint:
  `ruff check plugin tests; ruff format --check plugin tests`. Run
  `ruff format plugin tests` before committing; E501 (88 columns) applies.
- Tests import scripts with `helpers.load_module(path, name)` and run them
  with `helpers.run_script(script, *args, env=...)`; `helpers.clean_env(**kw)`
  is `os.environ` without any `CLAUDE_KIT_*` variable, plus `kw`.
  `helpers.PLUGIN` is the `plugin/` folder, `helpers.REPO` the repo root.
- `tests/test_spec_lint.py` defines `sl` (the loaded linter), `SCRIPT`,
  `VALID` (a clean spec dated 2026-09-30), a `root` fixture (a tmp folder
  with `src/app.py`) and `rules(text, root)` returning `(line, rule)` pairs.
- In `spec-lint.py`: `parse(text)` returns `Line = (number, text, in_fence)`
  tuples; `sections(lines)` maps each H2 title to `(heading line, body
  lines)`; `find(secs, prefixes)` returns the first section whose lowercased
  title starts with a prefix; `DATE_RE` matches `- **Date:** <value>`;
  `ITEM_RE` matches a list item start; `lint(text, root)` concatenates the
  `check_*` results and sorts them.
- Hooks always exit 0 (ADR 0007). `lean_context_inject.py` is the model for
  the new hook.
- Commit messages end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.

## Global Constraints

- Env var `CLAUDE_KIT_GRILL`: exactly `"1"` is on; unset or any other value
  is off.
- `L9-coverage` applies only when on and the spec Date parses with
  `datetime.date.fromisoformat` to a date on or after 2026-10-01
  (`COVERAGE_FROM`). Plans are never checked.
- The nine areas, in order: Purpose and success; Scope boundary; Interfaces;
  Data and irreversible actions; Failure modes; Security and secrets;
  Testing; Rollout and compatibility; Docs and decisions.
- Standard library only in `spec-lint.py` and the hook.
- ADR 0019; plugin version 0.10.0 → 0.11.0.

## Review Focus

1. A developer with `CLAUDE_KIT_GRILL=1` in their settings runs `pytest`:
   existing lint tests must still pass. Pinned in Task 2 by an autouse
   fixture that deletes the variable.
2. A spec whose area entry wraps onto indented continuation lines must count
   as having text. Pinned in Task 2.
3. A Date that matches the L2 pattern but is not a calendar date
   (`2026-02-30`) must skip L9 rather than crash. Pinned in Task 2.
4. An install without `skills/grill/coverage.md` next to `scripts/` must
   report a violation, not pass silently or crash. Pinned in Task 2.
5. The hook must print nothing for values like `true` or `yes`. Pinned in
   Task 3.

---

### Task 1: Grill skill and coverage checklist

**Files:**
- Create: `plugin/skills/grill/SKILL.md`
- Create: `plugin/skills/grill/coverage.md`
- Test: `tests/test_grill_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: `plugin/skills/grill/coverage.md` with a `## Areas` H2 whose
  bullets are `- **<Area>:** <question>`, the nine areas in Global
  Constraints order. Task 2 reads the bold labels.

- [ ] **Step 1: Write the failing test**

Create `tests/test_grill_skill.py`:

```python
"""Structure tests for the grill skill."""

from __future__ import annotations

import re

from helpers import PLUGIN

GRILL = PLUGIN / "skills" / "grill"
AREAS = [
    "Purpose and success",
    "Scope boundary",
    "Interfaces",
    "Data and irreversible actions",
    "Failure modes",
    "Security and secrets",
    "Testing",
    "Rollout and compatibility",
    "Docs and decisions",
]


def read(name):
    return (GRILL / name).read_text(encoding="utf-8")


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def test_frontmatter():
    front = frontmatter(read("SKILL.md"))
    assert front["name"] == "grill"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert front["argument-hint"] == "[topic]"
    assert "disable-model-invocation" not in front


def test_body_defines_the_procedure():
    body = read("SKILL.md")
    for phrase in ("➡️", "shared understanding", "coverage.md", "MIT"):
        assert phrase in body, phrase
    assert "mattpocock/skills" in body


def test_coverage_lists_the_nine_areas_in_order():
    text = read("coverage.md")
    areas_section = text.split("## Areas", 1)[1].split("\n## ", 1)[0]
    found = re.findall(r"^- \*\*([^*]+?):\*\*", areas_section, re.M)
    assert found == AREAS
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_grill_skill.py -v`
Expected: FAIL with `FileNotFoundError` for `SKILL.md` and `coverage.md`.

- [ ] **Step 3: Create `plugin/skills/grill/coverage.md`**

````markdown
# Coverage checklist

The grill walks every area below, and the spec's `## Coverage` section
answers each one. `spec-lint.py` (rule `L9-coverage`) reads the area names
from the bold labels under `## Areas`, so editing this list changes the grill
and the lint together.

## Areas

- **Purpose and success:** What outcome, for whom, and how is "done and
  correct" checked?
- **Scope boundary:** What is explicitly out, and what is deferred?
- **Interfaces:** Which commands, files, APIs or formats do others depend on,
  and do any change?
- **Data and irreversible actions:** What is written, deleted, migrated or
  published, and can it be undone?
- **Failure modes:** What happens on bad input, partial failure, or a missing
  dependency?
- **Security and secrets:** What is trusted, and what touches credentials or
  external input?
- **Testing:** Which tests prove each success criterion?
- **Rollout and compatibility:** What existing users, files or settings are
  affected, and how is the change switched on?
- **Docs and decisions:** Which docs change, and which choices deserve an
  ADR?

## Coverage section format

```
## Coverage

- **Purpose and success:** Purpose; Success criteria.
- **Security and secrets:** N/A: reads only files in the repo, no credentials.
```

One bullet per area, named exactly as above (case does not matter). The text
says where the spec addresses the area, or `N/A` followed by the reason. An
entry may wrap onto indented continuation lines.
````

- [ ] **Step 4: Create `plugin/skills/grill/SKILL.md`**

````markdown
---
name: grill
description: Use when the injected spec-grill rule applies (CLAUDE_KIT_GRILL=1), after a brainstorming design summary and before the spec is written, or when the user asks to be grilled on a plan, design or idea. Interviews the user in numbered rounds, each question with a recommended answer, over the design's open decisions plus a coverage checklist, until the user confirms a shared understanding.
argument-hint: [topic]
---

# Grill

Adapted from the `grilling` skill in
[mattpocock/skills](https://github.com/mattpocock/skills) (MIT licence).

Interview the user until you both hold a shared understanding of the design,
with nothing left silently assumed. The spec is written from the result.

## The tree

Map the subject as a design tree: every decision branches into the decisions
that hang off it. The tree holds:

- every choice the agreed design makes or leaves open (with no design in the
  conversation, the subject is `$ARGUMENTS`);
- every area listed under `## Areas` in `coverage.md` in this skill's
  directory.

## Facts and decisions

- **Facts are your job.** When a question needs a fact from the environment,
  read the repo or dispatch an Explore subagent. Never ask the user what you
  can look up. Only the questions that depend on a running lookup wait for
  it; ask the rest now.
- Close a coverage area as N/A without asking **only** when a fact settles
  it, and state the fact.
- **Decisions are the user's.** Put each one to them and wait. Never answer
  your own decision question.

## Rounds

The frontier is every open decision whose prerequisites are settled. Ask the
whole frontier in one round, and nothing that depends on another question
still open in the same round; that question belongs to a later round. Number
each question and give your recommended answer, separating questions with
`---`:

```
❓ **Q1 - <title>**: <question, with options when there are any>

➡️ <recommended answer and a one-line reason>

---

❓ **Q2 - <title>**: <question>

➡️ <recommended answer and a one-line reason>
```

If the user's instructions ask for one question at a time, ask one per
message instead.

After each round, recompute the frontier from the answers and ask the next
round. An answer that changes an earlier one reopens that branch.

## End

When the frontier is empty, post a grill summary:

- **Decisions:** each question and the user's answer.
- **Coverage:** each area in `coverage.md`, with where the design addresses
  it, or `N/A` and the reason.

Ask the user to confirm a shared understanding, and wait. Do not write the
spec or act on the design until they confirm.

## Hand-off to the spec

The settled decisions go into the spec's `## Decisions`. The coverage list
becomes its `## Coverage` section, in the format in `coverage.md`. With
`CLAUDE_KIT_GRILL=1`, `spec-lint.py` rule `L9-coverage` checks that section.
````

- [ ] **Step 5: Run the test to verify it passes**

Run: `pytest tests/test_grill_skill.py -v`
Expected: 3 passed.

- [ ] **Step 6: Run the full suite and lint, then commit**

Run: `pytest -q; ruff check plugin tests; ruff format --check plugin tests`
Expected: all tests pass; ruff prints `All checks passed!` and no files to
reformat.

```bash
git add plugin/skills/grill tests/test_grill_skill.py
git commit -m "Grill skill and coverage checklist

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 2: Lint rule `L9-coverage`

**Files:**
- Modify: `plugin/scripts/spec-lint.py`
- Test: `tests/test_spec_lint.py`

**Depends on:** Task 1

**Interfaces:**
- Consumes: `plugin/skills/grill/coverage.md` from Task 1.
- Produces: in `spec-lint.py`, `COVERAGE_FROM: date`, `COVERAGE_FILE: Path`,
  `grill_on() -> bool`, `coverage_areas(path: Path | None = None) ->
  list[str] | None` (None when unreadable), `spec_date(lines) -> date | None`,
  `check_coverage(lines, secs, areas_file: Path | None = None) ->
  list[tuple[int, str, str]]`, and `lint()` calling `check_coverage`.

- [ ] **Step 1: Write the failing tests**

At the top of `tests/test_spec_lint.py`, change the helpers import to
`from helpers import PLUGIN, clean_env, load_module, run_script`, and add
`import shutil` on its own line followed by a blank line, between
`from __future__ import annotations` and `import pytest` (ruff's isort rule
`I` must stay clean). After the `root`
fixture, add:

```python
@pytest.fixture(autouse=True)
def no_grill(monkeypatch):
    """Lint results never depend on the developer's CLAUDE_KIT_GRILL."""
    monkeypatch.delenv("CLAUDE_KIT_GRILL", raising=False)


@pytest.fixture
def grill(monkeypatch):
    monkeypatch.setenv("CLAUDE_KIT_GRILL", "1")
```

Append at the end of the file:

```python
AREAS = [
    "Purpose and success",
    "Scope boundary",
    "Interfaces",
    "Data and irreversible actions",
    "Failure modes",
    "Security and secrets",
    "Testing",
    "Rollout and compatibility",
    "Docs and decisions",
]
GRILLED = (
    VALID.replace("2026-09-30", "2026-10-01")
    + "\n## Coverage\n\n"
    + "".join(f"- **{area}:** Design.\n" for area in AREAS)
)
BARE = GRILLED.split("\n## Coverage")[0] + "\n"


def l9(text, root):
    return [line for line, rule in rules(text, root) if rule == "L9-coverage"]


def test_l9_reads_the_nine_areas():
    assert sl.coverage_areas() == AREAS


def test_l9_full_coverage_is_clean(root, grill):
    assert rules(GRILLED, root) == []


def test_l9_missing_section(root, grill):
    assert l9(BARE, root) == [1]


def test_l9_missing_area(root, grill):
    text = GRILLED.replace("- **Security and secrets:** Design.\n", "")
    assert len(l9(text, root)) == 1


def test_l9_empty_area(root, grill):
    text = GRILLED.replace("- **Testing:** Design.", "- **Testing:**")
    assert len(l9(text, root)) == 1


def test_l9_bare_na(root, grill):
    text = GRILLED.replace("- **Testing:** Design.", "- **Testing:** N/A -")
    assert len(l9(text, root)) == 1


def test_l9_na_with_reason_is_fine(root, grill):
    text = GRILLED.replace("- **Testing:** Design.", "- **Testing:** N/A: no code.")
    assert l9(text, root) == []


def test_l9_continuation_lines_count(root, grill):
    text = GRILLED.replace("- **Testing:** Design.", "- **Testing:**\n  Design.")
    assert l9(text, root) == []


def test_l9_unknown_area_ignored_and_first_duplicate_checked(root, grill):
    text = GRILLED.replace(
        "- **Testing:** Design.\n",
        "- **Testing:**\n- **Testing:** Design.\n- **Extra:** x.\n",
    )
    assert len(l9(text, root)) == 1


def test_l9_off_when_switch_unset(root):
    assert l9(BARE, root) == []


def test_l9_off_for_other_values(root, monkeypatch):
    monkeypatch.setenv("CLAUDE_KIT_GRILL", "true")
    assert l9(BARE, root) == []


def test_l9_skips_older_specs(root, grill):
    assert l9(BARE.replace("2026-10-01", "2026-09-30"), root) == []


def test_l9_skips_unparsable_date(root, grill):
    assert l9(BARE.replace("2026-10-01", "2026-02-30"), root) == []


def test_l9_never_checks_plans(root, grill):
    plan = "# P\n\n- **Status:** draft\n- **Date:** 2026-10-01\n"
    assert all(rule != "L9-coverage" for _, rule, _ in sl.lint_plan(plan, root))


def test_l9_coverage_file_without_areas_is_reported(root, tmp_path, grill):
    empty = tmp_path / "coverage.md"
    empty.write_text("# Coverage checklist

No areas.
", encoding="utf-8")
    lines = sl.parse(GRILLED)
    found = sl.check_coverage(lines, sl.sections(lines), empty)
    assert [rule for _, rule, _ in found] == ["L9-coverage"]


def test_l9_missing_coverage_file_is_reported(root, tmp_path):
    # A copy of the plugin's scripts/ folder with no skills/grill/ beside it.
    install = tmp_path / "install"
    (install / "scripts").mkdir(parents=True)
    copy = install / "scripts" / "spec-lint.py"
    shutil.copy(SCRIPT, copy)
    spec = root / "spec.md"
    spec.write_text(GRILLED, encoding="utf-8")
    result = run_script(
        copy, str(spec), "--root", str(root), env=clean_env(CLAUDE_KIT_GRILL="1")
    )
    assert result.returncode == 1
    assert "L9-coverage" in result.stdout
    assert "coverage.md" in result.stdout
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_spec_lint.py -k l9 -v`
Expected: FAIL for `reads_the_nine_areas` (`AttributeError: module
'spec_lint' has no attribute 'coverage_areas'`), `missing_section`,
`missing_area`, `empty_area`, `bare_na`,
`unknown_area_ignored_and_first_duplicate_checked`,
`coverage_file_without_areas_is_reported` and
`missing_coverage_file_is_reported`; the other `l9` tests already pass.

- [ ] **Step 3: Implement `L9-coverage` in `plugin/scripts/spec-lint.py`**

In the module docstring, after the `L8-path` paragraph, add:

```
- L9-coverage: only when CLAUDE_KIT_GRILL=1 and the Date parses to a date on
  or after 2026-10-01: a ``## Coverage`` section with one ``- **<Area>:**``
  bullet per area in skills/grill/coverage.md (next to this script's folder),
  each with text, and ``N/A`` followed by a reason. Continuation lines count;
  unknown areas are ignored; the first of two bullets for an area is checked.
  An unreadable coverage.md, or one with no areas, is itself a violation.
```

Add `import os` between `import hashlib` and `import re`, and
`from datetime import date` directly before `from pathlib import Path` (ruff's
isort rule `I` must stay clean).
After `DEPENDS_ITEM_RE`, add:

```python
COVERAGE_FROM = date(2026, 10, 1)
COVERAGE_FILE = Path(__file__).resolve().parent.parent / "skills" / "grill"
COVERAGE_FILE = COVERAGE_FILE / "coverage.md"
AREA_RE = re.compile(r"^- \*\*([^*]+?):\*\*(.*)$")
NA_STRIP = ":-–— "
```

After `check_paths`, add:

```python
def grill_on() -> bool:
    return os.environ.get("CLAUDE_KIT_GRILL") == "1"


def coverage_areas(path: Path | None = None) -> list[str] | None:
    """Area names from coverage.md's ``## Areas`` bullets; None if unreadable."""
    try:
        text = (path or COVERAGE_FILE).read_text(encoding="utf-8")
    except OSError:
        return None
    body = find(sections(parse(text)), ("areas",))
    if body is None:
        return []
    found = []
    for _, line, code in body[1]:
        match = None if code else AREA_RE.match(line)
        if match:
            found.append(match.group(1).strip())
    return found


def spec_date(lines: list[Line]) -> date | None:
    for _, line, code in lines:
        match = None if code else DATE_RE.match(line)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                return None
    return None


def coverage_entries(body: list[Line]) -> dict[str, tuple[int, str]]:
    """Lowercased area -> (line, text incl. continuation lines); first wins."""
    entries: dict[str, tuple[int, list[str]]] = {}
    current = None
    for number, line, code in body:
        match = None if code else AREA_RE.match(line)
        if match:
            key = match.group(1).strip().lower()
            current = None if key in entries else key
            if current:
                entries[key] = (number, [match.group(2)])
        elif code or ITEM_RE.match(line):
            current = None
        elif current and line[:1].isspace() and line.strip():
            entries[current][1].append(line)
        elif line.strip():
            current = None
    return {k: (n, " ".join(t).strip()) for k, (n, t) in entries.items()}


def check_coverage(
    lines: list[Line], secs: dict, areas_file: Path | None = None
) -> list[tuple[int, str, str]]:
    if not grill_on():
        return []
    when = spec_date(lines)
    if when is None or when < COVERAGE_FROM:
        return []
    path = areas_file or COVERAGE_FILE
    areas = coverage_areas(path)
    if not areas:
        return [(1, "L9-coverage", f"cannot read coverage areas: {path}")]
    body = find(secs, ("coverage",))
    if body is None:
        return [(1, "L9-coverage", "missing section '## Coverage'")]
    entries = coverage_entries(body[1])
    out = []
    for area in areas:
        entry = entries.get(area.lower())
        if entry is None:
            out.append((body[0], "L9-coverage", f"no entry for area {area!r}"))
            continue
        number, text = entry
        if not text:
            out.append((number, "L9-coverage", f"area {area!r} has no text"))
        elif text.upper().startswith("N/A") and not text[3:].strip(NA_STRIP):
            out.append((number, "L9-coverage", f"area {area!r}: N/A without reason"))
    return out
```

In `lint()`, add `+ check_coverage(lines, secs)` after
`+ check_paths(lines, secs, root)`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_spec_lint.py -v`
Expected: all pass, including the 16 new `l9` tests.

- [ ] **Step 5: Run the full suite and lint, then commit**

Run: `ruff format plugin tests; pytest -q; ruff check plugin tests; ruff format --check plugin tests`
Expected: all tests pass; ruff prints `All checks passed!` and no files to
reformat.

```bash
git add plugin/scripts/spec-lint.py tests/test_spec_lint.py
git commit -m "spec-lint: L9-coverage when CLAUDE_KIT_GRILL=1

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 3: Grill inject hook and manifest

**Files:**
- Create: `plugin/hooks/grill_inject.py`
- Modify: `plugin/hooks/hooks.json`
- Modify: `plugin/.claude-plugin/plugin.json`
- Test: `tests/test_grill_inject.py`
- Test: `tests/test_plugin_manifest.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: `grill_inject.py` printing SessionStart JSON whose
  `additionalContext` contains `claude-kit:grill` when `CLAUDE_KIT_GRILL=1`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_grill_inject.py`:

```python
import json

import pytest
from helpers import PLUGIN, clean_env, run_script

HOOK = PLUGIN / "hooks" / "grill_inject.py"


def run(**env: str):
    return run_script(HOOK, stdin="{}", env=clean_env(**env))


def test_one_injects_the_rule():
    result = run(CLAUDE_KIT_GRILL="1")
    assert result.returncode == 0
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    assert "claude-kit:grill" in out["additionalContext"]
    assert "## Coverage" in out["additionalContext"]


def test_unset_is_off():
    result = run()
    assert result.returncode == 0
    assert result.stdout == ""


@pytest.mark.parametrize("value", ["0", "", "true", "yes"])
def test_other_values_are_off(value):
    result = run(CLAUDE_KIT_GRILL=value)
    assert result.returncode == 0
    assert result.stdout == ""
```

Append to `tests/test_plugin_manifest.py`:

```python
def test_hooks_json_registers_grill_inject():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert any(
        "grill_inject.py" in h["command"]
        for g in hooks["hooks"]["SessionStart"]
        for h in g["hooks"]
    )


def test_description_mentions_grill():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert "grill" in data["description"]
    assert data["version"] == "0.11.0"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_grill_inject.py tests/test_plugin_manifest.py -v`
Expected: FAIL; the hook tests because `grill_inject.py` does not exist (a
non-zero exit), and the two new manifest tests on their asserts.

- [ ] **Step 3: Create `plugin/hooks/grill_inject.py`**

```python
#!/usr/bin/env python3
"""SessionStart hook: inject the spec-grill rule when it is switched on.

Off by default. CLAUDE_KIT_GRILL=1 turns it on; any other value, or none,
counts as off and nothing is printed. The ``claude-kit:grill`` skill stays
invocable either way. Always exits 0 (ADR 0007).
"""

from __future__ import annotations

import json
import os
import sys

RULE = (
    "Spec grill is on (CLAUDE_KIT_GRILL=1). When designing a spec, after "
    "presenting the design summary and before writing the spec, run the "
    "`claude-kit:grill` skill on the agreed design. Write the spec only after "
    "the user confirms a shared understanding, and give it a `## Coverage` "
    "section in the format the skill describes."
)


def enabled() -> bool:
    return os.environ.get("CLAUDE_KIT_GRILL") == "1"


def main() -> int:
    try:
        if enabled():
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": RULE,
                }
            }
            print(json.dumps(output))
    except Exception as exc:  # a hook must never raise
        print(f"[claude-kit] grill inject error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Register the hook and bump the plugin**

In `plugin/hooks/hooks.json`, in the `SessionStart` array, after the group
running `lean_context_inject.py`, add:

```json
      {
        "hooks": [
          {
            "type": "command",
            "command": "python \"${CLAUDE_PLUGIN_ROOT}/hooks/grill_inject.py\""
          }
        ]
      },
```

In `plugin/.claude-plugin/plugin.json`, set `"version": "0.11.0"` and replace
the description's ending `, teach skill for multi-session learning
workspaces."` with `, teach skill for multi-session learning workspaces, an
opt-in grill skill (CLAUDE_KIT_GRILL=1) that interviews before a spec is
written."` (one line in the JSON).

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pytest tests/test_grill_inject.py tests/test_plugin_manifest.py -v`
Expected: all pass.

- [ ] **Step 6: Run the full suite and lint, then commit**

Run: `ruff format plugin tests; pytest -q; ruff check plugin tests; ruff format --check plugin tests`
Expected: all tests pass; ruff prints `All checks passed!` and no files to
reformat.

```bash
git add plugin/hooks/grill_inject.py plugin/hooks/hooks.json plugin/.claude-plugin/plugin.json tests/test_grill_inject.py tests/test_plugin_manifest.py
git commit -m "grill_inject hook behind CLAUDE_KIT_GRILL; plugin 0.11.0

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

### Task 4: Docs, ADR 0019, and status

**Files:**
- Modify: `CLAUDE.md`
- Modify: `conventions/spec-driven-development.md`
- Modify: `README.md`
- Create: `knowledge/decisions/0019-spec-grill-opt-in.md`
- Modify: `knowledge/decisions/README.md`
- Modify: `docs/superpowers/specs/2026-10-01-spec-grill-design.md`
- Modify: `docs/superpowers/plans/2026-10-01-spec-grill.md`

**Depends on:** Task 1, Task 2, Task 3

**Interfaces:**
- Consumes: the skill (Task 1), `L9-coverage` (Task 2), the hook (Task 3).
- Produces: documentation only.

- [ ] **Step 1: `CLAUDE.md`**

At the end of the "Designing a spec" section's paragraph (after "key
decisions."), add as a new paragraph, leaving the existing text unchanged:

```markdown
With `CLAUDE_KIT_GRILL=1`, the `claude-kit:grill` skill runs between the
design summary and the spec
([ADR 0019](knowledge/decisions/0019-spec-grill-opt-in.md)); its rounds and the
shared-understanding confirmation are the only pause.
```

- [ ] **Step 2: `conventions/spec-driven-development.md`**

In "The stages", append as an indented continuation paragraph inside item 1
(Brainstorm), before item 2:

```markdown
   With the kit's opt-in grill on (`CLAUDE_KIT_GRILL=1`), the
   `claude-kit:grill` skill then interviews you on the agreed design and a
   coverage checklist (`plugin/skills/grill/coverage.md`) before the spec is
   written.
```

In "Spec anatomy", after the Success criteria bullet, add:

```markdown
- **Coverage** (required when `CLAUDE_KIT_GRILL=1`, for specs dated
  2026-10-01 or later) — one `- **<Area>:**` bullet per area in
  `plugin/skills/grill/coverage.md`, saying where the spec addresses it or
  `N/A` with the reason. `spec-lint.py` rule `L9-coverage` checks it
  ([ADR 0019](../knowledge/decisions/0019-spec-grill-opt-in.md)).
```

- [ ] **Step 3: `README.md`**

In the workflow diagram's `decide` subgraph, after the `dec{{...}}:::you`
line add `    grill["Grill (opt-in)<br/>decisions + coverage"]:::gate` and
change `    brain --> dec --> spec --> sgate --> sok` to
`    brain --> dec --> grill --> spec --> sgate --> sok`.

In the `plugin/` bullet, change "the `supabase-cli`,
`lean-context`, `audit` and `audit-deep` skills" to "the `supabase-cli`,
`lean-context`, `grill` (opt-in, `CLAUDE_KIT_GRILL=1`), `audit` and
`audit-deep` skills", change "seven hooks" to "eight hooks", and after
"inject the lean-context rule unless `CLAUDE_KIT_LEAN_CONTEXT=0`," add
" inject the grill rule when `CLAUDE_KIT_GRILL=1`,".

- [ ] **Step 4: ADR 0019**

Create `knowledge/decisions/0019-spec-grill-opt-in.md`:

```markdown
# ADR 0019: An opt-in grill runs between the design and the spec

- **Status:** accepted
- **Date:** 2026-10-01

## Context
Specs missed whole areas (failure modes, rollout, irreversible data) and
settled decisions silently; the spec gate (ADR 0015) caught some afterwards
as decision findings and `/ship` stopped on the rest. Brainstorming's
questions stop when the model feels it understands.

## Decision
- A `claude-kit:grill` skill, adapted from `grilling` in mattpocock/skills
  (MIT), runs after the brainstorming design summary and before the spec. It
  asks the design's open decisions plus a nine-area coverage checklist
  (`plugin/skills/grill/coverage.md`) in numbered rounds with recommended
  answers, looks facts up itself, and ends on a confirmed shared
  understanding.
- It is opt-in: a SessionStart hook injects the rule only when
  `CLAUDE_KIT_GRILL=1`. The skill stays invocable by hand either way.
- With the switch on, specs dated 2026-10-01 or later need a `## Coverage`
  section, checked by `spec-lint.py` rule `L9-coverage`, which reads the area
  names from `coverage.md`.

## Consequences
Spec design gains an interview step for users who opt in; older specs and
users who do not opt in see no change. Whether a spec needs `## Coverage`
depends on the machine's setting, so a spec gated with the switch off may
lack it. Flipping the default later needs a new ADR.
```

In `knowledge/decisions/README.md`, after the 0018 row add:

```markdown
| [0019](0019-spec-grill-opt-in.md) | An opt-in grill runs between the design and the spec | accepted | 2026-10-01 |
```

- [ ] **Step 5: Verify existing specs and this spec**

Run (Bash): `for f in docs/superpowers/specs/*.md; do CLAUDE_KIT_GRILL=1 python plugin/scripts/spec-lint.py "$f" | grep L9 ; done; echo done`
Expected: only `done` is printed (no `L9` lines).

Run (Bash): `CLAUDE_KIT_GRILL=1 python plugin/scripts/spec-lint.py docs/superpowers/specs/2026-10-01-spec-grill-design.md`
Expected: `clean`.

- [ ] **Step 6: Mark the spec and plan implemented**

Set `- **Status:** implemented` in
`docs/superpowers/specs/2026-10-01-spec-grill-design.md` and in this plan.

Run: `python plugin/scripts/spec-lint.py --verify-record docs/superpowers/specs/2026-10-01-spec-grill-design.md`
Expected: `ok: ...` (the hash ignores the Status line, so the spec gate
record stays valid).

- [ ] **Step 7: Run the full suite and lint, then commit**

Run: `pytest -q; ruff check plugin tests; ruff format --check plugin tests`
Expected: all tests pass, including `tests/test_docs.py` (links resolve,
"no approval pause between design sections" still present); ruff clean.

```bash
git add CLAUDE.md conventions/spec-driven-development.md README.md knowledge/decisions docs/superpowers
git commit -m "Docs and ADR 0019: opt-in spec grill

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
