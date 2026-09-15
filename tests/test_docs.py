import re
import subprocess

from helpers import REPO

LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
SCRIPT_REF_RE = re.compile(r"python \.\./(\S+\.py)")


FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)
# Plans embed snippets of other files (with their own relative links); skip them.
SKIP_DIRS = ("docs/superpowers/plans/",)


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


def prose(md):
    """Markdown text with fenced code blocks removed."""
    return FENCE_RE.sub("", md.read_text(encoding="utf-8"))


def test_relative_markdown_links_resolve():
    broken = []
    for md in tracked_markdown():
        for match in LINK_RE.finditer(prose(md)):
            href = match.group(1).split("#", 1)[0]
            if not href or "://" in href or href.startswith("mailto:"):
                continue
            if not (md.parent / href).exists():
                broken.append(f"{md.relative_to(REPO)} -> {href}")
    assert not broken, "\n".join(broken)


def test_claude_md_script_paths_exist():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    refs = SCRIPT_REF_RE.findall(text)
    assert refs, "CLAUDE.md should reference the renderer as python ../<path>.py"
    missing = [r for r in refs if not (REPO / r).exists()]
    assert not missing, missing
