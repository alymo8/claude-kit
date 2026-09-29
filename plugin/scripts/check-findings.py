#!/usr/bin/env python3
"""Check audit findings: each one cites a real ``path:line`` and quotes it.

    python check-findings.py REPO_ROOT REPORT [REPORT ...]

REPORT is a Markdown file, a directory (every ``*.md`` in it) or a glob; a
relative REPORT is tried from REPO_ROOT, then from the working directory.
A finding is a ``### [SEVERITY] Title`` block with Where, Evidence,
Confidence, Impact and Fix bullets, as defined in
``plugin/skills/audit/rules.md``. Blocks inside code fences are ignored.

Evidence ``(absent)`` (something that should exist) and ``(history <sha>)``
(found only in git history) skip the file checks. Otherwise the Where path
must exist under REPO_ROOT, the line must be inside the file, and the quote
(whitespace-normalised, ``...`` skipping a middle part) must appear within
three lines of the cited line or range.

Prints one line per rejected finding and a summary. Exits 0 when every
finding passes, 1 when any is rejected, 2 on bad usage.
"""

from __future__ import annotations

import glob
import re
import sys
from pathlib import Path

SEVERITIES = ("Critical", "High", "Medium", "Low")
FIELDS = ("Where", "Evidence", "Confidence", "Impact", "Fix")
ABSENT = "(absent)"
WINDOW = 3  # lines either side of the cited line that may hold the quote

FINDING_RE = re.compile(r"^###\s+\[([^\]]+)\]\s*(.*?)\s*$")
BOUNDARY_RE = re.compile(r"^#{1,3}\s")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
FIELD_RE = re.compile(r"^\s*[-*]\s+\*\*([A-Za-z]+):\*\*\s*(.*?)\s*$")
HISTORY_RE = re.compile(r"^\(history [0-9a-fA-F]{7,40}\)$")
TICKED_WHERE_RE = re.compile(r"`([^`]+?):(\d+)(?:-(\d+))?`")
BARE_WHERE_RE = re.compile(r"^(\S+?):(\d+)(?:-(\d+))?(?:\s|$)")
ELLIPSIS_RE = re.compile(r"\.\.\.|…")


def norm(text: str) -> str:
    return " ".join(text.split())


def quote(evidence: str) -> str:
    """The quoted text of an Evidence value: its first backtick span, else the
    value without surrounding double quotes."""
    ev = evidence.strip()
    ticks = len(ev) - len(ev.lstrip("`"))
    if ticks:
        close = ev.find("`" * ticks, ticks)
        if close != -1:
            return ev[ticks:close].strip()
    return ev.strip('"').strip()


def blocks(text: str) -> list[tuple[str, str, list[str]]]:
    """(severity, title, body lines) for every finding outside code fences."""
    found: list[tuple[str, str, list[str]]] = []
    current: tuple[str, str, list[str]] | None = None
    in_fence = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            in_fence = not in_fence
        elif not in_fence and BOUNDARY_RE.match(line):
            m = FINDING_RE.match(line)
            current = (m.group(1), m.group(2), []) if m else None
            if current is not None:
                found.append(current)
            continue
        if current is not None:
            current[2].append(line)
    return found


def fields(body: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in body:
        m = FIELD_RE.match(line)
        if m and m.group(1) in FIELDS and m.group(1) not in out:
            out[m.group(1)] = m.group(2)
    return out


def contains(lines: list[str], start: int, end: int, text: str) -> bool:
    window = norm(" ".join(lines[max(0, start - 1 - WINDOW) : end + WINDOW]))
    pos = 0
    for part in ELLIPSIS_RE.split(text):
        part = norm(part)
        if not part:
            continue
        at = window.find(part, pos)
        if at == -1:
            return False
        pos = at + len(part)
    return True


def check_finding(severity: str, body: list[str], root: Path) -> str | None:
    """Why this finding is rejected, or None when it passes."""
    if severity.strip().capitalize() not in SEVERITIES:
        return f"severity {severity!r} is not one of {', '.join(SEVERITIES)}"
    f = fields(body)
    missing = [key for key in FIELDS if not f.get(key)]
    if missing:
        return "missing " + ", ".join(missing)
    confidence = f["Confidence"].strip("`*[] ").lower()
    if not confidence.startswith(("verified", "inferred")):
        return f"confidence {f['Confidence']!r} is not verified or inferred"
    text = quote(f["Evidence"])
    if text == ABSENT or HISTORY_RE.match(text):
        return None
    where = f["Where"]
    m = TICKED_WHERE_RE.search(where) or BARE_WHERE_RE.match(where.strip("` "))
    if not m:
        return f"Where {where!r} is not path:line"
    name = m.group(1)
    path = Path(name)
    if not path.is_absolute():
        path = root / path
    if not path.is_file():
        return f"{name} does not exist"
    start = int(m.group(2))
    end = int(m.group(3) or start)
    if start < 1 or end < start:
        return f"line range {m.group(2)}-{end} in {name} is invalid"
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if start > len(lines):
        return f"line {start} is past the end of {name} ({len(lines)} lines)"
    if not norm(ELLIPSIS_RE.sub(" ", text)):
        return "Evidence has no quote"
    if not contains(lines, start, end, text):
        return f"quote not found near {name}:{start}"
    return None


def check_file(md: Path, root: Path) -> tuple[int, list[str]]:
    """(number of findings, one message per rejected finding)."""
    items = blocks(md.read_text(encoding="utf-8", errors="replace"))
    errors = []
    for severity, title, body in items:
        reason = check_finding(severity, body, root)
        if reason:
            errors.append(f'{md.name}: "{title}": {reason}')
    return len(items), errors


def reports(arg: str, root: Path) -> list[Path]:
    """Report files named by a path, directory or glob. A relative one is
    tried from REPO_ROOT first, then from the working directory."""
    given = Path(arg)
    targets = [given] if given.is_absolute() else [root / arg, Path.cwd() / arg]
    for target in targets:
        if any(ch in arg for ch in "*?["):
            hits = sorted(Path(p) for p in glob.glob(str(target)))
            hits = [p for p in hits if p.is_file()]
            if hits:
                return hits
        elif target.is_dir():
            return sorted(target.glob("*.md"))
        elif target.is_file():
            return [target]
    return []


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if len(argv) < 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    root = Path(argv[0])
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2
    total, errors = 0, []
    for arg in argv[1:]:
        found = reports(arg, root)
        if not found:
            print(f"no report found: {arg}", file=sys.stderr)
            return 2
        for md in found:
            count, errs = check_file(md, root)
            total += count
            errors += errs
    for line in errors:
        print(line)
    print(f"{total - len(errors)} of {total} findings pass, {len(errors)} rejected")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
