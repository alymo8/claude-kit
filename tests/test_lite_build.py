"""Checks on the generated agent-kit-lite plugin in lite/ (frozen, spec D10).

lite/ is built from plugin/ by scripts/build-lite.py. These tests hold it to
what Anthropic's plugin directory accepts from an unverified publisher.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
LITE = REPO / "lite"
PLUGIN = REPO / "plugin"

ALLOWED_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".png"}
LITE_SKILLS = {
    "audit",
    "capture-learnings",
    "grill",
    "lean-context",
    "plan-gate",
    "pr-review-respond",
    "present",
    "review",
    "spec-gate",
    "teach",
    "workspace-rules",
}
LITE_COMMANDS = {"handoff.md", "ship-fast.md", "ship.md"}
EXCLUDED_COMMANDS = (
    "ship-many",
    "new-project",
    "adopt-conventions",
    "spec-html",
    "statusline",
    "docker-compact",
    "archive-session",
    "audit-deep",
)
ALLOWED_VARS = {"CLAUDE_PLUGIN_ROOT", "ARGUMENTS"}
INSTALL_RE = re.compile(
    r"curl |wget |Invoke-WebRequest|pip install|npm i\b|npm install"
    r"|pnpm install|npx|uvx|pipx|bunx"
)
VAR_RE = re.compile(r"\$\{?([A-Za-z_]\w*)|%([A-Za-z_]\w*)%")
ENV_RE = re.compile(r"\$env:", re.I)
KIT_LITERALS = (
    "<plugin root>/scripts/",
    "${CLAUDE_PLUGIN_ROOT}/scripts/",
    "hooks.json",
    "CLAUDE_KIT_GRILL",
)
KIT_MAP_RE = re.compile(r"kit map", re.I)
LITE_SKILL_RE = re.compile(r"agent-kit-lite:([A-Za-z0-9_-]+)")
MARKER_RE = re.compile(r"<!--\s*/?(?:full-only|lite-only)")
COMMAND_RE = re.compile(
    r"/(?:[\w-]+:)?(?:" + "|".join(EXCLUDED_COMMANDS) + r")(?![\w-])"
)
HOME_RE = re.compile(r"(?:^|[\s`'\"(\[<])(?:~/|%USERPROFILE%)")
FENCE_RE = re.compile(r"^```.*?^```[ \t]*$", re.M | re.S)
CODE_SPAN_RE = re.compile(r"(`+)(?:(?!\n[ \t]*\n).)+?(?<!`)\1(?!`)", re.S)
LINK_RE = re.compile(r"\]\(([^)\s]+)\)")
FM_LINE_RE = re.compile(r"^([A-Za-z][\w-]*):(?: (.*))?$")
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def lite_files() -> list[Path]:
    return sorted(p for p in LITE.rglob("*") if p.is_file())


def rel(path: Path) -> str:
    return path.relative_to(LITE).as_posix()


def kit_code_names() -> list[str]:
    return sorted(
        p.name
        for folder in ("scripts", "hooks")
        for p in (PLUGIN / folder).iterdir()
        if p.is_file()
    )


def line_problems(
    line: str, skills: set[str], commands: set[str], kit_names: list[str]
) -> list[str]:
    found = []
    if INSTALL_RE.search(line):
        found.append("install")
    names = [a or b for a, b in VAR_RE.findall(line)]
    if ENV_RE.search(line) or any(n not in ALLOWED_VARS for n in names):
        found.append("variable")
    kit = any(n in line for n in kit_names)
    if kit or any(s in line for s in KIT_LITERALS) or KIT_MAP_RE.search(line):
        found.append("kit-code")
    known = skills | commands
    bad = [n for n in LITE_SKILL_RE.findall(line) if n not in known]
    if "agent-kit:" in line or bad:
        found.append("skill-name")
    if MARKER_RE.search(line):
        found.append("marker")
    if COMMAND_RE.search(line):
        found.append("command")
    if HOME_RE.search(line):
        found.append("home-path")
    return found


def run_check(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(root / "scripts" / "build-lite.py"), "--check"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def copy_repo(dest: Path) -> None:
    skip = shutil.ignore_patterns("__pycache__")
    for name in ("plugin", "scripts", "lite"):
        shutil.copytree(REPO / name, dest / name, ignore=skip)
    shutil.copy2(REPO / "LICENSE", dest / "LICENSE")


def test_build_check_finds_no_drift():
    result = run_check(REPO)
    assert result.returncode == 0, result.stdout + result.stderr


def test_build_check_accepts_a_crlf_checkout(tmp_path):
    copy_repo(tmp_path)
    for path in (tmp_path / "lite").rglob("*"):
        if path.is_file() and path.suffix != ".png":
            data = path.read_bytes().replace(b"\r\n", b"\n")
            path.write_bytes(data.replace(b"\n", b"\r\n"))
    result = run_check(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_build_check_reports_drift(tmp_path):
    copy_repo(tmp_path)
    ship = tmp_path / "lite" / "commands" / "ship.md"
    ship.write_bytes(ship.read_bytes() + b"drift\n")
    result = run_check(tmp_path)
    assert result.returncode == 1
    assert "commands/ship.md" in result.stdout


def test_lite_has_its_generated_files():
    for name in ("README.md", "LICENSE", ".claude-plugin/plugin.json"):
        assert (LITE / name).is_file(), name
    assert (LITE / ".claude-plugin" / "icon.png").is_file()
    assert (LITE / "skills" / "workspace-rules" / "SKILL.md").is_file()


def test_every_file_is_an_allowed_type():
    problems = []
    for path in lite_files():
        data = path.read_bytes()
        if path.suffix not in ALLOWED_EXT and path.name != "LICENSE":
            problems.append(f"{rel(path)}: file type")
        if data.startswith(b"#!"):
            problems.append(f"{rel(path)}: starts with #!")
        if path.suffix == ".png":
            continue
        if b"\0" in data:
            problems.append(f"{rel(path)}: NUL byte")
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            problems.append(f"{rel(path)}: not UTF-8")
    assert not problems, problems


def test_no_banned_files_or_folders():
    problems = []
    for path in LITE.rglob("*"):
        name = path.name
        if path.is_file() and name.lower() in {"claude.md", "agents.md"}:
            problems.append(rel(path))
        if name == ".mcp.json":
            problems.append(rel(path))
        if path.is_dir() and name in {"hooks", ".claude"}:
            problems.append(rel(path))
    assert not problems, problems


def test_no_line_breaks_a_built_text_check():
    skills = {p.name for p in (LITE / "skills").iterdir() if p.is_dir()}
    commands = {p.stem for p in (LITE / "commands").glob("*.md")}
    kit_names = kit_code_names()
    assert "spec-lint.py" in kit_names and "run.py" in kit_names
    problems = []
    for path in lite_files():
        if path.suffix == ".png":
            continue
        text = path.read_text(encoding="utf-8")
        for number, line in enumerate(text.splitlines(), 1):
            for rule in line_problems(line, skills, commands, kit_names):
                problems.append(f"{rel(path)}:{number}: {rule}")
    assert not problems, "\n".join(problems)


def test_frontmatter_values_are_quoted():
    files = sorted(LITE.glob("skills/*/SKILL.md"))
    files += sorted(LITE.glob("commands/*.md"))
    problems = []
    for path in files:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        assert text.startswith("---\n"), rel(path)
        head = text[4 : text.index("\n---\n", 4)]
        for line in head.splitlines():
            match = FM_LINE_RE.match(line)
            if not match:
                problems.append(f"{rel(path)}: not key: value: {line}")
                continue
            value = (match.group(2) or "").strip()
            quoted = len(value) >= 2 and value[0] == value[-1] == '"'
            if ("#" in value or ": " in value) and not quoted:
                problems.append(f"{rel(path)}: unquoted: {line}")
    assert not problems, problems


def png_chunks(data: bytes) -> list[bytes]:
    chunks, pos = [], 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos : pos + 4])
        chunks.append(data[pos + 4 : pos + 8])
        pos += 12 + length
    return chunks


def test_icon_is_a_square_png_within_limits():
    data = (LITE / ".claude-plugin" / "icon.png").read_bytes()
    assert data[:8] == PNG_SIGNATURE
    width, height = struct.unpack(">II", data[16:24])
    assert width == height
    assert 512 <= width <= 2048
    assert len(data) < 2 * 1024 * 1024
    chunks = png_chunks(data)
    assert chunks[0] == b"IHDR" and chunks[-1] == b"IEND"
    assert not {b"tEXt", b"iTXt", b"zTXt", b"eXIf", b"tIME"} & set(chunks)


def test_lint_checklist_names_every_rule():
    source = (PLUGIN / "scripts" / "spec-lint.py").read_text(encoding="utf-8")
    doc = ast.get_docstring(ast.parse(source))
    ids = set(re.findall(r"\b[LP]\d+-[a-z]+(?:-[a-z]+)*", doc))
    assert len(ids) >= 20
    checklist = LITE / "references" / "spec-lint-checks.md"
    text = checklist.read_text(encoding="utf-8")
    assert sorted(i for i in ids if i not in text) == []


def test_lite_manifest_matches_the_full_plugin():
    path = LITE / ".claude-plugin" / "plugin.json"
    lite = json.loads(path.read_text(encoding="utf-8"))
    full_path = PLUGIN / ".claude-plugin" / "plugin.json"
    full = json.loads(full_path.read_text(encoding="utf-8"))
    assert lite["name"] == "agent-kit-lite"
    assert lite["version"] == full["version"]
    assert lite["license"] == "MIT"
    for key in ("description", "author", "homepage", "repository", "keywords"):
        assert lite.get(key), key
    assert "icon" not in lite
    assert "hooks" not in lite


def test_lite_ships_exactly_the_d3_skills_and_commands():
    skills = {p.name for p in (LITE / "skills").iterdir() if p.is_dir()}
    assert skills == LITE_SKILLS
    commands = {p.name for p in (LITE / "commands").iterdir()}
    assert commands == LITE_COMMANDS
    assert (LITE / "skills" / "present" / "template.html.txt").is_file()
    assert not (LITE / "skills" / "audit" / "user-mode.md").exists()


def test_relative_links_resolve_inside_lite():
    root = LITE.resolve()
    broken = []
    for path in LITE.rglob("*.md"):
        prose = FENCE_RE.sub("", path.read_text(encoding="utf-8"))
        prose = CODE_SPAN_RE.sub("", prose)
        for match in LINK_RE.finditer(prose):
            href = match.group(1).split("#", 1)[0]
            if not href or "://" in href or href.startswith("mailto:"):
                continue
            target = (path.parent / href).resolve()
            if not target.exists() or not target.is_relative_to(root):
                broken.append(f"{rel(path)} -> {href}")
    assert not broken, broken


def find_bash() -> tuple[str, dict[str, str]] | None:
    env = dict(os.environ)
    if os.name != "nt":
        bash = shutil.which("bash")
        return (bash, env) if bash else None
    out = subprocess.run(["git", "--exec-path"], capture_output=True, text=True)
    if out.returncode != 0:
        return None
    root = Path(out.stdout.strip()).parents[2]
    bin_dir = root / "usr" / "bin"
    if not (bin_dir / "bash.exe").is_file():
        return None
    env["PATH"] = str(bin_dir) + os.pathsep + env.get("PATH", "")
    return str(bin_dir / "bash.exe"), env


def id_command() -> str:
    text = (LITE / "references" / "spec-lint-checks.md").read_text("utf-8")
    [line] = [x.strip() for x in text.splitlines() if "hash-object --stdin" in x]
    assert "<document>" in line
    return line


def lite_id(tmp_path: Path, text: str, newline: str = "\n") -> str:
    found = find_bash()
    if found is None:
        pytest.skip("no bash with tr, grep and sed")
    bash, env = found
    doc = tmp_path / "doc.md"
    doc.write_bytes(text.replace("\n", newline).encode("utf-8"))
    command = id_command().replace("<document>", "doc.md")
    result = subprocess.run(
        [bash, "-c", command], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    value = result.stdout.strip()
    assert re.fullmatch(r"[0-9a-f]{40}", value), value
    return value


SPEC = (
    "# Sample spec\n\n- **Status:** draft\n- **Date:** 2026-11-27\n\n"
    "## Purpose\n\nText.\n\n```\n- **Status:** draft\n- [x] fenced box\n```\n\n"
    "- [ ] open box\n"
)
PLAN = (
    "# Sample plan\n\n- **Status:** draft\n- **Date:** 2026-11-27\n\n"
    "### Task 1: One\n\n- [ ] **Step 1: Write it**\n  - [ ] nested\n\n"
    "~~~\n- [ ] fenced step\n~~~\n"
)


def test_lite_id_ignores_status_ticks_and_line_endings(tmp_path):
    base = lite_id(tmp_path, SPEC)
    approved = SPEC.replace("draft\n- **Date", "approved\n- **Date")
    assert lite_id(tmp_path, approved) == base
    assert lite_id(tmp_path, SPEC.replace("- [ ] open", "- [x] open")) == base
    assert lite_id(tmp_path, SPEC, newline="\r\n") == base
    assert lite_id(tmp_path, SPEC.rstrip("\n")) == base
    plan = lite_id(tmp_path, PLAN)
    ticked = PLAN.replace("- [ ] **Step", "- [x] **Step")
    assert lite_id(tmp_path, ticked.replace("  - [ ]", "  - [X]")) == plan
    assert lite_id(tmp_path, PLAN.replace("draft", "approved")) == plan


def test_lite_id_catches_other_changes(tmp_path):
    base = lite_id(tmp_path, SPEC)
    assert lite_id(tmp_path, SPEC.replace("Text.", "Text!")) != base
    fenced = SPEC.replace("```\n- **Status:** draft", "```\n- **Status:** done")
    assert lite_id(tmp_path, fenced) != base
    assert lite_id(tmp_path, SPEC.replace("- [x] fenced", "- [ ] fenced")) != base
    plan = lite_id(tmp_path, PLAN)
    assert lite_id(tmp_path, PLAN.replace("- [ ] fenced", "- [x] fenced")) != plan
    assert lite_id(tmp_path, PLAN.replace("Write it", "Write that")) != plan
