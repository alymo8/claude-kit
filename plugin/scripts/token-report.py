#!/usr/bin/env python3
"""Where do the tokens go? Measure Claude Code transcripts and simulate restarts.

Usage:
  token-report.py [--project DIR] [--root DIR] [--cap N ...]   one project
  token-report.py --all [--root DIR] [--cap N ...]              all projects

Transcripts live under ``~/.claude/projects/<encoded cwd>/*.jsonl``. Prints
sessions, turns, total input tokens, average context per call, the largest
sessions, tool output by tool and by Bash command family, results over 15k
characters, and total input tokens under a "restart with a 45k handoff at N
tokens" policy for each ``--cap``. Standard library only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RESTART_COST = 45_000
BIG_RESULT = 15_000
SUBCOMMAND_WORDS = {
    "git",
    "gh",
    "npm",
    "npx",
    "pnpm",
    "yarn",
    "python",
    "pytest",
    "ruff",
    "node",
}
USAGE_KEYS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
FAMILY_RE = re.compile(r"(?:cd\s+\S+\s*(?:&&|;)\s*)*(\S+)")


def encode_project(path: Path) -> str:
    return re.sub(r"[^A-Za-z0-9]", "-", str(path))


@dataclass
class Report:
    sessions: int = 0
    turns: int = 0
    input_tokens: int = 0
    contexts: list[list[int]] = field(default_factory=list)
    per_session: list[tuple[str, int, int, float | None]] = field(default_factory=list)
    tool_chars: Counter = field(default_factory=Counter)
    tool_calls: Counter = field(default_factory=Counter)
    families: Counter = field(default_factory=Counter)
    big_results: list[tuple[int, str, str]] = field(default_factory=list)


def family(command: str) -> str:
    match = FAMILY_RE.match(command.strip())
    word = match.group(1) if match else "?"
    if word in SUBCOMMAND_WORDS:
        sub = re.search(re.escape(word) + r"\s+(\S+)", command)
        word = f"{word} {sub.group(1)}" if sub else word
    return word


def result_text(block: dict) -> str:
    content = block.get("content")
    if isinstance(content, list):
        return "".join(x.get("text", "") for x in content if isinstance(x, dict))
    return content if isinstance(content, str) else ""


def scan(files: list[Path]) -> Report:
    report = Report()
    for path in files:
        report.sessions += 1
        tools: dict[str, tuple[str, dict]] = {}
        contexts: list[int] = []
        cost: float | None = None
        for line in path.open(encoding="utf-8", errors="replace"):
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            kind = record.get("type")
            message = record.get("message") or {}
            if kind == "cost-state":
                cost = record.get("totalCostUSD")
            elif kind == "assistant":
                usage = message.get("usage")
                if isinstance(usage, dict):
                    ctx = sum(int(usage.get(k) or 0) for k in USAGE_KEYS)
                    contexts.append(ctx)
                    report.turns += 1
                    report.input_tokens += ctx
                for block in message.get("content") or []:
                    if isinstance(block, dict) and (block.get("type") == "tool_use"):
                        tools[block.get("id", "")] = (
                            block.get("name", "?"),
                            block.get("input") or {},
                        )
                        report.tool_calls[block.get("name", "?")] += 1
            elif kind == "user" and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if not (
                        isinstance(block, dict) and block.get("type") == "tool_result"
                    ):
                        continue
                    text = result_text(block)
                    name, inp = tools.get(block.get("tool_use_id", ""), ("?", {}))
                    report.tool_chars[name] += len(text)
                    if name in ("Bash", "PowerShell"):
                        report.families[family(str(inp.get("command", "")))] += len(
                            text
                        )
                    if len(text) > BIG_RESULT:
                        what = (
                            inp.get("command")
                            or inp.get("file_path")
                            or inp.get("pattern")
                            or ""
                        )
                        report.big_results.append((len(text), name, str(what)[:80]))
        if contexts:
            report.contexts.append(contexts)
            report.per_session.append(
                (path.stem[:8], len(contexts), contexts[-1], cost)
            )
    return report


def simulate(contexts: list[list[int]], cap: int, restart: int = RESTART_COST) -> int:
    total = 0
    for session in contexts:
        offset = 0
        for ctx in session:
            effective = ctx - offset
            if effective > cap:
                offset = ctx - restart
                effective = restart
            total += effective
    return total


def render(report: Report, caps: list[int]) -> str:
    out: list[str] = []
    out.append(f"sessions: {report.sessions}   turns: {report.turns:,}")
    out.append(f"total input tokens (all turns): {report.input_tokens:,}")
    avg = report.input_tokens // report.turns if report.turns else 0
    out.append(f"avg context per call: {avg:,}")
    out.append("")
    out.append("largest sessions by end context (id, turns, end ctx, cost):")
    for sid, turns, end, cost in sorted(report.per_session, key=lambda r: -r[2])[:10]:
        cost_text = f"${cost:.2f}" if isinstance(cost, int | float) else "-"
        out.append(f"  {sid}  {turns:>5}  {end:>9,}  {cost_text}")
    out.append("")
    total_chars = sum(report.tool_chars.values()) or 1
    out.append("tool output by tool (chars, calls, share):")
    for name, chars in report.tool_chars.most_common(10):
        share = 100 * chars // total_chars
        out.append(f"  {name:22s} {chars:>12,} {report.tool_calls[name]:>6}  {share}%")
    out.append("")
    out.append("Bash output by command family (chars):")
    for name, chars in report.families.most_common(15):
        out.append(f"  {chars:>12,}  {name}")
    out.append("")
    out.append(f"results over {BIG_RESULT:,} chars: {len(report.big_results)}")
    for chars, name, what in sorted(report.big_results, reverse=True)[:10]:
        out.append(f"  {chars:>9,}  {name:10s} {what}")
    out.append("")
    out.append(f"restart simulation ({RESTART_COST:,}-token restart):")
    for cap in caps:
        simulated = simulate(report.contexts, cap)
        saved = (
            100 * (1 - simulated / report.input_tokens) if report.input_tokens else 0
        )
        out.append(f"  cap {cap:,}: {simulated:,}  ({saved:.0f}% fewer)")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--project",
        default=".",
        help="project directory (default: cwd)",
    )
    parser.add_argument("--all", action="store_true", help="scan every project folder")
    parser.add_argument(
        "--root",
        default=str(Path.home() / ".claude" / "projects"),
    )
    parser.add_argument(
        "--cap",
        type=int,
        nargs="*",
        default=[150_000, 200_000, 300_000],
    )
    args = parser.parse_args(argv)
    root = Path(args.root)
    if args.all:
        files = sorted(root.glob("*/*.jsonl")) if root.is_dir() else []
    else:
        folder = root / encode_project(Path(args.project).resolve())
        files = sorted(folder.glob("*.jsonl")) if folder.is_dir() else []
    if not files:
        print("no transcripts found")
        return 0
    print(render(scan(files), args.cap))
    return 0


if __name__ == "__main__":
    sys.exit(main())
