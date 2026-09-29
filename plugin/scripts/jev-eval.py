#!/usr/bin/env python3
"""Evaluate the jev triage pilot.

  replay [--n 60] [--seed 0] [--force]  sample past prompts, judge, write labels.csv
  score [labels.csv]                    precision/recall vs your labels; Replay gate
  report [--since YYYY-MM-DD]           shadow vs active outcomes from the hook log

Outputs go to ~/.claude/claude-kit/jev/. replay needs typesafe-sdk and
TYPESAFE_API_KEY. Spec: docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import io
import json
import math
import random
import re
import statistics
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "hooks"))

import jev_triage as triage  # noqa: E402

GATE_KEYS = ("underspecified", "new_feature")
GATE_PRECISION = 0.8
GATE_RECALL = 0.6
GATE_P95_MS = 500
SWEEP = [round(0.50 + 0.05 * i, 2) for i in range(9)]
INTERRUPT_PREFIX = "[Request interrupted by user"
LABEL_FIELDS = [
    "id",
    "project",
    "prompt",
    *(f"s_{k}" for k in triage.KEYS),
    "latency_ms",
    "input_tokens",
    "output_tokens",
    *(f"label_{k}" for k in triage.KEYS),
]


def projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if isinstance(record, dict):
                yield record


def typed_text(record: dict) -> str | None:
    """Cleaned text of a prompt the user typed; None for anything else."""
    if (
        record.get("type") != "user"
        or record.get("isMeta")
        or record.get("isSidechain")
        or "toolUseResult" in record
    ):
        return None
    content = (record.get("message") or {}).get("content")
    if isinstance(content, str):
        text = content
    elif isinstance(content, list):
        blocks = [b for b in content if isinstance(b, dict)]
        if any(b.get("type") == "tool_result" for b in blocks):
            return None
        texts = [str(b.get("text", "")) for b in blocks if b.get("type") == "text"]
        text = "\n".join(texts)
    else:
        return None
    text = triage.clean(text)
    if not text or text.startswith(("<", INTERRUPT_PREFIX)):
        return None
    return text


def is_interrupt(record: dict) -> bool:
    """The marker Claude Code records when the user interrupts a reply."""
    if record.get("type") != "user":
        return False
    content = (record.get("message") or {}).get("content")
    if isinstance(content, list):
        content = " ".join(
            str(b.get("text", "")) for b in content if isinstance(b, dict)
        )
    return isinstance(content, str) and content.startswith(INTERRUPT_PREFIX)


def prompt_text(record: dict) -> str | None:
    """Typed text the hook would judge."""
    text = typed_text(record)
    return text if text and triage.should_judge(text) else None


def iter_prompts(files: Iterable[Path]) -> Iterator[tuple[str, str]]:
    for path in files:
        for record in read_jsonl(path):
            text = prompt_text(record)
            if text:
                yield path.parent.name, text


def sample(prompts: list[tuple[str, str]], n: int, seed: int) -> list[tuple[str, str]]:
    """Up to n distinct prompts, round-robin across projects."""
    rng = random.Random(seed)
    groups: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for project, text in prompts:
        if text not in seen:
            seen.add(text)
            groups[project].append(text)
    for texts in groups.values():
        rng.shuffle(texts)
    order = sorted(groups)
    rng.shuffle(order)
    chosen: list[tuple[str, str]] = []
    while len(chosen) < n and any(groups[p] for p in order):
        for project in order:
            if groups[project] and len(chosen) < n:
                chosen.append((project, groups[project].pop()))
    return chosen


def percentile(values: list[float], pct: float) -> float | None:
    """Nearest-rank percentile; None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(pct / 100 * len(ordered)) - 1)]


def parse_score(value: object) -> float | None:
    """A number from a CSV cell; accepts a decimal comma (Excel in some locales)."""
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return None


def parse_label(value: object) -> int | None:
    number = parse_score(value)
    return int(number) if number in (0.0, 1.0) else None


