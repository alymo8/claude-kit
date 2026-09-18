import json
import subprocess
from pathlib import Path

import pytest
from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "handoff_snapshot.py"
HELPER = PLUGIN / "hooks" / "_transcript.py"


def git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    git("add", "a.txt", cwd=root)
    git("commit", "-q", "-m", "init", cwd=root)
    return root


def record(kind: str, **extra) -> str:
    return json.dumps({"type": kind, **extra})


def user(text: str, **extra) -> str:
    return record("user", message={"role": "user", "content": text}, **extra)


def tool_result() -> str:
    content = [{"type": "tool_result", "tool_use_id": "x", "content": "..."}]
    return record("user", message={"role": "user", "content": content})


@pytest.fixture
def transcript(tmp_path: Path) -> Path:
    lines = [
        user("<command-name>/clear</command-name>"),
        user("meta line", isMeta=True),
        user("first real prompt\nsecond line ignored"),
        tool_result(),
        user("x" * 200),
        user("last prompt"),
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def test_recent_prompts_filters_and_truncates(transcript):
    helper = load_module(HELPER, "_transcript")
    prompts = helper.recent_prompts(transcript.read_text(encoding="utf-8"))
    assert prompts == ["first real prompt", "x" * 120, "last prompt"]


def test_recent_prompts_limit(transcript):
    helper = load_module(HELPER, "_transcript")
    text = transcript.read_text(encoding="utf-8")
    assert helper.recent_prompts(text, limit=1) == ["last prompt"]


def test_read_tail_returns_whole_small_file_and_only_tail_of_big(tmp_path):
    helper = load_module(HELPER, "_transcript")
    small = tmp_path / "s.txt"
    small.write_text("a\nb\n", encoding="utf-8", newline="\n")
    assert helper.read_tail(small) == "a\nb\n"
    big = tmp_path / "b.txt"
    big.write_bytes(b"0123456789\n" * 100_000 + b"tail-line\n")
    tail = helper.read_tail(big, size=1024)
    assert tail.endswith("tail-line\n")
    assert len(tail.encode()) <= 1024
    assert tail.startswith("0123456789\n")  # starts at a line boundary


def test_read_tail_missing_file_is_empty(tmp_path):
    helper = load_module(HELPER, "_transcript")
    assert helper.read_tail(tmp_path / "nope.jsonl") == ""


def test_hook_writes_handoff_with_recent_prompts(repo, transcript):
    event = json.dumps(
        {
            "hook_event_name": "SessionEnd",
            "reason": "clear",
            "cwd": str(repo),
            "transcript_path": str(transcript),
        }
    )
    result = run_script(HOOK, stdin=event, cwd=repo)
    assert result.returncode == 0, result.stderr
    text = (repo / ".claude" / "handoffs" / "main.md").read_text(encoding="utf-8")
    assert "## State" in text
    assert "- last prompt" in text
    assert "meta line" not in text


def test_hook_is_silent_outside_git(tmp_path, transcript):
    plain = tmp_path / "plain"
    plain.mkdir()
    event = json.dumps({"cwd": str(plain), "transcript_path": str(transcript)})
    result = run_script(HOOK, stdin=event, cwd=plain)
    assert result.returncode == 0
    assert not (plain / ".claude").exists()


def test_hook_survives_malformed_stdin(repo):
    result = run_script(HOOK, stdin="{not json", cwd=repo)
    assert result.returncode == 0
    assert not (repo / ".claude").exists()


def test_hook_survives_missing_transcript(repo):
    event = json.dumps({"cwd": str(repo), "transcript_path": str(repo / "none")})
    result = run_script(HOOK, stdin=event, cwd=repo)
    assert result.returncode == 0
    assert (repo / ".claude" / "handoffs" / "main.md").exists()
