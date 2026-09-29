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
import json
import math
import random
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
    if not text or text.startswith("<"):
        return None
    return text


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


def parse_label(value: object) -> int | None:
    try:
        number = float(str(value).strip())
    except ValueError:
        return None
    return int(number) if number in (0.0, 1.0) else None


def parse_score(value: object) -> float | None:
    try:
        return float(str(value).strip())
    except ValueError:
        return None


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
    with path.open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    return [r for r in rows if any((v or "").strip() for v in r.values())]


def column_total(rows: list[dict], name: str) -> int:
    return sum(int(parse_score(r.get(name, "")) or 0) for r in rows)


def cmd_score(args: argparse.Namespace) -> int:
    path = Path(args.labels) if args.labels else triage.jev_dir() / "labels.csv"
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


def cmd_report(args: argparse.Namespace) -> int:
    print("report is not implemented yet", file=sys.stderr)
    return 1


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
