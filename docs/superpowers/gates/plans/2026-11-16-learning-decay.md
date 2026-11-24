# Plan gate: Learning decay: prune stale learnings at ship Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-16-learning-decay.md
- **Plan SHA-256:** 9cf456a80b4331c636c08e1bbd2fd8276ee253ce0978c3b0bff6f9af54d64c0a
- **Spec:** docs/superpowers/specs/2026-11-15-learning-decay-design.md
- **Spec SHA-256:** 9ab4678be6b15ce3493528b06ccc96a1a650f55b884cad70cd1d65c18af8a94d
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-16
- **Approved by:** /ship (auto)
- **Date:** 2026-11-16
- **Rounds:** 3 discovery + 0 verification

## Plan-introduced decisions

- The plugin version is 0.32.0, not the spec's 0.31.0, because `origin/main` already ships 0.31.1; the plan takes the next minor above `origin/main` at implementation time (Global Constraints, Task 3)
- Prune also reads each target on `origin/main` (`git show origin/main:<path>`) and skips entries already fixed there (Task 1)
- Prune and the audit staleness check read nested `knowledge/**/*.md` docs, excluding `knowledge/decisions/` (Tasks 1, 2)
- The files a `knowledge/` doc "describes" are the repo paths named in its body plus those in its `sources:` frontmatter (Task 2)
- The audit staleness bullet also applies to a repo that has only a `knowledge/` folder, widening section 4's applicability (Task 2)
- Multi-entry staleness findings: **Where** and **Evidence** cite the first stale entry, **Confidence** is `verified` only when every entry is, and **Impact** gives each entry with its own confidence (Task 2)
- A resolved memory item is rewritten in place as `done <YYYY-MM-DD> (<ref>): <item>`, where `<ref>` is the PR number once a PR exists, else the branch name (the normal case under `/ship`), and its `MEMORY.md` line uses the same wording (Task 1)

## Findings fixed

- round 1 [blocking] Success criterion 4 had no task: added Task 4 Step 5, which records the post-merge check as a project auto-memory entry and its `MEMORY.md` line (or in the final report when there is no memory directory).
- round 1 [minor] Scenario diff expectation too strict: the expected diff now allows removing the empty `## Gotchas` heading and checks only that `docs/notes.txt` and the title are untouched.
- round 1 [minor] Step 6 commit sentence ambiguous: now "when step 5 wrote to it, and step 4's prune edits,".
- round 1 [minor] Contradictory summary bullet order: the plan states the final order directly.
- round 1 [minor] Task 4 lint (no Run/Expected, no commit step): Files line is `none in the repo (no commit)` and Step 3 has a Run/Expected check.
- round 2 [blocking] ADR 0046 already taken on `origin/main`: the plan uses 0047 throughout and says to take the next free number if `origin/main` moved again; Task 3 Step 1's expected failure names either current version string.
- round 2 [blocking] Scenario repo not on `main`: the bare repo is created with `--initial-branch=main`, the clone switches to `main`, and the push is `git push -u origin main`.
- round 2 [minor] Replace targets cross line wraps: Task 1 Step 3 says quoted targets are whitespace-flattened and must be matched across the wrap.
- round 2 [minor] Scenario result had no home: Task 4 Step 4 returns it verbatim in the task report for the PR body's `Scenario check` heading.
- round 3 [minor] ADR index rebase conflict not covered: the conflict note keeps both rows, `origin/main`'s first.
- round 3 [minor] Expected scenario `MEMORY.md` line not spelled out: Task 4 Step 3 gives it verbatim.

## Open

- none
