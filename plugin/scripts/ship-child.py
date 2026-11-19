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

import argparse
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
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


def _now() -> datetime:
    return datetime.now(UTC)


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the child and everything it started."""
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        proc.wait(10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def run_attempt(
    claude: str, rel: str, cwd: Path, out: Path, err: Path, timeout: float
) -> dict:
    """Run one child; return its status entry."""
    cmd = [claude, "-p", f"/claude-kit:ship {rel}"]
    cmd += ["--permission-mode", "auto", "--permission-prompts", "none"]
    cmd += ["--output-format", "json"]
    env = {**os.environ, "CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS": "0"}
    if sys.platform == "win32":
        group = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    else:
        group = {"start_new_session": True}
    start = _now()
    timed_out = False
    with out.open("wb") as fout, err.open("wb") as ferr:
        proc = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=fout,
            stderr=ferr,
            **group,
        )
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            proc.wait()
            code, timed_out = 124, True
    return {
        "cwd": str(cwd),
        "start": start.isoformat(timespec="seconds"),
        "end": _now().isoformat(timespec="seconds"),
        "exit": code,
        "timed_out": timed_out,
        "cost": read_cost(out),
        "_start": start,
    }


def merged_since(gh: str, main: Path, branch: str, since: datetime) -> bool | None:
    """True if a PR from branch merged after since; None when gh fails."""
    cmd = [gh, "pr", "list", "--head", branch, "--state", "merged"]
    cmd += ["--json", "number,createdAt"]
    try:
        res = subprocess.run(
            cmd,
            cwd=main,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except OSError:
        return None
    if res.returncode != 0:
        return None
    try:
        prs = json.loads(res.stdout)
    except ValueError:
        return None
    if not isinstance(prs, list) or not all(isinstance(p, dict) for p in prs):
        return None
    for pr in prs:
        created = pr.get("createdAt")
        if not isinstance(created, str):
            continue
        try:
            when = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            continue
        if when > since:
            return True
    return False


def _worktrees(git: str, main: Path) -> str:
    res = subprocess.run(
        [git, "-C", str(main), "worktree", "list", "--porcelain"],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return res.stdout or ""


def decide_resume(
    first: dict, merged: bool | None, before: str, now: str, args, slug: str
) -> tuple[str, Path | None]:
    """Return (resume reason, directory to resume in or None)."""
    branch = f"feat/{slug}"
    if first["timed_out"]:
        return "timed out", None
    if merged is None:
        return "gh failed", None
    if merged:
        return "merged", None
    if worktree_on(before, branch) is not None:
        return "no worktree", None
    worktree = worktree_on(now, branch)
    if worktree is not None:
        if stop_rule_handoff(worktree, slug):
            return "stop rule", None
        return "resumed", worktree
    if (args.main / args.spec).is_file():
        return "resumed", args.main
    return "no worktree", None


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run one /ship-many child.")
    p.add_argument("--spec", required=True)
    p.add_argument("--main", required=True, type=Path)
    p.add_argument("--log", required=True, type=Path)
    p.add_argument("--name", required=True)
    p.add_argument("--timeout", type=float, default=7200)
    p.add_argument("--resume-wait", type=float, default=60)
    p.add_argument("--claude", default="claude")
    p.add_argument("--gh", default="gh")
    p.add_argument("--git", default="git")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        args = _parse(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2
    exes = {}
    for key in ("claude", "gh", "git"):
        name = getattr(args, key)
        found = shutil.which(name)
        if found is None:
            print(f"ship-child.py: executable not found: {name}", file=sys.stderr)
            return 2
        exes[key] = found
    if not args.main.is_dir():
        print(f"ship-child.py: --main is not a directory: {args.main}", file=sys.stderr)
        return 2
    args.log.mkdir(parents=True, exist_ok=True)
    slug = branch_slug(args.spec)
    log = args.log
    awake = keep_awake(sys.platform)
    try:
        before = _worktrees(exes["git"], args.main)
        first = run_attempt(
            exes["claude"],
            args.spec,
            args.main,
            log / f"{args.name}.json",
            log / f"{args.name}.err",
            args.timeout,
        )
        attempts = [first]
        merged = None
        if not first["timed_out"]:
            merged = merged_since(
                exes["gh"], args.main, f"feat/{slug}", first["_start"]
            )
        now = _worktrees(exes["git"], args.main)
        resume, where = decide_resume(first, merged, before, now, args, slug)
        if where is not None:
            time.sleep(args.resume_wait)
            attempts.append(
                run_attempt(
                    exes["claude"],
                    args.spec,
                    where,
                    log / f"{args.name}.resume.json",
                    log / f"{args.name}.resume.err",
                    args.timeout,
                )
            )
        for a in attempts:
            a.pop("_start", None)
        costs = [a["cost"] for a in attempts if a["cost"] is not None]
        last = attempts[-1]
        status = {
            "spec": args.spec,
            "branch": f"feat/{slug}",
            "keep_awake": bool(awake.active),
            "attempts": attempts,
            "resume": resume,
            "timed_out": last["timed_out"],
            "exit": last["exit"],
            "cost": round(sum(costs), 6) if costs else None,
        }
        path = log / f"{args.name}.status.json"
        path.write_text(json.dumps(status, indent=2), encoding="utf-8")
        return last["exit"]
    finally:
        awake.release()


if __name__ == "__main__":
    sys.exit(main())
