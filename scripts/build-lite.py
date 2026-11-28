"""Build agent-kit-lite, the Markdown-only plugin, from plugin/ into lite/.

Usage: python scripts/build-lite.py [--check]

Copies an allowlist of plugin/ (the conventions, ten skills, three commands and
the references they name) into lite/, applies the full-only and lite-only
comment blocks the sources carry, rewrites agent-kit: skill names to
agent-kit-lite:, swaps three descriptions, and generates the manifest, README,
licence, icon and the workspace-rules skill. It refuses output that breaks the
plugin directory's rules (installs, variables, kit code, unknown skill names,
leftover markers, full-only commands, home paths) and leaves lite/ untouched.
With --check it writes nothing and reports drift between the build and lite/.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKILLS = (
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
COMMANDS = ("ship.md", "ship-fast.md", "handoff.md")
SKIP = {"skills/audit/user-mode.md"}
KEEP_EXT = {".md", ".txt", ".json", ".yaml", ".yml", ".png"}
OPEN_FULL = "<!-- full-only -->"
CLOSE_FULL = "<!-- /full-only -->"
OPEN_LITE = "<!-- lite-only (agent-kit-lite only; agent-kit ignores this block)"
REF_RE = re.compile(r"references/([\w.-]+\.md)")
CONV_RE = re.compile(r"(?<![\w./-])" + "conventions" + "/")
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

OVERRIDES = {
    "skills/grill/SKILL.md": (
        "Use when the user asks to be grilled on a plan, design or idea, for "
        "example after a design summary and before the spec is written. "
        "Interviews the user in numbered rounds, each question with a "
        "recommended answer, over the design's open decisions plus a coverage "
        "checklist, until the user confirms a shared understanding."
    ),
    "skills/audit/SKILL.md": (
        "Use when asked to audit or health-check a whole repository, or the "
        "Claude Code setup in it (CLAUDE.md, .claude/, hooks, skills, commands, "
        "plugin), in one pass. Read-only; writes one report of cited, checked "
        "findings to docs/audit/audit.md."
    ),
    "commands/ship-fast.md": (
        "Use for a proof of concept of about an hour - interview the user for "
        "the spec (or take an existing one), have the user read and approve it, "
        "ask the product decisions out loud, and take it to a tested, smoke-run "
        "pull request with green CI, with no gates, no review round and no "
        "merge; tasks run one at a time"
    ),
}

RULES_FRONTMATTER = (
    "---\n"
    "name: workspace-rules\n"
    'description: "Use before building a feature, designing or gating a spec or '
    "plan, creating a worktree, opening a pull request, or running /ship or "
    "/ship-fast. The agent-kit-lite workspace rules: key decisions, gates, "
    'pre-flight checks, worktrees and clean-up."\n'
    "---\n"
    "\n"
)

MANIFEST_DESCRIPTION = (
    "Markdown-only agent-kit for Claude Code: gated specs and plans, /ship and "
    "/ship-fast from spec to pull request, handoffs and the workspace "
    "conventions, with no hooks or scripts."
)

INLINE_FULL_RE = re.compile(re.escape(OPEN_FULL) + ".*?" + re.escape(CLOSE_FULL))
INLINE_LITE_RE = re.compile(re.escape(OPEN_LITE) + "(.*?)-->")
LEFTOVER = ("<!-- full-only", "<!-- /full-only", "<!-- lite-only")

INSTALL_RE = re.compile(
    r"curl |wget |Invoke-WebRequest|pip install|npm i\b|npm install|"
    r"pnpm install|npx|uvx|pipx|bunx"
)
VAR_RE = re.compile(r"\$\{?([A-Za-z_]\w*)|%([A-Za-z_]\w*)%")
ENV_RE = re.compile(r"\$env:", re.I)
ALLOWED_VARS = {"CLAUDE_PLUGIN_ROOT", "ARGUMENTS"}
KIT_CODE = (
    "<plugin root>/scripts/",
    "${CLAUDE_PLUGIN_ROOT}/scripts/",
    "hooks.json",
    "CLAUDE_KIT_GRILL",
)
KIT_MAP_RE = re.compile(r"kit map", re.I)
LITE_NAME_RE = re.compile(r"agent-kit-lite:([\w-]+)")
MARKER_RE = re.compile(r"<!--\s*(?:/full-only|full-only|lite-only)")
COMMAND_RE = re.compile(
    r"/(?:[\w-]+:)?(?:" + "|".join(EXCLUDED_COMMANDS) + r")(?![\w-])"
)
HOME_RE = re.compile(r"(?:^|(?<=[\s`'\"(\[<]))(?:~/|%USERPROFILE%)")


class MarkerError(ValueError):
    """A full-only or lite-only block that the build cannot apply."""


def apply_markers(text: str, path: str) -> str:
    """Drop full-only blocks and unwrap lite-only blocks (text is LF)."""
    out: list[str] = []
    state = "none"
    opened = 0
    for n, line in enumerate(text.split("\n"), 1):
        stripped = line.strip()
        if state == "none":
            if stripped in (OPEN_FULL, OPEN_LITE):
                state = "full" if stripped == OPEN_FULL else "lite"
                opened = n
                continue
            new = INLINE_FULL_RE.sub("", line)
            new = INLINE_LITE_RE.sub(lambda m: m.group(1).strip(), new)
            if any(marker in new for marker in LEFTOVER):
                raise MarkerError(
                    f"{path}:{n}: marker must be alone on its line or open and "
                    "close on one line"
                )
            if new != line and not new.strip():
                continue
            out.append(new)
        elif state == "full":
            if stripped == CLOSE_FULL:
                state = "none"
            elif "<!--" in line:
                raise MarkerError(f"{path}:{n}: nested marker inside a full-only block")
        else:
            if stripped == "-->":
                state = "none"
            elif "<!--" in line or "-->" in line:
                raise MarkerError(f"{path}:{n}: comment inside a lite-only block")
            else:
                out.append(line)
    if state != "none":
        raise MarkerError(f"{path}:{opened}: unclosed {state}-only block")
    return "\n".join(out)


def rewrite_skill_names(text: str) -> str:
    return text.replace("agent-kit:", "agent-kit-lite:")


def override_description(text: str, value: str, path: str) -> str:
    """Replace the frontmatter description line with a JSON-quoted value."""
    if not text.startswith("---\n"):
        raise ValueError(f"{path}: no frontmatter")
    end = text.find("\n---\n", 3)
    if end == -1:
        raise ValueError(f"{path}: no frontmatter")
    lines = text[4:end].split("\n")
    for i, line in enumerate(lines):
        if line.startswith("description:"):
            lines[i] = "description: " + json.dumps(value, ensure_ascii=False)
            return "---\n" + "\n".join(lines) + text[end:]
    raise ValueError(f"{path}: no description: line in the frontmatter")


def rules_skill(rules_text: str) -> str:
    return RULES_FRONTMATTER + CONV_RE.sub("../../conventions/", rules_text)


def transform(source: str, rel: str, text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = apply_markers(text, source)
    text = rewrite_skill_names(text)
    if rel in OVERRIDES:
        text = override_description(text, OVERRIDES[rel], source)
    return text


def _sources(plugin: Path, problems: list[str]) -> list[tuple[str, Path]]:
    """(lite path, source file) pairs of the kept plugin files, sorted."""
    pairs: list[tuple[str, Path]] = []
    conventions = plugin / "conventions"
    if conventions.is_dir():
        pairs += [(f"{conventions.name}/{p.name}", p) for p in conventions.glob("*.md")]
    else:
        problems.append("plugin/conventions: missing source folder")
    for name in SKILLS:
        folder = plugin / "skills" / name
        if not folder.is_dir():
            problems.append(f"plugin/skills/{name}: missing source folder")
            continue
        for path in folder.rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            rel = path.relative_to(plugin).as_posix()
            if rel not in SKIP:
                pairs.append((rel, path))
    for name in COMMANDS:
        path = plugin / "commands" / name
        if path.is_file():
            pairs.append((f"commands/{name}", path))
        else:
            problems.append(f"plugin/commands/{name}: missing source file")
    return sorted(pairs)


def _decode(data: bytes, source: str, problems: list[str]) -> str | None:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        problems.append(f"{source}: not UTF-8 text")
        return None


def _text(source: str, rel: str, data: bytes, problems: list[str]) -> str | None:
    text = _decode(data, source, problems)
    if text is None:
        return None
    try:
        return transform(source, rel, text)
    except ValueError as exc:  # MarkerError included
        problems.append(str(exc))
        return None


def _read(root: Path, rel: str, problems: list[str]) -> bytes | None:
    path = root / rel
    if not path.is_file():
        problems.append(f"{rel}: missing source file")
        return None
    return path.read_bytes()


def build(root: Path, dest: Path) -> list[str]:
    """Build the lite tree from root/plugin into dest; return the problems."""
    problems: list[str] = []
    plugin = root / "plugin"
    texts: dict[str, str] = {}
    blobs: dict[str, bytes] = {}

    for rel, path in _sources(plugin, problems):
        source = f"plugin/{rel}"
        data = path.read_bytes()
        if data.startswith(b"#!"):
            continue
        if path.suffix == ".html":
            out_rel = rel + ".txt"
        elif path.suffix in KEEP_EXT and path.suffix != ".png":
            out_rel = rel
        elif path.name == "LICENSE":
            out_rel = rel
        elif path.suffix == ".png":
            blobs[rel] = data
            continue
        else:
            continue
        text = _text(source, out_rel, data, problems)
        if text is not None:
            texts[out_rel] = text

    seen: dict[str, str] = {"spec-lint-checks.md": "build-lite.py"}
    queue = ["spec-lint-checks.md"]
    for rel in sorted(texts):
        for name in REF_RE.findall(texts[rel]):
            if name not in seen:
                seen[name] = rel
                queue.append(name)
    while queue:
        name = queue.pop(0)
        path = plugin / "references" / name
        if not path.is_file():
            problems.append(f"{seen[name]}: names missing references/{name}")
            continue
        rel = f"references/{name}"
        text = _text(f"plugin/{rel}", rel, path.read_bytes(), problems)
        if text is None:
            continue
        texts[rel] = text
        for found in REF_RE.findall(text):
            if found not in seen:
                seen[found] = rel
                queue.append(found)

    data = _read(root, "plugin/.claude-plugin/plugin.json", problems)
    if data is not None:
        source = json.loads(data.decode("utf-8-sig"))
        manifest = {"name": "agent-kit-lite"}
        for key in ("version", "author", "homepage", "repository", "keywords"):
            if key in source:
                manifest[key] = source[key]
        manifest["description"] = MANIFEST_DESCRIPTION
        manifest["license"] = "MIT"
        texts[".claude-plugin/plugin.json"] = (
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
    data = _read(root, "scripts/lite-README.md", problems)
    if data is not None:
        text = _text("scripts/lite-README.md", "README.md", data, problems)
        if text is not None:
            texts["README.md"] = text
    data = _read(root, "LICENSE", problems)
    if data is not None:
        text = _decode(data, "LICENSE", problems)
        if text is not None:
            texts["LICENSE"] = text.replace("\r\n", "\n").replace("\r", "\n")
    data = _read(root, "scripts/lite-icon.png", problems)
    if data is not None:
        blobs[".claude-plugin/icon.png"] = data
    rel = "skills/workspace-rules/SKILL.md"
    data = _read(root, "plugin/rules.md", problems)
    if data is not None:
        text = _text("plugin/rules.md", rel, data, problems)
        if text is not None:
            texts[rel] = rules_skill(text)

    dest.mkdir(parents=True, exist_ok=True)
    for rel in sorted(set(texts) | set(blobs)):
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel in blobs:
            target.write_bytes(blobs[rel])
        else:
            with target.open("w", encoding="utf-8", newline="\n") as fh:
                fh.write(texts[rel])
    return problems


def check_text(
    rel: str, text: str, kit_names: list[str], skills: set[str], commands: set[str]
) -> list[str]:
    """The directory-rule violations in one built file's text."""
    out: list[str] = []
    for n, line in enumerate(text.split("\n"), 1):

        def hit(rule: str, detail: str, n: int = n) -> None:
            out.append(f"{rel}:{n}: {rule}: {detail}")

        m = INSTALL_RE.search(line)
        if m:
            hit("install", m.group(0).strip())
        bad = [
            m.group(0)
            for m in VAR_RE.finditer(line)
            if (m.group(1) or m.group(2)) not in ALLOWED_VARS
        ]
        m = ENV_RE.search(line)
        if m:
            bad.append(m.group(0))
        if bad:
            hit("variable", bad[0])
        found = [name for name in kit_names if name in line]
        found += [code for code in KIT_CODE if code in line]
        m = KIT_MAP_RE.search(line)
        if m:
            found.append(m.group(0))
        if found:
            hit("kit-code", found[0])
        names = []
        if "agent-kit:" in line:
            names.append("agent-kit:")
        names += [
            m.group(0)
            for m in LITE_NAME_RE.finditer(line)
            if m.group(1) not in skills and m.group(1) not in commands
        ]
        if names:
            hit("skill-name", names[0])
        m = MARKER_RE.search(line)
        if m:
            hit("marker", m.group(0))
        m = COMMAND_RE.search(line)
        if m:
            hit("command", m.group(0))
        m = HOME_RE.search(line)
        if m:
            hit("home-path", m.group(0))
    return out


