import json
import re

from helpers import PLUGIN, load_module, run_script

SCRIPT = PLUGIN / "scripts" / "statusline.py"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

SAMPLE = {
    "model": {"id": "claude-opus-5", "display_name": "Opus"},
    "workspace": {"current_dir": "C:/anywhere"},
    "cost": {"total_cost_usd": 14.2},
    "context_window": {
        "total_input_tokens": 312_000,
        "context_window_size": 1_000_000,
        "used_percentage": 31.2,
    },
}


def plain(text: str) -> str:
    return ANSI.sub("", text)


def test_renders_documented_fields():
    mod = load_module(SCRIPT, "statusline")
    assert plain(mod.render(SAMPLE, "feature/foo")) == (
        "ctx 312k/1M 31% | $14.20 | feature/foo"
    )


def test_small_window_and_missing_branch():
    mod = load_module(SCRIPT, "statusline")
    data = {**SAMPLE, "context_window": {**SAMPLE["context_window"]}}
    data["context_window"]["context_window_size"] = 200_000
    assert plain(mod.render(data, "")) == "ctx 312k/200k 31% | $14.20"


def test_nulls_before_first_call():
    mod = load_module(SCRIPT, "statusline")
    data = {"context_window": {"total_input_tokens": 0, "used_percentage": None}}
    assert plain(mod.render(data, "main")) == "ctx - | $0.00 | main"


def test_color_by_percentage():
    mod = load_module(SCRIPT, "statusline")
    low = {"context_window": {"total_input_tokens": 10_000, "used_percentage": 10}}
    mid = {"context_window": {"total_input_tokens": 10_000, "used_percentage": 45}}
    high = {"context_window": {"total_input_tokens": 10_000, "used_percentage": 75}}
    assert "\x1b[" not in mod.render(low, "")
    assert "\x1b[33m" in mod.render(mid, "")
    assert "\x1b[31m" in mod.render(high, "")


def test_output_is_ascii():
    mod = load_module(SCRIPT, "statusline")
    mod.render(SAMPLE, "main").encode("ascii")


def test_cli_reads_stdin_and_survives_garbage():
    result = run_script(SCRIPT, stdin=json.dumps(SAMPLE))
    assert result.returncode == 0, result.stderr
    assert plain(result.stdout).startswith("ctx 312k/1M 31% | $14.20")
    bad = run_script(SCRIPT, stdin="not json")
    assert bad.returncode == 0
    assert bad.stdout == "\n"
