import re
import subprocess

from helpers import REPO, broken_links

SCRIPT_REF_RE = re.compile(r"python \.\./(\S+\.py)")
# Plans embed snippets of other files; template links resolve only once rendered.
# vendor/ is an unchanged upstream copy.
SKIP_DIRS = ("docs/superpowers/plans/", "plugin/templates/", "vendor/")


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
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    refs = SCRIPT_REF_RE.findall(text)
    assert refs, "CLAUDE.md should reference the renderer as python ../<path>.py"
    missing = [r for r in refs if not (REPO / r).exists()]
    assert not missing, missing


def test_claude_md_is_the_agents_stub():
    text = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
    assert text.strip() == "@AGENTS.md"
    assert len(text.splitlines()) == 1


def _claude_md_section(title):
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    body = text.split(f"\n## {title}\n", 1)[1]
    return body.split("\n## ", 1)[0]


def test_claude_md_gates_plans():
    assert "claude-kit:plan-gate" in _claude_md_section("Specs and plans")


def test_claude_md_has_no_per_section_design_approval():
    section = " ".join(_claude_md_section("Designing a spec").split())
    assert "no approval pause between design sections" in section


def test_docs_wire_ship_fast():
    adr = "0021-ship-fast-skips-gates.md"
    assert (REPO / "knowledge" / "decisions" / adr).is_file()
    index = (REPO / "knowledge" / "decisions" / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
    conv = (REPO / "conventions" / "spec-driven-development.md").read_text(
        encoding="utf-8"
    )
    assert "/ship-fast" in conv and adr in conv
    for name in ("README.md", "AGENTS.md"):
        assert "/ship-fast" in (REPO / name).read_text(encoding="utf-8"), name
    skill = (REPO / "plugin" / "skills" / "parallel-tasks" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "`/ship` or `/ship-fast`" in skill
    assert "committed in `/ship` step 3" not in skill


def _paragraphs_with(text, needle):
    return [p for p in text.replace("\r\n", "\n").split("\n\n") if needle in p]


def test_docs_wire_ship_fast_interview():
    adr = "0022-ship-fast-user-driven-spec.md"
    decisions = REPO / "knowledge" / "decisions"
    assert (decisions / adr).is_file()
    index = (decisions / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
    row_0021 = next(
        line for line in index.splitlines() if "0021-ship-fast-skips-gates.md" in line
    )
    assert "amended by 0022" in row_0021
    adr_0021 = (decisions / "0021-ship-fast-skips-gates.md").read_text("utf-8")
    assert "amended by 0022" in adr_0021 and adr in adr_0021
    for name in ("README.md", "AGENTS.md", "conventions/spec-driven-development.md"):
        text = (REPO / name).read_text(encoding="utf-8")
        paragraphs = _paragraphs_with(text, "/ship-fast")
        assert any("interview" in p for p in paragraphs), name


def test_learnings_capture_is_part_of_finishing():
    claude = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    para = claude.split(
        "**A feature is not finished until its workspace is gone.**", 1
    )[1]
    para = para.split("\n\n", 1)[0]
    assert "claude-kit:capture-learnings" in para
    convention = (REPO / "conventions" / "project-memory.md").read_text(
        encoding="utf-8"
    )
    assert "## Capturing learnings" in convention
    assert "capture-learnings" in convention.split("## Capturing learnings", 1)[1]


def test_claude_md_has_rules_moved_from_memory():
    text = " ".join((REPO / "AGENTS.md").read_text(encoding="utf-8").split())
    for phrase in (
        "never suggests deleting",
        "Never write the names of private repos",
        "fold it into an existing flow step",
    ):
        assert phrase in text, phrase
    kit_dev = text.split("## Developing the kit", 1)[1]
    assert "Never write the names of private repos" in kit_dev
    assert "fold it into an existing flow step" in kit_dev


def test_team_setup_adrs_indexed():
    decisions = REPO / "knowledge" / "decisions"
    index = (decisions / "README.md").read_text(encoding="utf-8")
    for name in (
        "0033-cross-platform-installer.md",
        "0034-workspace-rules-inject.md",
        "0035-process-rules-in-claude-md.md",
    ):
        assert (decisions / name).is_file(), name
        assert f"]({name})" in index, name
    row = next(line for line in index.splitlines() if "0005-kit-is" in line)
    assert "amended by 0033" in row
    adr = (decisions / "0005-kit-is-a-skills-dir-plugin.md").read_text("utf-8")
    assert "amended by 0033" in adr


def _tracked_plugin_text():
    """Every tracked text file under plugin/ (binary files are skipped)."""
    out = subprocess.run(
        ["git", "ls-files", "plugin"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    for line in out.splitlines():
        try:
            yield (REPO / line).read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError):
            continue


def test_setup_guide_exists_and_is_linked():
    assert (REPO / "docs" / "setup.md").is_file()
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "](docs/setup.md)" in readme


def test_setup_guide_lists_every_env_switch():
    guide = (REPO / "docs" / "setup.md").read_text(encoding="utf-8")
    names = set()
    for text in _tracked_plugin_text():
        names |= set(re.findall(r"CLAUDE_KIT_[A-Z][A-Z_]*", text))
    names.add("CLAUDE_KIT_WORKSPACE_RULES")
    missing = sorted(name for name in names if name not in guide)
    assert not missing, missing


def test_setup_guide_names_prerequisites_and_installer():
    guide = (REPO / "docs" / "setup.md").read_text(encoding="utf-8")
    assert "superpowers@claude-plugins-official" in guide
    assert "install.py" in guide
    assert "ExecutionPolicy" in guide
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    assert "ExecutionPolicy" not in readme
    assert "eleven hooks" in readme
    assert "CLAUDE_KIT_VAULT" not in readme
    assert "CLAUDE_KIT_WORKSPACE_RULES=0" in readme


def test_agent_agnostic_adr_amends_0034_and_0035():
    decisions = REPO / "knowledge" / "decisions"
    adr = "0050-agent-agnostic-kit.md"
    assert (decisions / adr).is_file()
    index = (decisions / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
    amended = ("0034-workspace-rules-inject.md", "0035-process-rules-in-claude-md.md")
    for old in amended:
        row = next(line for line in index.splitlines() if old in line)
        assert "amended by 0050" in row, old
        assert "amended by 0050" in (decisions / old).read_text("utf-8"), old


def test_vault_adrs_moved_by_0051():
    decisions = REPO / "knowledge" / "decisions"
    adr = "0051-vault-tooling-split.md"
    assert (decisions / adr).is_file()
    index = (decisions / "README.md").read_text(encoding="utf-8")
    assert f"]({adr})" in index
    for old in ("0040-personal-vault.md", "0047-untrusted-vault-content.md"):
        row = next(line for line in index.splitlines() if old in line)
        assert "| moved |" in row, old
        text = (decisions / old).read_text("utf-8")
        assert "- **Status:** moved" in text, old
        assert "ADR 0051" in text, old


def test_docs_cover_other_agents():
    guide = (REPO / "docs" / "setup.md").read_text(encoding="utf-8")
    section = guide.split("## Using the kit with Vibe, Codex or Cursor", 1)[1]
    section = section.split("\n## ", 1)[0]
    for needle in ("--agent vibe", "--agent codex", "--agent cursor", "/hooks"):
        assert needle in section, needle
    for needle in ("vendor-superpowers.py", "agent-skills.py", "/ship-many"):
        assert needle in section, needle
    readme = " ".join((REPO / "README.md").read_text(encoding="utf-8").split())
    para = readme.split("Mistral Vibe", 1)[1][:400]
    assert "Codex" in para and "Cursor" in para and "docs/setup.md" in para
