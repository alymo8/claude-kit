"""Tests for plugin/scripts/check-findings.py."""

from __future__ import annotations

import pytest
from helpers import PLUGIN, load_module

cf = load_module(PLUGIN / "scripts" / "check-findings.py", "check_findings")

SRC = "import os\n\n\ndef run(cmd):\n    os.system(cmd)  # noqa\n    return True\n"


def finding(
    sev="High",
    title="Shell call",
    where="`app.py:5`",
    evidence="`os.system(cmd)  # noqa`",
    confidence="verified",
    impact="Shell injection.",
    fix="Use subprocess.run with a list. Effort: S",
):
    lines = [f"### [{sev}] {title}"]
    for key, value in (
        ("Where", where),
        ("Evidence", evidence),
        ("Confidence", confidence),
        ("Impact", impact),
        ("Fix", fix),
    ):
        if value is not None:
            lines.append(f"- **{key}:** {value}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "app.py").write_text(SRC, encoding="utf-8")
    return tmp_path


def report(repo, *findings, newline="\n"):
    md = repo / "docs" / "audit" / "audit.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    text = "# Audit\n\n## Security\n\n" + "\n".join(findings)
    md.write_bytes(text.replace("\n", newline).encode("utf-8"))
    return md


def check(repo, *findings):
    return cf.check_file(report(repo, *findings), repo)


def test_valid_finding_passes(repo):
    assert check(repo, finding()) == (1, [])


def test_quote_within_three_lines_passes(repo):
    assert check(repo, finding(where="`app.py:3`")) == (1, [])


def test_line_range_passes(repo):
    assert check(repo, finding(where="`app.py:4-6`", evidence="`return True`")) == (
        1,
        [],
    )


def test_where_with_trailing_text_passes(repo):
    assert check(repo, finding(where="`app.py:5` (and two more)")) == (1, [])


def test_severity_is_case_insensitive(repo):
    assert check(repo, finding(sev="HIGH")) == (1, [])


def test_ellipsis_quote_passes(repo):
    ev = "`def run(cmd): ... return True`"
    assert check(repo, finding(where="`app.py:4`", evidence=ev)) == (1, [])


def test_inferred_with_source_passes(repo):
    conf = "inferred (from: the README install section)"
    assert check(repo, finding(confidence=conf)) == (1, [])


def test_absent_finding_skips_path_checks(repo):
    f = finding(where="`.github/workflows/ci.yml`", evidence="(absent)")
    assert check(repo, f) == (1, [])


def test_history_evidence_skips_file_checks(repo):
    f = finding(where="`config/old.env:3`", evidence="`(history 1a2b3c4)`")
    assert check(repo, f) == (1, [])


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"where": "`app.py:99`"}, "past the end"),
        ({"where": "`app.py:0`"}, "invalid"),
        ({"impact": None}, "missing Impact"),
        ({"sev": "Urgent"}, "severity"),
        ({"confidence": "probably"}, "confidence"),
        ({"where": "`nope.py:3`"}, "does not exist"),
        ({"where": "app.py"}, "not path:line"),
        ({"evidence": "`os.remove(path)`"}, "quote not found"),
        ({"evidence": "`...`"}, "no quote"),
    ],
)
def test_rejections(repo, kwargs, reason):
    count, errors = check(repo, finding(**kwargs))
    assert count == 1
    assert len(errors) == 1
    assert reason in errors[0]
    assert '"Shell call"' in errors[0]


def test_quote_too_far_is_rejected(repo):
    (repo / "long.py").write_text("x = 1\n" * 20 + "danger()\n", encoding="utf-8")
    f = finding(where="`long.py:5`", evidence="`danger()`")
    _, errors = check(repo, f)
    assert "quote not found" in errors[0]


def test_quote_extraction():
    assert cf.quote("``a`b``") == "a`b"
    assert cf.quote("`x`, and `y`") == "x"
    assert cf.quote("  `spaced`  ") == "spaced"
    assert cf.quote('"plain words"') == "plain words"
    assert cf.quote("(absent)") == cf.ABSENT


def test_fenced_example_is_ignored(repo):
    example = "```markdown\n" + finding(where="`x.py:1`") + "```\n"
    assert check(repo, example) == (0, [])


def test_other_headings_are_ignored(repo):
    assert check(repo, "### Hooks\n\nAll fine.\n") == (0, [])


def test_crlf_files(repo):
    (repo / "app.py").write_bytes(SRC.replace("\n", "\r\n").encode("utf-8"))
    md = report(repo, finding(), newline="\r\n")
    assert cf.check_file(md, repo) == (1, [])


def test_main_exit_codes(repo, capsys):
    good = report(repo, finding())
    assert cf.main([str(repo), str(good)]) == 0
    assert "1 of 1 findings pass" in capsys.readouterr().out
    report(repo, finding(where="`app.py:99`"))
    assert cf.main([str(repo), str(good)]) == 1
    assert cf.main([]) == 2
    assert cf.main([str(repo / "missing"), str(good)]) == 2
    assert cf.main([str(repo), str(repo / "nothing.md")]) == 2


def test_main_accepts_relative_paths_dirs_and_globs(repo):
    report(repo, finding())
    assert cf.main([str(repo), "docs/audit/audit.md"]) == 0
    assert cf.main([str(repo), "docs/audit"]) == 0
    assert cf.main([str(repo), "docs/audit/*.md"]) == 0


def test_main_prints_non_ascii_titles(repo, capsys):
    md = report(repo, finding(title="Hook → never fires", where="`app.py:99`"))
    assert cf.main([str(repo), str(md)]) == 1
    assert "never fires" in capsys.readouterr().out
