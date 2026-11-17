# Plan gate: Untrusted vault content Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-16-untrusted-vault-content.md
- **Plan SHA-256:** 36254bbab2ab303750aafb8da5cdb93e7b38bc82a389451fce0e757293d1db25
- **Spec:** docs/superpowers/specs/2026-11-15-untrusted-vault-content-design.md
- **Spec SHA-256:** 19575bcbd72f6b636cecb1302531bd9e02609152f4fe9261f01080a47a1afedb
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-16
- **Approved by:** /ship (auto)
- **Date:** 2026-11-16
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- `tests/test_vault_init.py` (outside the spec's Scope In) is edited: `trust` and `flags` are added to its `FRONTMATTER` key lists for the source and call templates, which it pins exactly (Task 3)
- An HTML comment with no closing `-->` is flagged from `<!--` to the end of the file (Task 1)
- Tool-call tokens (`Bash(`, `WebFetch(`, `Write(`, `Edit(`, `mcp__`) match case-sensitively and only when not preceded by a letter, digit, `_` (or `.` for the first four); the phrases stay case-insensitive, so `bash(` and `fh.Write(` are not flagged (Task 1)
- On a `changed` file, the source page's `trust` and `flags` are recomputed (added when absent) and `## Flags` is replaced, or removed when there are no flags (Task 3)

## Findings fixed

- round 1 [blocking] Raw invisible and bidi characters in the test code: written as `\u` escapes; a global constraint bans raw zero-width, BOM and bidi characters in tracked files.
- round 1 [minor] Task-prompt warning position: expected on the line right after `# Task: <title>`.
- round 1 [minor] PWNED.txt search too narrow: also searches `%USERPROFILE%`.
- round 1 [minor] Stale `pending()` annotation: changed to `list[dict[str, object]]`.
- round 2 [minor] Raw zero-width character in the escape example: replaced by the escape text.
- round 2 [minor] Tag-name boundary in depth counting: the name is followed by whitespace, `/` or `>`.

## Open

- none