def _files(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file())


def check_tree(root: Path, dest: Path) -> list[str]:
    """Run check_text over every built text file under dest."""
    kit_names: list[str] = []
    for sub in ("scripts", "hooks"):
        folder = root / "plugin" / sub
        if folder.is_dir():
            kit_names += sorted(p.name for p in folder.iterdir() if p.is_file())
    skills_dir = dest / "skills"
    skills = (
        {p.name for p in skills_dir.iterdir() if p.is_dir()}
        if skills_dir.is_dir()
        else set()
    )
    commands_dir = dest / "commands"
    commands = (
        {p.stem for p in commands_dir.iterdir() if p.is_file()}
        if commands_dir.is_dir()
        else set()
    )
    problems: list[str] = []
    for path in _files(dest):
        if path.suffix == ".png":
            continue
        rel = path.relative_to(dest).as_posix()
        text = path.read_text(encoding="utf-8")
        problems += check_text(rel, text, kit_names, skills, commands)
    return problems


def _content(path: Path) -> bytes:
    data = path.read_bytes()
    return data if path.suffix == ".png" else data.replace(b"\r\n", b"\n")


def compare(built: Path, lite: Path) -> list[str]:
    """Drift between a fresh build and the committed lite/ tree."""

    def rels(folder: Path) -> set[str]:
        if not folder.is_dir():
            return set()
        return {p.relative_to(folder).as_posix() for p in _files(folder)}

    a, b = rels(built), rels(lite)
    out = [f"missing: {rel}" for rel in a - b]
    out += [f"extra: {rel}" for rel in b - a]
    out += [
        f"differs: {rel}"
        for rel in a & b
        if _content(built / rel) != _content(lite / rel)
    ]
    return sorted(out)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args not in ([], ["--check"]):
        print("usage: python scripts/build-lite.py [--check]", file=sys.stderr)
        return 2
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass
    lite = ROOT / "lite"
    with tempfile.TemporaryDirectory() as tmp:
        built = Path(tmp) / "lite"
        problems = build(ROOT, built)
        problems += check_tree(ROOT, built)
        if args:
            problems += compare(built, lite)
        if problems:
            for line in problems:
                print(line)
            return 1
        if args:
            print("ok")
            return 0
        if lite.exists():
            shutil.rmtree(lite)
        shutil.copytree(built, lite)
        print(f"wrote lite/ ({len(_files(lite))} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
