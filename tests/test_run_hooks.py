import json
import shutil
import subprocess
import sys

import pytest
from helpers import PLUGIN, clean_env, load_module

RUN = PLUGIN / "hooks" / "run.py"
TOOLS = PLUGIN / "references" / "agent-tools.md"
AGENTS = ("vibe", "codex", "cursor")
SCRIPTS = {
    "json_ctx.py": (
        "import json, os, sys\n"
        "e = json.load(sys.stdin)\n"
        "t = f\"json src={e['source']} agent={os.environ['CLAUDE_KIT_AGENT']}\"\n"
        "print(json.dumps({'hookSpecificOutput': {'additionalContext': t}}))\n"
    ),
    "plain.py": "import os\nprint('plain cwd=' + os.path.basename(os.getcwd()))\n",
    "context_nudge.py": "print('CLAUDE ONLY')\n",
    "fails.py": "import sys\nprint('partial')\nsys.exit(3)\n",
    "matched.py": "print('matched')\n",
    "argv.py": "import sys\nprint('stop ' + sys.argv[1])\n",
}


def group(script, matcher=None, arg=""):
    command = f'python "${{CLAUDE_PLUGIN_ROOT}}/hooks/{script}"{arg}'
    out = {"hooks": [{"type": "command", "command": command}]}
    if matcher:
        out["matcher"] = matcher
    return out


def make_kit(tmp_path, session=None):
    plugin = tmp_path / "kit" / "plugin"
    (plugin / "hooks").mkdir(parents=True)
    (plugin / "references").mkdir()
    shutil.copy(RUN, plugin / "hooks" / "run.py")
    shutil.copy(TOOLS, plugin / "references" / "agent-tools.md")
    for name, body in SCRIPTS.items():
        (plugin / "hooks" / name).write_text(body, encoding="utf-8")
    if session is None:
        session = [
            group("json_ctx.py"),
            group("plain.py"),
            group("context_nudge.py"),
            group("fails.py"),
            group("matched.py", "startup|clear"),
        ]
    stop = [group("argv.py", arg=' "${CLAUDE_PROJECT_DIR}/docs"')]
    hooks = {"hooks": {"SessionStart": session, "Stop": stop}}
    (plugin / "hooks" / "hooks.json").write_text(json.dumps(hooks), "utf-8")
    return plugin


@pytest.fixture
def project(tmp_path):
    path = tmp_path / "proj"
    path.mkdir()
    return path


def run(plugin, agent, project, event="SessionStart", stdin=None, cwd=None):
    if stdin is None:
        stdin = json.dumps({"cwd": str(project), "source": "startup"})
    env = clean_env()
    env.pop("CLAUDE_PROJECT_DIR", None)
    return subprocess.run(
        [sys.executable, str(plugin / "hooks" / "run.py")]
        + ["--agent", agent, "--event", event],
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=cwd or project,
        env=env,
        timeout=60,
    )


def context(result, agent, event="SessionStart"):
    assert result.returncode == 0, result.stderr
    data = json.loads(result.stdout)
    if agent == "vibe":
        return data["hook_specific_output"]["additional_context"]
    if agent == "codex":
        assert data["hookSpecificOutput"]["hookEventName"] == event
        return data["hookSpecificOutput"]["additionalContext"]
    return data["additional_context"]


@pytest.mark.parametrize("agent", AGENTS)
def test_each_agent_gets_its_shape(tmp_path, project, agent):
    text = context(run(make_kit(tmp_path), agent, project), agent)
    assert f"json src=startup agent={agent}" in text
    assert "plain cwd=proj" in text
    assert "matched" in text
    assert "CLAUDE ONLY" not in text
    assert "partial" not in text


def test_matcher_applies_to_source(tmp_path, project):
    plugin = make_kit(tmp_path)
    for source, seen in (("resume", False), ("clear", True)):
        stdin = json.dumps({"cwd": str(project), "source": source})
        text = context(run(plugin, "vibe", project, stdin=stdin), "vibe")
        assert ("matched" in text) is seen, source


@pytest.mark.parametrize("agent", AGENTS)
def test_missing_source_becomes_startup(tmp_path, project, agent):
    stdin = json.dumps({"cwd": str(project)})
    result = run(make_kit(tmp_path), agent, project, stdin=stdin)
    text = context(result, agent)
    assert "json src=startup" in text and "matched" in text


def test_failing_script_is_skipped_with_stderr(tmp_path, project):
    result = run(make_kit(tmp_path), "codex", project)
    assert result.returncode == 0
    assert "[agent-kit]" in result.stderr and "fails.py" in result.stderr


def test_slow_script_times_out(tmp_path, capsys):
    mod = load_module(RUN, "kit_run_hooks")
    argv = [sys.executable, "-c", "import time; time.sleep(5)"]
    assert mod.run_one(argv, "{}", clean_env(), tmp_path, timeout=1) == ""
    assert "[agent-kit]" in capsys.readouterr().err


def test_stop_expands_project_dir_and_adds_no_extras(tmp_path, project):
    result = run(make_kit(tmp_path), "codex", project, event="Stop")
    text = context(result, "codex", event="Stop")
    assert f"stop {project.resolve().as_posix()}/docs" in text
    assert "agent-kit agent tools" not in text


