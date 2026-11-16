# Gate: Untrusted vault content: scan raw files and keep injected text out of the wiki

- **Spec:** docs/superpowers/specs/2026-11-15-untrusted-vault-content-design.md
- **Spec SHA-256:** 19575bcbd72f6b636cecb1302531bd9e02609152f4fe9261f01080a47a1afedb
- **Verdict:** pass
- **Date:** 2026-11-15
- **Rounds:** 3 discovery + 1 verification

Round 1 reviewed the combined agent-config security spec, which was split
into this spec and `2026-11-15-user-config-audit-design.md` on that
round's too-large finding.

## Key decisions

- A deterministic scanner in `vault-pending.py` plus skill rules, not rules alone (D1)
- Flagged lines (from `line` to `end_line`) are withheld from the wiki and the rest of the file is ingested; no quarantine; a minified page may be withheld whole (accepted cost) (D2)
- A `truncated` scan (over 50 flags) withholds everything from the 50th flag to the end of the file
- `trust` on source pages, `own` only for `raw/notes/`; any other value (external, empty, absent) counts as external, and existing vaults are not migrated (D3)
- `instruction` phrases match across line breaks; unreadable `.docx` and `.pdf` are reported as `unscanned:`
- Ingest writes only in `wiki/` and `tasks/` and runs only `vault-pending.py`; text addressed to an AI never becomes a task
- task-prompt warns for an external or missing source page, not for a task with an empty `source`; it paraphrases and never uses `## Flags` content
- The precision check copies the real vault's `raw/` into a scratch vault; the PR gives counts only
- Nothing is frozen (D4); split from the user-config audit (D5); one ADR records D1-D3; minor version bump

## Findings fixed

- round 1 [blocking] Two independent subsystems in one spec: split into this spec and the user-config-audit spec.
- round 1 [blocking] Extent of flagged text for multi-line hidden content: flags carry `end_line`; ingest withholds `line` to `end_line`; multi-line comment test added.
- round 1 [blocking] D3 matches a MUST trigger but the ADR left it out: this spec's ADR records D1, D2 and D3.
- round 1 [minor] "A line the page marks as flagged" was vague: now "anything under a source page's `## Flags` section".
- round 1 [minor] Two invisible characters must be on separate lines: test says "on two different lines".
- round 2 [blocking] Precision check scanned only pending files: it now runs on a scratch copy of the real `raw/`, stating files scanned.
- round 2 [blocking] Ingest's handling of `truncated` was undefined: withhold from the 50th flag to end of file; written as `"truncated"`; report says so.
- round 2 [blocking] Warning for a task with no source page: a missing page warns; an empty `source` does not.
- round 2 [minor] Line-level withholding can drop a minified page: accepted in D2.
- round 2 [minor] No `.docx` scanner test: added; `.docx` lines count the `--extract` output.
- round 3 [blocking] Criterion 3 asked for a task the scenario never creates: transcript has two action items; only the person's becomes a task.
- round 3 [blocking] Empty `trust:` got no warning: any value other than `own` warns; D3 updated.
- round 3 [blocking] Unreadable `.docx` scan result: `scanned: false`, reported as `unscanned:`; tested.
- round 3 [blocking] `instruction` matching across line breaks: line breaks collapsed before matching; split-phrase test added.
- round 3 [minor] Real-vault counts in a public PR: counts only, no file names or excerpts.

## Plan questions

- One `instruction` flag per line (or multi-line match) or one per phrase occurrence? (Design: Scanner)
- Are tool-call tokens (`Write(`, `Edit(`) matched case-sensitively and as whole words, to avoid flagging `file.write(`? (Design: Scanner)
- Is the excerpt the first 80 characters of the line or a window around the match? (Design: Scanner)
- Does the plain-output count include the `truncated` entry, and what is the exact suffix text? (Design: Scanner)
- How are nested same-name elements paired with their closing tag? (Design: Scanner)
- The existing exact-dict assertion in `tests/test_vault_pending.py` breaks with the new keys; update it. (Testing)
- On a `changed` file, does ingest replace `flags` and `## Flags`, and add `trust`/`flags` to a page that has neither? (Design: Ingest)
- Are the `.docx` and `.pdf` fixtures committed binaries or generated in the test? (Testing)
- Which literal strings do the task-prompt assertions look for (missing-page and empty-`source` cases)? (Testing)

## Open

- none
