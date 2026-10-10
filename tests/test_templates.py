import re

from helpers import PLUGIN, load_module

TEMPLATES = PLUGIN / "templates"
PROJECT = TEMPLATES / "project"
PLACEHOLDER_RE = re.compile(r"\{\{[a-z_]+\}\}")
ALLOWED = {
    "{{project_name}}",
    "{{date}}",
    "{{stack}}",
    "{{stack_commands}}",
    "{{stack_gitignore}}",
}
EXPECTED = [
    "CLAUDE.md",
    "README.md",
    ".gitignore",
    ".github/workflows/ci.yml",
    ".github/workflows/claude-review.yml",
    ".github/workflows/secret-scan.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    "knowledge/README.md",
    "knowledge/decisions/README.md",
    "knowledge/decisions/0000-template.md",
    "knowledge/archive/.gitkeep",
    "docs/superpowers/README.md",
    "docs/superpowers/specs/.gitkeep",
    "docs/superpowers/plans/.gitkeep",
]


def test_project_template_has_exactly_the_expected_files():
    found = sorted(
        p.relative_to(PROJECT).as_posix() for p in PROJECT.rglob("*") if p.is_file()
    )
    assert found == sorted(EXPECTED)


def test_each_stack_has_its_three_files():
    for stack in ("node", "python"):
        for name in ("ci.yml", "commands.part", "gitignore.part"):
            assert (TEMPLATES / "stacks" / stack / name).exists(), f"{stack}/{name}"


def test_only_allowed_placeholders_are_used():
    used = set()
    for path in TEMPLATES.rglob("*"):
        if path.is_file():
            used |= set(PLACEHOLDER_RE.findall(path.read_text(encoding="utf-8")))
    assert used <= ALLOWED, used - ALLOWED


def test_empty_index_template_matches_generator_output(tmp_path):
    docs = tmp_path / "docs" / "superpowers"
    (docs / "specs").mkdir(parents=True)
    (docs / "plans").mkdir()
    generated = load_module(PLUGIN / "scripts" / "spec-index.py", "si").render(docs)
    template = (PROJECT / "docs" / "superpowers" / "README.md").read_text("utf-8")
    assert template == generated


def test_claude_review_is_disabled_by_default():
    text = (PROJECT / ".github" / "workflows" / "claude-review.yml").read_text("utf-8")
    triggers = text.split("jobs:")[0]
    yaml_only = "\n".join(
        line for line in triggers.splitlines() if not line.lstrip().startswith("#")
    )
    assert "workflow_dispatch:" in yaml_only
    assert "pull_request" not in yaml_only


SECRET_SCAN = PROJECT / ".github" / "workflows" / "secret-scan.yml"
KIT_SECRET_SCAN = PLUGIN.parent / ".github" / "workflows" / "secret-scan.yml"


def _yaml_lines(text):
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def test_secret_scan_uses_pinned_cli():
    text = SECRET_SCAN.read_text("utf-8")
    assert "gitleaks-action" not in text
    assert re.search(r"GITLEAKS_VERSION: \d+\.\d+\.\d+\b", text)
    assert re.search(r"GITLEAKS_SHA256: [0-9a-f]{64}\b", text)
    for needle in (
        "sha256sum -c",
        "gitleaks git",
        '--log-opts="HEAD"',
        "fetch-depth: 0",
    ):
        assert needle in text, needle


def test_secret_scan_declares_read_only_permissions():
    lines = _yaml_lines(SECRET_SCAN.read_text("utf-8"))
    start = lines.index("permissions:")
    block = []
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        block.append(line.strip())
    assert "contents: read" in block
    assert all(not entry or entry == "contents: read" for entry in block), block


def test_kit_secret_scan_matches_template():
    assert KIT_SECRET_SCAN.read_bytes() == SECRET_SCAN.read_bytes()


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
