# ADR Triggers Implementation Plan

- **Status:** approved
- **Date:** 2026-10-10

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the judgment-based ADR rule with MUST / SHOULD / NOT REQUIRED
lists in the convention and the scaffold template, make the spec gate enforce
MUST triggers as rubric check 8, record ADR 0027, and bump the plugin to 0.18.0.

**Architecture:** Markdown-only behaviour changes (a convention, a template
README, a reviewer rubric) pinned by structure tests in pytest. No Python
script changes.

**Tech Stack:** Markdown, Python 3.11+ pytest, ruff.

**Spec:** `docs/superpowers/specs/2026-10-10-adr-triggers-design.md`

## Context for a cold start

- Repo root: the worktree you are in (branch `feat/adr-triggers`). Run
  commands from the repo root in Git Bash.
- Test and lint (from `CLAUDE.md`): `pytest`, `ruff check plugin tests`,
  `ruff format --check plugin tests`.
- `tests/helpers.py` exports `PLUGIN` (the `plugin/` dir) and `REPO` (the
  repo root).
- The section text and the rubric text are given verbatim in the spec
  (Design → "The three lists" and "Spec gate check 8"). Copy them
  character for character; the tests compare text.

## Global Constraints

- Section heading is exactly `## When to write one`; the section is
  byte-identical in `conventions/decision-log.md` and
  `plugin/templates/project/knowledge/decisions/README.md`.
- Rubric check 8 goes after check 7 and before `## Severity` in
  `plugin/skills/spec-gate/rubric.md`.
- No change to `plugin/skills/spec-gate/SKILL.md`, the linter, or the gate
  record format.
- Version: `0.17.0` → `0.18.0` (minor bump from `main`; if `main` has moved
  past 0.17.0 when this ships, bump the minor of whatever `main` has, and
  use that version everywhere this plan says 0.18.0: the test, `plugin.json`
  and the commit message).
- ADR file: `knowledge/decisions/0027-adr-triggers.md` (if 0027 is taken on
  `main` at ship time, use the next free number and use it everywhere this
  plan says 0027).
- Files keep LF line endings.

## Review Focus

- Template README rendered by the scaffolder: `{{project_name}}` must still
  be the only placeholder in it, and the new section must contain no `{{`.
  Covered by the existing `test_only_allowed_placeholders_are_used` and by
  Task 1's scaffold check.
- The section in the template must end at `## Index`, not run into the
  table. Covered by Task 1's equality test (it would fail otherwise).
- Trailing whitespace or CRLF differences between the two copies would fail
  the equality test only on some machines: Task 1's test compares text read
  with `read_text` (universal newlines), so CRLF checkouts still pass.
- Check 8 must not be numbered into the Severity section: Task 2's test
  slices check 8 up to `## Severity`.
- The old phrase "significant and meant to stick" must be gone from the
  convention (spec criterion 3): Task 1 asserts it.

## Answers to the gate's plan questions

- **Where does the README line go?** Next to the spec gate, as the spec
  says: the one place `README.md` names the spec gate is the mermaid node
  `sgate["Spec gate<br/>independent review"]:::gate`, and that one line
  becomes `sgate["Spec gate<br/>independent review<br/>+ ADR triggers"]:::gate`.
  (Task 3)
- **How is check 8's paragraph sliced in the test?** From
  `8. **ADR triggers.**` up to `## Severity`. (Task 2)
- **Is the hand-run spec-gate reviewer eval re-run?** No, following
  precedent: the last rubric change (#27, `4418d80`) did not re-run it
  either; its Results table still ends at 2026-09-30. The spec's Testing
  section lists only the pytest tests. The PR body says the eval was not
  re-run. (Task 3)
- **Is the version bump computed from `main` at merge time?** Yes; see
  Global Constraints. (Task 3)
- **How does `tests/test_plugin_manifest.py` change?** As earlier version
  bumps did (see `test_description_mentions_ship_fast`, which asserts
  `>= (0, 15, 0)`): the previous exact pin in
  `test_description_mentions_present` is relaxed to `>= (0, 17, 0)`, and a
  new test pins the new version. (Task 3)

---

### Task 1: Trigger lists in the convention and the template

**Files:**
- Modify: `conventions/decision-log.md:8-10`
- Modify: `plugin/templates/project/knowledge/decisions/README.md`
- Test: `tests/test_templates.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the `## When to write one` section in both files (Task 2's
  rubric text refers to it by heading).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_templates.py`:

```python
CONVENTION = PLUGIN.parent / "conventions" / "decision-log.md"
DECISIONS_README = PROJECT / "knowledge" / "decisions" / "README.md"


