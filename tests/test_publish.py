"""Tests for publishing the kit as an installable plugin (agent-kit)."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from helpers import FENCE_RE, LINK_RE, PLUGIN, REPO, RULES

MARKETPLACE = REPO / ".claude-plugin" / "marketplace.json"


def test_marketplace_fields():
    data = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
    assert data["name"] == "agent-kit"
    assert data["owner"]["name"] == "alymo8"
    [entry] = data["plugins"]
    assert entry["name"] == "agent-kit"
    assert entry["source"] == "./plugin"
    assert entry["description"].strip()
    assert "version" not in entry


def test_marketplace_file_is_tracked():
    out = subprocess.run(
        ["git", "ls-files", ".claude-plugin/marketplace.json"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert out.strip() == ".claude-plugin/marketplace.json"


def test_gitignore_whitelists_marketplace():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "!/.claude-plugin/" in lines


def test_frontmatter_hints_are_quoted():
    review = (PLUGIN / "skills" / "review" / "SKILL.md").read_text("utf-8")
    assert 'argument-hint: "[base-ref] [spec.md] [plan.md]"' in review
    new = (PLUGIN / "commands" / "new-project.md").read_text("utf-8")
    assert 'argument-hint: "[name] [node|python]"' in new


def tracked(*paths: str, root: Path = REPO) -> list[str]:
    lines = []
    for extra in ([], ["--others", "--exclude-standard"]):
        out = subprocess.run(
            ["git", "ls-files", *extra, *paths],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
        ).stdout
        lines += [line for line in out.splitlines() if line]
    return lines


def test_plugin_links_stay_inside_plugin():
    root = PLUGIN.resolve()
    outside = []
    for rel in tracked("plugin"):
        if not rel.endswith(".md"):
            continue
        md = REPO / rel
        prose = FENCE_RE.sub("", md.read_text(encoding="utf-8"))
        for match in LINK_RE.finditer(prose):
            href = match.group(1)
            if "://" in href or href.startswith("mailto:"):
                continue
            path = href.split("#", 1)[0]
            if not path:
                continue
            target = (md.parent / path).resolve()
            try:
                target.relative_to(root)
            except ValueError:
                outside.append(f"{rel} -> {href}")
    assert not outside, outside


OLD_ROOT_RE = re.compile(r"(?<![\w./-])conventions/")
EXEMPT_PHRASES = {
    "plugin/skills/review/SKILL.md": (
        "the repo's `conventions/engineering-practices.md`"
    ),
    "plugin/skills/spec-gate/rubric.md": (
        "`conventions/decision-log.md` in the repository"
    ),
    # A path inside the built Vibe plugin copy, not the old repo-root folder.
    "tests/test_vibe_plugin.py": '"conventions/README.md"',
}
SKIP_PREFIXES = ("docs/superpowers/", "docs/audit/", "vendor/")
SKIP_FILES = {"tests/test_publish.py", "plugin/rules.md"}


def skipped(rel: str) -> bool:
    if rel.startswith(SKIP_PREFIXES) or rel in SKIP_FILES:
        return True
    if re.fullmatch(r"knowledge/decisions/0[^/]*\.md", rel):
        return True
    return bool(re.fullmatch(r"plugin/conventions/[^/]*\.md", rel))


def test_no_live_file_names_old_conventions_root():
    hits = []
    for rel in tracked():
        if skipped(rel):
            continue
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        phrase = EXEMPT_PHRASES.get(rel)
        if phrase:
            text = text.replace(phrase, "")
        for number, line in enumerate(text.splitlines(), 1):
            if OLD_ROOT_RE.search(line):
                hits.append(f"{rel}:{number}")
    assert not hits, "\n".join(hits)


def test_gitignore_drops_root_conventions():
    lines = (REPO / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "!/conventions/" not in lines


def test_agents_md_imports_rules():
    agents = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    assert "@plugin/rules.md" in agents.splitlines()
    assert "## Developing the kit" in agents
    assert "## How we work" not in agents
    rules = RULES.read_text(encoding="utf-8")
    assert rules.startswith("# Workspace conventions\n")
    assert "These rules apply to every repo that uses the kit." in rules
    assert "This file plays two roles" not in rules
    assert "python ../plugin" not in rules
    assert "](docs/" not in rules
    assert "https://github.com/alymo8/claude-kit/blob/main/docs/setup.md" in rules


ALLOWED = (
    "<config>/claude-kit/",
    "alymo8/claude-kit",
    "claude-kit.task",
    ".claude/claude-kit/",
    '"claude-kit" / "nudge-level"',
    "/claude-kit/nudge-level",
    "claude-kit-nudge-",
    'STATE_FOLDER = "claude-kit"',
)
RENAME_SKIP_PREFIXES = ("docs/superpowers/", "docs/audit/", "knowledge/", "vendor/")
RENAME_SKIP_FILES = {
    "tests/test_publish.py",
    "tests/test_install.py",
    "tests/test_install_statusline.py",
    "tests/test_spec_index.py",
}
LEGACY_FILES = {
    "plugin/install.py",
    "plugin/scripts/install-statusline.py",
    "plugin/scripts/spec-index.py",
}
LEGACY_RE = re.compile(r"^\s*LEGACY_\w+ = ")


def claude_kit_hits(root: Path) -> list[str]:
    hits = []
    for rel in tracked(root=root):
        if rel.startswith(RENAME_SKIP_PREFIXES) or rel in RENAME_SKIP_FILES:
            continue
        try:
            text = (root / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for number, line in enumerate(text.splitlines(), 1):
            if rel in LEGACY_FILES and LEGACY_RE.match(line):
                continue
            for allowed in ALLOWED:
                line = line.replace(allowed, "")
            if "claude-kit" in line:
                hits.append(f"{rel}:{number}")
    return hits


def test_claude_kit_only_in_allowed_places():
    hits = claude_kit_hits(REPO)
    assert not hits, "\n".join(hits)


def test_guards_check_untracked_unignored_files(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text("ignored.md\n", encoding="utf-8")
    (tmp_path / "new.md").write_text("see claude-kit\n", encoding="utf-8")
    (tmp_path / "ignored.md").write_text("claude-kit\n", encoding="utf-8")
    files = tracked(root=tmp_path)
    assert "new.md" in files and "ignored.md" not in files
    assert claude_kit_hits(tmp_path) == ["new.md:1"]


def test_no_plugin_file_names_old_skills_link():
    hits = []
    for rel in tracked("plugin"):
        try:
            text = (REPO / rel).read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "skills/claude-kit" in text:
            hits.append(rel)
    assert not hits, hits


def test_fallbacks_name_the_kit_map_root():
    bad = []
    for sub in ("commands", "skills", "references"):
        for md in sorted((PLUGIN / sub).rglob("*.md")):
            text = " ".join(md.read_text(encoding="utf-8").split())
            if "~/.claude/skills/agent-kit" in text or "<plugin root>/" in text:
                if "the plugin root stated in the kit map" not in text:
                    bad.append(md.relative_to(PLUGIN).as_posix())
    assert not bad, bad
