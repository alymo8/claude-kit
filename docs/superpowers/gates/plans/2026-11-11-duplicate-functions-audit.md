# Plan gate: Duplicate-intent pass in `audit` and `audit-deep` Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-11-duplicate-functions-audit.md
- **Plan SHA-256:** c13621160e09dde55678dfcfe198263d27ea7763568de3426de59d65656bc72e
- **Spec:** docs/superpowers/specs/2026-11-10-duplicate-functions-audit-design.md
- **Spec SHA-256:** e9854ab2392e4b3b1b17390d1c934db8fc0829087a104f15efa8365c9e0adea0
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-11
- **Approved by:** /ship (auto)
- **Date:** 2026-11-11
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- When `function-catalog.py` exits non-zero, the pass writes `Skipped: function-catalog.py exited <code>: <first stderr line>.` and ends; the rest of the audit continues (Task 2)
- Each distinct `other: <subdomain>` label (trimmed, lowercased) is its own domain for the 3-function threshold, the 150-entry units and the cap of 12 (Task 2)
- Severity is set from the session's own reading of the functions; where it could not open one, the finding is `inferred` and severity follows the subagent's "how they differ" (Task 2)
- Grouping gap: catalog entries with no `file`+`line` match count as uncategorized, categorized entries with no catalog match are dropped, and the report gets a `Grouping gap: <k> of <n> functions not categorized (batches: ...).` line (Task 2)
- Grouping and compare subagents are both `general-purpose`; grouping uses `model: haiku`, compare uses no model override and is told to read only (Task 2)
- `--split DIR` first deletes any existing `batch-*.json` in DIR (Task 1)
- `--batch-size` without `--split` is ignored; `-o` with `--split` is a usage error; `-o FILE` prints the entry count on stdout (Task 1)
- Criterion 4's live audit runs in `/ship` step 10's detached `<tmp>` worktree at the squash commit, and its counts line goes in the step 12 report (After the tasks)

## Findings fixed

- round 1 [blocking] Nothing ran success criterion 4: "After the tasks" now gives explicit post-merge steps in `/ship` step 10 (audit on `<tmp>`, `check-findings.py` exit 0, counts line copied to the step 12 report)
- round 1 [blocking] Task 4's criterion 5 and full-suite checks could run before Tasks 1-3 merged: Task 4 now depends on Task 1, Task 2, Task 3
- round 1 [minor] Java/C# keyword filter not exercised: added `function_name` to the interface and `test_java_keyword_names_dropped`
- round 1 [minor] `git ls-files -z` decoding unstated: git runs with `encoding="utf-8"`
- round 1 [minor] Vendored-path test could pass vacuously under a global gitignore: `make_repo` uses `git add -A -f`
- round 2 [minor] Index step's expected output already true: expected output now allows no change
- round 2 [minor] Extension list only implied: the full extension list is inline in Task 1 Step 4

## Open

- none
