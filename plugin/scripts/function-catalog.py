#!/usr/bin/env python3
"""List the functions of a git repository as JSON, for the duplicate-intent pass.

Usage: function-catalog.py <repo-root> [-o FILE | --split DIR]
       [--batch-size N] [--context N] [--include-tests]

Files come from ``git ls-files``, filtered by extension to the supported
languages. A line that matches a language's function pattern becomes one entry
``{"file", "line", "name", "language", "snippet"}``: ``file`` is the
repo-relative path, ``line`` is 1-based, and ``snippet`` is the matched line
plus the next ``--context`` lines (default 15), at most 1,200 characters.
Entries are sorted by file, then line.

With no ``-o`` or ``--split`` the JSON array goes to stdout. ``-o FILE`` writes
it to FILE and prints the entry count. ``--split DIR`` writes
``DIR/batch-001.json``, ``batch-002.json`` ... of at most ``--batch-size``
entries (default 150) and prints the number of batch files; it first deletes
any ``batch-*.json`` already in DIR.

Always skipped: paths with a ``node_modules``, ``vendor``, ``dist``, ``build``,
``.venv`` or ``third_party`` component, and ``*.min.js``. Skipped unless
``--include-tests``: paths with a ``test``, ``tests``, ``__tests__`` or ``spec``
component, and file names matching ``test_*``, ``*_test.*``, ``*.test.*``,
``*.spec.*``. Names starting with ``_`` are dropped. A file that is not UTF-8
is skipped with a stderr line.

Exit 0 on success (an empty array included); exit 2 on bad usage, a root that
is not a git repo, a git failure, or an output path that cannot be written.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from pathlib import Path

SNIPPET_MAX = 1200
DEFAULT_BATCH = 150
DEFAULT_CONTEXT = 15

SKIP_DIRS = {"node_modules", "vendor", "dist", "build", ".venv", "third_party"}
SKIP_FILES = ["*.min.js"]
TEST_DIRS = {"test", "tests", "__tests__", "spec"}
TEST_FILES = ["test_*", "*_test.*", "*.test.*", "*.spec.*"]

JAVA_KEYWORDS = {
    "if",
    "else",
    "for",
    "foreach",
    "while",
    "do",
    "switch",
    "case",
    "catch",
    "try",
    "return",
    "new",
    "throw",
    "using",
    "lock",
    "synchronized",
    "typeof",
    "sizeof",
    "nameof",
}

EXTENSIONS = {
    ".py": "Python",
    ".js": "JavaScript/TypeScript",
    ".jsx": "JavaScript/TypeScript",
    ".mjs": "JavaScript/TypeScript",
    ".cjs": "JavaScript/TypeScript",
    ".ts": "JavaScript/TypeScript",
    ".tsx": "JavaScript/TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java/C#",
    ".cs": "Java/C#",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".rb": "Ruby",
    ".sh": "Shell",
    ".bash": "Shell",
    ".ps1": "PowerShell",
    ".psm1": "PowerShell",
}

_JS_IDENT = r"[A-Za-z_$][\w$]*"
_KOTLIN_MODS = (
    r"(?:public|private|protected|internal|override|open|suspend|inline|operator"
    r"|infix|tailrec|abstract|final)"
)

PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "Python": [
        re.compile(r"^[ \t]*(?:async[ \t]+)?def[ \t]+([A-Za-z_]\w*)[ \t]*\("),
    ],
    "JavaScript/TypeScript": [
        re.compile(
            r"^[ \t]*(?:export[ \t]+)?(?:default[ \t]+)?(?:async[ \t]+)?"
            rf"function(?:[ \t]*\*[ \t]*|[ \t]+)({_JS_IDENT})[ \t]*\("
        ),
        re.compile(
            rf"^[ \t]*(?:export[ \t]+)?(?:const|let)[ \t]+({_JS_IDENT})[ \t]*"
            r"(?::[^=\n]+)?=[ \t]*(?:async[ \t]+)?"
            rf"(?:function\b|\([^)\n]*\)[^=\n]*=>|{_JS_IDENT}[ \t]*=>)"
        ),
    ],
    "Go": [
        re.compile(r"^[ \t]*func[ \t]+(?:\([^)]*\)[ \t]*)?([A-Za-z_]\w*)[ \t]*[\[(]"),
    ],
    "Rust": [
        re.compile(
            r"^[ \t]*(?:pub(?:\([^)]*\))?[ \t]+)?(?:const[ \t]+)?(?:async[ \t]+)?"
            r"(?:unsafe[ \t]+)?fn[ \t]+([A-Za-z_]\w*)"
        ),
    ],
    "Java/C#": [
        re.compile(
            r"^[ \t]*(?:public|protected|private|internal)\b[^=;(\n]*?"
            r"\b([A-Za-z_]\w*)[ \t]*\("
        ),
    ],
    "Kotlin": [
        re.compile(
            rf"^[ \t]*(?:{_KOTLIN_MODS}[ \t]+)*fun[ \t]+(?:<[^>\n]*>[ \t]*)?"
            r"(?:[\w.<>?, ]+\.)?([A-Za-z_]\w*)[ \t]*\("
        ),
    ],
    "Ruby": [
        re.compile(r"^[ \t]*def[ \t]+(?:self\.)?([A-Za-z_]\w*[?!=]?)"),
    ],
    "Shell": [
        re.compile(r"^[ \t]*function[ \t]+([A-Za-z_][\w-]*)"),
        re.compile(r"^[ \t]*([A-Za-z_][\w-]*)[ \t]*\(\)[ \t]*\{?"),
    ],
    "PowerShell": [
        re.compile(r"^[ \t]*function[ \t]+([A-Za-z_][\w-]*)", re.IGNORECASE),
    ],
}


class CatalogError(Exception):
    """Raised when the file list cannot be read from git."""


def function_name(line: str, language: str) -> str | None:
    """The name ``line`` defines in ``language``, or None.

    The first matching pattern wins. Names starting with ``_`` are dropped, and
    for Java/C# so are control keywords.
    """
    for pattern in PATTERNS.get(language, []):
        match = pattern.match(line)
        if not match:
            continue
        name = next((g for g in match.groups() if g), None)
        if not name or name.startswith("_"):
            return None
        if language == "Java/C#" and name in JAVA_KEYWORDS:
            return None
        return name
    return None


def git_files(root: Path) -> list[str]:
    if not root.is_dir():
        raise CatalogError(f"not a directory: {root}")
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
        )
    except OSError as exc:
        raise CatalogError(f"cannot run git: {exc}") from exc
    if result.returncode != 0:
        err = result.stderr.decode("utf-8", errors="replace")
        first = (err.strip().splitlines() or ["git failed"])[0]
        raise CatalogError(f"git ls-files failed: {first}")
    try:
        listing = result.stdout.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CatalogError(f"git ls-files output is not UTF-8: {exc}") from exc
    return [p for p in listing.split("\0") if p]


def wanted(rel: str, include_tests: bool) -> str | None:
    """The language of ``rel`` when it should be catalogued, else None."""
    path = Path(rel)
    language = EXTENSIONS.get(path.suffix.lower())
    if language is None:
        return None
    dirs = set(path.parts[:-1])
    if dirs & SKIP_DIRS:
        return None
    if any(fnmatch.fnmatch(path.name, g) for g in SKIP_FILES):
        return None
    if not include_tests:
        if dirs & TEST_DIRS:
            return None
        if any(fnmatch.fnmatch(path.name, g) for g in TEST_FILES):
            return None
    return language


def catalog(
    root: Path, *, context: int = DEFAULT_CONTEXT, include_tests: bool = False
) -> list[dict]:
    entries: list[dict] = []
    for rel in git_files(root):
        language = wanted(rel, include_tests)
        if language is None:
            continue
        try:
            text = (root / rel).read_bytes().decode("utf-8")
        except UnicodeDecodeError:
            print(f"skipped (not UTF-8): {rel}", file=sys.stderr)
            continue
        except OSError:
            continue
        lines = text.splitlines()
        for i, line in enumerate(lines):
            name = function_name(line, language)
            if name is None:
                continue
            snippet = "\n".join(lines[i : i + context + 1])[:SNIPPET_MAX]
            entries.append(
                {
                    "file": rel,
                    "line": i + 1,
                    "name": name,
                    "language": language,
                    "snippet": snippet,
                }
            )
    entries.sort(key=lambda e: (e["file"], e["line"]))
    return entries


def dump(entries: list[dict]) -> str:
    return json.dumps(entries, ensure_ascii=False, indent=1) + "\n"


def write_split(entries: list[dict], folder: Path, size: int) -> int:
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("batch-*.json"):
        old.unlink()
    count = 0
    for start in range(0, len(entries), size):
        count += 1
        target = folder / f"batch-{count:03d}.json"
        target.write_text(dump(entries[start : start + size]), encoding="utf-8")
    return count


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(
        description="List a git repository's functions as JSON."
    )
    parser.add_argument("repo_root", type=Path)
    out = parser.add_mutually_exclusive_group()
    out.add_argument("-o", "--output", type=Path, help="write the array to FILE")
    out.add_argument("--split", type=Path, metavar="DIR", help="write batch files")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    parser.add_argument("--context", type=int, default=DEFAULT_CONTEXT)
    parser.add_argument("--include-tests", action="store_true")
    args = parser.parse_args(argv)
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    if args.context < 0:
        parser.error("--context must be 0 or more")

    try:
        entries = catalog(
            args.repo_root, context=args.context, include_tests=args.include_tests
        )
        if args.split is not None:
            message = str(write_split(entries, args.split, args.batch_size))
        elif args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(dump(entries), encoding="utf-8")
            message = str(len(entries))
        else:
            sys.stdout.write(dump(entries))
            return 0
    except CatalogError as exc:
        print(f"function-catalog: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        text = " ".join(str(exc).split())
        print(f"function-catalog: cannot write output: {text}", file=sys.stderr)
        return 2
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main())
