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
raw file's current lowercase hex sha256, null for ``missing``).

``--extract FILE`` prints the text of a ``.docx`` file, one line per
non-empty paragraph. It cannot be combined with ``VAULT`` or ``--json``.

Exit codes: 0 success (also when nothing is pending); 1 ``--extract`` on a
file that is not a readable ``.docx``; 2 usage error, or ``VAULT`` has no
``vault.toml`` or it does not parse.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
import zipfile
from pathlib import Path
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


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


def pending(vault: Path) -> list[dict[str, str | None]]:
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

    entries: list[dict[str, str | None]] = []
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
                entries.append(
                    {"path": rel, "status": "new", "source": None, "sha256": digest}
                )
            elif digest != mapped[rel][1]:
                entries.append(
                    {
                        "path": rel,
                        "status": "changed",
                        "source": mapped[rel][0],
                        "sha256": digest,
                    }
                )
    for rel, (page_rel, _sha) in mapped.items():
        if rel not in seen and not (vault / rel).is_file():
            entries.append(
                {"path": rel, "status": "missing", "source": page_rel, "sha256": None}
            )
    entries.sort(key=lambda e: e["path"] or "")
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
            print(f"{entry['status']}\t{entry['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
