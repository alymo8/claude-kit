import csv
import json
import sys

import pytest
from helpers import PLUGIN, load_module

ev = load_module(PLUGIN / "scripts" / "jev-eval.py", "jev_eval")
triage = ev.triage


def user(content, **extra):
    return {"type": "user", "message": {"role": "user", "content": content}, **extra}


def write_jsonl(path, records, junk=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r) for r in records]
    if junk:
        lines.insert(1, "{not json")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


TOOL_RESULT = [{"type": "tool_result", "tool_use_id": "x", "content": "ok"}]
REMINDED = "why does the login test fail <system-reminder>x</system-reminder>"
FIXTURE = [
    user("add a dark mode toggle to settings"),
    user(TOOL_RESULT, toolUseResult={}),
    user([{"type": "text", "text": "Caveat: meta"}], isMeta=True),
    user("<command-name>/clear</command-name>"),
    user("lgtm"),
    user([{"type": "text", "text": REMINDED}]),
    user("a sidechain prompt here", isSidechain=True),
]


def test_iter_prompts_keeps_only_typed_prompts(tmp_path):
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", FIXTURE, junk=True)
    assert list(ev.iter_prompts([path])) == [
        ("proj-a", "s1", "add a dark mode toggle to settings"),
        ("proj-a", "s1", "why does the login test fail"),
    ]


def test_sample_is_stratified_and_deduplicated():
    prompts = [
        ("a", "s1", "p1 x y"),
        ("a", "s1", "p1 x y"),
        ("a", "s2", "p2 x y"),
        ("b", "s3", "q1 x y"),
    ]
    three = ev.sample(prompts, 3, 0)
    assert len(three) == 3
    assert len({t for _, _, t in three}) == 3
    assert {p for p, _, _ in ev.sample(prompts, 2, 0)} == {"a", "b"}


def fake(prompt):
    return triage.Judgment(
        {"underspecified": 0.1, "new_feature": 0.9, "key_decision": 0.2},
        {"input_tokens": 10, "output_tokens": 3, "model": "jev-test"},
    )


@pytest.fixture
def dirs(monkeypatch, tmp_path):
    projects = tmp_path / "projects"
    monkeypatch.setattr(ev, "projects_dir", lambda: projects)
    monkeypatch.setattr(triage, "jev_dir", lambda: tmp_path / "jev")
    for key in triage.KEYS:
        monkeypatch.delenv(f"CLAUDE_KIT_JEV_T_{key.upper()}", raising=False)
    return projects, tmp_path / "jev"


def test_replay_writes_labels(monkeypatch, dirs):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)
    monkeypatch.setattr(triage, "judge", fake)
    assert ev.main(["replay", "--n", "5"]) == 0
    rows = read_rows(jev / "labels.csv")
    assert len(rows) == 2
    assert rows[0]["s_new_feature"] == "0.9000"
    assert rows[0]["input_tokens"] == "10"
    assert rows[0]["label_new_feature"] == ""
    assert rows[0]["session_id"] == "s1"
    assert ev.main(["replay"]) == 1
    assert ev.main(["replay", "--force"]) == 0


def test_replay_stops_on_missing_key(monkeypatch, dirs):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)

    def no_key(prompt):
        raise triage.JevError("missing_key")

    monkeypatch.setattr(triage, "judge", no_key)
    assert ev.main(["replay"]) == 1
    assert not (jev / "labels.csv").exists()


def dated(text, day):
    return user(text, timestamp=f"{day}T10:00:00.000Z")


def test_iter_prompts_since(tmp_path):
    records = [
        dated("an old prompt from july", "2026-07-15"),
        dated("a prompt from the first day", "2026-08-01"),
        user("a prompt with no timestamp"),
    ]
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", records)
    assert [t for _, _, t in ev.iter_prompts([path], "2026-08-01")] == [
        "a prompt from the first day"
    ]
    assert len(list(ev.iter_prompts([path]))) == 3


def must_not_call(prompt):
    raise AssertionError("judge must not be called")


def test_replay_no_judge_needs_no_key(monkeypatch, dirs):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", FIXTURE)
    monkeypatch.setattr(triage, "judge", must_not_call)
    monkeypatch.setitem(sys.modules, "typesafe_sdk", None)
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    assert ev.main(["replay", "--no-judge"]) == 0
    rows = read_rows(jev / "labels.csv")
    assert list(rows[0]) == ev.LABEL_FIELDS
    assert [r["session_id"] for r in rows] == ["s1", "s1"]
    for row in rows:
        assert row["s_new_feature"] == row["latency_ms"] == row["input_tokens"] == ""
    assert ev.main(["replay", "--no-judge"]) == 1  # the overwrite guard holds


