"""Unit tests of scripts/build-lite.py, the agent-kit-lite build."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from helpers import REPO, load_module

bl = load_module(REPO / "scripts" / "build-lite.py", "build_lite")
OPEN = bl.OPEN_LITE
C = "conventions" + "/"

SKILL_NAMES = (
    "capture-learnings",
    "lean-context",
    "teach",
    "grill",
    "spec-gate",
    "plan-gate",
    "review",
    "present",
    "pr-review-respond",
    "audit",
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    _write(root / "LICENSE", "MIT License\n\nCopyright\n")
    _write(root / "scripts" / "lite-README.md", "# Lite\n")
    icon = root / "scripts" / "lite-icon.png"
    icon.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)
    manifest = {
        "name": "agent-kit",
        "version": "9.9.9",
        "author": {"name": "someone"},
        "homepage": "https://example.com/kit",
        "repository": "https://example.com/kit",
        "keywords": ["a", "b"],
    }
    _write(root / "plugin" / ".claude-plugin" / "plugin.json", json.dumps(manifest))
    _write(root / "plugin" / "rules.md", f"# Rules\n\nSee [x]({C}a.md).\n")
    _write(root / "plugin" / "conventions" / "a.md", "# A\n")
    _write(root / "plugin" / "scripts" / "tool.py", "print('x')\n")
    _write(root / "plugin" / "hooks" / "hook.py", "print('y')\n")
    _write(root / "plugin" / "references" / "spec-lint-checks.md", "# Checks\n")
    commands = root / "plugin" / "commands"
    _write(commands / "ship.md", "---\ndescription: ship\n---\nShip it.\n")
    _write(commands / "ship-fast.md", "---\ndescription: fast\n---\nFast.\n")
    _write(commands / "handoff.md", "---\ndescription: handoff\n---\nHand off.\n")
    for name in SKILL_NAMES:
        _write(
            root / "plugin" / "skills" / name / "SKILL.md",
            f"---\nname: {name}\ndescription: the {name} skill\n---\nBody.\n",
        )
    return root


def test_full_only_block_on_its_own_lines_is_removed():
    text = "a\n<!-- full-only -->\nb\n<!-- /full-only -->\nc\n"
    assert bl.apply_markers(text, "x.md") == "a\nc\n"


def test_lite_only_block_on_its_own_lines_is_unwrapped():
    text = f"a\n{OPEN}\nb\n-->\nc\n"
    assert bl.apply_markers(text, "x.md") == "a\nb\nc\n"


def test_inline_blocks():
    text = f"x <!-- full-only -->old<!-- /full-only -->{OPEN} new --> y\n"
    assert bl.apply_markers(text, "x.md") == "x new y\n"


def test_line_emptied_by_inline_removal_is_dropped():
    text = "a\n<!-- full-only -->b<!-- /full-only -->\nc\n"
    assert bl.apply_markers(text, "x.md") == "a\nc\n"


def test_indented_markers():
    text = "1. a\n   <!-- full-only -->\n   b\n   <!-- /full-only -->\n   c\n"
    assert bl.apply_markers(text, "x.md") == "1. a\n   c\n"


def test_unclosed_block_fails():
    with pytest.raises(bl.MarkerError, match="x.md:2: unclosed"):
        bl.apply_markers("a\n<!-- full-only -->\nb\n", "x.md")
    with pytest.raises(bl.MarkerError, match="x.md:2: unclosed"):
        bl.apply_markers(f"a\n{OPEN}\nb\n", "x.md")


def test_nested_block_fails():
    text = f"<!-- full-only -->\n{OPEN}\n-->\n<!-- /full-only -->\n"
    with pytest.raises(bl.MarkerError, match="x.md:2: nested"):
        bl.apply_markers(text, "x.md")


def test_comment_inside_lite_block_fails():
    text = f"{OPEN}\nb --> c\n-->\n"
    with pytest.raises(bl.MarkerError, match="x.md:2: comment inside"):
        bl.apply_markers(text, "x.md")


def test_other_lite_opener_fails():
    text = "a\n<!-- lite-only something else\nb\n-->\n"
    with pytest.raises(bl.MarkerError, match="x.md:2: marker must be alone"):
        bl.apply_markers(text, "x.md")


def test_stray_closer_fails():
    text = "a\n<!-- /full-only -->\nb\n"
    with pytest.raises(bl.MarkerError, match="x.md:2: marker must be alone"):
        bl.apply_markers(text, "x.md")


def test_skill_names_are_rewritten_once():
    text = "use agent-kit:spec-gate and agent-kit-lite:review"
    assert bl.rewrite_skill_names(text) == (
        "use agent-kit-lite:spec-gate and agent-kit-lite:review"
    )


def test_description_override_is_quoted():
    text = "---\nname: g\ndescription: old: text\n---\nbody\n"
    out = bl.override_description(text, 'new: "x" # y', "g.md")
    assert out == '---\nname: g\ndescription: "new: \\"x\\" # y"\n---\nbody\n'
    with pytest.raises(ValueError):
        bl.override_description("no frontmatter\n", "v", "g.md")


def test_rules_skill_moves_conventions_links():
    rules = (
        f"[a]({C}a.md#x) `{C}` [{C}b.md]({C}b.md)"
        " plugin/conventions/c.md ../../conventions/d.md\n"
    )
    out = bl.rules_skill(rules)
    assert out.startswith('---\nname: workspace-rules\ndescription: "')
    body = out.split("\n---\n", 1)[1]
    assert "](../../conventions/a.md#x)" in body
    assert "`../../conventions/`" in body
    assert "[../../conventions/b.md](../../conventions/b.md)" in body
    assert "plugin/conventions/c.md" in body
    assert " ../../conventions/d.md" in body


FLAGGED = [
    ("pip install x", "install"),
    ("npx thing", "install"),
    ("see $HOME", "variable"),
    ("%TEMP%", "variable"),
    ("$env:PATH", "variable"),
    ("run tool.py", "kit-code"),
    ("the Kit Map", "kit-code"),
    ("hooks.json", "kit-code"),
    ("agent-kit:review", "skill-name"),
    ("agent-kit-lite:nope", "skill-name"),
    ("<!-- full-only -->", "marker"),
    ("run /ship-many now", "command"),
    ("/other:audit-deep", "command"),
    ("`~/.claude/x`", "home-path"),
]


def _check(line: str) -> list[str]:
    return bl.check_text("x.md", line + "\n", ["tool.py"], {"spec-gate"}, {"ship"})


@pytest.mark.parametrize(("line", "rule"), FLAGGED)
def test_check_text_flags_each_rule(line, rule):
    out = _check(line)
    assert len(out) == 1, out
    assert out[0].startswith(f"x.md:1: {rule}: "), out


CLEAN = [
    "${CLAUDE_PLUGIN_ROOT}/conventions/a.md",
    "$ARGUMENTS",
    "echo $1 $@",
    "$(git rev-parse HEAD)",
    "agent-kit-lite:spec-gate",
    "/agent-kit-lite:ship x",
    "a SessionStart hook in your project",
    "tests/x.py",
    "costs $5",
]


@pytest.mark.parametrize("line", CLEAN)
def test_check_text_allows_clean_lines(line):
    assert _check(line) == []


def test_build_writes_the_tree(tmp_path):
    root = make_root(tmp_path)
    _write(root / "plugin" / "skills" / "audit" / "user-mode.md", "# User\n")
    dest = tmp_path / "out"
    assert bl.build(root, dest) == []
    manifest = json.loads(
        (dest / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["name"] == "agent-kit-lite"
    assert manifest["version"] == "9.9.9"
    assert "icon" not in manifest
    for rel in (
        ".claude-plugin/icon.png",
        "README.md",
        "LICENSE",
        "skills/workspace-rules/SKILL.md",
        "references/spec-lint-checks.md",
        "commands/ship.md",
        "commands/ship-fast.md",
        "commands/handoff.md",
    ):
        assert (dest / rel).is_file(), rel
    assert not (dest / "skills" / "audit" / "user-mode.md").exists()


def test_file_rules(tmp_path):
    root = make_root(tmp_path)
    present = root / "plugin" / "skills" / "present"
    _write(present / "template.html", "<html></html>\n")
    _write(present / "tool.py", "print(1)\n")
    _write(present / "run.md", "#!/bin/sh\necho hi\n")
    _write(root / "plugin" / "skills" / "teach" / "LICENSE", "MIT\n")
    dest = tmp_path / "out"
    assert bl.build(root, dest) == []
    assert (dest / "skills" / "present" / "template.html.txt").is_file()
    assert (dest / "skills" / "teach" / "LICENSE").is_file()
    assert not (dest / "skills" / "present" / "tool.py").exists()
    assert not (dest / "skills" / "present" / "run.md").exists()
    assert not (dest / "skills" / "present" / "template.html").exists()


def test_references_follow_built_text(tmp_path):
    root = make_root(tmp_path)
    refs = root / "plugin" / "references"
    _write(
        root / "plugin" / "commands" / "ship.md",
        "---\ndescription: ship\n---\n"
        "<!-- full-only -->\n"
        "Read ${CLAUDE_PLUGIN_ROOT}/references/a.md.\n"
        "<!-- /full-only -->\n"
        "Read references/b.md.\n",
    )
    _write(refs / "a.md", "# A\n")
    _write(refs / "b.md", "# B\n\nSee references/c.md.\n")
    _write(refs / "c.md", "# C\n")
    dest = tmp_path / "out"
    assert bl.build(root, dest) == []
    assert (dest / "references" / "b.md").is_file()
    assert (dest / "references" / "c.md").is_file()
    assert not (dest / "references" / "a.md").exists()

    _write(refs / "c.md", "# C\n\nSee references/missing.md.\n")
    problems = bl.build(root, tmp_path / "out2")
    assert any("references/missing.md" in p for p in problems), problems


def _text_files(folder: Path) -> list[Path]:
    return [p for p in folder.rglob("*") if p.is_file() and p.suffix != ".png"]


def _to_crlf(path: Path) -> None:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    path.write_bytes(data.replace(b"\n", b"\r\n"))


def test_build_normalises_crlf_sources(tmp_path):
    root = make_root(tmp_path)
    first = tmp_path / "first"
    assert bl.build(root, first) == []
    for path in _text_files(root / "plugin"):
        _to_crlf(path)
    second = tmp_path / "second"
    assert bl.build(root, second) == []
    assert bl.compare(first, second) == []
    for path in _text_files(second):
        assert b"\r" not in path.read_bytes(), path


def test_compare_reports_drift(tmp_path):
    root = make_root(tmp_path)
    one, two = tmp_path / "one", tmp_path / "two"
    assert bl.build(root, one) == []
    assert bl.build(root, two) == []
    with (two / "commands" / "ship.md").open("a", encoding="utf-8") as fh:
        fh.write("more\n")
    (two / "README.md").unlink()
    _write(two / "extra.md", "# Extra\n")
    out = bl.compare(one, two)
    assert "differs: commands/ship.md" in out
    assert "missing: README.md" in out
    assert "extra: extra.md" in out
    assert len(out) == 3, out

    three = tmp_path / "three"
    assert bl.build(root, three) == []
    for path in _text_files(three):
        _to_crlf(path)
    assert bl.compare(one, three) == []
