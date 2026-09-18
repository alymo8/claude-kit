import json
from pathlib import Path

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "token-report.py"


def assistant(ctx: int, tool: dict | None = None) -> str:
    content = [tool] if tool else []
    usage = {
        "input_tokens": 10,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": ctx - 10,
    }
    msg = {"type": "assistant", "message": {"usage": usage, "content": content}}
    return json.dumps(msg)


def result(tool_use_id: str, text: str) -> str:
    block = {"type": "tool_result", "tool_use_id": tool_use_id, "content": text}
    return json.dumps({"type": "user", "message": {"content": [block]}})


def make_project(root: Path) -> Path:
    folder = root / "C--proj"
    folder.mkdir(parents=True)
    bash = {
        "type": "tool_use",
        "id": "t1",
        "name": "Bash",
        "input": {"command": "cat x"},
    }
    read = {"type": "tool_use", "id": "t2", "name": "Read", "input": {"file_path": "f"}}
    s1 = [
        assistant(50_000, bash),
        result("t1", "a" * 20_000),
        assistant(80_000, read),
        result("t2", "b" * 100),
        assistant(120_000),
    ]
    s2 = [assistant(10_000), assistant(400_000)]
    s1_text = "\n".join(s1) + "\n"
    s2_text = "\n".join(s2) + "\n"
    (folder / "s1.jsonl").write_text(s1_text, encoding="utf-8", newline="\n")
    (folder / "s2.jsonl").write_text(s2_text, encoding="utf-8", newline="\n")
    return folder


def test_encode_project_matches_claude_code_scheme():
    mod = load_module(SCRIPT, "token_report")
    assert mod.encode_project(Path("C:/Users/x/Desktop/Github")) == (
        "C--Users-x-Desktop-Github"
    )


def test_scan_counts_turns_tokens_and_tool_output(tmp_path):
    mod = load_module(SCRIPT, "token_report")
    folder = make_project(tmp_path)
    report = mod.scan(sorted(folder.glob("*.jsonl")))
    assert report.sessions == 2
    assert report.turns == 5
    assert report.input_tokens == 50_000 + 80_000 + 120_000 + 10_000 + 400_000
    assert report.tool_chars["Bash"] == 20_000
    assert report.tool_chars["Read"] == 100
    assert report.families["cat"] == 20_000
    assert [b[0] for b in report.big_results] == [20_000]


def test_simulate_restarts_at_cap():
    mod = load_module(SCRIPT, "token_report")
    contexts = [[100, 200, 300]]
    assert mod.simulate(contexts, cap=1_000, restart=45) == 600
    # cap 250: turn 3 (300) restarts -> counted as 45, later turns offset by 255
    expected = 100 + 200 + 45 + 65
    assert mod.simulate([[100, 200, 300, 320]], cap=250, restart=45) == expected


def test_cli_prints_report_and_simulation(tmp_path):
    make_project(tmp_path)
    out = run_script(SCRIPT, "--all", "--root", str(tmp_path), "--cap", "100000")
    assert out.returncode == 0, out.stderr
    assert "sessions: 2" in out.stdout
    assert "avg context per call" in out.stdout
    assert "cap 100,000" in out.stdout
    assert "Bash" in out.stdout and "cat" in out.stdout


def test_cli_empty_root_is_graceful(tmp_path):
    out = run_script(SCRIPT, "--all", "--root", str(tmp_path / "missing"))
    assert out.returncode == 0
    assert "no transcripts found" in out.stdout
