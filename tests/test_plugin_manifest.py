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
    for name in ("new-project", "adopt-conventions"):
        text = (PLUGIN / "commands" / f"{name}.md").read_text(encoding="utf-8")
        assert text.startswith("---\n"), name
        assert "description:" in text.split("---", 2)[1], name
        assert "scripts/scaffold.py" in text, name
