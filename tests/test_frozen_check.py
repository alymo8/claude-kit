import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "frozen-check.py"
fc = load_module(SCRIPT, "frozen_check")


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    ).stdout


def commit(root: Path, msg: str, files: dict[str, str | None]) -> None:
    """Write (str) or delete (None) each file, then commit everything."""
    for rel, content in files.items():
        path = root / rel
        if content is None:
            path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    git("add", "-A", cwd=root)
    git("commit", "-q", "--allow-empty", "-m", msg, cwd=root)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """`main` holds tests/a.py and src/x.py; HEAD is branch `feat` at main."""
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    commit(root, "base", {"tests/a.py": "a\n", "src/x.py": "x\n"})
    git("checkout", "-q", "-b", "feat", cwd=root)
    return root


def spec(tmp_path: Path, bullet: str, name: str = "spec.md") -> Path:
    path = tmp_path / name
    path.write_text(f"# S\n\n- **Status:** approved\n{bullet}\n", encoding="utf-8")
    return path


def check(repo: Path, *specs: Path, base: str = "main"):
    args = [str(s) for s in specs]
    return run_script(SCRIPT, *args, "--base", base, "--root", str(repo))


def approve(repo: Path, path: str) -> None:
    git(
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "approve",
        "-m",
        f"Frozen-change-approved: {path}",
        cwd=repo,
    )


def test_no_bullet_is_none_declared(repo, tmp_path):
    r = check(repo, spec(tmp_path, "- **Date:** 2026-11-10"))
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "frozen: none declared"


def test_untouched_base_file_is_ok(repo, tmp_path):
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/a.py`"))
    assert r.returncode == 0, r.stderr
    assert "frozen: ok (1 files)" in r.stdout


def test_modified_base_file_is_a_violation(repo, tmp_path):
    commit(repo, "edit", {"tests/a.py": "b\n"})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/a.py`"))
    assert r.returncode == 1, r.stderr
    assert "frozen: changed tests/a.py since " in r.stdout


def test_deleted_base_file_is_a_violation(repo, tmp_path):
    commit(repo, "delete", {"tests/a.py": None})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/a.py`"))
    assert r.returncode == 1, r.stderr


def test_created_file_never_edited_is_ok(repo, tmp_path):
    commit(repo, "create", {"tests/new.py": "n\n"})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/new.py`"))
    assert r.returncode == 0, r.stderr
    assert "ok (1 files)" in r.stdout


def test_created_file_edited_later_is_a_violation(repo, tmp_path):
    commit(repo, "create", {"tests/new.py": "n\n"})
    commit(repo, "edit", {"tests/new.py": "m\n"})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/new.py`"))
    assert r.returncode == 1, r.stderr


def test_created_file_deleted_later_is_a_violation(repo, tmp_path):
    commit(repo, "create", {"tests/new.py": "n\n"})
    commit(repo, "delete", {"tests/new.py": None})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/new.py`"))
    assert r.returncode == 1, r.stderr


def test_approval_trailer_moves_the_snapshot(repo, tmp_path):
    s = spec(tmp_path, "- **Frozen:** `tests/a.py`")
    commit(repo, "edit", {"tests/a.py": "b\n"})
    approve(repo, "tests/a.py")
    r = check(repo, s)
    assert r.returncode == 0, r.stdout + r.stderr
    commit(repo, "edit again", {"tests/a.py": "c\n"})
    r = check(repo, s)
    assert r.returncode == 1, r.stderr


def test_last_trailer_wins(repo, tmp_path):
    s = spec(tmp_path, "- **Frozen:** `tests/a.py`")
    commit(repo, "edit", {"tests/a.py": "b\n"})
    approve(repo, "tests/a.py")
    commit(repo, "edit again", {"tests/a.py": "c\n"})
    approve(repo, "tests/a.py")
    r = check(repo, s)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "frozen: ok" in r.stdout


def test_glob_matches_nested_files(repo, tmp_path):
    s = spec(tmp_path, "- **Frozen:** `tests/acceptance/**`")
    commit(repo, "create", {"tests/acceptance/x/y.txt": "y\n"})
    r = check(repo, s)
    assert r.returncode == 0, r.stderr
    assert "ok (1 files)" in r.stdout
    commit(repo, "edit", {"tests/acceptance/x/y.txt": "z\n"})
    r = check(repo, s)
    assert r.returncode == 1, r.stderr
    assert "tests/acceptance/x/y.txt" in r.stdout


@pytest.mark.parametrize("pattern", ["tests/acceptance", "tests/acceptance/"])
def test_directory_pattern_freezes_its_files(repo, tmp_path, pattern):
    s = spec(tmp_path, f"- **Frozen:** `{pattern}`")
    commit(repo, "create", {"tests/acceptance/x/y.txt": "y\n"})
    r = check(repo, s)
    assert r.returncode == 0, r.stderr
    assert "ok (1 files)" in r.stdout
    commit(repo, "edit", {"tests/acceptance/x/y.txt": "z\n"})
    r = check(repo, s)
    assert r.returncode == 1, r.stderr
    assert "tests/acceptance/x/y.txt" in r.stdout


