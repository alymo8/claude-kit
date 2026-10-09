"""Structure tests for the present skill and its deck checker."""

from __future__ import annotations

import re

from helpers import PLUGIN, load_module, run_script

PRESENT = PLUGIN / "skills" / "present"
TEMPLATE = PRESENT / "template.html"
SCRIPT = PLUGIN / "scripts" / "check-deck.py"


def frontmatter(text):
    assert text.startswith("---\n")
    out = {}
    for line in text.split("---", 2)[1].strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


def deck(slides: str) -> str:
    """The template with its example slides replaced by ``slides``."""
    text = TEMPLATE.read_text(encoding="utf-8")
    head, rest = text.split("<!-- SLIDES START -->", 1)
    _, tail = rest.split("<!-- SLIDES END -->", 1)
    return f"{head}<!-- SLIDES START -->\n{slides}\n<!-- SLIDES END -->{tail}"


def slide(time: str, body: str = "<h2>x</h2>") -> str:
    return f'<section class="slide" data-time="{time}">{body}</section>'


def test_frontmatter():
    front = frontmatter((PRESENT / "SKILL.md").read_text(encoding="utf-8"))
    assert front["name"] == "present"
    assert front["description"].startswith("Use when")
    assert len(front["description"]) <= 1024
    assert "disable-model-invocation" not in front
    assert front["argument-hint"]


def test_body_defines_the_contract():
    body = (PRESENT / "SKILL.md").read_text(encoding="utf-8")
    for phrase in (
        "template.html",
        "check-deck.py",
        "AskUserQuestion",
        "Planned",
        "superseded",
        "every slide",
        "data-time",
    ):
        assert phrase in body, phrase


def test_template_is_self_contained_and_marked():
    text = TEMPLATE.read_text(encoding="utf-8")
    assert "<!-- SLIDES START -->" in text and "<!-- SLIDES END -->" in text
    assert not re.search(r"(src|href)\s*=\s*[\"']?https?:", text)
    assert "@import" not in text and "url(http" not in text


def test_template_passes_the_checker():
    checker = load_module(SCRIPT, "check_deck")
    assert checker.problems(TEMPLATE.read_text(encoding="utf-8"), minutes=10) == []


def test_checker_counts_slides_and_times():
    checker = load_module(SCRIPT, "check_deck")
    html = deck(slide("0:00") + slide("1:30") + slide("8:45"))
    assert checker.slide_times(html) == ["0:00", "1:30", "8:45"]
    assert checker.problems(html, minutes=10) == []


def test_checker_flags_missing_and_unordered_times():
    checker = load_module(SCRIPT, "check_deck")
    html = deck(slide("0:00") + '<section class="slide"><h2>x</h2></section>')
    assert any("data-time" in p for p in checker.problems(html, minutes=10))
    html = deck(slide("0:00") + slide("3:00") + slide("2:00"))
    assert any("order" in p for p in checker.problems(html, minutes=10))


def test_checker_flags_overrun_and_external_urls():
    checker = load_module(SCRIPT, "check_deck")
    html = deck(slide("0:00") + slide("10:30"))
    assert any("10" in p for p in checker.problems(html, minutes=10))
    html = deck(slide("0:00", '<img src="https://example.com/a.png">'))
    assert any("external" in p for p in checker.problems(html, minutes=10))


def test_cli_reports_problems_without_rendering(tmp_path):
    good = tmp_path / "good.html"
    good.write_text(deck(slide("0:00") + slide("2:00")), encoding="utf-8")
    result = run_script(SCRIPT, str(good), "--minutes", "10", "--no-render")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "2 slides" in result.stdout

    bad = tmp_path / "bad.html"
    bad.write_text(deck(slide("0:00") + slide("12:00")), encoding="utf-8")
    result = run_script(SCRIPT, str(bad), "--minutes", "10", "--no-render")
    assert result.returncode == 1