def _section(text, heading="## When to write one"):
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = rest.find("\n## ")
    return heading + (rest if end == -1 else rest[: end + 1])


def test_adr_triggers_match_convention():
    convention = CONVENTION.read_text(encoding="utf-8")
    template = DECISIONS_README.read_text(encoding="utf-8")
    section = _section(convention)
    assert section == _section(template)
    for marker in ("**MUST**", "**SHOULD**", "**NOT REQUIRED:**"):
        assert marker in section
    assert "significant and meant to stick" not in convention
    assert "\n## Index\n" in template
    assert template.index("## When to write one") < template.index("## Index")
    assert template.index("## Index") < template.index("| # | Title |")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_templates.py::test_adr_triggers_match_convention -v`
Expected: FAIL with `ValueError: substring not found`.

- [ ] **Step 3: Edit the convention**

In `conventions/decision-log.md`, delete the paragraph (lines 8-10):

```markdown
Record a decision as an ADR whenever a choice is **significant and meant to stick** —
it shapes the architecture, the product boundary, or how the team works. Routine,
easily-reversed choices do not need one.
```

and put in its place the whole fenced block under spec Design → "The three
lists" (from `## When to write one` through "matches a MUST or SHOULD
trigger."), without the fence lines. Keep one blank line before it and one
blank line before `## How it works`.

- [ ] **Step 4: Edit the template README**

`plugin/templates/project/knowledge/decisions/README.md` becomes: the
existing opening paragraph, a blank line, the same section text as Step 3,
a blank line, `## Index`, a blank line, then the existing table header:

```markdown
| # | Title | Status | Date |
|---|-------|--------|------|
```

- [ ] **Step 5: Run the test and a scaffold check**

Run: `pytest tests/test_templates.py -v`
Expected: all PASS.

Run (scaffold into a temp dir and check the section; the scaffolder does
`git init` and one commit there):

```bash
tmp=$(mktemp -d) && python plugin/scripts/scaffold.py --name t --stack python --parent "$tmp" >/dev/null && grep -c "## When to write one" "$tmp/t/knowledge/decisions/README.md"; rm -rf "$tmp"
```

Expected: `1`.

- [ ] **Step 6: Full suite, lint, commit**

Run: `pytest -q && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass.

```bash
git add conventions/decision-log.md plugin/templates/project/knowledge/decisions/README.md tests/test_templates.py
git commit -m "ADR triggers: MUST/SHOULD/NOT REQUIRED lists in the convention and template"
```

### Task 2: Spec gate rubric check 8

**Files:**
- Modify: `plugin/skills/spec-gate/rubric.md:33-36` (insert after check 7)
- Test: `tests/test_spec_gate_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: the heading text `## When to write one` (Task 1); only as text.
- Produces: rubric check 8.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_spec_gate_skill.py`:

```python
def test_rubric_checks_adr_triggers():
    rubric = read("rubric.md")
    start = rubric.index("8. **ADR triggers.**")
    check = rubric[start : rubric.index("## Severity")]
    assert rubric.index("7. **Key decisions.**") < start
    for text in (
        "knowledge/decisions/",
        "When to write one",
        "../conventions/decision-log.md",
        "open-what",
        "NOT REQUIRED",
        "SHOULD match is a `minor` finding",
    ):
        assert text in check, text
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_spec_gate_skill.py::test_rubric_checks_adr_triggers -v`
Expected: FAIL with `ValueError: substring not found`.

- [ ] **Step 3: Add check 8**

In `plugin/skills/spec-gate/rubric.md`, after check 7 (which ends
"them.") and before the blank line and `## Severity`, insert a blank line
and the fenced block under spec Design → "Spec gate check 8" (from
`8. **ADR triggers.**` through "convention itself.)"), without the fence
lines, keeping its three-space continuation indent.

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_spec_gate_skill.py -v`
Expected: all PASS.

- [ ] **Step 5: Full suite, lint, commit**

Run: `pytest -q && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass.

