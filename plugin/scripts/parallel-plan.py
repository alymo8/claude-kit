#!/usr/bin/env python3
"""Group a plan's tasks into waves that can run concurrently.

    python parallel-plan.py waves PLAN.md [--max N]
    python parallel-plan.py specs SPEC.md [SPEC.md ...] [--max N]

Prints one JSON object, ``{"waves": [[1, 2], [3]]}``: task numbers per wave,
in order. A task's paths are the backticked paths in the Create/Modify/Test
bullets of its ``**Files:**`` block. Its dependencies are its
``**Depends on:**`` line (``none`` or ``Task N`` items), or every earlier task
when the line is missing, plus every earlier task whose paths overlap its own.
A task goes into the first wave after its dependencies' waves that holds fewer
than ``--max`` (default 3) tasks.

``specs`` groups specs by the paths in their Scope section before
the Out label (``docs/superpowers/README.md`` excluded; ADR files with the same
number overlap) and prints ``{"waves": [...], "overlaps": [[earlier, later,
[paths]], ...]}``.

A path is a backticked span that, without a ``:LINE`` or ``:LINE-LINE``
suffix, has no whitespace, none of ``< > * $ { ://``, does not start with
``-`` or ``~``, and has a file suffix (its last part starts with ``.`` or has
``.`` then a letter) or ends with ``/``. Two paths overlap when equal or when
one ends with ``/`` and the other starts with it.

Exits 0 on success, 1 on an invalid ``**Depends on:**`` line (one stderr line
per problem), 2 on bad usage or an unreadable file.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path


def _load_spec_lint():
    path = Path(__file__).resolve().parent / "spec-lint.py"
    spec = importlib.util.spec_from_file_location("spec_lint_for_parallel", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sl = _load_spec_lint()

BULLET_RE = re.compile(r"^\s*- (Create|Modify|Test):(.*)$")
LINE_SUFFIX_RE = re.compile(r":\d+(-\d+)?$")
SUFFIX_RE = re.compile(r"\.[A-Za-z]")
NOT_A_PATH = ("<", ">", "*", "$", "{", "://")
SPEC_INDEX = "docs/superpowers/README.md"
ADR_RE = re.compile(r"^knowledge/decisions/(\d{4})(?!\d)")


def as_path(span: str) -> str | None:
    """The span as a path, or None when it is not one."""
    span = LINE_SUFFIX_RE.sub("", span.split("::", 1)[0])  # pytest node ids
    if not span or any(ch.isspace() for ch in span):
        return None
    if any(bad in span for bad in NOT_A_PATH) or span.startswith(("-", "~")):
        return None
    if span.endswith("/"):
        return span
    name = span.rsplit("/", 1)[-1]
    return span if name.startswith(".") or SUFFIX_RE.search(name) else None


def overlaps(a: str, b: str) -> bool:
    """Equal paths, or a directory path and a path under it."""
    if a == b:
        return True
    return (a.endswith("/") and b.startswith(a)) or (
        b.endswith("/") and a.startswith(b)
    )


def any_overlap(left, right) -> bool:
    return any(overlaps(a, b) for a in left for b in right)


def task_paths(body) -> set[str]:
    """Paths in the Create/Modify/Test bullets of a task's Files block."""
    out: set[str] = set()
    in_files = in_bullet = False
    for _, line, code in body:
        if code:
            in_files = in_bullet = False
            continue
        if sl.FILES_RE.match(line):
            in_files, in_bullet = True, False
            continue
        match = BULLET_RE.match(line) if in_files else None
        if match:
            text, in_bullet = match.group(2), True
        elif in_bullet and line.startswith((" ", "\t")) and line.strip():
            text = line  # a wrapped bullet's continuation line
        else:
            if line.strip() and not line.startswith((" ", "\t")):
                in_files = False
            in_bullet = False
            continue
        for span in sl.SPAN_RE.findall(text):
            path = as_path(span)
            if path:
                out.add(path)
    return out


