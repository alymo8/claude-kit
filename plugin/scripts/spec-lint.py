#!/usr/bin/env python3
"""Lint a spec, hash it, or verify its gate record.

    python spec-lint.py SPEC.md [--root DIR]            # lint
    python spec-lint.py --hash SPEC.md                  # print the spec hash
    python spec-lint.py --verify-record SPEC.md [--root DIR]

Lint prints one ``SPEC:LINE: RULE message`` line per violation, then a summary.
Rules (text in fenced code blocks is ignored by all of them):

- L1-status: a ``- **Status:**`` bullet: draft, approved, implemented, superseded.
- L2-date: a ``- **Date:** YYYY-MM-DD`` bullet.
- L3-section: H2 sections Purpose, Scope, Design (or Structure), Decisions,
  Success criteria (case-insensitive prefix match).
- L4-out-of-scope: an ``**Out:**`` label (``**Out (later):**`` too) in Scope,
  or an ``## Out of scope`` section, followed by at least one list item.
- L5-placeholder: no TBD, TODO, FIXME, ??? or "as discussed" outside backticks
  and double quotes; no "etc." outside them in Scope or Success criteria.
- L6-empty: no heading followed by a same-or-higher-level heading (or the end of
  the file) with nothing in between.
- L7-criterion: each top-level list item under Success criteria has a backticked
  span or a verification word (test, pytest, run, command, exit, output, prints,
  returns, asserts, manual, verify, check).
- L8-path: each backticked repo path in Scope, before its Out label (the files
  the spec changes), exists under the root, unless a line of the spec has both
  that path and "(new)". Paths elsewhere may belong to another folder or repo;
  the reviewer checks those.

--hash prints the SHA-256 of the spec with line endings normalised and its
first Status bullet removed, so approving a spec keeps the same hash.
--verify-record checks docs/superpowers/gates/<spec file name> under the root:
it must exist, say ``- **Verdict:** pass`` and carry the current hash in
``- **Spec SHA-256:**``. Prints ok/missing/not passed/stale; exits 0 only for ok.

The root defaults to ``git rev-parse --show-toplevel`` from the spec's folder,
else the folder three levels above it (the parent of ``docs/``). Exits 0 when
clean, 1 on violations, 2 on bad usage or an unreadable file.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

STATUSES = ("draft", "approved", "implemented", "superseded")
REQUIRED = (
    ("Purpose", ("purpose",)),
    ("Scope", ("scope",)),
    ("Design", ("design", "structure")),
    ("Decisions", ("decisions",)),
    ("Success criteria", ("success criteria",)),
)
VERIFY_WORDS = (
    "test pytest run command exit output prints returns asserts manual verify check"
)

STATUS_RE = re.compile(r"^- \*\*Status:\*\*\s*(.*?)\s*$")
DATE_RE = re.compile(r"^- \*\*Date:\*\*\s*(.*?)\s*$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
SPAN_RE = re.compile(r"`([^`\n]+)`")
QUOTED_RE = re.compile(r"\"[^\"\n]*\"|“[^”\n]*”")
OUT_RE = re.compile(r"\*\*Out\b[^*\n]*:\*\*")
PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME)\b|\?\?\?|\bas discussed\b", re.I)
ETC_RE = re.compile(r"\betc\.", re.I)
ITEM_RE = re.compile(r"^(?:[-*]|\d+\.)\s+")
VERIFY_RE = re.compile(r"\b(" + "|".join(VERIFY_WORDS.split()) + r")\b", re.I)
LINE_SUFFIX_RE = re.compile(r":\d+(-\d+)?$")
NOT_A_PATH = ("<", ">", "*", "$", "{", "://")
GATES = Path("docs") / "superpowers" / "gates"
VERDICT_PASS_RE = re.compile(r"^- \*\*Verdict:\*\*\s*pass\s*$", re.M)
RECORD_HASH_RE = re.compile(r"^- \*\*Spec SHA-256:\*\*\s*([0-9a-f]{64})\s*$", re.M)

Line = tuple[int, str, bool]  # (line number, text, inside a code fence)


def parse(text: str) -> list[Line]:
    """Split text into numbered lines, flagging fenced code (fence lines too)."""
    out: list[Line] = []
    fence = None
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE_RE.match(line)
        if match:
            if fence is None:
                fence = match.group(1)
            elif match.group(1) == fence:
                fence = None
            out.append((number, line, True))
            continue
        out.append((number, line, fence is not None))
    return out


def headings(lines: list[Line]) -> list[tuple[int, int, str]]:
    """(line number, level, title) for every heading outside code fences."""
    found = []
    for number, line, code in lines:
        match = None if code else HEADING_RE.match(line)
        if match:
            found.append((number, len(match.group(1)), match.group(2)))
    return found


def sections(lines: list[Line]) -> dict[str, tuple[int, list[Line]]]:
    """H2 title -> (heading line, lines up to the next H1 or H2)."""
    out: dict[str, tuple[int, list[Line]]] = {}
    current = None
    for entry in lines:
        number, line, code = entry
        match = None if code else HEADING_RE.match(line)
        if match and len(match.group(1)) <= 2:
            current = match.group(2) if len(match.group(1)) == 2 else None
            if current is not None and current not in out:
                out[current] = (number, [])
            continue
        if current is not None:
            out[current][1].append(entry)
    return out


def find(secs: dict, prefixes: tuple[str, ...]) -> tuple[int, list[Line]] | None:
    for title, body in secs.items():
        if title.lower().startswith(prefixes):
            return body
    return None


def strip_spans(line: str) -> str:
    """The line without backticked spans and double-quoted text."""
    return QUOTED_RE.sub("", SPAN_RE.sub("", line))


def check_status_date(lines: list[Line]) -> list[tuple[int, str, str]]:
    out = []
    status = [(n, STATUS_RE.match(t)) for n, t, c in lines if not c]
    status = [(n, m) for n, m in status if m]
    if not status:
        out.append((1, "L1-status", "missing '- **Status:**' bullet"))
    else:
        number, match = status[0]
        word = match.group(1).split(" ")[0].strip("*").lower()
        if word not in STATUSES:
            out.append((number, "L1-status", f"invalid Status {match.group(1)!r}"))
    date = [(n, DATE_RE.match(t)) for n, t, c in lines if not c]
    date = [(n, m) for n, m in date if m]
    if not date:
        out.append((1, "L2-date", "missing '- **Date:**' bullet"))
    elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date[0][1].group(1)):
        out.append((date[0][0], "L2-date", "Date is not YYYY-MM-DD"))
    return out


def check_sections(secs: dict) -> list[tuple[int, str, str]]:
    out = []
    for name, prefixes in REQUIRED:
        if find(secs, prefixes) is None:
            out.append((1, "L3-section", f"missing section '## {name}'"))
    return out


def has_item_after(body: list[Line]) -> bool:
    """Whether an ``**Out...:**`` label in the body is followed by a list item."""
    seen = False
    for _, line, code in body:
        if code:
            continue
        if OUT_RE.search(line):
            seen = True
        elif seen and ITEM_RE.match(line.strip()):
            return True
    return False


def check_out_of_scope(secs: dict) -> list[tuple[int, str, str]]:
    separate = find(secs, ("out of scope",))
    if separate and any(ITEM_RE.match(t.strip()) for _, t, c in separate[1] if not c):
        return []
    scope = find(secs, ("scope",))
    if scope is None:
        return []  # already reported by L3
    if has_item_after(scope[1]):
        return []
    return [(scope[0], "L4-out-of-scope", "no '**Out:**' list in Scope")]


def check_placeholders(lines: list[Line], secs: dict) -> list[tuple[int, str, str]]:
    out = []
    for number, line, code in lines:
        if code:
            continue
        match = PLACEHOLDER_RE.search(strip_spans(line))
        if match:
            out.append((number, "L5-placeholder", f"placeholder {match.group(0)!r}"))
    for prefixes in (("scope",), ("success criteria",)):
        body = find(secs, prefixes)
        for number, line, code in body[1] if body else []:
            if not code and ETC_RE.search(strip_spans(line)):
                out.append((number, "L5-placeholder", "'etc.' in a requirement"))
    return out


def check_empty(lines: list[Line]) -> list[tuple[int, str, str]]:
    heads = headings(lines)
    head_lines = {number for number, _, _ in heads}
    out = []
    for index, (number, level, title) in enumerate(heads):
        nxt = heads[index + 1] if index + 1 < len(heads) else None
        end = nxt[0] if nxt else len(lines) + 1
        content = any(
            line.strip() and n not in head_lines
            for n, line, _ in lines
            if number < n < end
        )
        if not content and (nxt is None or nxt[1] <= level):
            out.append((number, "L6-empty", f"empty section {title!r}"))
    return out


def check_criteria(secs: dict) -> list[tuple[int, str, str]]:
    body = find(secs, ("success criteria",))
    if body is None:
        return []
    items: list[tuple[int, list[str]]] = []
    for number, line, code in body[1]:
        if not code and ITEM_RE.match(line):
            items.append((number, [line]))
        elif items:
            items[-1][1].append(line)
    out = []
    for number, text in items:
        joined = "\n".join(text)
        if not SPAN_RE.search(joined) and not VERIFY_RE.search(joined):
            out.append((number, "L7-criterion", "criterion names no verification"))
    return out


def looks_like_path(span: str) -> bool:
    if "/" not in span or any(ch.isspace() for ch in span):
        return False
    if any(bad in span for bad in NOT_A_PATH) or span.startswith(("-", "~")):
        return False
    return bool(Path(span).suffix) or span.endswith("/")


def in_scope(secs: dict) -> list[tuple[int, str]]:
    """Prose lines of the Scope section before its ``**Out...:**`` label."""
    scope = find(secs, ("scope",))
    out = []
    for number, line, code in scope[1] if scope else []:
        if not code and OUT_RE.search(line):
            break
        if not code:
            out.append((number, line))
    return out


def check_paths(
    lines: list[Line], secs: dict, root: Path
) -> list[tuple[int, str, str]]:
    prose = [(n, t) for n, t, c in lines if not c]
    new = {s for _, t in prose if "(new)" in t for s in SPAN_RE.findall(t)}
    out = []
    for number, line in in_scope(secs):
        for span in SPAN_RE.findall(line):
            if not looks_like_path(span) or span in new:
                continue
            path = LINE_SUFFIX_RE.sub("", span)
            if not (root / path).exists():
                out.append((number, "L8-path", f"path not found: {span}"))
    return out


def lint(text: str, root: Path) -> list[tuple[int, str, str]]:
    """All violations in a spec, as (line, rule, message), sorted by line."""
    lines = parse(text)
    secs = sections(lines)
    found = (
        check_status_date(lines)
        + check_sections(secs)
        + check_out_of_scope(secs)
        + check_placeholders(lines, secs)
        + check_empty(lines)
        + check_criteria(secs)
        + check_paths(lines, secs, root)
    )
    return sorted(found, key=lambda v: (v[0], v[1]))


def spec_hash(text: str) -> str:
    """SHA-256 of the spec without its Status line, line endings normalised."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    kept, dropped = [], False
    for _, line, code in parse(text):
        if not dropped and not code and STATUS_RE.match(line):
            dropped = True
            continue
        kept.append(line)
    return hashlib.sha256("\n".join(kept).encode("utf-8")).hexdigest()


