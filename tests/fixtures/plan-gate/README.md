# Plan gate reviewer eval

Seeded-defect plans for measuring the plan-gate reviewer
(`plugin/skills/plan-gate/rubric.md`). This eval is run by hand, not in CI.
Every plan implements the hypothetical feature in `spec.md`; `00-clean.md`
is the control, and each seeded plan is a copy of it with one edit.

| File | Seeded defect | Hit when reported as |
|---|---|---|
| `00-clean.md` | none (control) | — |
| `01-uncovered.md` | spec criterion 3 (empty folder) has no task | `[blocking]` |
| `02-missing-fact.md` | output format left to "the kit's standard report format", which does not exist | `[blocking]` |
| `03-order.md` | Task 1 imports `spec_status`, which Task 2 creates | `[blocking]` |
| `04-false-claim.md` | calls `read_status()` from `spec-index.py`, which does not exist | `[blocking]` |
| `05-scope-creep.md` | Task 3 adds a `--csv` flag the spec does not ask for | `[blocking]` |
| `06-decision.md` | resolves the default `docs/superpowers/specs` from the git top level, not the current directory; the spec does not say which | a Plan-introduced decision, and not `[blocking]` |

## How to run

1. Make a detached checkout of the branch without these fixtures:
   `git worktree add --detach <tmp> HEAD`, then delete
   `<tmp>/tests/fixtures/plan-gate/` in it.
2. Copy `spec.md` into `<tmp>-eval/` as `s.md`, and each plan as a neutral
   name in shuffled order (for example `p1.md` … `p7.md`), keeping the
   mapping only outside `<tmp>`. In each copy, rewrite the `**Spec:**` line to
   the spec copy's absolute path, so it names the neutral `s.md`.
3. For each copy, dispatch a new general-purpose subagent with the prompt from
   step 2 of `plugin/skills/plan-gate/SKILL.md`: the copy as the plan, `s.md`
   as the spec, `<tmp>` as the repository, and the rubric's absolute path.
4. Run all seven twice (two independent runs). Remove `<tmp>` and
   `<tmp>-eval/` afterwards.

**Pass:** at least 5 of 6 hits on each run, and at most 1 `[blocking]`
finding on `00-clean.md` on each run.

## Results

| Date | Run | Hits (01–06) | Clean blocking | Pass |
|---|---|---|---|---|
| 2026-09-30 | 0 (discarded) | 5/6 (06, then a SQLite cache, listed both as a decision and as `[blocking]`) | 1 (a real control gap: a 90-character test line fails ruff E501) | no: the control was fixed (line wrapped, plus minor fixes), and rubric check 6 was sharpened ("how" vs scope creep; list a decision once) |
| 2026-09-30 | A | 5/6 (06 cache reported as `[blocking]` scope creep, no decision) | 0 | yes |
| 2026-09-30 | B | 5/6 (06 cache reported as `[blocking]` scope creep, no decision) | 0 | yes |
| 2026-09-30 | 06 rerun | 2/2 on the new 06 (git top-level default) | — | yes: listed as a decision, no `[blocking]`, in both reviews |

The cache in the first 06 also writes a new file into the user's specs
folder, so reviewers fairly read it as work the spec does not ask for (scope
creep) rather than a choice about how to do the asked-for work. It was
replaced by the git top-level default, an in-scope interpretation choice, and
that file was reviewed twice by fresh reviewers.

Reviewers ran in a detached checkout without these fixtures, on copies with
neutral, shuffled names, so they could not read the defect list above.