@dataclass
class Confusion:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    skipped: int = 0

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0


def confusion(rows: list[dict], key: str, threshold: float) -> Confusion:
    c = Confusion()
    for row in rows:
        label = parse_label(row.get(f"label_{key}", ""))
        score = parse_score(row.get(f"s_{key}", ""))
        if label is None or score is None:
            c.skipped += 1
            continue
        predicted = score >= threshold
        if predicted and label:
            c.tp += 1
        elif predicted:
            c.fp += 1
        elif label:
            c.fn += 1
        else:
            c.tn += 1
    return c


def label_row(i: int, project: str, text: str) -> dict:
    """Judge one prompt and build its labels.csv row; raises JevError."""
    start = time.perf_counter()
    try:
        judgment = triage.judge(text)
    except triage.JevError as exc:
        if exc.code in ("missing_key", "missing_sdk"):
            raise
        print(f"prompt {i}: {exc.code}", file=sys.stderr)
        judgment = triage.Judgment({}, None)
    usage = judgment.usage or {}
    scores = judgment.scores
    return {
        "id": i,
        "project": project,
        "prompt": text,
        **{f"s_{k}": f"{scores[k]:.4f}" if k in scores else "" for k in triage.KEYS},
        "latency_ms": round((time.perf_counter() - start) * 1000),
        "input_tokens": usage.get("input_tokens") or "",
        "output_tokens": usage.get("output_tokens") or "",
        **{f"label_{k}": "" for k in triage.KEYS},
    }


def cmd_replay(args: argparse.Namespace) -> int:
    out = triage.jev_dir() / "labels.csv"
    if out.exists() and not args.force:
        print(f"{out} exists; pass --force to overwrite", file=sys.stderr)
        return 1
    files = sorted(projects_dir().glob("*/*.jsonl"))
    chosen = sample(list(iter_prompts(files)), args.n, args.seed)
    try:
        rows = [label_row(i, p, t) for i, (p, t) in enumerate(chosen, 1)]
    except triage.JevError as exc:
        print(f"cannot judge: {exc.code}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=LABEL_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} prompts to {out}")
    print("fill the label_* columns with 1 or 0, then run: jev-eval.py score")
    return 0


