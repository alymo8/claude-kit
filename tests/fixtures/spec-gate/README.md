# Spec gate reviewer eval

Seeded-defect specs for measuring the spec-gate reviewer
(`plugin/skills/spec-gate/rubric.md`). This eval is run by hand, not in CI.

| File | Seeded defect |
|---|---|
| `00-clean.md` | none (control) |
| `01-ambiguous.md` | "handled gracefully" for a missing README: exit 0 or exit 1? |
| `02-open-decision.md` | CRLF line endings: "must take this into account" without saying how |
| `03-uncheckable.md` | criterion 2 "feels fast and is pleasant to use" |
| `04-false-claim.md` | calls `dry_run_index`, which does not exist |
| `05-contradiction.md` | Decisions say a hand-written README fails; Design and criteria say it passes |
| `06-two-subsystems.md` | adds ADR linting to the hook: a second, independent subsystem |

## How to run

For each file, dispatch a new general-purpose subagent with the prompt from
step 2 of `plugin/skills/spec-gate/SKILL.md`, using this file's absolute path
as the spec and the kit repo root as the repository. Run all seven files
twice (two independent runs).

A seeded file is a **hit** when the run reports its seeded defect as a
`[blocking]` finding. Count `[blocking]` findings on `00-clean.md`.

**Pass:** at least 5 of 6 hits on each run, and at most 1 `[blocking]` finding
on `00-clean.md` on each run.

## Results

| Date | Run | Hits (01–06) | Clean blocking | Pass |
|---|---|---|---|---|
| 2026-09-30 | 0 (first control, discarded) | 6/6 | 3 | no: the control had 3 real gaps (unknown-flag rule vs "behaves exactly as today", overlapping cases with no order, error handling in `--check` mode); the control was fixed, not the rubric |
| 2026-09-30 | A | 6/6 | 1 (when `render()` runs relative to the ordered cases: a real residual gap) | yes |
| 2026-09-30 | B | 6/6 | 0 | yes |

Reviewers ran in a detached checkout without these fixtures, on copies with
neutral, shuffled names, so they could not read the defect list above.
