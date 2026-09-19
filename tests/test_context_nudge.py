import json
import os
import subprocess
import sys
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

HOOK = PLUGIN / "hooks" / "context_nudge.py"


def transcript_with(path: Path, tokens: int, padding_bytes: int = 0) -> Path:
    usage = {
        "input_tokens": 100,
        "cache_creation_input_tokens": 900,
        "cache_read_input_tokens": tokens - 1000,
    }
    lines = []
    if padding_bytes:
        filler = json.dumps({"type": "user", "message": {"content": "x" * 1000}})
        lines += [filler] * (padding_bytes // (len(filler) + 1))
    lines.append(json.dumps({"type": "assistant", "message": {"usage": usage}}))
    lines.append(json.dumps({"type": "user", "message": {"content": "next"}}))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return path


def run(tmp_path: Path, tokens: int, env: dict | None = None, padding: int = 0):
    transcript = transcript_with(tmp_path / "t.jsonl", tokens, padding)
    event = json.dumps(
        {
            "hook_event_name": "UserPromptSubmit",
            "session_id": "s1",
            "cwd": str(tmp_path),
            "scratchpad_dir": str(tmp_path / "scratch"),
            "transcript_path": str(transcript),
        }
    )
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=event,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, **(env or {})},
        timeout=60,
    )


def test_next_level_math():
    mod = load_module(HOOK, "nudge")
    assert mod.next_level(100_000, 0, 300_000, 100_000) is None
    assert mod.next_level(310_000, 0, 300_000, 100_000) == 300_000
    assert mod.next_level(350_000, 300_000, 300_000, 100_000) is None
    assert mod.next_level(420_000, 300_000, 300_000, 100_000) == 400_000
    assert mod.next_level(650_000, 300_000, 300_000, 100_000) == 600_000


def test_fires_once_per_threshold(tmp_path):
    assert run(tmp_path, 100_000).stdout == ""
    first = run(tmp_path, 310_000)
    out = json.loads(first.stdout)
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "310k tokens" in out["hookSpecificOutput"]["additionalContext"]
    assert "/handoff" in out["systemMessage"]
    assert run(tmp_path, 350_000).stdout == ""
    again = json.loads(run(tmp_path, 420_000).stdout)
    assert "420k tokens" in again["hookSpecificOutput"]["additionalContext"]


def test_env_vars_change_thresholds(tmp_path):
    env = {"CLAUDE_KIT_NUDGE_AT": "20000", "CLAUDE_KIT_NUDGE_STEP": "5000"}
    assert run(tmp_path, 19_000, env).stdout == ""
    assert "21k tokens" in run(tmp_path, 21_000, env).stdout
    assert run(tmp_path, 24_000, env).stdout == ""
    assert "26k tokens" in run(tmp_path, 26_000, env).stdout


def test_reads_only_the_tail_of_a_large_transcript(tmp_path):
    result = run(tmp_path, 310_000, padding=5 * 1024 * 1024)
    assert result.returncode == 0, result.stderr
    assert "310k tokens" in result.stdout


def test_rearms_after_context_drops_below_first_threshold(tmp_path):
    assert "310k tokens" in run(tmp_path, 310_000).stdout
    assert run(tmp_path, 50_000).stdout == ""
    assert "310k tokens" in run(tmp_path, 310_000).stdout


def test_missing_transcript_or_bad_stdin_is_silent(tmp_path):
    event = json.dumps({"transcript_path": str(tmp_path / "none.jsonl")})
    assert run_script(HOOK, stdin=event).returncode == 0
    assert run_script(HOOK, stdin=event).stdout == ""
    assert run_script(HOOK, stdin="{bad").returncode == 0
