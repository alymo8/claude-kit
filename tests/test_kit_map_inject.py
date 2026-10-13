import json
import os
import re
import shutil
import subprocess
import sys

import pytest
from helpers import PLUGIN, REPO, clean_env, load_module, run_script

HOOK = PLUGIN / "hooks" / "kit_map_inject.py"
ROW = re.compile(r"^\|\s*\[([^\]]+)\]\(([^)#\s]+\.md)\)\s*\|")


def run(script=HOOK, **env: str):
    return run_script(script, stdin="{}", env=clean_env(**env))


def context(result) -> str:
    out = json.loads(result.stdout)["hookSpecificOutput"]
    assert out["hookEventName"] == "SessionStart"
    return out["additionalContext"]


def readme_playbooks() -> list[str]:
    """Parse the playbook table independently of the hook."""
    files, section = [], False
    readme = REPO / "conventions" / "README.md"
    for line in readme.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            section = line.strip() == "## The playbooks"
            continue
        m = ROW.match(line.strip())
        if section and m:
            files.append(m.group(2))
    return files


@pytest.mark.parametrize("env", [{}, {"CLAUDE_KIT_KIT_MAP": "1"}])
def test_on_by_default_lists_root_and_every_playbook(env):
    result = run(**env)
    assert result.returncode == 0
    text = context(result)
    assert f"Kit root: {REPO.as_posix()}." in text
    files = readme_playbooks()
    assert len(files) == 6
    for name in files:
        path = REPO / "conventions" / name
        assert path.is_file()
        assert path.as_posix() in text
    assert f"Kit ADRs: {(REPO / 'knowledge' / 'decisions').as_posix()}/" in text
    assert "resolve against the kit root" in text


def test_zero_turns_it_off():
    result = run(CLAUDE_KIT_KIT_MAP="0")
    assert result.returncode == 0
    assert result.stdout == ""


def test_size_cap():
    # The root appears once per line, so this assumes a normal-length checkout
    # path (the cap holds up to roughly 130 characters of root).
    assert len(context(run())) <= 1500


def make_kit(tmp_path, readme: str):
    kit = tmp_path / "kit"
    (kit / "plugin" / "hooks").mkdir(parents=True)
    shutil.copy(HOOK, kit / "plugin" / "hooks" / HOOK.name)
    if readme is not None:
        (kit / "conventions").mkdir()
        (kit / "conventions" / "README.md").write_text(readme, encoding="utf-8")
    return kit


def test_missing_conventions_prints_nothing(tmp_path):
    kit = make_kit(tmp_path, None)
    result = run(kit / "plugin" / "hooks" / HOOK.name)
    assert result.returncode == 0
    assert result.stdout == ""


def test_missing_playbook_file_is_skipped(tmp_path):
    readme = (
        "## The playbooks\n\n| Playbook | What |\n|---|---|\n"
        "| [Real](real.md) | x |\n| [Ghost](ghost.md) | y |\n"
    )
    kit = make_kit(tmp_path, readme)
    (kit / "conventions" / "real.md").write_text("x", encoding="utf-8")
    text = context(run(kit / "plugin" / "hooks" / HOOK.name))
    assert "- Real: " in text
    assert "Ghost" not in text
    assert "Kit ADRs" not in text


def test_only_playbooks_section_is_parsed(tmp_path):
    readme = (
        "## Intro\n\n| [Other](other.md) | z |\n\n"
        "## The playbooks\n\n| [Real](real.md) | x |\n"
    )
    kit = make_kit(tmp_path, readme)
    for name in ("real.md", "other.md"):
        (kit / "conventions" / name).write_text("x", encoding="utf-8")
    text = context(run(kit / "plugin" / "hooks" / HOOK.name))
    assert "- Real: " in text
    assert "Other" not in text


def test_zero_rows_omits_playbook_list(tmp_path):
    kit = make_kit(tmp_path, "## The playbooks\n\nnothing\n")
    text = context(run(kit / "plugin" / "hooks" / HOOK.name))
    assert "Kit root:" in text
    assert "Playbooks" not in text


@pytest.fixture
def plugin_link(tmp_path):
    link = tmp_path / "link"
    try:
        if sys.platform == "win32":
            done = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(link), str(PLUGIN)],
                capture_output=True,
            )
            if done.returncode != 0:
                pytest.skip("cannot create a junction")
        else:
            os.symlink(PLUGIN, link, target_is_directory=True)
    except OSError:
        pytest.skip("cannot create a link")
    yield link
    # Remove only the link itself; a recursive delete would follow it into plugin/.
    if sys.platform == "win32":
        os.rmdir(link)
    else:
        os.unlink(link)


def test_resolves_through_link(plugin_link):
    text = context(run(plugin_link / "hooks" / HOOK.name))
    assert f"Kit root: {REPO.as_posix()}." in text


def test_build_map_uses_link_text_verbatim():
    module = load_module(HOOK, "kit_map_inject")
    assert "- Decision log (ADRs): " in module.build_map(REPO)


def test_registered_on_session_start_without_matcher():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    groups = hooks["hooks"]["SessionStart"]
    commands = [[h["command"] for h in g["hooks"]] for g in groups]
    lean = next(i for i, c in enumerate(commands) if "lean_context_inject.py" in c[0])
    kit = groups[lean + 1]
    assert "hooks/kit_map_inject.py" in kit["hooks"][0]["command"]
    assert "matcher" not in kit


POINTER = "the session-hygiene playbook (path in the kit map)"


def test_lean_context_pointers_name_playbook_via_kit_map():
    lean = PLUGIN / "hooks" / "lean_context_inject.py"
    assert POINTER in run_script(lean, stdin="{}", env=clean_env()).stdout
    skill = (PLUGIN / "skills" / "lean-context" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert POINTER in skill
    assert "`conventions/session-hygiene.md` in the kit" not in skill


def test_rows_outside_conventions_are_ignored(tmp_path):
    readme = "## The playbooks\n\n| [Up](../up.md) | x |\n| [Real](real.md) | y |\n"
    kit = make_kit(tmp_path, readme)
    (kit / "up.md").write_text("x", encoding="utf-8")
    (kit / "conventions" / "real.md").write_text("x", encoding="utf-8")
    text = context(run(kit / "plugin" / "hooks" / HOOK.name))
    assert "- Real: " in text
    assert "Up" not in text
