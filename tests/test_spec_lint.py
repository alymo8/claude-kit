"""Tests for plugin/scripts/spec-lint.py."""

from __future__ import annotations

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "spec-lint.py"
sl = load_module(SCRIPT, "spec_lint")

VALID = """\
# Thing

- **Status:** draft
- **Date:** 2026-09-30

## Purpose

Why.

## Scope

**In:**

- `src/app.py`: the app.
- `src/new.py` (new): a new module.

**Out:**

- Anything else.

## Design

Text.

## Decisions

- A over B, because C.

## Success criteria

1. `pytest` passes.
2. A manual check shows the page.
"""


@pytest.fixture
def root(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def rules(text, root):
    return [(line, rule) for line, rule, _ in sl.lint(text, root)]


def test_valid_spec_is_clean(root):
    assert sl.lint(VALID, root) == []


def test_l1_missing_status(root):
    text = VALID.replace("- **Status:** draft\n", "")
    assert rules(text, root) == [(1, "L1-status")]


def test_l1_bad_status_value(root):
    text = VALID.replace("**Status:** draft", "**Status:** done")
    assert rules(text, root) == [(3, "L1-status")]


def test_l1_superseded_with_link_is_fine(root):
    text = VALID.replace("**Status:** draft", "**Status:** superseded by x")
    assert sl.lint(text, root) == []


def test_l2_bad_date(root):
    text = VALID.replace("2026-09-30", "30/09/2026")
    assert rules(text, root) == [(4, "L2-date")]


def test_l3_missing_section(root):
    text = VALID.replace("## Decisions", "## Choices")
    found = sl.lint(text, root)
    assert [(line, rule) for line, rule, _ in found] == [(1, "L3-section")]
    assert "Decisions" in found[0][2]


def test_l3_structure_counts_as_design(root):
    text = VALID.replace("## Design", "## Structure / design")
    assert sl.lint(text, root) == []


def test_l4_missing_out_of_scope(root):
    text = VALID.replace("**Out:**\n\n- Anything else.\n\n", "")
    assert rules(text, root) == [(10, "L4-out-of-scope")]


def test_l4_separate_out_of_scope_section(root):
    text = VALID.replace("**Out:**\n\n- Anything else.\n\n", "").replace(
        "## Design", "## Out of scope\n\n- Anything else.\n\n## Design"
    )
    assert sl.lint(text, root) == []


def test_l5_placeholder(root):
    text = VALID.replace("Why.", "Why: TBD.")
    assert rules(text, root) == [(8, "L5-placeholder")]


def test_l5_as_discussed_is_case_insensitive(root):
    text = VALID.replace("Why.", "As discussed earlier.")
    assert rules(text, root) == [(8, "L5-placeholder")]


def test_l5_backticked_placeholder_is_fine(root):
    text = VALID.replace("Why.", "The linter bans `TBD` and `TODO`.")
    assert sl.lint(text, root) == []


def test_l5_etc_only_in_scope_and_criteria(root):
    in_purpose = VALID.replace("Why.", "Why, etc.")
    assert sl.lint(in_purpose, root) == []
    in_scope = VALID.replace("- Anything else.", "- Docs, etc.")
    assert rules(in_scope, root) == [(19, "L5-placeholder")]


def test_l6_empty_section(root):
    text = VALID.replace("Text.\n", "")
    assert rules(text, root) == [(21, "L6-empty")]


def test_l6_subsection_directly_under_section_is_fine(root):
    text = VALID.replace("Text.", "### Part\n\nText.")
    assert sl.lint(text, root) == []


def test_l6_empty_subsection_before_next_section(root):
    text = VALID.replace("Text.", "Text.\n\n### Part\n")
    assert rules(text, root) == [(25, "L6-empty")]


def test_l6_heading_at_end_of_file(root):
    text = VALID + "\n## Notes\n"
    assert rules(text, root) == [(34, "L6-empty")]


def test_l7_criterion_without_verification(root):
    text = VALID.replace("2. A manual check shows the page.", "2. It feels fast.")
    assert rules(text, root) == [(32, "L7-criterion")]


def test_l7_continuation_lines_count(root):
    text = VALID.replace(
        "2. A manual check shows the page.",
        "2. It feels fast,\n   which a test asserts.",
    )
    assert sl.lint(text, root) == []


def test_l8_missing_path(root):
    text = VALID.replace("`src/app.py`", "`src/gone.py`")
    assert rules(text, root) == [(14, "L8-path")]


def test_l8_new_path_marked_once_is_fine(root):
    text = VALID + "3. `src/new.py` imports without error.\n"
    assert sl.lint(text, root) == []


def test_l8_ignores_line_suffix_and_placeholders(root):
    spans = "`src/app.py:1-2`, `docs/<slug>.md`, `**/*.html`, `origin/main`"
    text = VALID.replace("`src/app.py`: the app.", spans + ": the app.")
    assert sl.lint(text, root) == []


def test_l8_only_checks_scope_before_out(root):
    in_design = VALID.replace("Text.", "Writes `src/gone.py` at runtime.")
    assert sl.lint(in_design, root) == []
    in_out = VALID.replace("- Anything else.", "- `src/gone.py`, a later spec.")
    assert sl.lint(in_out, root) == []


def test_l4_out_label_with_qualifier(root):
    text = VALID.replace("**Out:**", "**Out (later specs):**")
    assert sl.lint(text, root) == []


def test_l5_double_quoted_placeholder_is_fine(root):
    text = VALID.replace("Why.", 'Concrete paths, no "as discussed".')
    assert sl.lint(text, root) == []


def test_code_fences_are_ignored(root):
    fenced = "```\nTODO\n## Empty\n- **Status:** nonsense\n`src/gone.py`\n```"
    text = VALID.replace("Text.", fenced)
    assert sl.lint(text, root) == []


def test_cli_clean_exits_zero(root):
    spec = root / "spec.md"
    spec.write_text(VALID, encoding="utf-8")
    result = run_script(SCRIPT, str(spec), "--root", str(root))
    assert result.returncode == 0
    assert "clean" in result.stdout


def test_cli_violation_format_and_exit_one(root):
    spec = root / "spec.md"
    spec.write_text(VALID.replace("Why.", "TODO"), encoding="utf-8")
    result = run_script(SCRIPT, str(spec), "--root", str(root))
    assert result.returncode == 1
    assert f"{spec}:8: L5-placeholder" in result.stdout


def test_cli_missing_file_exits_two(root):
    result = run_script(SCRIPT, str(root / "nope.md"), "--root", str(root))
    assert result.returncode == 2


def test_cli_no_arguments_exits_two():
    assert run_script(SCRIPT).returncode == 2


def test_hash_ignores_status_line():
    approved = VALID.replace("**Status:** draft", "**Status:** approved")
    assert sl.spec_hash(VALID) == sl.spec_hash(approved)
    assert len(sl.spec_hash(VALID)) == 64


def test_hash_changes_on_any_other_edit():
    assert sl.spec_hash(VALID) != sl.spec_hash(VALID.replace("Why.", "Why!"))


def test_hash_ignores_line_endings():
    assert sl.spec_hash(VALID) == sl.spec_hash(VALID.replace("\n", "\r\n"))


def test_cli_hash_prints_digest(root):
    spec = root / "spec.md"
    spec.write_text(VALID, encoding="utf-8")
    result = run_script(SCRIPT, "--hash", str(spec))
    assert result.returncode == 0
    assert result.stdout.strip() == sl.spec_hash(VALID)


def gated(root, verdict="pass", digest=None):
    specs = root / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    spec = specs / "2026-09-30-x-design.md"
    spec.write_text(VALID, encoding="utf-8")
    if verdict is not None:
        gates = root / "docs" / "superpowers" / "gates"
        gates.mkdir(parents=True)
        (gates / spec.name).write_text(
            "# Gate: Thing\n\n"
            f"- **Spec:** docs/superpowers/specs/{spec.name}\n"
            f"- **Spec SHA-256:** {digest or sl.spec_hash(VALID)}\n"
            f"- **Verdict:** {verdict}\n",
            encoding="utf-8",
        )
    return spec


@pytest.mark.parametrize(
    ("verdict", "digest", "code", "reason"),
    [
        ("pass", None, 0, "ok"),
        (None, None, 1, "missing"),
        ("fail", None, 1, "not passed"),
        ("pass", "0" * 64, 1, "stale"),
    ],
)
def test_verify_record(root, verdict, digest, code, reason):
    spec = gated(root, verdict, digest)
    result = run_script(SCRIPT, "--verify-record", str(spec), "--root", str(root))
    assert result.returncode == code
    assert result.stdout.startswith(reason + ":")


def test_verify_record_survives_approval(root):
    spec = gated(root)
    spec.write_text(VALID.replace("draft", "approved"), encoding="utf-8")
    result = run_script(SCRIPT, "--verify-record", str(spec), "--root", str(root))
    assert result.returncode == 0


def test_longer_fence_is_not_closed_by_a_shorter_inner_fence(root):
    fenced = "````markdown\n```python\nTODO = 1\n# comment\n```\n````"
    text = VALID.replace("Text.", fenced)
    assert sl.lint(text, root) == []


def test_backticks_in_info_string_do_not_open_a_fence(root):
    text = VALID.replace("Text.", "```x``` is inline.\n\nWhy: TBD.")
    assert rules(text, root) == [(25, "L5-placeholder")]


def test_lowercase_todo_in_prose_is_fine(root):
    text = VALID.replace("Why.", "A todo app stores todo items.")
    assert sl.lint(text, root) == []


def test_crlf_spec_lints_like_lf(root):
    text = VALID.replace("Why.", "TODO")
    assert sl.lint(text.replace("\n", "\r\n"), root) == sl.lint(text, root)


PLAN = """\
# X Implementation Plan

- **Status:** draft
- **Date:** 2026-09-30

**Goal:** Build the thing.

**Spec:** `docs/superpowers/specs/2026-09-30-x-design.md`

### Task 1: First

**Files:**
- Create: `src/new.py`
- Modify: `src/app.py`
- Test: `tests/test_new.py`

- [ ] **Step 1: Write the failing test**

```python
def test_x():
    assert True
```

- [ ] **Step 2: Run it**

Run: `pytest tests/test_new.py -q`
Expected: FAIL

- [ ] **Step 3: Commit**

```bash
git commit -m "x"
```

### Task 2: Second

**Files:**
- Modify: `src/new.py`

- [ ] **Step 1: Check it**

```bash
pytest -q
```
Expected: PASS

- [ ] **Step 2: Commit**

Done.
"""

PLAN_SPEC = "docs/superpowers/specs/2026-09-30-x-design.md"


def plan_root(root, record=True):
    """Gate a spec at PLAN_SPEC (record optional); return the plan's path."""
    gated(root, "pass" if record else None)
    plans = root / "docs" / "superpowers" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    return plans / "2026-09-30-x.md"


def plan_rules(text, root):
    return [(line, rule) for line, rule, _ in sl.lint_plan(text, root)]


def test_plan_has_49_lines():
    assert len(PLAN.splitlines()) == 49


def test_valid_plan_is_clean(root):
    plan_root(root)
    assert sl.lint_plan(PLAN, root) == []


@pytest.mark.parametrize(
    ("old", "new", "record", "line", "rule"),
    [
        ("- **Status:** draft\n", "", True, 1, "P1-status"),
        ("- **Date:** 2026-09-30", "- **Date:** 30/09/2026", True, 4, "P2-date"),
        ("**Goal:** Build the thing.\n\n", "", True, 1, "P3-header"),
        ("### Task 2: Second", "### Task 3: Second", True, 35, "P5-tasks"),
        ("Build the thing.", "TBD", True, 6, "P7-placeholder"),
        ("Done.", "## Notes", True, 49, "P8-empty"),
        ("Expected: PASS", "It passes.", True, 35, "P6-task-parts"),
        ("", "", False, 8, "P4-spec-gated"),
        ("- Modify: `src/new.py`", "- Modify: `src/other.py`", True, 38, "P9-path"),
    ],
)
def test_each_plan_rule_alone(root, old, new, record, line, rule):
    plan = plan_root(root, record)
    plan.write_text(PLAN.replace(old, new) if old else PLAN, encoding="utf-8")
    result = run_script(SCRIPT, str(plan), "--root", str(root))
    out = result.stdout.splitlines()
    assert result.returncode == 1
    assert out[-1] == "1 violation(s)"
    assert out[0].startswith(f"{plan}:{line}: {rule} ")


def test_plan_rules_apply_only_in_a_plans_folder(root):
    plan = plan_root(root)
    plan.write_text(PLAN, encoding="utf-8")
    assert run_script(SCRIPT, str(plan), "--root", str(root)).returncode == 0
    other = root / "docs" / "superpowers" / "specs" / "plan-shaped.md"
    other.write_text(PLAN, encoding="utf-8")
    result = run_script(SCRIPT, str(other), "--root", str(root))
    assert "L3-section" in result.stdout
    assert "P5-tasks" not in result.stdout


def test_p3_missing_spec_line(root):
    plan_root(root)
    text = PLAN.replace("**Spec:**", "**Source:**")
    assert plan_rules(text, root) == [(1, "P3-header")]


def test_p3_spec_line_with_two_paths(root):
    plan_root(root, record=False)
    text = PLAN.replace("x-design.md`", "x-design.md` and `docs/a/b.md`")
    assert plan_rules(text, root) == [(8, "P3-header")]


def test_p5_no_tasks(root):
    plan_root(root)
    text = PLAN[: PLAN.index("### Task 1")]
    assert plan_rules(text, root) == [(1, "P5-tasks")]


def test_p5_compares_with_the_previous_heading(root):
    plan_root(root)
    task2 = PLAN[PLAN.index("### Task 2") :]
    text = PLAN.replace("### Task 2: Second", "### Task 3: Second")
    text += "\n" + task2.replace("### Task 2: Second", "### Task 4: Fourth")
    found = [v for v in plan_rules(text, root) if v[1] == "P5-tasks"]
    assert found == [(35, "P5-tasks")]


def test_p5_task_heading_inside_a_fence_is_ignored(root):
    plan_root(root)
    text = PLAN.replace("Done.", "````markdown\n### Task 9: Not a task\n````")
    assert sl.lint_plan(text, root) == []


def test_p7_has_no_etc_rule(root):
    plan_root(root)
    text = PLAN.replace("Build the thing.", "Build the thing, etc.")
    assert sl.lint_plan(text, root) == []


def test_crlf_plan_lints_like_lf(root):
    plan = plan_root(root)
    plan.write_bytes(PLAN.replace("\n", "\r\n").encode("utf-8"))
    assert run_script(SCRIPT, str(plan), "--root", str(root)).returncode == 0


def test_p6_missing_files_line(root):
    plan_root(root)
    text = PLAN.replace("**Files:**\n- Modify: `src/new.py`", "Files below.")
    assert plan_rules(text, root) == [(35, "P6-task-parts")]


def test_p6_missing_commit_step(root):
    plan_root(root)
    text = PLAN.replace("- [ ] **Step 2: Commit**", "- [ ] **Step 2: Push**")
    assert plan_rules(text, root) == [(35, "P6-task-parts")]


def test_p6_file_content_fence_is_not_a_command(root):
    plan_root(root)
    text = PLAN.replace(
        "```bash\npytest -q\n```", "```python file=x.py\npytest -q\n```"
    )
    assert plan_rules(text, root) == [(35, "P6-task-parts")]


def test_p6_run_and_expected_inside_a_fence_do_not_count(root):
    plan_root(root)
    text = PLAN.replace(
        "Run: `pytest tests/test_new.py -q`\nExpected: FAIL",
        "```text\nRun: x\nExpected: FAIL\n```",
    )
    assert plan_rules(text, root) == [(10, "P6-task-parts")]


def test_p6_ticked_steps_and_lowercase_commit_count(root):
    plan_root(root)
    text = PLAN.replace("- [ ] **Step 3: Commit**", "- [x] **Step 3: Lint and commit**")
    assert sl.lint_plan(text, root) == []


def test_p4_names_the_spec_reason(root):
    plan_root(root, record=False)
    found = sl.lint_plan(PLAN, root)
    assert [(n, r) for n, r, _ in found] == [(8, "P4-spec-gated")]
    assert "missing" in found[0][2]


def test_p4_spec_not_found(root):
    plan_root(root)
    found = sl.lint_plan(PLAN.replace("x-design.md", "y-design.md"), root)
    assert [(n, r) for n, r, _ in found] == [(8, "P4-spec-gated")]
    assert "spec not found" in found[0][2]


def test_p9_test_paths_are_not_checked_and_line_suffix_is_stripped(root):
    plan_root(root)
    text = PLAN.replace("- Modify: `src/app.py`", "- Modify: `src/app.py:1-3`")
    text = text.replace("- Test: `tests/test_new.py`", "- Test: `tests/missing.py`")
    assert sl.lint_plan(text, root) == []


def test_p9_test_path_counts_as_new_for_a_later_modify(root):
    plan_root(root)
    text = PLAN.replace("- Modify: `src/new.py`", "- Modify: `tests/test_new.py`")
    assert sl.lint_plan(text, root) == []


def test_p9_create_in_a_later_task_does_not_count(root):
    plan_root(root)
    text = PLAN.replace("- Modify: `src/app.py`", "- Modify: `src/late.py`")
    text = text.replace("- Modify: `src/new.py`", "- Create: `src/late.py`")
    assert plan_rules(text, root) == [(14, "P9-path")]
