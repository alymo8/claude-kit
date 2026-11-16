#!/usr/bin/env python3
"""List the raw files of a personal vault that ingest has not processed yet.

Usage: vault-pending.py VAULT [--json]
       vault-pending.py --extract FILE

With ``VAULT``, compare every file under ``VAULT/raw/`` (recursive; any path
with a component starting with ``.`` is skipped) with the ``raw`` and
``sha256`` frontmatter of ``VAULT/wiki/sources/*.md``. Each pending entry has
a status:

- ``new``: no source page names the raw file;
- ``changed``: the raw file's sha256 differs from its source page's;
- ``missing``: a source page names a raw file that no longer exists.

Text output is one ``<status>\\t<raw path>`` line per entry, sorted by path,
with vault-relative posix paths; nothing is printed when nothing is pending.
``--json`` prints a list of objects with ``path``, ``status``, ``source`` (the
source page for ``changed`` and ``missing``, else null) and ``sha256`` (the
raw file's current lowercase hex sha256, null for ``missing``). Entries also
carry ``scanned`` (false for formats the scanner cannot read and for
``missing``) and ``flags`` (``{kind, line, end_line, excerpt}`` entries, at
most 50, then ``{kind: "truncated"}``). A text line for a file with flags ends
in ``\\t<N> flag(s)``.

``--extract FILE`` prints the text of a ``.docx`` file, one line per
non-empty paragraph. It cannot be combined with ``VAULT`` or ``--json``.

Exit codes: 0 success (also when nothing is pending); 1 ``--extract`` on a
file that is not a readable ``.docx``; 2 usage error, or ``VAULT`` has no
``vault.toml`` or it does not parse.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
import tomllib
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

MAX_FLAGS = 50
INSTRUCTION_PHRASES: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore all previous",
    "disregard the above",
    "disregard your instructions",
    "you are claude",
    "you are an ai",
    "as an ai assistant",
    "system prompt",
    "new instructions:",
    "assistant:",
    "<system>",
    "</system>",
)
TEXT_SUFFIXES = {".md", ".txt", ".vtt", ".html"}
HIDDEN_HTML_SUFFIXES = {".md", ".html"}
VOID_ELEMENTS = frozenset(
    "area base br col embed hr img input link meta source track wbr".split()
)
INVISIBLE = frozenset(
    chr(c)
    for c in [
        *range(0x200B, 0x200E),
        0x2060,
        0xFEFF,
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
    ]
)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    body = re.escape(phrase)
    if re.match(r"\w", phrase[0]):
        body = r"\b" + body
    if re.match(r"\w", phrase[-1]):
        body = body + r"\b"
    return re.compile(body, re.IGNORECASE)


INSTRUCTION_PATTERNS = [_phrase_pattern(p) for p in INSTRUCTION_PHRASES] + [
    re.compile(r"(?<![\w.])(?:Bash|WebFetch|Write|Edit)\(|(?<!\w)mcp__")
]
COMMENT_RE = re.compile(r"<!--(.*?)(?:-->|\Z)", re.S)
TAG_RE = re.compile(r"<([A-Za-z][\w-]*)\b([^>]*)>", re.S)
STYLE_RE = re.compile(r"""(?<![\w-])style\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
HIDDEN_STYLE_RE = re.compile(
    r"display:none|visibility:hidden|font-size:0(?![.\d])"
    r"|(?:left|top|text-indent):-\d{4,}"
)


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return value


def read_frontmatter(path: Path) -> dict[str, str]:
    """Return the ``key: value`` pairs of a Markdown file's frontmatter."""
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        key, sep, value = line.partition(":")
        if sep and key.strip():
            result[key.strip()] = _unquote(value)
    return result


def _normalize(rel: str) -> str:
    rel = rel.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    return rel


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pending(vault: Path) -> list[dict[str, object]]:
    """Return the vault's new, changed and missing raw files, sorted by path."""
    mapped: dict[str, tuple[str, str]] = {}
    sources = vault / "wiki" / "sources"
    if sources.is_dir():
        for page in sorted(sources.glob("*.md")):
            meta = read_frontmatter(page)
            rel = _normalize(meta.get("raw", ""))
            if rel and rel not in mapped:
                page_rel = page.relative_to(vault).as_posix()
                mapped[rel] = (page_rel, meta.get("sha256", "").lower())

    entries: list[dict[str, object]] = []
    raw_dir = vault / "raw"
    seen: set[str] = set()
    if raw_dir.is_dir():
        for path in raw_dir.rglob("*"):
            if not path.is_file():
                continue
            if any(part.startswith(".") for part in path.relative_to(raw_dir).parts):
                continue
            rel = path.relative_to(vault).as_posix()
            seen.add(rel)
            digest = _sha256(path)
            if rel not in mapped:
                status, src = "new", None
            elif digest != mapped[rel][1]:
                status, src = "changed", mapped[rel][0]
            else:
                continue
            scanned, flags = scan(path)
            entries.append(
                {
                    "path": rel,
                    "status": status,
                    "source": src,
                    "sha256": digest,
                    "scanned": scanned,
                    "flags": flags,
                }
            )
    for rel, (page_rel, _sha) in mapped.items():
        if rel not in seen and not (vault / rel).is_file():
            entries.append(
                {
                    "path": rel,
                    "status": "missing",
                    "source": page_rel,
                    "sha256": None,
                    "scanned": False,
                    "flags": [],
                }
            )
    entries.sort(key=lambda e: str(e["path"]))
    return entries