def verify_record(spec: Path, root: Path) -> tuple[bool, str]:
    """Whether the spec's gate record exists, passed, and matches its hash."""
    record = root / GATES / spec.name
    if not record.is_file():
        return False, f"missing: {record}"
    body = record.read_text(encoding="utf-8-sig")
    if not VERDICT_PASS_RE.search(body):
        return False, f"not passed: {record}"
    match = RECORD_HASH_RE.search(body)
    text = read(spec)
    if not match or text is None or match.group(1) != spec_hash(text):
        return False, f"stale: {record}"
    return True, f"ok: {record}"


def default_root(spec: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=spec.resolve().parent,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return Path(result.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    parents = spec.resolve().parents
    return parents[3] if len(parents) > 3 else spec.resolve().parent


def read(spec: Path) -> str | None:
    try:
        return spec.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        print(f"spec-lint: cannot read {spec}: {exc}", file=sys.stderr)
        return None


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="spec-lint.py")
    parser.add_argument("spec")
    parser.add_argument("--root")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--hash", action="store_true")
    mode.add_argument("--verify-record", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    spec = Path(args.spec)
    text = read(spec)
    if text is None:
        return 2
    if args.hash:
        print(spec_hash(text))
        return 0
    root = Path(args.root) if args.root else default_root(spec)
    if args.verify_record:
        valid, message = verify_record(spec, root)
        print(message)
        return 0 if valid else 1
    found = lint(text, root)
    for number, rule, message in found:
        print(f"{args.spec}:{number}: {rule} {message}")
    print(f"{len(found)} violation(s)" if found else "clean")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
