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
