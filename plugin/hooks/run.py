#!/usr/bin/env python3
"""Run the kit's hooks for a non-Claude agent (Mistral Vibe, Codex, Cursor).

Usage: run.py --agent {vibe,codex,cursor} --event {SessionStart,Stop}

Reads plugin/hooks/hooks.json, the one list of hooks, and runs every command
registered for the event in file order, except the Claude-only ones. Each
script gets the agent's event normalised to the Claude shape on stdin,
CLAUDE_PROJECT_DIR set to the project directory and CLAUDE_KIT_AGENT set to
the agent name. At SessionStart the tool mapping (references/agent-tools.md)
and the project's CLAUDE.md (when it has no AGENTS.md) come first. The joined
context is printed in the agent's JSON shape; nothing collected prints nothing.

Spec: docs/superpowers/specs/2026-11-18-agent-agnostic-kit-design.md (ADR 0050).
Claude never calls this file: it keeps its own hooks.json. Always exits 0 and
prints errors to stderr prefixed [claude-kit] (ADR 0007).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
TOOLS = "references/agent-tools.md"
CLAUDE_ONLY = frozenset(
    {"context_nudge.py", "handoff_snapshot.py", "precompact_keep.py", "on_spec_edit.py"}
)
TIMEOUT = 10
AGENTS = ("vibe", "codex", "cursor")
EVENTS = ("SessionStart", "Stop")


def normalise(raw: str, event: str) -> dict:
    """The agent's stdin event in the Claude shape the scripts read."""
    try:
        data = json.loads(raw) if raw.strip() else {}
    except ValueError:
        data = {}
    if not isinstance(data, dict):
        data = {}
    cwd = data.get("cwd")
    path = Path(cwd).resolve() if isinstance(cwd, str) and cwd else Path.cwd()
    source = data.get("source")
    if not isinstance(source, str) or not source:
        source = "startup"
    return {"cwd": str(path), "source": source, "hook_event_name": event}


def project_dir(cwd: Path) -> Path:
    """The git top level of cwd, else cwd itself."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except (OSError, subprocess.SubprocessError):
        return cwd
    top = result.stdout.strip()
    if result.returncode != 0 or not top:
        return cwd
    return Path(top).resolve()


def commands(
    hooks: dict, event: str, source: str, plugin: Path, project: Path
) -> list[list[str]]:
    """The argv of each portable command registered for event, in file order."""
    out: list[list[str]] = []
    for grp in hooks.get("hooks", {}).get(event, []):
        matcher = grp.get("matcher")
        if matcher and not re.fullmatch(matcher, source):
            continue
        for hook in grp.get("hooks", []):
            command = hook.get("command")
            if not isinstance(command, str):
                continue
            tokens = shlex.split(command)
            if not tokens:
                continue
            if any(Path(t).name in CLAUDE_ONLY for t in tokens):
                continue
            tokens = [
                t.replace("${CLAUDE_PLUGIN_ROOT}", plugin.as_posix()).replace(
                    "${CLAUDE_PROJECT_DIR}", project.as_posix()
                )
                for t in tokens
            ]
            if tokens[0] in ("python", "python3"):
                tokens[0] = sys.executable
            out.append(tokens)
    return out


def script_name(argv: list[str]) -> str:
    """The script a command runs, for error messages."""
    for token in argv[1:]:
        if token.endswith(".py"):
            return Path(token).name
    return Path(argv[0]).name if argv else "?"


def contribution(stdout: str) -> str:
    """A script's context: hookSpecificOutput.additionalContext, else its text."""
    try:
        data = json.loads(stdout)
    except ValueError:
        return stdout.strip()
    if isinstance(data, dict):
        specific = data.get("hookSpecificOutput")
        if isinstance(specific, dict):
            text = specific.get("additionalContext")
            if isinstance(text, str):
                return text
    return stdout.strip()


def run_one(
    argv: list[str],
    stdin: str,
    env: dict[str, str],
    cwd: Path,
    timeout: float = TIMEOUT,
) -> str:
    """Run one command; its contribution, or "" (with a stderr line) on failure."""
    name = script_name(argv)
    try:
        result = subprocess.run(
            argv,
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=str(cwd),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        print(f"[claude-kit] run.py: {name} timed out", file=sys.stderr)
        return ""
    except OSError as exc:
        print(f"[claude-kit] run.py: {name} {exc}", file=sys.stderr)
        return ""
    if result.returncode != 0:
        reason = f"exited {result.returncode}"
        print(f"[claude-kit] run.py: {name} {reason}", file=sys.stderr)
        return ""
    return contribution(result.stdout)


def tool_mapping(plugin: Path) -> str:
    """The tool mapping with <plugin> replaced by the real plugin path."""
    text = (plugin / TOOLS).read_text(encoding="utf-8")
    return text.replace("<plugin>", plugin.as_posix()).strip()


def project_instructions(project: Path) -> str:
    """The project's CLAUDE.md when it has no AGENTS.md, @imports expanded once."""
    claude_md = project / "CLAUDE.md"
    if (project / "AGENTS.md").exists() or not claude_md.is_file():
        return ""
    lines = []
    for line in claude_md.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("@") and len(stripped) > 1:
            target = project / stripped[1:]
            if target.is_file():
                lines.append(target.read_text(encoding="utf-8").rstrip("\n"))
                continue
        lines.append(line)
    header = (
        f"Project instructions (from {project.as_posix()}/CLAUDE.md; this repo "
        "has no AGENTS.md, so your agent did not load them). Follow them as you "
        "would an AGENTS.md."
    )
    return header + "\n\n" + "\n".join(lines).strip()


def optional(piece, *args) -> str:
    """piece(*args), or "" with a stderr note when it fails."""
    try:
        return piece(*args)
    except (OSError, ValueError) as exc:
        print(f"[claude-kit] run.py: {piece.__name__} skipped: {exc}", file=sys.stderr)
        return ""


def render(agent: str, event: str, text: str) -> str:
    """The context in the agent's hook output shape."""
    if agent == "vibe":
        data: dict = {"hook_specific_output": {"additional_context": text}}
    elif agent == "codex":
        data = {
            "hookSpecificOutput": {"hookEventName": event, "additionalContext": text}
        }
    else:
        data = {"additional_context": text}
    return json.dumps(data)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
        parser.add_argument("--agent", required=True, choices=AGENTS)
        parser.add_argument("--event", required=True, choices=EVENTS)
        args = parser.parse_args(argv)
        event = normalise(sys.stdin.read(), args.event)
        cwd = Path(event["cwd"])
        project = project_dir(cwd)
        hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text("utf-8"))
        env = dict(os.environ)
        env["CLAUDE_PROJECT_DIR"] = str(project)
        env["CLAUDE_KIT_AGENT"] = args.agent
        pieces: list[str] = []
        if args.event == "SessionStart":
            pieces.append(optional(tool_mapping, PLUGIN))
            pieces.append(optional(project_instructions, project))
        stdin = json.dumps(event)
        for command in commands(hooks, args.event, event["source"], PLUGIN, project):
            pieces.append(run_one(command, stdin, env, cwd))
        text = "\n\n".join(p for p in pieces if p)
        if text:
            print(render(args.agent, args.event, text))
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - never fail the session
        print(f"[claude-kit] run.py error: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
