# Gates converge: a verification round and a narrower blocking bar

- **Status:** approved
- **Date:** 2026-10-02

## Purpose

The spec gate escalates to the user most of the time. Of the five spec gate
records in this repo, three needed more than 3 rounds (blocking findings per
round: 3-2-1-1, 4-3-2 then a rerun, 2-4-4-2-1-1). In real projects the
pattern is the same: blocking counts fall round by round but rarely reach
zero, and the gate fails with no decision for the user to make.

Two causes, both in the gate itself:

1. **No convergence.** The rubric makes every unanswered implementation
   question `blocking`. Each fresh reviewer samples a different subset of an
   unbounded set of questions, and each fix adds detail that raises new ones.
   Many late findings are "how" questions (which test file holds which check,
   exact timestamps) that the plan settles anyway.
2. **Round 3 fails by construction.** When the last allowed round finds
   anything, it is fixed and never re-reviewed, so the verdict is `fail` even
   when nothing needs the user.

This work narrows `blocking` to a fixed set of classes, moves "how" questions
to a new `[plan]` severity that the plan must answer, and ends both gates
with a scoped verification round that checks the last fixes instead of
searching again. Done means: the user is asked only for real decisions or a
fix that stays wrong after verification.

## Scope

**In:**

- `plugin/skills/spec-gate/rubric.md`: the six blocking classes, the
  `**Class:**` field, the `[plan]` severity.
- `plugin/skills/spec-gate/SKILL.md`: discovery and verification rounds,
  `[plan]` handling, record format, verdict.
- `plugin/skills/spec-gate/verify.md` (new): the verification reviewer's
  rubric, shared by both gates.
- `plugin/skills/plan-gate/SKILL.md`: verification rounds; the reviewer
  prompt names the spec's gate record.
- `plugin/skills/plan-gate/rubric.md`: a Plan-questions check.
- `plugin/commands/ship.md`: step 3 answers the spec record's Plan questions.
- `conventions/spec-driven-development.md`: the "Spec gate" and "Plan gate"
  sections describe the new rounds and the `[plan]` severity.
- `knowledge/decisions/0020-gates-end-with-verification.md` (new) and its row
  in `knowledge/decisions/README.md`.
- `plugin/.claude-plugin/plugin.json`: version 0.11.0 → 0.12.0.
- Tests: additions to `tests/test_spec_gate_skill.py`,
  `tests/test_plan_gate_skill.py` and `tests/test_ship_command.py`.

**Out:**

- Changing `spec-lint.py`. `--verify-record` reads only the Verdict, hash and
  Decisions-approved lines, so the new record fields need no lint change.
- A `[plan]` severity or blocking classes in the plan gate. The plan is the
  last document before code, so its "how" questions are real blockers.
- Several reviewers in parallel per round.
- Rewriting existing gate records.
- Editing `superpowers:writing-plans` (not ours). Outside `/ship`, the plan
  gate's new check catches a plan that ignores the Plan questions.

## Design

### Spec rubric (`rubric.md`)

Severity becomes:

- `blocking`: only when it fits one of six classes, named in the finding's
  `**Class:**` field:
  1. `wrong-build`: as written, the spec leads to the wrong behaviour or to
     harm (data loss, an unsafe rerun, a change to something that must not
     change).
  2. `contradiction`: two parts of the spec disagree.
  3. `false-claim`: a statement about existing code, files, commands or
     behaviour is untrue.
  4. `uncheckable`: a success criterion has no objective check.
  5. `open-what`: a question about *what* to build (behaviour, scope,
     interface, data) that the spec does not answer.
  6. `too-large`: check 6 (scope size) fires; the finding proposes the
     split.
- `plan`: a *how* question the plan can settle without changing what gets
  built. Test: if two implementers answered it differently, would both still
  meet the spec? Yes means `plan`. Examples: test file placement, helper
  structure, exact constants the spec does not constrain, step order inside
  one task.
- `minor`: wording or clarity that does not change what gets built
  (unchanged).