def plan_waves(text: str, max_size: int) -> tuple[list[list[int]], list[str]]:
    """(waves, problems) for a plan's text; waves is empty when problems exist."""
    tasks = sorted(sl.task_spans(sl.parse(text)), key=lambda t: t[1])
    problems = [message for _, _, message in sl.depends_problems(tasks)]
    if problems:
        return [], problems
    numbers = [task for _, task, _ in tasks]
    paths = {task: task_paths(body) for _, task, body in tasks}
    wave_of: dict[int, int] = {}
    waves: list[list[int]] = []
    for _, task, body in tasks:
        found = sl.task_depends(body)
        if found:
            deps = set(sl.depends_value(found[0][1]))
        else:
            deps = {n for n in numbers if n < task}
        deps |= {n for n in numbers if n < task and any_overlap(paths[n], paths[task])}
        wave = max((wave_of[d] + 1 for d in deps if d in wave_of), default=0)
        while wave < len(waves) and len(waves[wave]) >= max_size:
            wave += 1
        if wave == len(waves):
            waves.append([])
        waves[wave].append(task)
        wave_of[task] = wave
    return waves, []


def spec_paths(text: str) -> set[str]:
    """Paths in a spec's Scope section before its Out label, minus the index."""
    secs = sl.sections(sl.parse(text))
    out: set[str] = set()
    for _, line in sl.in_scope(secs):
        for span in sl.SPAN_RE.findall(line):
            path = as_path(span)
            if path and path != SPEC_INDEX:
                out.add(path)
    return out


def shared_paths(left: set[str], right: set[str]) -> list[str]:
    """Sorted paths of ``left`` that overlap ``right`` (same ADR number too)."""
    found = set()
    for a in left:
        for b in right:
            same_adr = ADR_RE.match(a) and ADR_RE.match(b)
            if overlaps(a, b) or (
                same_adr and ADR_RE.match(a).group(1) == ADR_RE.match(b).group(1)
            ):
                found.add(a)
    return sorted(found)


def plan_specs(
    named: list[tuple[str, str]], max_size: int
) -> tuple[list[list[str]], list[list]]:
    """(waves, overlaps) for (name, text) pairs, in argument order."""
    paths = [spec_paths(text) for _, text in named]
    wave_of: list[int] = []
    waves: list[list[str]] = []
    found: list[list] = []
    for j, (name, _) in enumerate(named):
        deps = []
        for i in range(j):
            shared = shared_paths(paths[i], paths[j])
            if shared:
                found.append([i, j, shared])
                deps.append(i)
        wave = max((wave_of[i] + 1 for i in deps), default=0)
        while wave < len(waves) and len(waves[wave]) >= max_size:
            wave += 1
        if wave == len(waves):
            waves.append([])
        waves[wave].append(name)
        wave_of.append(wave)
    found.sort(key=lambda entry: (entry[0], entry[1]))
    overlaps_out = [[named[i][0], named[j][0], shared] for i, j, shared in found]
    return waves, overlaps_out


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="parallel-plan.py")
    commands = parser.add_subparsers(dest="command", required=True)
    waves_cmd = commands.add_parser("waves")
    waves_cmd.add_argument("plan")
    waves_cmd.add_argument("--max", type=int, default=3)
    specs_cmd = commands.add_parser("specs")
    specs_cmd.add_argument("specs", nargs="+")
    specs_cmd.add_argument("--max", type=int, default=3)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.max < 1:
        print("parallel-plan: --max must be at least 1", file=sys.stderr)
        return 2
    if args.command == "specs":
        named = []
        for name in args.specs:
            try:
                named.append((name, Path(name).read_text(encoding="utf-8-sig")))
            except (OSError, UnicodeDecodeError) as exc:
                print(f"parallel-plan: cannot read {name}: {exc}", file=sys.stderr)
                return 2
        waves, found = plan_specs(named, args.max)
        print(json.dumps({"waves": waves, "overlaps": found}))
        return 0
    try:
        text = Path(args.plan).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"parallel-plan: cannot read {args.plan}: {exc}", file=sys.stderr)
        return 2
    waves, problems = plan_waves(text, args.max)
    for problem in problems:
        print(f"{args.plan}: {problem}", file=sys.stderr)
    if problems:
        return 1
    print(json.dumps({"waves": waves}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