def read_labels(path: Path) -> list[dict]:
    """labels.csv as written by replay or re-saved by Excel (ANSI, semicolons)."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", "replace")
    header = text.splitlines()[0] if text else ""
    delimiter = ";" if header.count(";") > header.count(",") else ","
    rows = list(csv.DictReader(io.StringIO(text, newline=""), delimiter=delimiter))
    return [r for r in rows if any((v or "").strip() for v in r.values())]


def column_total(rows: list[dict], name: str) -> int:
    return sum(int(parse_score(r.get(name, "")) or 0) for r in rows)


def cmd_score(args: argparse.Namespace) -> int:
    path = Path(args.labels) if args.labels else triage.jev_dir() / "labels.csv"
    if not path.is_file():
        print(f"{path} not found; run: jev-eval.py replay", file=sys.stderr)
        return 1
    rows = read_labels(path)
    limits = triage.thresholds()
    failures: list[str] = []
    for key in triage.KEYS:
        c = confusion(rows, key, limits[key])
        print(
            f"{key}: threshold {limits[key]:.2f}  precision {c.precision:.2f}  "
            f"recall {c.recall:.2f}  f1 {c.f1:.2f}  "
            f"(labelled {len(rows) - c.skipped}, unlabelled {c.skipped})"
        )
        sweep = []
        for t in SWEEP:
            s = confusion(rows, key, t)
            sweep.append(f"{t:.2f} P{s.precision:.2f} R{s.recall:.2f}")
        print("  sweep: " + " | ".join(sweep))
        if key in GATE_KEYS:
            if c.precision < GATE_PRECISION:
                failures.append(f"{key} precision {c.precision:.2f} < {GATE_PRECISION}")
            if c.recall < GATE_RECALL:
                failures.append(f"{key} recall {c.recall:.2f} < {GATE_RECALL}")
    judged = [r for r in rows if parse_score(r.get("s_new_feature", "")) is not None]
    latencies = [parse_score(r.get("latency_ms", "")) for r in judged]
    p95 = percentile([v for v in latencies if v is not None], 95)
    p50 = percentile([v for v in latencies if v is not None], 50)
    if p95 is None or p50 is None:
        failures.append("no judged rows")
    else:
        print(
            f"latency p50 {p50:.0f} ms, p95 {p95:.0f} ms over {len(judged)} calls; "
            f"tokens in {column_total(judged, 'input_tokens')} / "
            f"out {column_total(judged, 'output_tokens')} "
            "(cost = calls x the per-evaluation price on the TypeSafe dashboard)"
        )
        if p95 > GATE_P95_MS:
            failures.append(f"p95 latency {p95:.0f} ms > {GATE_P95_MS}")
    if failures:
        print("Replay gate: FAIL: " + "; ".join(failures))
        return 1
    print("Replay gate: PASS")
    return 0


CORRECTION_RE = re.compile(
    r"^\s*(?:no\b|don['’]?t\b|do not\b|actually\b|stop\b|wait\b|that['’]?s not\b)",
    re.I,
)
CHECK_RE = re.compile(r"git\s+(?:-C\s+\S+\s+)?(?:branch\s+--show-current|fetch)")
EDIT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")
# Specs, plans, ADRs and Claude's own files are written before the pre-flight
# check by design (brainstorm -> spec -> plan -> build); they are not "building".
DOC_PATH_RE = re.compile(r"(?:^|[\\/])(?:docs[\\/]superpowers|knowledge|\.claude)[\\/]")
SESSION_RE = re.compile(r"[\w-]+")
SPOTCHECK_FIELDS = [
    "session_id",
    "mode",
    "prompt",
    "fired",
    "asked",
    "preflight",
    "corrected",
    "false_alarm",
]


@dataclass
class Outcome:
    asked: bool
    preflight: bool | None  # None: no code edit in the turn sequence
    corrected: bool


Turn = tuple[str, list[dict], str | None]
INTERRUPTED = {"type": "interrupted"}  # marker kept in a turn's records


def turns(path: Path) -> list[Turn]:
    """(typed prompt, assistant records until the next typed prompt, next prompt).

    An interrupt is not a prompt: it stays in the turn as the INTERRUPTED marker.
    """
    out: list[Turn] = []
    current: str | None = None
    bucket: list[dict] = []
    for record in read_jsonl(path):
        text = typed_text(record)
        if text is not None:
            if current is not None:
                out.append((current, bucket, text))
            current, bucket = text, []
        elif current is None:
            continue
        elif record.get("type") == "assistant":
            bucket.append(record)
        elif is_interrupt(record):
            bucket.append(INTERRUPTED)
    if current is not None:
        out.append((current, bucket, None))
    return out


def tool_uses(records: list[dict]) -> Iterator[dict]:
    for record in records:
        content = (record.get("message") or {}).get("content")
        if isinstance(content, list):
            yield from (b for b in content if isinstance(b, dict))


def preflight_of(records: list[dict]) -> bool | None:
    """Was the pre-flight check run before the first code edit? None: no edit."""
    checked = False
    for block in tool_uses(records):
        if block.get("type") != "tool_use":
            continue
        name = block.get("name")
        args = block.get("input") or {}
        if name in ("Bash", "PowerShell"):
            checked = checked or bool(CHECK_RE.search(str(args.get("command", ""))))
        elif name in EDIT_TOOLS:
            target = str(args.get("file_path") or args.get("notebook_path") or "")
            if not DOC_PATH_RE.search(target):
                return checked
    return None


def outcome(
    assistant: list[dict], next_prompt: str | None, window: list[dict] | None = None
) -> Outcome:
    """Outcome of one turn; ``window`` (default: the turn) is scanned for preflight."""
    asked = False
    last_text = ""
    for block in tool_uses(assistant):
        if block.get("type") == "text":
            last_text = str(block.get("text", ""))
        elif block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion":
            asked = True
    asked = asked or last_text.rstrip().endswith("?")
    corrected = INTERRUPTED in assistant or bool(
        next_prompt and CORRECTION_RE.match(next_prompt)
    )
    return Outcome(
        asked, preflight_of(assistant if window is None else window), corrected
    )


def match(records: list[dict], session_turns: list[Turn]) -> list[tuple[dict, Outcome]]:
    """Pair log records (in time order) with transcript turns by prompt text.

    The preflight window is the matched turn plus the following turns whose prompt
    the hook would not judge (short replies such as "lgtm"): one turn sequence.
    """
    out: list[tuple[dict, Outcome]] = []
    start = 0
    for record in records:
        k = start
        while k < len(session_turns) and session_turns[k][0] != record.get("prompt"):
            k += 1
        if k == len(session_turns):
            continue
        _, assistant, next_prompt = session_turns[k]
        window = list(assistant)
        j = k + 1
        while j < len(session_turns) and not triage.should_judge(session_turns[j][0]):
            window += session_turns[j][1]
            j += 1
        out.append((record, outcome(assistant, next_prompt, window)))
        start = k + 1
    return out


def token_report():
    """token-report.py, loaded by path (hyphenated name) and cached."""
    if "token_report" not in sys.modules:
        spec = importlib.util.spec_from_file_location(
            "token_report", HERE / "token-report.py"
        )
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules["token_report"] = module  # dataclasses look the module up
        spec.loader.exec_module(module)
    return sys.modules["token_report"]


def session_tokens(path: Path) -> int:
    report = token_report().scan([path])
    return sum(report.contexts[0]) if report.contexts else 0


def transcript_for(session_id: object) -> Path | None:
    if not isinstance(session_id, str) or not SESSION_RE.fullmatch(session_id):
        return None
    return next(projects_dir().glob(f"*/{session_id}.jsonl"), None)


def collect(
    records: list[dict],
) -> tuple[list[tuple[dict, Outcome]], dict[str, int]]:
    """Matched (record, outcome) pairs and tokens per session with a transcript."""
    by_session: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        by_session[str(record.get("session_id"))].append(record)
    matched: list[tuple[dict, Outcome]] = []
    tokens: dict[str, int] = {}
    for session_id, recs in by_session.items():
        path = transcript_for(session_id)
        if path is None:
            continue
        recs.sort(key=lambda r: str(r.get("ts", "")))
        matched += match(recs, turns(path))
        tokens[session_id] = session_tokens(path)
    return matched, tokens


def ratio(part: int, whole: int) -> float | None:
    return part / whole if whole else None


def misses_of(pairs: list[tuple[dict, Outcome]]) -> tuple[int, int]:
    """(convention misses, applicable checks) over fired prompts."""
    applicable = misses = 0
    for record, result in pairs:
        keys = set(record.get("fired") or [])
        if "new_feature" in keys and result.preflight is not None:
            applicable += 1
            misses += not result.preflight
        if keys & {"underspecified", "key_decision"}:
            applicable += 1
            misses += not result.asked
    return misses, applicable


def summarize(
    records: list[dict], matched: list[tuple[dict, Outcome]], tokens: dict[str, int]
) -> dict[str, dict]:
    stats: dict[str, dict] = {}
    for mode in ("shadow", "active"):
        recs = [r for r in records if r.get("mode") == mode]
        if not recs:
            continue
        judged = [r for r in recs if r.get("scores")]
        pairs = [(r, o) for r, o in matched if r.get("mode") == mode]
        misses, applicable = misses_of(pairs)
        sessions = {str(r.get("session_id")) for r in recs}
        totals = [tokens[s] for s in sessions if s in tokens]
        # Every record, errors included: the user waited for timeouts too.
        latencies = [
            r["latency_ms"] for r in recs if isinstance(r.get("latency_ms"), int)
        ]
        errors = sum(1 for r in recs if r.get("error"))
        corrected = sum(1 for _, o in pairs if o.corrected)
        stats[mode] = {
            "logged": len(recs),
            "matched": len(pairs),
            "error_rate": ratio(errors, len(recs)),
            "fire_share": {
                k: ratio(
                    sum(1 for r in judged if k in (r.get("fired") or [])), len(judged)
                )
                for k in triage.KEYS
            },
            "misses": misses,
            "applicable": applicable,
            "convention_miss_rate": ratio(misses, applicable),
            "correction_rate": ratio(corrected, len(pairs)),
            "median_tokens": statistics.median(totals) if totals else None,
            "latency_p50": percentile(latencies, 50),
            "latency_p95": percentile(latencies, 95),
        }
    return stats


def fmt(value: float | None, pct: bool = False) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0%}" if pct else f"{value:.0f}"


def render(stats: dict[str, dict]) -> str:
    lines = []
    for mode, s in stats.items():
        shares = ", ".join(f"{k} {fmt(v, True)}" for k, v in s["fire_share"].items())
        lines += [
            f"{mode}: {s['logged']} prompts logged, "
            f"{s['matched']} matched to transcripts",
            f"  fired: {shares}",
            "  convention misses per applicable check: "
            f"{s['misses']}/{s['applicable']} "
            f"({fmt(s['convention_miss_rate'], True)})",
            f"  correction rate: {fmt(s['correction_rate'], True)}",
            f"  median tokens per session: {fmt(s['median_tokens'])}",
            f"  latency p50 {fmt(s['latency_p50'])} ms, "
            f"p95 {fmt(s['latency_p95'])} ms; errors {fmt(s['error_rate'], True)}",
        ]
    return "\n".join(lines)


def read_log(since: str) -> list[dict]:
    path = triage.jev_dir() / "log.jsonl"
    if not path.exists():
        return []
    return [r for r in read_jsonl(path) if str(r.get("ts", ""))[:10] >= since]


def write_spotcheck(matched: list[tuple[dict, Outcome]]) -> tuple[int, Path]:
    fired_pairs = [(r, o) for r, o in matched if r.get("fired")]
    chosen = random.Random(0).sample(fired_pairs, min(20, len(fired_pairs)))
    chosen.sort(key=lambda pair: str(pair[0].get("ts", "")))
    out = triage.jev_dir() / "spotcheck.csv"
    with out.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SPOTCHECK_FIELDS)
        writer.writeheader()
        for record, result in chosen:
            preflight = "n/a" if result.preflight is None else result.preflight
            writer.writerow(
                {
                    "session_id": record.get("session_id"),
                    "mode": record.get("mode"),
                    "prompt": record.get("prompt"),
                    "fired": " ".join(record.get("fired") or []),
                    "asked": result.asked,
                    "preflight": preflight,
                    "corrected": result.corrected,
                    "false_alarm": "",
                }
            )
    return len(chosen), out


def cmd_report(args: argparse.Namespace) -> int:
    records = read_log(args.since)
    if not records:
        print("no log records" + (f" since {args.since}" if args.since else ""))
        return 1
    matched, tokens = collect(records)
    print(render(summarize(records, matched, tokens)))
    count, out = write_spotcheck(matched)
    print(f"spot-check {count} fired prompts in {out} (fill false_alarm 1/0)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the jev triage pilot.")
    sub = parser.add_subparsers(dest="command", required=True)
    replay = sub.add_parser("replay", help="judge a sample of past prompts")
    replay.add_argument("--n", type=int, default=60)
    replay.add_argument("--seed", type=int, default=0)
    replay.add_argument("--force", action="store_true")
    score = sub.add_parser("score", help="score labels.csv against the gate")
    score.add_argument("labels", nargs="?")
    report = sub.add_parser("report", help="shadow vs active outcomes")
    report.add_argument("--since", default="")
    args = parser.parse_args(argv)
    handler = {"replay": cmd_replay, "score": cmd_score, "report": cmd_report}
    return handler[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