Check 1 (dry-run plan) keeps listing questions; each unanswered question
becomes a `blocking` (class `open-what`) or `plan` finding by the test above.
The other checks keep their current text and map to classes: an
ambiguity (check 2) is `open-what` when the two readings build different
things and `plan` when both readings meet the spec; a contradiction
(check 3) is `contradiction`; a false code claim (check 4) is
`false-claim`; an uncheckable criterion (check 5) is `uncheckable`; a
scope-size finding (check 6) is `too-large`.

Output format: findings are `### [blocking] <title>`, `### [plan] <title>`
or `### [minor] <title>`. A `blocking` finding has `- **Class:** <class>`
before `**Line:**`. A `plan` finding has `**Line:**` and `**Problem:**` and,
in place of `**Fix:**`, `- **Question:** <the question the plan must
answer>`.

### Verification rubric (`verify.md`, new, used by both gates)

The verification reviewer gets the document, the repository, the list of
fixed findings (title and what changed) and a unified diff of the document
from before those fixes to now. It checks only:

1. **Each fix.** Does the changed text resolve the finding it names?
2. **The diff.** Do the changed or added lines contradict another part of
   the document, make a false claim about the code, or lead to the wrong
   behaviour?

It does not search for problems outside the diff, and does not re-raise
problems an earlier round did not raise. Output, exactly:

```
## Fixes
- <finding title> — resolved | not resolved: <why>

## Findings
### [blocking] <title>
- **Line:** <line or section>
- **Problem:** <what is wrong, quoting the changed text>
- **Fix:** <a concrete change>

## Decisions changed
- <decision added or changed by the diff> (<section>)
```

`none` under Findings and under Decisions changed when there are none. Each
`not resolved` fix is also listed as a `[blocking]` finding. "Decisions"
means the document's kind of decision: for a spec, key decisions as
`rubric.md` check 7 defines them; for a plan, plan-introduced decisions as
the plan rubric's check 6 defines them. The prompt says which document kind
it is.

### Spec gate steps (`SKILL.md`)

The step numbers stay 1–7 with the same names (Lint, Review round, Fix,
Repeat, Verdict, Record, Report), so the references in `/ship` step 0
("steps 1–6 (skip step 7's question …)"), `ship-many.md` ("steps 1–6") and
the SKILL.md trailer ("skips step 7's question") stay true and do not
change. Changes by step:

1. **Lint:** unchanged.
2. **Review round:** unchanged prompt; this is a **discovery round**.
3. **Fix:** as today for `[blocking]` (fix, or collect as a decision
   finding) and `[minor]`. `[plan]` findings are **not** fixed in the spec;
   collect them, dropping duplicates by question. Before applying a round's
   fixes, copy the spec to the scratchpad as
   `<spec name>.before-round-<N>.md`.
4. **Repeat, then verify.** Repeat steps 2 and 3 until a discovery round
   returns no `[blocking]` findings, for at most 3 discovery rounds. Then,
   when the last discovery round had `[blocking]` findings, all fixed, and
   there are no decision findings: run up to 2 **verification rounds**. Each
   is a new general-purpose subagent given only:

   > Verify fixes to the design spec at `<spec>` in the repository at
   > `<repo root>`. Read `<verify.md>` first and follow it exactly. The
   > document is a spec. The fixed findings are listed in `<fixes file>`;
   > the diff of the fixes is in `<diff file>`. Return only the output
   > format it defines.

   The diff file is the output of `git diff --no-index <snapshot> <spec>`
   (exit status 1 means the files differ and is expected) written to the
   scratchpad as `<spec name>.diff-<R>.txt`, and the fixes file is
   `<spec name>.fixes-<R>.md` in the scratchpad, where `<R>` names the
   round whose fixes are verified (`round-3`, `verify-1`); where the snapshot is the copy taken before
   the fixes being verified. The fixes file lists each fixed blocking
   finding's title and what changed. If a verification round returns
   `[blocking]` findings, copy the spec to
   `<spec name>.before-verify-<N>.md`, fix them, and run the next
   verification round on those fixes only. A verification finding that
   needs a choice the spec and conversation do not settle is a decision
   finding: stop verifying; the verdict is `fail`. At most 5 review rounds
   in total (3 discovery + 2 verification). When decision findings exist
   after discovery, verification is skipped: the verdict is `fail`, and the
   rerun after the user answers starts from step 1.
