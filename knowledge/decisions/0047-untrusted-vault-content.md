# ADR 0047: Untrusted vault content

- **Status:** accepted
- **Date:** 2026-11-16

## Context
Raw files in a personal vault (web pages, documents, call transcripts) can carry
text addressed to an AI agent. That text reaches the unattended daily ingest, which
runs with full tools, every later session that reads the wiki, and `task-prompt`,
which turns tasks into prompts the user runs.

## Decision
- **D1:** a deterministic scanner in `vault-pending.py` flags hidden HTML, invisible
  characters and instruction-like text, and the skill rules act on its flags,
  because a script cannot be talked out of flagging; rejected: rules alone.
- **D2:** flagged lines are withheld from the wiki and the rest of the file is
  ingested, so the daily ingest keeps working and every flag is reported; rejected:
  quarantining the file, since false positives would stall the ingest.
- **D3:** source pages record `trust`, and anything but `own` counts as external,
  because existing vaults have no `trust` and a fail-safe default warns; rejected:
  migrating existing vaults.

## Consequences
A minified page may be withheld whole, since all of it sits on one flagged line.
`.pdf` files are not scanned and are reported as unscanned. The flags are
heuristic: they catch common patterns, not every possible injection, and can flag
harmless text.

The spec's precision check on real study notes gave 36 false flags, so its phrase
list was narrowed before merge: "system prompt" became "your system prompt", and
"assistant:" counts only as a speaker turn at the start of a line. Prose about
prompts no longer flags; an injected "assistant:" in the middle of a line is left
to ingest's reader rule. A hidden element that never closes is withheld only to
the end of its opening line, as the spec defines.

The branch review added three cases the spec did not list. Unicode tag
characters (U+E0000 to U+E007F) count as `invisible-char`, since models read
them while screens do not show them. Text with a UTF-16 or UTF-32 byte-order
mark is decoded with that codec, and text that still holds NUL bytes after
decoding is reported as unscanned. A `.docx` the reader cannot decompress is
unscanned rather than an error. Variation selectors stay unflagged (emoji use
U+FE0F), and the zero-width joiner the spec names flags emoji sequences too.