def test_replay_since_filters_the_sample(monkeypatch, dirs):
    projects, jev = dirs
    records = [
        dated("an old prompt from july", "2026-07-15"),
        dated("a prompt from august", "2026-08-02"),
    ]
    write_jsonl(projects / "proj-a" / "s1.jsonl", records)
    assert ev.main(["replay", "--no-judge", "--since", "2026-08-01"]) == 0
    assert [r["prompt"] for r in read_rows(jev / "labels.csv")] == [
        "a prompt from august"
    ]


HEADER = [
    "id",
    "project",
    "prompt",
    "s_underspecified",
    "s_new_feature",
    "s_key_decision",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "label_underspecified",
    "label_new_feature",
    "label_key_decision",
]
S_UNDER = [0.9, 0.1, 0.1, 0.1, 0.8]
L_UNDER = [1, 0, 0, 0, 1]
S_FEATURE = [0.9, 0.8, 0.7, 0.3, 0.2]


def labels_csv(
    path, feature_labels, latencies=(100, 150, 200, 250, 300), fmt=str, bom=False
):
    path.parent.mkdir(parents=True, exist_ok=True)
    encoding = "utf-8-sig" if bom else "utf-8"
    with path.open("w", encoding=encoding, newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        for i in range(5):
            writer.writerow(
                [
                    i + 1,
                    "p",
                    f"prompt {i}",
                    S_UNDER[i],
                    S_FEATURE[i],
                    0.5,
                    latencies[i],
                    10,
                    3,
                    fmt(L_UNDER[i]),
                    fmt(feature_labels[i]),
                    "",
                ]
            )
        if bom:
            writer.writerow([""] * len(HEADER))
    return path


def read_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def test_confusion_math(tmp_path):
    rows = read_rows(labels_csv(tmp_path / "l.csv", [1, 1, 0, 1, 0]))
    c = ev.confusion(rows, "new_feature", 0.65)
    assert (c.tp, c.fp, c.fn, c.tn, c.skipped) == (2, 1, 1, 1, 0)
    assert c.precision == pytest.approx(2 / 3)
    assert c.recall == pytest.approx(2 / 3)
    assert ev.confusion(rows, "key_decision", 0.65).skipped == 5


def test_score_gate_fails_on_precision(tmp_path, dirs, capsys):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 0, 1, 0])
    assert ev.main(["score", str(path)]) == 1
    out = capsys.readouterr().out
    assert "Replay gate: FAIL" in out
    assert "new_feature precision 0.67 < 0.8" in out


def test_score_gate_passes(tmp_path, dirs, capsys):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 1, 0, 0])
    assert ev.main(["score", str(path)]) == 0
    out = capsys.readouterr().out
    assert "Replay gate: PASS" in out
    assert "p95 300 ms" in out


def test_score_gate_fails_on_latency(tmp_path, dirs, capsys):
    slow = (100, 150, 200, 250, 900)
    path = labels_csv(tmp_path / "l.csv", [1, 1, 1, 0, 0], latencies=slow)
    assert ev.main(["score", str(path)]) == 1
    assert "p95 latency 900 ms > 500" in capsys.readouterr().out


def test_score_tolerates_excel_edits(tmp_path, dirs):
    path = labels_csv(
        tmp_path / "l.csv", [1, 1, 1, 0, 0], fmt=lambda v: f" {v}.0 ", bom=True
    )
    c = ev.confusion(read_rows(path), "new_feature", 0.65)
    assert (c.tp, c.fp, c.fn, c.tn) == (3, 0, 0, 2)
    assert ev.main(["score", str(path)]) == 0


USAGE = {
    "input_tokens": 10,
    "cache_creation_input_tokens": 0,
    "cache_read_input_tokens": 90,
}


def assistant(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks), "usage": USAGE}}


def say(text):
    return {"type": "text", "text": text}


def tool(name, **inp):
    return {"type": "tool_use", "id": f"{name}-{len(inp)}", "name": name, "input": inp}


P1 = "add a dark mode toggle to settings"
P2 = "no, use the existing theme module"
P3 = "make the thing better somehow please"
P4 = "ok go ahead with option one"
SESSION = [
    user(P1),
    assistant(say("On it."), tool("Edit", file_path="a.py")),
    user(P2),
    assistant(
        tool("Bash", command="git branch --show-current"),
        tool("Write", file_path="b.py"),
    ),
    user(P3),
    assistant(tool("AskUserQuestion", questions=[])),
    user(P4),
    assistant(say("Done. Anything else?")),
]


def log_record(session, mode, prompt, fired=(), error=None, second=0, latency=200):
    return {
        "ts": f"2026-09-28T10:00:{second:02d}",
        "session_id": session,
        "project": "proj-a",
        "mode": mode,
        "prompt": prompt,
        "scores": None if error else {"new_feature": 0.5},
        "thresholds": {},
        "fired": list(fired),
        "injected": bool(fired),
        "latency_ms": latency,
        "usage": None,
        "error": error,
    }