def test_approval_trailer_moves_the_snapshot_of_a_created_file(repo, tmp_path):
    s = spec(tmp_path, "- **Frozen:** `tests/new.py`")
    commit(repo, "create", {"tests/new.py": "n\n"})
    commit(repo, "edit", {"tests/new.py": "m\n"})
    approve(repo, "tests/new.py")
    r = check(repo, s)
    assert r.returncode == 0, r.stdout + r.stderr
    commit(repo, "edit again", {"tests/new.py": "o\n"})
    r = check(repo, s)
    assert r.returncode == 1, r.stderr


def test_bullet_after_first_section_is_ignored(repo, tmp_path):
    commit(repo, "edit", {"tests/a.py": "b\n"})
    path = tmp_path / "plan.md"
    path.write_text(
        "# P\n\n- **Status:** approved\n\n## Task 1\n\n- **Frozen:** `tests/a.py`\n",
        encoding="utf-8",
    )
    r = check(repo, path)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "frozen: none declared"


def test_unmatched_pattern_warns_and_passes(repo, tmp_path):
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/nothing/*.py`"))
    assert r.returncode == 0, r.stderr
    assert "frozen: warning: no file matches tests/nothing/*.py" in r.stdout
    assert "ok (0 files)" in r.stdout


def test_single_star_stays_in_one_segment(repo, tmp_path):
    s = spec(tmp_path, "- **Frozen:** `tests/*.py`")
    commit(repo, "create", {"tests/sub/b.py": "b\n"})
    commit(repo, "edit", {"tests/sub/b.py": "c\n"})
    r = check(repo, s)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ok (1 files)" in r.stdout


def test_double_star_slash_matches_zero_dirs(repo, tmp_path):
    commit(repo, "edit", {"tests/a.py": "b\n"})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/**/a.py`"))
    assert r.returncode == 1, r.stderr


def test_bullets_in_two_files_are_united(repo, tmp_path):
    s = spec(tmp_path, "- **Frozen:** `tests/a.py`")
    p = spec(tmp_path, "- **Frozen:** `src/x.py`", name="plan.md")
    r = check(repo, s, p)
    assert r.returncode == 0, r.stderr
    assert "ok (2 files)" in r.stdout
    commit(repo, "edit", {"src/x.py": "y\n"})
    r = check(repo, s, p)
    assert r.returncode == 1, r.stderr
    assert "src/x.py" in r.stdout


def test_bullet_in_code_fence_is_ignored(repo, tmp_path):
    bullet = "```\n- **Frozen:** `tests/a.py`\n```"
    r = check(repo, spec(tmp_path, bullet))
    assert r.returncode == 0, r.stderr
    assert "none declared" in r.stdout


def test_missing_input_file_exits_2(repo, tmp_path):
    r = check(repo, tmp_path / "nope.md")
    assert r.returncode == 2
    assert "cannot read" in r.stderr


def test_unknown_base_exits_2(repo, tmp_path):
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/a.py`"), base="nosuch")
    assert r.returncode == 2
    assert r.stderr != ""


def test_renamed_then_edited_created_file_is_a_violation(repo, tmp_path):
    git("mv", "src/x.py", "tests/frozen.py", cwd=repo)
    git("commit", "-q", "-m", "rename", cwd=repo)
    commit(repo, "edit", {"tests/frozen.py": "y\n"})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/frozen.py`"))
    assert r.returncode == 1, r.stdout + r.stderr


def test_non_ascii_path_is_reported_as_is(repo, tmp_path):
    commit(repo, "create", {"tests/é.txt": "e\n"})
    commit(repo, "edit", {"tests/é.txt": "f\n"})
    r = check(repo, spec(tmp_path, "- **Frozen:** `tests/é.txt`"))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "tests/é.txt" in r.stdout


def test_root_may_be_a_subdirectory(repo, tmp_path):
    commit(repo, "edit", {"tests/a.py": "b\n"})
    s = spec(tmp_path, "- **Frozen:** `tests/a.py`")
    r = run_script(SCRIPT, str(s), "--base", "main", "--root", str(repo / "src"))
    assert r.returncode == 1, r.stdout + r.stderr


def test_wrapped_bullet_continuation_counts(repo, tmp_path):
    commit(repo, "edit", {"tests/a.py": "b\n"})
    s = spec(tmp_path, "- **Frozen:** `src/x.py`,\n  `tests/a.py`")
    r = check(repo, s)
    assert r.returncode == 1, r.stdout + r.stderr


def test_parse_patterns_unit():
    text = "- **Frozen:** `./a/b.py`, `c/**`\n"
    assert fc.parse_patterns(text) == ["a/b.py", "c/**"]


def test_pattern_regex_unit():
    assert fc.pattern_regex("a/*.py").fullmatch("a/b/c.py") is None
    assert fc.pattern_regex("a/**/c.py").fullmatch("a/c.py")
    assert fc.pattern_regex("a/**").fullmatch("a/b/c")
    assert fc.pattern_regex("a/?.py").fullmatch("a/bc.py") is None
