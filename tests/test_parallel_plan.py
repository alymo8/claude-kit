"""Tests for plugin/scripts/parallel-plan.py."""

from __future__ import annotations

import json

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "parallel-plan.py"
pp = load_module(SCRIPT, "parallel_plan")


def plan(*tasks):
    """A plan whose task i has Modify bullets ``files`` and an optional Depends."""
    parts = ["# P\n\n**Goal:** g.\n\n**Spec:** `docs/x.md`\n"]
    for number, (files, depends) in enumerate(tasks, 1):
        parts.append(f"\n### Task {number}: T{number}\n\n**Files:**\n")
        parts += [f"- Modify: `{name}`\n" for name in files]
        if depends is not None:
            parts.append(f"\n**Depends on:** {depends}\n")
        parts.append("\n- [ ] **Step 1: Commit**\n")
    return "".join(parts)


def waves(text, max_size=3):
    found, problems = pp.plan_waves(text, max_size)
    assert problems == []
    return found


def test_no_depends_lines_runs_one_task_per_wave():
    text = plan((["a.py"], None), (["b.py"], None), (["c.py"], None))
    assert waves(text) == [[1], [2], [3]]


def test_independent_tasks_fill_waves_up_to_max():
    text = plan(*[([f"{n}.py"], "none") for n in "abcd"])
    assert waves(text) == [[1, 2, 3], [4]]
    assert waves(text, 2) == [[1, 2], [3, 4]]


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("a.py", "a.py"),
        ("src/", "src/x.py"),
        ("CLAUDE.md", "CLAUDE.md"),
        ("a.py:1-5", "a.py"),
    ],
)
def test_overlapping_paths_keep_plan_order(first, second):
    text = plan(([first], "none"), ([second], "none"))
    assert waves(text) == [[1], [2]]


def test_declared_dependency_forces_a_later_wave():
    text = plan((["a.py"], "none"), (["b.py"], "none"), (["c.py"], "Task 1"))
    assert waves(text) == [[1, 2], [3]]


@pytest.mark.parametrize(
    ("span", "path"),
    [
        ("CLAUDE.md", "CLAUDE.md"),
        (".gitignore", ".gitignore"),
        ("smoke/", "smoke/"),
        ("plugin/a.py:12-20", "plugin/a.py"),
        ("0001", None),
        ("0.8.0", None),
        ("origin/main", None),
        ("docs/<slug>.md", None),
        ("a b.py", None),
    ],
)
def test_as_path(span, path):
    assert pp.as_path(span) == path


def test_plan_with_no_tasks_has_no_waves(tmp_path):
    assert pp.plan_waves("# P\n\nNothing yet.\n", 3) == ([], [])
    path = tmp_path / "plan.md"
    path.write_text("# P\n\nNothing yet.\n", encoding="utf-8")
    result = run_script(SCRIPT, "waves", str(path))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"waves": []}


def test_crlf_plan_gives_the_same_waves():
    text = plan((["a.py"], "none"), (["b.py"], "none"))
    assert waves(text.replace("\n", "\r\n")) == waves(text)


def test_depends_line_in_a_fence_is_ignored():
    text = plan((["a.py"], "none"), (["b.py"], "none"))
    text += "\n```text\n**Depends on:** Task 9\n```\n"
    assert waves(text) == [[1, 2]]


@pytest.mark.parametrize("value", ["Task 2", "Task 9", "Task 1, Task 1"])
def test_invalid_depends_is_reported(value, tmp_path):
    text = plan((["a.py"], "none"), (["b.py"], value))
    if value == "Task 2":
        text = plan((["a.py"], value), (["b.py"], "none"))
    found, problems = pp.plan_waves(text, 3)
    assert found == [] and len(problems) == 1
    path = tmp_path / "plan.md"
    path.write_text(text, encoding="utf-8")
    assert run_script(SCRIPT, "waves", str(path)).returncode == 1


def test_cli_prints_json(tmp_path):
    path = tmp_path / "plan.md"
    path.write_text(plan((["a.py"], "none"), (["b.py"], "none")), encoding="utf-8")
    result = run_script(SCRIPT, "waves", str(path))
    assert result.returncode == 0
    assert json.loads(result.stdout) == {"waves": [[1, 2]]}


def test_cli_invalid_plan_exits_one(tmp_path):
    path = tmp_path / "plan.md"
    text = plan((["a.py"], "none"), (["b.py"], "none")).replace(
        "**Depends on:** none\n", "**Depends on:** none\n**Depends on:** none\n", 1
    )
    path.write_text(text, encoding="utf-8")
    result = run_script(SCRIPT, "waves", str(path))
    assert result.returncode == 1
    assert "Depends" in result.stderr


