import json
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "on_spec_edit.py"


def event(path: str) -> str:
    return json.dumps({"tool_name": "Write", "tool_input": {"file_path": path}})


def test_spec_path_is_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    p = "C:/repo/docs/superpowers/specs/2026-01-01-x-design.md"
    assert mod.target_from_event(event(p)) == Path(p)


def test_plan_path_with_backslashes_is_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    p = r"C:\repo\docs\superpowers\plans\2026-01-01-x.md"
    assert mod.target_from_event(event(p)) == Path(p)


def test_unrelated_path_is_not_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    assert mod.target_from_event(event("C:/repo/src/app.py")) is None
    assert mod.target_from_event(event("C:/repo/docs/superpowers/specs/x.html")) is None
    assert (
        mod.target_from_event(event("C:/repo/notdocs/superpowers/specs/x.md")) is None
    )


def test_malformed_event_is_not_a_target():
    mod = load_module(HOOK, "on_spec_edit")
    assert mod.target_from_event("") is None
    assert mod.target_from_event("{not json") is None
    assert mod.target_from_event(json.dumps({"tool_input": {}})) is None


def test_hook_indexes_but_does_not_render_html(tmp_path):
    spec_dir = tmp_path / "docs" / "superpowers" / "specs"
    spec_dir.mkdir(parents=True)
    md = spec_dir / "2026-01-01-thing-design.md"
    md.write_text("# Thing\n", encoding="utf-8")
    result = run_script(HOOK, stdin=event(str(md)), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "docs" / "superpowers" / "README.md").exists()
    assert not (spec_dir / "2026-01-01-thing-design.html").exists()


def test_hook_ignores_unrelated_file(tmp_path):
    other = tmp_path / "notes.md"
    other.write_text("# n\n", encoding="utf-8")
    result = run_script(HOOK, stdin=event(str(other)), cwd=tmp_path)
    assert result.returncode == 0
    assert not (tmp_path / "notes.html").exists()


def test_hook_survives_garbage_stdin(tmp_path):
    result = run_script(HOOK, stdin="{{{", cwd=tmp_path)
    assert result.returncode == 0
    assert list(tmp_path.iterdir()) == []


def test_hook_regenerates_index_after_render(tmp_path):
    spec_dir = tmp_path / "docs" / "superpowers" / "specs"
    spec_dir.mkdir(parents=True)
    md = spec_dir / "2026-01-01-thing-design.md"
    md.write_text("# Thing\n\n- **Status:** draft\n", encoding="utf-8")
    result = run_script(HOOK, stdin=event(str(md)), cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    index = (tmp_path / "docs" / "superpowers" / "README.md").read_text("utf-8")
    assert "[Thing](specs/2026-01-01-thing-design.md) | draft |" in index
