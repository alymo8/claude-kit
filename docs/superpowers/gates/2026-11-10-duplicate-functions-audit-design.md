# Gate: Duplicate-intent pass in `audit` and `audit-deep`

- **Spec:** docs/superpowers/specs/2026-11-10-duplicate-functions-audit-design.md
- **Spec SHA-256:** e9854ab2392e4b3b1b17390d1c934db8fc0829087a104f15efa8365c9e0adea0
- **Verdict:** pass
- **Date:** 2026-11-10
- **Rounds:** 3 discovery + 2 verification

## Key decisions

- The pass is added to both `audit` (Pass 4) and `audit-deep` (Phase H), with one shared procedure file `plugin/skills/audit/duplicates.md` (Scope, Design)
- The audits stay read-only: they recommend a surviving function and never consolidate; `rules.md` and `check-findings.py` are unchanged (Scope Out)
- A line-based regex catalog in a standard-library script covering 9 language families, no parsers, noise accepted; tests, vendored and build paths excluded by default; `_private` names and dunders skipped (D4, Design)
- Domain grouping runs on `haiku` subagents in batches of 150, with a fallback to the session's model when Haiku is unavailable; this is the kit's first model pin. Comparison runs on the session's model (D2)
- Thresholds: skip under 20 or over 3,000 functions; compare domains with 3 or more functions, in units of at most 150 entries; at most 12 compare subagents; units not compared are listed (D3)
- Phase H runs in `audit-deep`'s main session between Phases B–E and F and writes `07-duplicates.md`, which Phase G includes (D5, Design)
- Pass 3 and Phase E leave duplicate functions to this pass, so one root cause gets one finding (Design)
- Both audits' reports carry one counts line: functions catalogued, compare units dispatched, groups by HIGH/MEDIUM/LOW (Design, Success criterion 4)
- Severity is Medium only when the duplicates behave differently, else Low; LOW-confidence groups go in a table, not findings (D6)
- Ships with the review spec in one `/ship-many` run, in successive waves, because the two share `plugin.json`, `README.md` and the manifest test (D1)

## Findings fixed

- round 1 [blocking] No behaviour for catalogs too large for one Haiku subagent: grouping is batched (150 entries per Haiku subagent, output without snippets, joined back by file and line); a 3,000-function limit skips the pass; `--split`/`--batch-size` added to the script with a test
- round 1 [blocking] False claim that the other scripts reconfigure stdout: now cites `docker-disk.py` only
- round 1 [minor] Dunder wording made consistent
- round 1 [minor] D1 names the shared files and the rebase rule
- round 1 [minor] Criterion 4 names `/ship`'s final report
- round 2 [blocking] Counts not defined anywhere: one counts line opens the section, the `07-duplicates.md` header and both chat reports
- round 2 [blocking] No per-subagent size limit: domains over 150 entries split into compare units counted against the cap of 12
- round 2 [minor] Skip message no longer suggests a folder
- round 2 [minor] Phase G input range and `G-report.md` line made explicit
- round 3 [minor] Header no longer names the count twice
- round 3 [minor] Pass 3 and Phase E leave duplicate functions to this pass (`E-design.md` added to Scope In)
- round 3 [minor] D2 states the first model pin and why
- D1 reworded: successive `/ship-many` waves, not parallel (shared Scope paths)
- verify 1 [blocking] D2's Haiku fallback was not in the procedure: step 2 now re-dispatches a refused batch with no model override
- verify 1 [blocking] Phase H sentence applied the G range to the overwrite list: split into two sentences

## Plan questions

- Is each `other: <subdomain>` label its own domain for the 3-function threshold and the cap, or are all `other` entries pooled into one domain? (duplicates.md steps 2–3)
- How are test-like fixtures (`test_*.py`, `*.spec.ts`) kept out of pytest collection and ruff: generated in the temp repo at test time, non-colliding names, or config exclusions? (Scope In, Testing)
- Which subagent type does each dispatch use (grouping writes files; comparing only reads), and what does the pass do when `function-catalog.py` exits 2 (skip line or stop)? (duplicates.md steps 1–3)
- Do all language patterns allow leading whitespace, and do the fixtures include indented methods per language? (Design, language table)
- What exact regex does the Java/C# pattern use, which identifier is the name, which control keywords are excluded, and which negative fixture exercises that exclusion? (Design, language table; Testing)
- Is `--batch-size` without `--split` ignored or a usage error, and what does `--split` write and print for 0 entries? (Design, script usage)
- Does the session set severity (Medium vs Low) from its own reading of the functions, or map it from the subagent's confidence and "how they differ"? (duplicates.md step 4; D6)
- Does the join count catalog entries with no matching `file`/`line` key in the categorized output as part of the reported gap? (duplicates.md step 2)

## Open

- none
