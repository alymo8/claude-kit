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
