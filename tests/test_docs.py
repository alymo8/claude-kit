import re
import subprocess

from helpers import REPO, broken_links

SCRIPT_REF_RE = re.compile(r"python \.\./(\S+\.py)")
# Plans embed snippets of other files; template links resolve only once rendered.
SKIP_DIRS = ("docs/superpowers/plans/", "plugin/templates/")


def tracked_markdown():
    out = subprocess.run(
        ["git", "ls-files", "--", "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [
        REPO / line
        for line in out.splitlines()
        if line and not line.startswith(SKIP_DIRS)
    ]


def test_relative_markdown_links_resolve():
    assert not broken_links(tracked_markdown())


def test_claude_md_script_paths_exist():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    refs = SCRIPT_REF_RE.findall(text)
    assert refs, "CLAUDE.md should reference the renderer as python ../<path>.py"
    missing = [r for r in refs if not (REPO / r).exists()]
    assert not missing, missing


def _claude_md_section(title):
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    body = text.split(f"\n## {title}\n", 1)[1]
    return body.split("\n## ", 1)[0]


def test_claude_md_gates_plans():
    assert "claude-kit:plan-gate" in _claude_md_section("Specs and plans")


def test_claude_md_has_no_per_section_design_approval():
    section = " ".join(_claude_md_section("Designing a spec").split())
    assert "no approval pause between design sections" in section