def extract_docx(path: Path) -> list[str]:
    """Return the non-empty paragraphs of a ``.docx`` file, in order."""
    try:
        with zipfile.ZipFile(path) as z:
            data = z.read("word/document.xml")
        root = ElementTree.fromstring(data)
    except (zipfile.BadZipFile, KeyError, ElementTree.ParseError, OSError) as exc:
        raise ValueError(f"{path} is not a readable .docx file: {exc}") from exc
    paragraphs = []
    for para in root.iter(f"{W}p"):
        text = "".join(t.text or "" for t in para.iter(f"{W}t"))
        if text.strip():
            paragraphs.append(text)
    return paragraphs


def _read_scan_text(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        try:
            return path.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            return None
    if suffix == ".docx":
        try:
            return "\n".join(extract_docx(path))
        except ValueError:
            return None
    return None


def _excerpt(text: str, index: int) -> str:
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    if end == -1:
        end = len(text)
    line = text[start:end]
    if line.endswith("\r"):
        line = line[:-1]
    col = max(0, index - start - 20)
    chunk = line[col : col + 80]
    return "".join(
        "?" if ch in INVISIBLE or unicodedata.category(ch) == "Cc" else ch
        for ch in chunk
    )


def _hidden_element_end(text: str, name: str, after: int) -> int | None:
    """Return the index of the closing tag that matches an opening tag."""
    pattern = re.compile(
        rf"<(/?){re.escape(name)}(?=[\s/>])([^>]*)>", re.IGNORECASE | re.S
    )
    depth = 1
    for m in pattern.finditer(text, after):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return m.end() - 1
        elif not m.group(2).rstrip().endswith("/"):
            depth += 1
    return None


def scan(path: Path) -> tuple[bool, list[dict]]:
    """Flag hidden HTML, invisible characters and instruction-like text.

    Returns ``(scanned, flags)``; ``scanned`` is False for formats that are not
    scanned and for a ``.docx`` that cannot be read.
    """
    text = _read_scan_text(path)
    if text is None:
        return False, []

    newlines = [m.start() for m in re.finditer("\n", text)]

    def line_of(index: int) -> int:
        return bisect.bisect_left(newlines, index) + 1

    def flag(kind: str, start: int, last: int) -> dict:
        return {
            "kind": kind,
            "line": line_of(start),
            "end_line": line_of(last),
            "excerpt": _excerpt(text, start),
        }

    flags: list[dict] = []

    # instruction: search a whitespace-collapsed copy, mapped back to raw indexes
    chars: list[str] = []
    raw_index: list[int] = []
    for m in re.finditer(r"\s+|\S+", text):
        if m.group().isspace():
            chars.append(" ")
            raw_index.append(m.start())
        else:
            chars.extend(m.group())
            raw_index.extend(range(m.start(), m.end()))
    collapsed = "".join(chars)
    found: dict[tuple[int, int], int] = {}
    for pattern in INSTRUCTION_PATTERNS:
        for m in pattern.finditer(collapsed):
            first = raw_index[m.start()]
            last = raw_index[m.end() - 1]
            span = (line_of(first), line_of(last))
            if span not in found or first < found[span]:
                found[span] = first
    for (line, end_line), first in found.items():
        flags.append(
            {
                "kind": "instruction",
                "line": line,
                "end_line": end_line,
                "excerpt": _excerpt(text, first),
            }
        )

    # hidden-html
    if path.suffix.lower() in HIDDEN_HTML_SUFFIXES:
        for m in COMMENT_RE.finditer(text):
            if sum(ch.isalpha() for ch in m.group(1)) >= 20:
                flags.append(flag("hidden-html", m.start(), max(m.end() - 1, 0)))
        for m in TAG_RE.finditer(text):
            name, attrs = m.group(1), m.group(2)
            style = STYLE_RE.search(attrs)
            if not style:
                continue
            value = "".join((style.group(1) or style.group(2) or "").lower().split())
            if not HIDDEN_STYLE_RE.search(value):
                continue
            tag_end = m.end() - 1
            if attrs.rstrip().endswith("/") or name.lower() in VOID_ELEMENTS:
                end = tag_end
            else:
                end = _hidden_element_end(text, name, m.end())
                if end is None:
                    end = tag_end
            flags.append(flag("hidden-html", m.start(), end))

    # invisible-char: the first one on each line
    seen_lines: set[int] = set()
    for index, ch in enumerate(text):
        if ch in INVISIBLE and not (index == 0 and ch == "\ufeff"):
            line = line_of(index)
            if line not in seen_lines:
                seen_lines.add(line)
                flags.append(flag("invisible-char", index, index))

    flags.sort(key=lambda f: (f["line"], f["end_line"], f["kind"]))
    if len(flags) > MAX_FLAGS:
        flags = flags[:MAX_FLAGS] + [{"kind": "truncated"}]
    return True, flags


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="List a vault's pending raw files, or extract .docx text."
    )
    parser.add_argument("vault", nargs="?", help="the vault folder")
    parser.add_argument("--json", action="store_true", help="print JSON")
    parser.add_argument("--extract", metavar="FILE", help="print a .docx's text")
    args = parser.parse_args(argv)

    if args.extract is not None:
        if args.vault is not None or args.json:
            parser.error("--extract cannot be combined with VAULT or --json")
        try:
            lines = extract_docx(Path(args.extract))
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        for line in lines:
            print(line)
        return 0
    if args.vault is None:
        parser.error("give VAULT or --extract FILE")

    vault = Path(args.vault)
    config = vault / "vault.toml"
    try:
        tomllib.loads(config.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"error: {config} not found; not a vault", file=sys.stderr)
        return 2
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        print(f"error: cannot read {config}: {exc}", file=sys.stderr)
        return 2

    entries = pending(vault)
    if args.json:
        print(json.dumps(entries))
    else:
        for entry in entries:
            line = f"{entry['status']}\t{entry['path']}"
            n = sum(f["kind"] != "truncated" for f in entry["flags"])
            if n >= 1:
                line += f"\t{n} flag(s)"
            print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