5. **Verdict:** `pass` when the linter is clean, the last round (discovery
   or verification) returned no `[blocking]` findings, and there are no
   decision findings. Otherwise `fail`. `[plan]` findings never affect the
   verdict.
6. **Record:** as today, with these changes:
   - `- **Rounds:** <D> discovery + <V> verification`.
   - Key decisions: the discovery rounds' lists merged as today, plus each
     verification round's `## Decisions changed` entries (a changed
     decision replaces the old wording).
   - Findings fixed in a verification round are logged as
     `verify <N> [blocking] <title>: <what changed>`.
   - A new section after `## Findings fixed`:

     ```
     ## Plan questions

     - <question> (<spec section>)
     ```

     or `- none`.
7. **Report:** unchanged, except that "in N rounds" becomes "in D
   discovery + V verification rounds", plus "K plan questions handed to
   the plan" when K > 0.

The frontmatter `description` changes "runs up to 3 rounds of a
fresh-context reviewer subagent" to "runs up to 3 discovery rounds of a
fresh-context reviewer subagent, then up to 2 verification rounds of its
fixes".

### Plan gate (`plan-gate/SKILL.md`, `rubric.md`)

- **Setup** adds **Spec gate record:** `docs/superpowers/gates/<spec file
  name>`.
- **Review prompt** adds: "The spec's gate record is at `<spec gate record>`;
  its `## Plan questions` section lists questions the plan must answer."
- **Rubric** adds check 7, **Plan questions**: each question under the spec
  gate record's `## Plan questions` is answered by some task; an unanswered
  one is `blocking`. A missing section or `- none` means nothing to check.
- **Steps:** the numbering stays 1–7, so `/ship` step 3 ("steps 1–6 (step
  7 is not shown)") and the trailer ("runs steps 1–6 only") stay true.
  Step 4 becomes "Repeat, then verify", the same as the spec gate's: up to 3
  discovery rounds, then, when the last one's blocking findings were all
  fixed and there are no spec findings, up to 2 verification rounds using
  `../spec-gate/verify.md` and this prompt:

  > Verify fixes to the implementation plan at `<plan>` in the repository
  > at `<repo root>`. Read `<verify.md>` first and follow it exactly. The
  > document is a plan; its spec is at `<spec>`. The fixed findings are
  > listed in `<fixes file>`; the diff of the fixes is in `<diff file>`.
  > Return only the output format it defines.

  Snapshots, fixes files and diff files use the same names with the plan
  file. A verification finding whose fix would change what the spec asks
  for is a spec finding: stop verifying; the verdict is `fail`.
- **Decisions:** the plan-introduced decisions (for the verdict and the
  record) are the last discovery round's list plus every verification
  round's `## Decisions changed` entries. So `pass-with-decisions` still
  fires when verification runs, and a decision a fix adds is signed off
  like any other.
- **Verdict:** unchanged, except that "the last round returned no
  `[blocking]` findings" counts verification rounds, and "the last round
  listed no plan-introduced decisions" becomes "the plan-introduced
  decisions (as defined above) are empty".
- **Record:** the same `Rounds` format and `verify <N>` entries; "The
  decisions section holds the last round's list" becomes "holds the
  plan-introduced decisions as defined above".
- The frontmatter `description` changes "runs up to 3 rounds of a
  fresh-context reviewer subagent" to "runs up to 3 discovery rounds of a
  fresh-context reviewer subagent, then up to 2 verification rounds of its
  fixes".

### `/ship` step 3

After "write ... from the spec", add: "Answer every question under the spec
gate record's `## Plan questions` in the task it affects."

### Docs

`conventions/spec-driven-development.md`, "Spec gate": replace "runs up to
three rounds of a fresh-context reviewer ... reports every question it would
have to ask" with the discovery and verification rounds, the six blocking
classes, and `[plan]` findings handed to the plan. "Plan gate": add the
verification rounds and the Plan-questions check. Both cite ADR 0020.