```bash
git add plugin/skills/spec-gate/rubric.md tests/test_spec_gate_skill.py
git commit -m "spec-gate: rubric check 8 enforces ADR MUST triggers"
```

### Task 3: ADR 0027, version 0.18.0, README

**Files:**
- Create: `knowledge/decisions/0027-adr-triggers.md`
- Modify: `knowledge/decisions/README.md` (append a row)
- Modify: `plugin/.claude-plugin/plugin.json` (`version`)
- Modify: `tests/test_plugin_manifest.py:193-197`
- Modify: `README.md` (the `sgate` mermaid node, line 28)

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: version `0.18.0`.

- [ ] **Step 1: Update the manifest test (failing first)**

In `tests/test_plugin_manifest.py`, change the end of
`test_description_mentions_present` from
`assert data["version"] == "0.17.0"` to:

```python
    version = tuple(int(part) for part in data["version"].split("."))
    assert version >= (0, 17, 0)
```

and append:

```python
def test_version_is_0_18_0():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "0.18.0"
```

Run: `pytest tests/test_plugin_manifest.py -v`
Expected: `test_version_is_0_18_0` FAILS (`0.17.0 != 0.18.0`).

- [ ] **Step 2: Bump the version**

In `plugin/.claude-plugin/plugin.json` set `"version": "0.18.0"`.
Run: `pytest tests/test_plugin_manifest.py -v` → all PASS.

- [ ] **Step 3: Write ADR 0027**

Create `knowledge/decisions/0027-adr-triggers.md`:

```markdown
# ADR 0027: ADR triggers: MUST, SHOULD, NOT REQUIRED

- **Status:** accepted
- **Date:** 2026-10-10

## Context
`conventions/decision-log.md` said to record a decision "whenever a choice
is significant and meant to stick". The call was left to judgment, and on
projects other than the kit ADRs stopped being written.

## Decision
- The convention and the scaffold template's `knowledge/decisions/README.md`
  carry the same `## When to write one` section: MUST, SHOULD and NOT
  REQUIRED lists. A NOT REQUIRED match overrides the other two. A test keeps
  the two copies identical.
- The spec gate's rubric gains check 8: a key decision that matches a MUST
  trigger with no ADR in the spec's Scope In is a blocking `open-what`
  finding, which the gate fixes by adding the ADR to the spec. A SHOULD
  match is reported as minor and never added without the user.
- The trigger lists are read from the repo's decisions README, else
  `conventions/decision-log.md`, else `../conventions/decision-log.md`;
  without any of them the check is skipped.

## Consequences
- Specs that hit a MUST trigger carry their ADR, visible in the gate
  record's Findings fixed.
- `/ship-fast` POCs are exempt: they skip the gates (ADR 0024).
- The plan gate does not check ADRs; decisions a plan adds still reach the
  user through the plan gate's sign-off (ADR 0016).
```

Append to `knowledge/decisions/README.md`'s table, after the 0026 row:

```markdown
| [0027](0027-adr-triggers.md) | ADR triggers: MUST, SHOULD, NOT REQUIRED, enforced by the spec gate | accepted | 2026-10-10 |
```

- [ ] **Step 4: README line**

In `README.md`'s mermaid diagram, replace the line

```
    sgate["Spec gate<br/>independent review"]:::gate
```

with

```
    sgate["Spec gate<br/>independent review<br/>+ ADR triggers"]:::gate
```

- [ ] **Step 5: Full suite, lint, commit**

Run: `pytest -q && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass. (`tests/test_docs.py` checks links in all tracked
markdown, including the new row in `knowledge/decisions/README.md`.)

Run: `pytest -k "adr_triggers" -v`
Expected: exactly `test_adr_triggers_match_convention` and
`test_rubric_checks_adr_triggers` collected; `2 passed`.

Run: `grep -c "0027-adr-triggers.md" knowledge/decisions/README.md`
Expected: `1`.

```bash
git add knowledge/decisions/0027-adr-triggers.md knowledge/decisions/README.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py README.md
git commit -m "ADR 0027: ADR triggers; v0.18.0"
```

PR note for `/ship`: the hand-run spec-gate reviewer eval
(`tests/fixtures/spec-gate/README.md`) was not re-run; say so in the PR body.
