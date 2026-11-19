#!/usr/bin/env python3
"""Run one ``/ship-many`` child with a time limit, keep-awake and one resume.

Usage::

    python ship-child.py --spec <rel> --main <main checkout> --log <log dir>
        --name <log-name> [--timeout 7200] [--resume-wait 60]
        [--claude claude] [--gh gh] [--git git]

1. Keep-awake for the runner's lifetime: ``SetThreadExecutionState`` on
   Windows, ``caffeinate`` on macOS, ``systemd-inhibit`` elsewhere when found;
   when none applies, carry on and record ``"keep_awake": false``.
2. Attempt: ``claude -p "/claude-kit:ship <rel>" --permission-mode auto
   --permission-prompts none --output-format json`` with
   ``CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0``, in its own process group,
   stdout to ``<log>/<name>.json`` and stderr to ``<log>/<name>.err``. After
   ``--timeout`` seconds the whole process tree is killed.
3. Decide once on a resume from the merged-PR state (``gh``), a stop-rule
   handoff in the child's ``feat/<slug>`` worktree, and whether that worktree
   existed before the run.
4. Resume: wait ``--resume-wait`` seconds, then run one more attempt in the
   chosen directory (logs ``<name>.resume.json`` and ``<name>.resume.err``).
5. Status: write ``<log>/<name>.status.json``. The exit code is the last
   attempt's (124 when it timed out); 2 on bad usage.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import signal
import subprocess
from pathlib import Path

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
SNAPSHOT_BY = "session-end snapshot"
WRITTEN_RE = re.compile(r"^- \*\*Written:\*\* .* by (.+?)\s*$", re.M)


def branch_slug(spec: str) -> str:
    """Return the branch slug of a spec path: file name without date or -design."""
    stem = spec.replace("\\", "/").rsplit("/", 1)[-1]
    if stem.endswith(".md"):
        stem = stem[: -len(".md")]
    stem = re.sub(r"^\d{4}-\d{2}-\d{2}-", "", stem)
    if stem.endswith("-design"):
        stem = stem[: -len("-design")]
    return stem


def worktree_on(porcelain: str, branch: str) -> Path | None:
    """Return the first worktree in ``git worktree list --porcelain`` on branch."""
    want = f"branch refs/heads/{branch}"
    for block in re.split(r"\n\s*\n", porcelain.replace("\r", "")):
        path = None
        on_branch = False
        for line in block.splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree ") :]
            elif line.strip() == want:
                on_branch = True
        if path is not None and on_branch:
            return Path(path)
    return None


def stop_rule_handoff(worktree: Path, slug: str) -> bool:
    """True when the worktree holds a handoff not written by the snapshot hook."""
    path = worktree / ".claude" / "handoffs" / f"feat_{slug}.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return False
    for match in WRITTEN_RE.finditer(text):
        if match.group(1).replace("\r", "").strip() != SNAPSHOT_BY:
            return True
    return False


def read_cost(path: Path) -> float | None:
    """Return ``total_cost_usd`` from a child's JSON output, else None."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    cost = data.get("total_cost_usd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        return None
    return float(cost)


class KeepAwake:
    """A keep-awake request; ``release()`` ends it and may be called twice."""

    def __init__(
        self,
        active: bool = False,
        proc: subprocess.Popen | None = None,
        group: bool = False,
        windows: bool = False,
    ) -> None:
        self.active = active
        self._proc = proc
        self._group = group
        self._windows = windows

    def release(self) -> None:
        if self._windows:
            self._windows = False
            try:
                _set_execution_state(ES_CONTINUOUS)
            except (OSError, AttributeError):
                pass
        proc, self._proc = self._proc, None
        if proc is None:
            return
        try:
            if self._group:
                os.killpg(proc.pid, signal.SIGTERM)
            else:
                proc.terminate()
        except (OSError, ProcessLookupError):
            pass
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except (OSError, ProcessLookupError):
                pass
        except OSError:
            pass


def _set_execution_state(flags: int) -> int:
    import ctypes

    func = ctypes.windll.kernel32.SetThreadExecutionState
    func.restype = ctypes.c_uint32
    return func(flags)


def _start_holder(cmd: list[str], group: bool) -> KeepAwake:
    kwargs = {"start_new_session": True} if group else {}
    try:
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **kwargs,
        )
    except OSError:
        return KeepAwake()
    try:
        proc.wait(timeout=1)
    except subprocess.TimeoutExpired:
        return KeepAwake(active=True, proc=proc, group=group)
    except OSError:
        pass
    return KeepAwake()


def keep_awake(platform: str) -> KeepAwake:
    """Ask the OS not to sleep; the result's ``active`` says whether it holds."""
    if platform == "win32":
        try:
            ok = _set_execution_state(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        except (OSError, AttributeError):
            return KeepAwake()
        return KeepAwake(active=True, windows=True) if ok else KeepAwake()
    if platform == "darwin":
        return _start_holder(["caffeinate", "-i", "-w", str(os.getpid())], False)
    if platform.startswith("linux") and shutil.which("systemd-inhibit"):
        cmd = ["systemd-inhibit", "--what=sleep", "--mode=block"]
        return _start_holder([*cmd, "sleep", "infinity"], True)
    return KeepAwake()
