#!/usr/bin/env python3
"""Claude Code status line: context tokens, percentage, cost and branch.

Reads the status line JSON on stdin and prints one ASCII line, e.g.
``ctx 312k/1M 31% | $14.20 | feature/foo``. The percentage is yellow from 30%
and red from 60%. Prints an empty line on malformed input; never raises.
"""

from __future__ import annotations

import json
import subprocess
import sys

YELLOW = "\x1b[33m"
RED = "\x1b[31m"
RESET = "\x1b[0m"


def _k(n: int) -> str:
    return "1M" if n >= 1_000_000 else f"{round(n / 1000)}k"


def current_branch(cwd: str) -> str:
    if not cwd:
        return ""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def render(data: dict, branch: str) -> str:
    ctx = data.get("context_window") or {}
    used = ctx.get("total_input_tokens") or 0
    size = ctx.get("context_window_size") or 0
    pct = ctx.get("used_percentage")
    if used and pct is not None:
        pct_int = int(round(float(pct)))
        color = RED if pct_int >= 60 else YELLOW if pct_int >= 30 else ""
        pct_text = f"{color}{pct_int}%{RESET if color else ''}"
        if size:
            ctx_text = f"ctx {_k(int(used))}/{_k(int(size))} {pct_text}"
        else:
            ctx_text = f"ctx {_k(int(used))} {pct_text}"
    else:
        ctx_text = "ctx -"
    cost = float((data.get("cost") or {}).get("total_cost_usd") or 0)
    parts = [ctx_text, f"${cost:.2f}"]
    if branch:
        parts.append(branch)
    return " | ".join(parts)


def main() -> int:
    try:
        data = json.loads(sys.stdin.read() or "{}")
        if not isinstance(data, dict):
            raise ValueError("not an object")
        workspace = data.get("workspace") or {}
        cwd = workspace.get("current_dir") or data.get("cwd") or ""
        print(render(data, current_branch(str(cwd))))
    except Exception:
        print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
