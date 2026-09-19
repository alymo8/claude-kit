"""Helpers for reading the tail of a Claude Code transcript (JSONL).

Transcripts grow to tens of MB; hooks read only the last chunk.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

TAIL_BYTES = 256 * 1024
USAGE_KEYS = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
)


def read_tail(path: Path, size: int = TAIL_BYTES) -> str:
    """Last ``size`` bytes of ``path`` from the first full line; '' if unreadable."""
    try:
        total = path.stat().st_size
        with path.open("rb") as fh:
            if total > size:
                fh.seek(total - size)
                data = fh.read()
                cut = data.find(b"\n")
                data = data[cut + 1 :] if cut != -1 else data
            else:
                data = fh.read()
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def iter_records(text: str) -> Iterator[dict]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except ValueError:
            continue
        if isinstance(record, dict):
            yield record


def last_usage_tokens(text: str) -> int | None:
    """Context size after the last API call: input + cache creation + cache read."""
    found: int | None = None
    for record in iter_records(text):
        if record.get("type") != "assistant":
            continue
        usage = (record.get("message") or {}).get("usage")
        if isinstance(usage, dict):
            found = sum(int(usage.get(k) or 0) for k in USAGE_KEYS)
    return found


def recent_prompts(text: str, limit: int = 5) -> list[str]:
    """Last ``limit`` typed user prompts, first line only, at most 120 chars."""
    prompts: list[str] = []
    for record in iter_records(text):
        if record.get("type") != "user" or record.get("isMeta"):
            continue
        content = (record.get("message") or {}).get("content")
        if not isinstance(content, str):
            continue
        first = content.strip().splitlines()[0] if content.strip() else ""
        if not first or first.startswith("<"):
            continue
        prompts.append(first[:120])
    return prompts[-limit:]
