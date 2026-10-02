import json
import re

from helpers import PLUGIN


def test_plugin_manifest_is_valid():
    data = json.loads(
        (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert data["name"] == "claude-kit"
    assert data["version"]


def test_skill_and_renderer_live_under_plugin():
    assert (PLUGIN / "skills" / "supabase-cli" / "SKILL.md").exists()
    assert (PLUGIN / "scripts" / "render-spec.py").exists()


def test_hook_commands_reference_existing_scripts():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [
        h["command"]
        for groups in hooks["hooks"].values()
        for group in groups
        for h in group["hooks"]
    ]
    assert commands
    for command in commands:
        match = re.search(r"\$\{CLAUDE_PLUGIN_ROOT\}/([^\"]+)", command)
        assert match, command
        assert (PLUGIN / match.group(1)).exists(), command


def test_commands_exist_with_frontmatter():
    expected = {
        "new-project": "scripts/scaffold.py",
        "adopt-conventions": "scripts/scaffold.py",
        "handoff": "scripts/handoff.py",
        "ship": None,
        "ship-many": "scripts/parallel-plan.py",
        "spec-html": "scripts/open-spec.py",
    }
    for name, script in expected.items():
        text = (PLUGIN / "commands" / f"{name}.md").read_text(encoding="utf-8")
        assert text.startswith("---\n"), name
        assert "description:" in text.split("---", 2)[1], name
        if script:
            assert script in text, name


def test_hooks_json_registers_session_hygiene_hooks():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    events = hooks["hooks"]
    assert any(
        "handoff_snapshot.py" in h["command"]
        for g in events["SessionEnd"]
        for h in g["hooks"]
    )
    starts = [g for g in events["SessionStart"] if g.get("matcher") == "startup|clear"]
    assert starts and "handoff_inject.py" in starts[0]["hooks"][0]["command"]
    assert any(
        "context_nudge.py" in h["command"]
        for g in events["UserPromptSubmit"]
        for h in g["hooks"]
    )


def test_lean_context_skill_exists_and_is_short():
    skill_path = PLUGIN / "skills" / "lean-context" / "SKILL.md"
    text = skill_path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = text.split("---", 2)[1]
    assert "name: lean-context" in front
    assert "description:" in front
    assert len(text.splitlines()) <= 60


def test_plugin_version_bumped():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+\.\d+\.\d+", data["version"])
    assert data["version"] != "0.5.0"
    assert "handoff" in data["description"]
    assert "/ship" in data["description"]
    assert "jev" not in data["description"]
    assert "audit-deep" in data["description"]


def test_no_jev_hook_registered():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [
        h["command"] for g in hooks["hooks"]["UserPromptSubmit"] for h in g["hooks"]
    ]
    assert not any("jev" in c for c in commands)
    assert any("context_nudge.py" in c for c in commands)


def test_session_end_hook_has_timeout_above_default_budget():
    # SessionEnd hooks share a 1.5 s budget unless a per-hook timeout raises it;
    # the snapshot measured ~1.2-1.5 s, so without this it is killed silently.
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    snapshot = [
        h
        for g in hooks["hooks"]["SessionEnd"]
        for h in g["hooks"]
        if "handoff_snapshot.py" in h["command"]
    ]
    assert snapshot and snapshot[0].get("timeout", 0) >= 20


def test_stop_hook_regenerates_spec_index():
    # Edits made through Bash never reach the PostToolUse Write|Edit matcher.
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    commands = [h["command"] for g in hooks["hooks"]["Stop"] for h in g["hooks"]]
    assert any(
        "scripts/spec-index.py" in c and "${CLAUDE_PROJECT_DIR}/docs/superpowers" in c
        for c in commands
    )


def test_side_effecting_commands_are_user_only():
    user_only = {"ship", "ship-many", "new-project", "adopt-conventions", "spec-html"}
    for name in user_only | {"handoff"}:
        text = (PLUGIN / "commands" / f"{name}.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        flagged = "disable-model-invocation: true" in frontmatter
        assert flagged == (name in user_only), name


def test_teach_skill_copied_with_license():
    teach = PLUGIN / "skills" / "teach"
    for name in (
        "SKILL.md",
        "GLOSSARY-FORMAT.md",
        "LEARNING-RECORD-FORMAT.md",
        "MISSION-FORMAT.md",
        "RESOURCES-FORMAT.md",
    ):
        assert (teach / name).exists(), name
    front = (teach / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    assert "name: teach" in front
    assert "disable-model-invocation: true" in front
    license_text = (teach / "LICENSE").read_text(encoding="utf-8")
    assert "MIT License" in license_text
    assert "Matt Pocock" in license_text


def test_handoff_command_has_focus_skills_and_redaction():
    text = (PLUGIN / "commands" / "handoff.md").read_text(encoding="utf-8")
    assert "argument-hint:" in text.split("---", 2)[1]
    assert "$ARGUMENTS" in text
    assert "## Suggested skills" in text
    assert text.index("## Commands that work") < text.index("## Suggested skills")
    assert text.index("## Suggested skills") < text.index("## Open questions")
    assert "Never write secrets" in text
    assert "commit or" in text and "diff" in text


def test_hooks_json_registers_grill_inject():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert any(
        "grill_inject.py" in h["command"]
        for g in hooks["hooks"]["SessionStart"]
        for h in g["hooks"]
    )


def test_description_mentions_grill():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert "grill" in data["description"]
    version = tuple(int(part) for part in data["version"].split("."))
    assert version >= (0, 11, 0)