def test_mapping_injected_with_plugin_path(tmp_path, project):
    plugin = make_kit(tmp_path)
    text = context(run(plugin, "cursor", project), "cursor")
    assert text.startswith("# agent-kit agent tools")
    assert plugin.resolve().as_posix() in text
    assert "<plugin>" not in text
    assert "~/.claude/skills/agent-kit" in text
    assert "`code-review`" in text and "requesting-code-review" in text


def test_project_claude_md_injected_when_no_agents_md(tmp_path, project):
    (project / "CLAUDE.md").write_text(
        "proj rules\n@extra.md\n@missing.md\n", encoding="utf-8"
    )
    (project / "extra.md").write_text("extra text\n", encoding="utf-8")
    text = context(run(make_kit(tmp_path), "vibe", project), "vibe")
    assert "proj rules" in text and "extra text" in text
    assert "@missing.md" in text
    order = [text.index(s) for s in ("agent tools", "proj rules", "json src")]
    assert order == sorted(order)


def test_project_with_agents_md_not_injected(tmp_path, project):
    (project / "CLAUDE.md").write_text("proj rules\n", encoding="utf-8")
    (project / "AGENTS.md").write_text("agents rules\n", encoding="utf-8")
    text = context(run(make_kit(tmp_path), "vibe", project), "vibe")
    assert "proj rules" not in text and "agents rules" not in text


def test_unreadable_project_claude_md_keeps_the_rest(tmp_path, project):
    (project / "CLAUDE.md").write_bytes("caf\xe9 rules\n".encode("latin-1"))
    result = run(make_kit(tmp_path), "vibe", project)
    text = context(result, "vibe")
    assert "agent tools" in text and "json src" in text
    assert "caf" not in text
    assert "project_instructions skipped" in result.stderr


def test_bad_arguments_exit_0(tmp_path, project):
    result = run(make_kit(tmp_path), "bogus", project)
    assert result.returncode == 0
    assert result.stdout == ""
    assert "[agent-kit]" in result.stderr


@pytest.mark.parametrize("stdin", ["", "not json"])
def test_empty_or_bad_stdin(tmp_path, project, stdin):
    result = run(make_kit(tmp_path), "vibe", project, stdin=stdin)
    assert "plain cwd=proj" in context(result, "vibe")


def test_project_dir_is_git_top_level(tmp_path, project):
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    sub = project / "sub"
    sub.mkdir()
    stdin = json.dumps({"cwd": str(sub)})
    result = run(make_kit(tmp_path), "vibe", sub, event="Stop", stdin=stdin)
    text = context(result, "vibe", event="Stop")
    assert f"stop {project.resolve().as_posix()}/docs" in text


def test_nothing_collected_prints_nothing(tmp_path, project):
    plugin = make_kit(tmp_path)
    (plugin / "hooks" / "argv.py").write_text("pass\n", encoding="utf-8")
    result = run(plugin, "vibe", project, event="Stop")
    assert result.returncode == 0 and result.stdout == ""


def test_claude_only_set():
    mod = load_module(RUN, "kit_run_hooks")
    assert mod.CLAUDE_ONLY == {
        "context_nudge.py",
        "handoff_snapshot.py",
        "precompact_keep.py",
        "on_spec_edit.py",
    }


def test_real_hooks_json_commands(tmp_path):
    mod = load_module(RUN, "kit_run_hooks")
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text("utf-8"))
    session = mod.commands(hooks, "SessionStart", "startup", PLUGIN, tmp_path)
    assert len(session) == 6
    for argv in session:
        assert argv[0] == sys.executable
        assert (PLUGIN / "hooks").as_posix() in argv[1]
    (stop,) = mod.commands(hooks, "Stop", "startup", PLUGIN, tmp_path)
    assert stop == [sys.executable, f"{PLUGIN.as_posix()}/scripts/spec-index.py"]


def test_stop_hook_writes_index_in_project_folder(tmp_path, project):
    plugin = make_kit(tmp_path)
    (plugin / "scripts").mkdir()
    shutil.copy(PLUGIN / "scripts" / "spec-index.py", plugin / "scripts")
    command = 'python "${CLAUDE_PLUGIN_ROOT}/scripts/spec-index.py"'
    stop = [{"hooks": [{"type": "command", "command": command}]}]
    hooks = {"hooks": {"Stop": stop}}
    (plugin / "hooks" / "hooks.json").write_text(json.dumps(hooks), "utf-8")
    subprocess.run(["git", "init", "-q", str(project)], check=True)
    specs = project / "docs" / "superpowers" / "specs"
    specs.mkdir(parents=True)
    (specs / "2026-01-01-a.md").write_text("# A\n", encoding="utf-8")
    sub = project / "sub"
    sub.mkdir()
    stdin = json.dumps({"cwd": str(sub)})
    result = run(plugin, "codex", sub, event="Stop", stdin=stdin)
    assert result.returncode == 0, result.stderr
    assert (project / "docs" / "superpowers" / "README.md").exists()
    assert not (sub / "docs").exists()
