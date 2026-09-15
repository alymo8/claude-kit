import json

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
