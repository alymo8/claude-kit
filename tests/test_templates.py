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
    ".github/dependabot.yml",
    ".github/workflows/README.md",
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


KIT_WORKFLOWS = PLUGIN.parent / ".github" / "workflows"
STACK_CIS = [TEMPLATES / "stacks" / s / "ci.yml" for s in ("node", "python")]
PIN_RE = re.compile(r"uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+(\.\d+){0,2}$")


def _workflow_files():
    return [
        *sorted((PROJECT / ".github" / "workflows").glob("*.yml")),
        *STACK_CIS,
        *sorted(KIT_WORKFLOWS.glob("*.yml")),
    ]


def test_actions_are_sha_pinned():
    for path in _workflow_files():
        lines = _yaml_lines(path.read_text("utf-8"))
        uses = [line for line in lines if "uses:" in line]
        for line in uses:
            assert PIN_RE.search(line), f"{path}: {line}"
        if any(line.strip() == "steps:" for line in lines):
            assert uses, f"{path} has steps but no pinned action"


def test_pull_request_has_no_paths_filter():
    for path in [SECRET_SCAN, *STACK_CIS]:
        lines = path.read_text("utf-8").splitlines()
        for line in _yaml_lines("\n".join(lines)):
            stripped = line.strip()
            assert not stripped.startswith(("paths:", "paths-ignore:")), path
        index = next(
            i for i, line in enumerate(lines) if line.strip() == "pull_request:"
        )
        comments = []
        for line in reversed(lines[:index]):
            if not line.lstrip().startswith("#"):
                break
            comments.append(line)
        assert "`paths:`" in "\n".join(comments), path


DEPENDABOT = PROJECT / ".github" / "dependabot.yml"
KIT_DEPENDABOT = PLUGIN.parent / ".github" / "dependabot.yml"
WORKFLOWS_README = PROJECT / ".github" / "workflows" / "README.md"
JOB_RE = re.compile(r"^  ([\w-]+):\s*$")


def _job_ids(text):
    ids, in_jobs = [], False
    for line in _yaml_lines(text):
        if line.startswith("jobs:"):
            in_jobs = True
        elif line and not line[0].isspace():
            in_jobs = False
        elif in_jobs and (match := JOB_RE.match(line)):
            ids.append(match.group(1))
    return ids


def test_dependabot_matches_kit_and_is_monthly_grouped():
    assert KIT_DEPENDABOT.read_bytes() == DEPENDABOT.read_bytes()
    text = DEPENDABOT.read_text("utf-8")
    for needle in ("package-ecosystem: github-actions", "interval: monthly", "groups:"):
        assert needle in text, needle


def test_workflows_readme_names_every_job():
    readme = WORKFLOWS_README.read_text("utf-8")
    template_workflows = sorted((PROJECT / ".github" / "workflows").glob("*.yml"))
    jobs = set()
    for path in [*template_workflows, *STACK_CIS]:
        jobs |= set(_job_ids(path.read_text("utf-8")))
    assert jobs == {"build-test", "gitleaks", "review"}
    for job in jobs:
        assert f"`{job}`" in readme, job
    for path in template_workflows:
        assert path.name in readme, path.name
    for needle in ("paths:", "branches/main/protection", "Not included"):
        assert needle in readme, needle