def test_turns_and_outcomes(tmp_path):
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", SESSION, junk=True)
    result = ev.turns(path)
    assert [t[0] for t in result] == [P1, P2, P3, P4]
    o1, o2, o3, o4 = (ev.outcome(a, nxt) for _, a, nxt in result)
    assert (o1.asked, o1.preflight, o1.corrected) == (False, False, True)
    assert (o2.preflight, o2.corrected) == (True, False)
    assert o3.asked is True and o3.preflight is None
    assert o4.asked is True and o4.corrected is False


def test_report_end_to_end(dirs, capsys):
    projects, jev = dirs
    write_jsonl(projects / "proj-a" / "s1.jsonl", SESSION, junk=True)
    records = [
        log_record("s1", "active", P1, ["new_feature"], second=1),
        log_record("s1", "active", P2, second=2),
        log_record("s1", "active", P3, ["underspecified"], second=3),
        log_record("s1", "active", P4, second=4),
        log_record(
            "s1", "active", "never typed here", error="timeout", second=5, latency=2000
        ),
        log_record("s2-missing", "shadow", P1, ["key_decision"]),
    ]
    write_jsonl(jev / "log.jsonl", records)

    matched, tokens = ev.collect(records)
    stats = ev.summarize(records, matched, tokens)
    active = stats["active"]
    assert active["logged"] == 5
    assert active["matched"] == 4
    assert active["error_rate"] == pytest.approx(0.2)
    assert active["fire_share"]["new_feature"] == pytest.approx(0.25)
    assert active["convention_miss_rate"] == pytest.approx(0.5)
    assert (active["misses"], active["applicable"]) == (1, 2)
    assert active["correction_rate"] == pytest.approx(0.25)
    assert active["median_tokens"] == 400
    assert active["latency_p95"] == 2000  # timeouts count: the user waited
    assert stats["shadow"]["matched"] == 0
    assert stats["shadow"]["convention_miss_rate"] is None

    assert ev.main(["report"]) == 0
    out = capsys.readouterr().out
    assert "active" in out and "shadow" in out
    assert "1/2 (50%)" in out
    spot = read_rows(jev / "spotcheck.csv")
    assert [r["prompt"] for r in spot] == [P1, P3]
    assert ev.main(["report", "--since", "2026-09-29"]) == 1


INTERRUPT = "[Request interrupted by user for tool use]"
FOLLOW_UP = "please use the theme module instead"


def test_interrupt_is_not_a_prompt_but_counts_as_correction(tmp_path):
    session = [
        user(P1),
        assistant(tool("Edit", file_path="a.py")),
        user([{"type": "text", "text": INTERRUPT}]),
        user(FOLLOW_UP),
        assistant(say("Switching.")),
    ]
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", session)
    assert [t for _, _, t in ev.iter_prompts([path])] == [P1, FOLLOW_UP]
    result = ev.turns(path)
    assert [t[0] for t in result] == [P1, FOLLOW_UP]
    assert ev.outcome(result[0][1], result[0][2]).corrected is True


SPEC = "C:\\repo\\docs\\superpowers\\specs\\x.md"
NEXT_FEATURE = "add a csv export for the report page"


def test_preflight_ignores_docs_writes_and_spans_short_replies(tmp_path):
    session = [
        user(P1),
        assistant(tool("Write", file_path=SPEC), say("Spec written. Approve?")),
        user("lgtm"),
        assistant(
            tool("Bash", command="git -C /repo branch --show-current"),
            tool("MultiEdit", file_path="src/a.py"),
        ),
        user(NEXT_FEATURE),
        assistant(tool("NotebookEdit", notebook_path="nb.ipynb")),
    ]
    path = write_jsonl(tmp_path / "proj-a" / "s1.jsonl", session)
    records = [
        log_record("s1", "active", P1, ["new_feature"], second=1),
        log_record("s1", "active", NEXT_FEATURE, ["new_feature"], second=2),
    ]
    [(_, first), (_, second)] = ev.match(records, ev.turns(path))
    assert first.asked is True
    assert first.preflight is True
    assert second.preflight is False


def test_score_missing_file(tmp_path, dirs, capsys):
    assert ev.main(["score", str(tmp_path / "nope.csv")]) == 1
    assert "not found" in capsys.readouterr().err


def test_score_reads_ansi_semicolon_decimal_comma(tmp_path, dirs):
    path = labels_csv(tmp_path / "l.csv", [1, 1, 1, 0, 0])
    text = path.read_text(encoding="utf-8")
    text = text.replace(",", ";").replace(".", ",")
    text = text.replace("prompt 0", "prompt – “smart”")
    path.write_bytes(text.encode("cp1252"))
    assert ev.main(["score", str(path)]) == 0
