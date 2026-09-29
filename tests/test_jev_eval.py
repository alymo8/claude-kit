import csv
import json

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
        ("proj-a", "add a dark mode toggle to settings"),
        ("proj-a", "why does the login test fail"),
    ]


def test_sample_is_stratified_and_deduplicated():
    prompts = [("a", "p1 x y"), ("a", "p1 x y"), ("a", "p2 x y"), ("b", "q1 x y")]
    three = ev.sample(prompts, 3, 0)
    assert len(three) == 3
    assert len({t for _, t in three}) == 3
    assert {p for p, _ in ev.sample(prompts, 2, 0)} == {"a", "b"}


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