ADR 0020, "Gates end with a verification round; blocking is a fixed set of
classes": context (the round counts above and the two causes), decision (as
this Design), consequences (fewer escalations; up to 5 subagents per gate; a
`[plan]` question can be misclassified, and the plan gate is the backstop).
ADR 0020 states that it supersedes the "up to three rounds" sentences in
ADRs 0015 and 0016; those ADRs are not edited.

## Decisions

- **Spec gate gets both changes; plan gate gets the verification round
  only** (user's choice). The plan has no later document to defer "how"
  questions to.
- **Plan questions live in the spec's gate record**, not in the spec
  (user's choice 2a). The spec stays lean and its hash is not touched by
  them; `/ship` step 3 and the plan gate carry them forward.
- **At most 2 verification rounds, 5 rounds in total** (user's choice).
- **Verification is scoped to the diff** and may anchor on the earlier
  findings; anchoring is acceptable for checking fixes, which is why
  discovery rounds stay context-free.
- **One shared `verify.md`** in `spec-gate/`, referenced by the plan gate,
  so the two gates cannot drift.
- **No verification when decision findings exist**: the gate fails and the
  rerun starts fresh after the user answers.

## Success criteria

1. `pytest` passes, and `ruff check plugin tests` and
   `ruff format --check plugin tests` are clean.
2. `tests/test_spec_gate_skill.py` asserts: `rubric.md` contains
   `### [plan]`, `**Class:**`, `**Question:**` and the six class names;
   `SKILL.md` contains `verify.md`, `verification round`, `## Plan
   questions`, `3 discovery + 2 verification` and `--no-index`; `verify.md`
   exists and contains `## Fixes`, `### [blocking]`, `## Decisions changed`
   and `outside the diff`. The existing `"3 rounds" in body` assertion
   becomes `"3 discovery rounds" in body`.
3. `tests/test_plan_gate_skill.py` asserts: `SKILL.md` contains
   `../spec-gate/verify.md` (resolving to an existing file),
   `verification round`, `Plan questions` and `## Decisions changed`;
   `rubric.md` contains `Plan questions`. The existing `"3 rounds" in body`
   assertion becomes `"3 discovery rounds" in body`.
4. `tests/test_ship_command.py` asserts `ship.md` contains
   `## Plan questions`.
5. ADR 0020 exists with a row in `knowledge/decisions/README.md`;
   `conventions/spec-driven-development.md` cites it under both "Spec gate"
   and "Plan gate"; the manifest version is 0.12.0.
6. **Reviewer comparison.** For each of the three merged specs
   `2026-10-01-spec-grill-design.md`, `2026-09-30-ship-many-design.md` and
   `2026-09-30-plan-gate-design.md`, run one review subagent with the old
   rubric (`git show main:plugin/skills/spec-gate/rubric.md` saved to the
   scratchpad) and one with the new rubric, named by its worktree path
   (`<worktree>/plugin/skills/spec-gate/rubric.md`; the installed skill
   resolves to the main checkout, which still has the old files). Pass when the new blocking count
   is at most the old count for each spec. If one spec fails, rerun both
   arms once on that spec and compare the summed counts of the two runs;
   if it still fails, that is a stop under `/ship`'s stop-rule procedure:
   write the handoff, report the counts, and end without opening or
   merging the PR. The PR description lists every
   old blocking finding the new review does not raise as blocking, with the
   new class or severity, for the user to judge.
7. **Full run.** One new spec-gate run, steps 1–6, followed by hand from
   `<worktree>/plugin/skills/spec-gate/SKILL.md` with the worktree's
   `rubric.md` and `verify.md` paths in the subagent prompts (not by
   invoking the installed `claude-kit:spec-gate` skill), on
   `2026-10-01-spec-grill-design.md` inside the worktree writes a record
   with a `Rounds:` line in the new format and a `## Plan questions`
   section (the `Rounds:` line is reported as-is; a verification round is
   not required to occur), and `spec-lint.py --verify-record` on that spec prints `ok:` if
   the verdict is `pass`. The spec and record changes from this run are then
   discarded (`git checkout`/`git clean` on those two paths) and never
   committed.
8. This spec passes `spec-lint.py` and the spec gate.