def test_cli_bad_max_and_missing_file_exit_two(tmp_path):
    path = tmp_path / "plan.md"
    path.write_text(plan((["a.py"], "none")), encoding="utf-8")
    assert run_script(SCRIPT, "waves", str(path), "--max", "0").returncode == 2
    assert run_script(SCRIPT, "waves", str(tmp_path / "no.md")).returncode == 2


def test_pytest_node_id_is_its_file():
    assert pp.as_path("tests/x.py::test_a") == "tests/x.py"


def test_wrapped_files_bullet_is_read():
    text = plan((["a.py"], "none"), (["c.py"], "none")).replace(
        "- Modify: `a.py`\n", "- Modify: `a.py` and\n  `c.py`\n", 1
    )
    assert waves(text) == [[1], [2]]


def spec(*paths, out=()):
    """A spec whose Scope In names ``paths`` and whose Out names ``out``."""
    text = "# S\n\n- **Status:** draft\n\n## Scope\n\n**In:**\n\n"
    text += "".join(f"- `{p}`: x.\n" for p in paths)
    text += "\n**Out:**\n\n" + "".join(f"- `{p}`: later.\n" for p in out)
    return text


def grouped(*texts, max_size=3):
    named = [(name, text) for name, text in zip("abcdef", texts, strict=False)]
    return pp.plan_specs(named, max_size)


def test_disjoint_specs_share_a_wave():
    assert grouped(spec("x/a.py"), spec("x/b.py")) == ([["a", "b"]], [])


def test_shared_scope_path_splits_and_is_listed():
    waves, found = grouped(spec("x/a.py"), spec("x/a.py"))
    assert waves == [["a"], ["b"]]
    assert found == [["a", "b", ["x/a.py"]]]


def test_shared_root_file_splits():
    assert grouped(spec("CLAUDE.md"), spec("CLAUDE.md"))[0] == [["a"], ["b"]]


def test_spec_index_alone_never_splits():
    index = "docs/superpowers/README.md"
    assert grouped(spec(index), spec(index)) == ([["a", "b"]], [])


def test_same_numbered_adr_files_split():
    first = spec("knowledge/decisions/0019-one.md")
    second = spec("knowledge/decisions/0019-two.md")
    assert grouped(first, second)[0] == [["a"], ["b"]]


def test_paths_after_out_are_ignored():
    assert grouped(spec("x/a.py"), spec("x/b.py", out=["x/a.py"]))[0] == [["a", "b"]]


def test_max_caps_a_wave():
    texts = [spec(f"x/{n}.py") for n in "abcd"]
    assert grouped(*texts)[0] == [["a", "b", "c"], ["d"]]


def test_spec_without_scope_overlaps_nothing():
    assert grouped("# S\n\nNo scope.\n", spec("x/a.py"))[0] == [["a", "b"]]


def test_overlaps_are_ordered_and_sorted():
    texts = (spec("x/b.py", "x/a.py"), spec("x/a.py", "x/b.py"), spec("x/a.py"))
    waves, found = grouped(*texts)
    assert waves == [["a"], ["b"], ["c"]]
    assert found == [
        ["a", "b", ["x/a.py", "x/b.py"]],
        ["a", "c", ["x/a.py"]],
        ["b", "c", ["x/a.py"]],
    ]


def test_cli_specs_prints_json_with_names_as_given(tmp_path):
    first, second = tmp_path / "one.md", tmp_path / "two.md"
    first.write_text(spec("x/a.py"), encoding="utf-8")
    second.write_text(spec("x/a.py"), encoding="utf-8")
    result = run_script(SCRIPT, "specs", str(first), str(second))
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "waves": [[str(first)], [str(second)]],
        "overlaps": [[str(first), str(second), ["x/a.py"]]],
    }


def test_cli_specs_bad_input_exits_two(tmp_path):
    path = tmp_path / "one.md"
    path.write_text(spec("x/a.py"), encoding="utf-8")
    assert run_script(SCRIPT, "specs", str(path), "--max", "0").returncode == 2
    missing = run_script(SCRIPT, "specs", str(tmp_path / "no.md"))
    assert missing.returncode == 2
    assert "cannot read" in missing.stderr


def test_leading_dot_slash_is_normalised():
    assert grouped(spec("./CLAUDE.md"), spec("CLAUDE.md"))[0] == [["a"], ["b"]]


def test_cli_warns_on_a_spec_without_paths(tmp_path):
    empty, full = tmp_path / "empty.md", tmp_path / "full.md"
    empty.write_text("# E\n\nNo scope.\n", encoding="utf-8")
    full.write_text(spec("x/a.py"), encoding="utf-8")
    result = run_script(SCRIPT, "specs", str(empty), str(full))
    assert result.returncode == 0
    assert "no Scope paths" in result.stderr and str(empty) in result.stderr
