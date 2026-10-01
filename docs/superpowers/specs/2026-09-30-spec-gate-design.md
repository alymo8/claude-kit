# Spec gate: linter and independent reviewer

- **Status:** approved
- **Date:** 2026-09-30

## Purpose

A spec is the contract `/ship` builds against with no further check-ins, but
nothing in the kit checks a spec's quality. Today the only check is the
`superpowers:brainstorming` skill's four-point self-review, done by the same
session that wrote the spec, plus the user's review. In practice the user
mostly does not read specs in full, so a spec with gaps reaches `/ship`. There
it either fires a stop rule or, worse, the gap is settled by a silent guess.

This work adds a **spec gate**: a rigorous check that does the reading in
place of the user. It has two layers:

1. A **linter script**: a deterministic floor of structural checks.
2. A **fresh-context reviewer subagent**. It reads the spec cold, the way
   `/ship` will, and tries to plan from it.

A gate pass does not approve the spec. It reduces the user's review to a
one-line OK on a short verdict and the key decisions the gate found. This
keeps the workspace rule "verify key decisions with me" without requiring the
user to read the spec.

This is spec 1 of 2. Spec 2, a parallel runner for plans and specs, follows
and relies on gated specs.

## Scope

**In:**

- `plugin/scripts/spec-lint.py` (new): the linter, plus spec hashing and gate
  record verification.
- `plugin/skills/spec-gate/SKILL.md` (new): the gate procedure, invocable as
  `/spec-gate <spec.md>`.
- `plugin/skills/spec-gate/rubric.md` (new): the reviewer's rubric and finding
  format.
- Gate records under `docs/superpowers/gates/` (new), one per spec.
- `plugin/commands/ship.md`: a new step 0 that requires a valid gate record
  (running the gate if needed), a new stop rule for a failed gate, and step 2
  copying the gate record into the worktree with the spec.
- Workspace `CLAUDE.md` ("Specs and plans" section): run the gate after
  writing or revising a spec, before asking the user for review.
- `conventions/spec-driven-development.md`: a "Spec gate" section, and the
  required spec sections the linter enforces.
- `knowledge/decisions/0015-spec-gate-replaces-full-read.md` (new): ADR 0015.
- Tests: `tests/test_spec_lint.py` (new), additions to
  `tests/test_ship_command.py`, and a `test_spec_gate_skill` check in the
  style of `tests/test_audit_skills.py`.
- A reviewer eval: `tests/fixtures/spec-gate/` (new) with seeded-defect specs
  and a README describing how to run the eval manually.
- Plugin version bump in `plugin/.claude-plugin/plugin.json` (0.5.2 → 0.6.0).

**Out:**

- Editing the superpowers plugin (`superpowers:brainstorming` is not ours).
  The gate is enforced through `CLAUDE.md` and `/ship` instead.
- Gating implementation plans. Plans are written by `/ship` from a gated spec.
- Running the LLM reviewer eval in CI. It costs money and its results vary,
  so it is run manually and the results are reported in the PR.
- A hook that runs the linter automatically on every spec edit. The gate runs
  it when it matters.
- Retrofitting the four existing implemented specs to pass the linter. They
  are only used for a back-test (see Success criteria).
- Parallel execution (spec 2).

## Design

### Required spec shape

The linter enforces the spec anatomy that `conventions/spec-driven-development.md`
already describes, in the form existing specs use:

- A `# Title` H1.
- `- **Status:** <draft|approved|implemented|superseded>` and
  `- **Date:** YYYY-MM-DD` bullets.
- H2 sections, matched case-insensitively by prefix: `Purpose`, `Scope`,
  `Design` (or `Structure`), `Decisions`, `Success criteria`. Other H2
  sections are allowed.
- Out of scope is stated either as an `**Out:**` marker inside `## Scope` or as
  a separate `## Out of scope` section.

### `plugin/scripts/spec-lint.py`

```
python spec-lint.py SPEC.md [--root DIR]        # lint
python spec-lint.py --hash SPEC.md               # print the spec hash
python spec-lint.py --verify-record SPEC.md      # check the gate record
```

`--root` is the repo root for path checks. It defaults to
`git rev-parse --show-toplevel` run from the spec's directory, and falls back
to the directory three levels above the spec's folder (the parent of `docs/`).

**Lint mode** prints one line per violation as `SPEC:LINE: RULE message` and
then a summary line. Exit 0 when clean, 1 on any violation, 2 on bad usage or
an unreadable file. Text inside fenced code blocks is ignored by every rule.
The rules:

| Rule | Check |
|---|---|
| `L1-status` | A Status bullet with one of the four values. |
| `L2-date` | A Date bullet in `YYYY-MM-DD` form. |
| `L3-section` | Each required H2 section is present. One violation per missing section. |
| `L4-out-of-scope` | An `**Out:**` marker in Scope, or an `## Out of scope` section, with at least one bullet after it. |
| `L5-placeholder` | No `TBD`, `TODO`, `FIXME`, `???` or `as discussed` (case-insensitive, whole word) anywhere outside backticked spans. No `etc.` outside backticked spans in the Scope or Success criteria sections. |
| `L6-empty` | No heading followed directly by a heading of the same or a higher level, or by end of file, with no text in between. |
| `L7-criterion` | Every top-level list item (`-`, `*` or `N.`) under Success criteria names how it is verified: it contains a backticked span, or one of the words `test`, `pytest`, `run`, `command`, `exit`, `output`, `prints`, `returns`, `asserts`, `manual`, `verify`, `check` (case-insensitive, whole word). |
| `L8-path` | Every backticked span that looks like a repo path exists under `--root`, unless some line of the spec contains both that span and `(new)`, so a new file is marked once, where it is introduced. A span "looks like a repo path" when it contains `/`, has no whitespace, does not contain `<`, `>`, `*`, `$`, `{` or `://`, does not start with `-` or `~`, and either has a file extension or ends with `/`. |

**Hash mode** prints the SHA-256 hex digest of the spec's UTF-8 text, after
line endings are normalised to `\n` and the Status bullet line is removed. So
approving a spec (draft → approved) does not invalidate its gate record, but
any other edit does.

**Verify-record mode** reads `docs/superpowers/gates/<spec-basename>` (same
file name as the spec) under the root. It exits 0 when the record exists, its
`- **Verdict:** pass` line is present, and its `- **Spec SHA-256:**` value
equals the spec's current hash. Otherwise it prints the reason (`missing`,
`not passed`, `stale`) and exits 1.

Like the other kit scripts, it uses the standard library only.

### `plugin/skills/spec-gate/rubric.md`

The reviewer's instructions. The reviewer gets only the spec path, the repo,
and this file, never the conversation that produced the spec. It must:

1. **Dry-run plan.** Write the ordered list of implementation tasks it would
   plan from this spec. For each task, list every question it would have to
   ask before building. Each question the spec does not answer is a
   `blocking` finding.
2. **Ambiguity.** Find requirements with two reasonable readings that lead to
   different code or behaviour. Quote both readings.
3. **Contradictions** between sections, including Design versus Decisions
   versus Success criteria.
4. **Code claims.** Check every statement about existing code, files, commands
   or behaviour against the repo. A false claim is `blocking`.
5. **Checkability.** For each success criterion, say how it would be checked.
   A criterion with no objective check is `blocking`.
6. **Scope size.** If the dry-run plan has more than 15 tasks, or covers
   two or more independent subsystems, raise a `blocking` finding proposing a
   split.
7. **Key decisions.** List the decisions the spec makes about scope,
   architecture, product boundary, data or irreversible actions, or the
   interpretation of the request. These are not findings. They are what the
   user confirms.

Output format (the gate parses it by hand, not by script):

```
## Dry-run plan
1. <task> — questions: <q1>; <q2> | none

## Findings
### [blocking] <title>
- **Line:** <spec line number or section>
- **Problem:** <what is wrong, quoting the spec>
- **Fix:** <a concrete change to the spec>

### [minor] <title>
...

## Key decisions
- <decision> (<section>)
```

`blocking` means `/ship` would have to guess, stop, or would build the wrong
thing. `minor` is wording or clarity that does not change what gets built.
The reviewer flags only; it never edits the spec.

### `plugin/skills/spec-gate/SKILL.md`

`/spec-gate <spec.md>` (default: the newest spec under
`docs/superpowers/specs/`). The procedure:

1. **Lint.** Run `spec-lint.py` on the spec, fix every violation, and re-run
   until it exits 0.
2. **Review round.** Dispatch a new general-purpose subagent with the spec
   path and `rubric.md`. Each round uses a new subagent, never a reused one,
   so the reviewer is never anchored on its earlier findings.
3. **Fix.** For each `blocking` finding:
   - If the fix needs a scope, product or behaviour choice the spec and
     conversation do not settle, it is a **decision finding**. Do not guess;
     collect it for the user.
   - Otherwise edit the spec to fix it. Fix `minor` findings too when the fix
     is clear. Re-run the linter after edits.
4. **Repeat** steps 2 and 3 until a round returns no `blocking` findings, up
   to 3 rounds in total.
5. **Verdict.**
   - **pass:** the linter is clean, the last round had no `blocking` findings,
     and there are no decision findings.
   - **fail:** anything else (blocking findings left after round 3, or any
     decision finding).
6. **Record.** Write `docs/superpowers/gates/<spec-basename>`:

   ```
   # Gate: <spec title>

   - **Spec:** docs/superpowers/specs/<spec-basename>
   - **Spec SHA-256:** <output of spec-lint.py --hash>
   - **Verdict:** pass | fail
   - **Date:** YYYY-MM-DD
   - **Rounds:** <n>

   ## Key decisions
   ## Findings fixed
   ## Open
   ```

   `Open` lists the decision findings and unresolved blocking findings, or
   says `none`. The hash is computed after the last spec edit.
7. **Report to the user.** One short message:
   - **pass:** "Gate passed in N rounds." Then the key decisions as a list,
     the count of findings fixed, the spec path (per `CLAUDE.md`, the path
     only; never open the spec), then "OK to mark it approved?". On yes, set
     the spec's Status to `approved`.
   - **fail:** "Gate failed." Then each decision finding as a direct question,
     with options and a recommendation. After the user answers, update the
     spec and rerun the gate from step 1.

### `/ship` changes (`plugin/commands/ship.md`)

- **New step 0, Gate.** Run `spec-lint.py --verify-record <spec>`. On exit 0,
  continue. Otherwise run the `claude-kit:spec-gate` procedure (steps 1–6;
  step 7's question is skipped, since invoking `/ship` is the approval). On a
  pass, continue; this also covers specs never gated before.
- **New stop rule.** The gate fails in step 0. Stop and report the gate
  record's Open items.
- **Step 2.** The gate record is copied into the worktree and committed
  alongside the spec, under the same untracked-and-identical rules as the
  spec.

### Enforcement outside `/ship`

Workspace `CLAUDE.md`, "Specs and plans": after writing or revising a spec,
run `claude-kit:spec-gate` on it before asking the user to review it. The
user's review is the gate's one-line verdict, not a read of the spec.

## Decisions

- **Two layers (linter + reviewer)** over a linter only (cannot judge meaning,
  so not rigorous enough to replace the user's read), or a reviewer only (no
  deterministic floor; results vary).
- **A gate pass needs the user's one-line OK** rather than approving the spec
  automatically. This keeps the "verify key decisions with me" rule while
  removing the full read. Under `/ship`, the invocation itself is that OK.
- **A new reviewer per round, with no conversation context.** It reads the
  spec as `/ship` will. Reusing a reviewer anchors it on its earlier findings.
- **A dry-run plan as the core probe.** An unanswered implementer question is
  exactly the gap that fires a `/ship` stop rule later, so it is found before
  building.
- **Decision findings go to the user, never to the author.** The author fixes
  defects but does not settle open product choices by itself.
- **The hash ignores only the Status line**, so approval does not invalidate
  the record but any content edit does.
- **Gate records are tracked files in `docs/superpowers/gates/`** rather than
  a field inside the spec (editing the spec to record its own hash would
  change the hash) or a gitignored file (`/ship` and later sessions need it).
- **Enforced via `CLAUDE.md` and `/ship`**, because the brainstorming skill
  belongs to the superpowers plugin and is not edited by the kit.
- **The reviewer eval is manual, not in CI.** It costs money and its results
  vary; the linter's deterministic tests are what CI gates on.

## Success criteria

1. **Linter tests pass.** `pytest tests/test_spec_lint.py` passes, with, for
   each rule `L1`–`L8`, a fixture that violates only that rule and asserts the
   exact rule ID, line number and exit code 1. A fully compliant fixture exits
   0, and a missing file exits 2.
2. **Hash behaviour is tested.** A test asserts that changing only the Status
   line keeps `--hash` output the same, and that changing any other line
   changes it. Tests for `--verify-record` cover `missing`, `not passed`,
   `stale` (exit 1) and a valid record (exit 0).
3. **`/ship` wiring is tested.** `tests/test_ship_command.py` asserts that
   step 0 runs `spec-lint.py --verify-record`, that the Stop rules include a
   failed gate, and that step 2 mentions copying the gate record.
4. **The skill is wired.** A test asserts that `plugin/skills/spec-gate/SKILL.md`
   has `name: spec-gate` frontmatter and references `rubric.md` and
   `spec-lint.py`, and that `rubric.md` defines the `[blocking]` and `[minor]`
   finding headings.
5. **Back-test.** Run `spec-lint.py` on each of the four existing implemented
   specs in `docs/superpowers/specs/` and report the output in the PR. Every
   violation is classified as a real gap or a false alarm. Any rule with a
   false alarm is loosened, with a test added, before merge.
6. **Reviewer eval: catches seeded defects.** `tests/fixtures/spec-gate/` has
   six specs, each derived from a real kit spec with exactly one seeded
   defect:
   1. a requirement with two readings
   2. a decision left open
   3. an uncheckable criterion
   4. a false code claim (a named function that does not exist in the repo)
   5. two contradicting sections
   6. scope covering two independent subsystems

   Plus one clean control spec. Its `README.md` names the defect in each file
   and the manual eval steps. Run one reviewer pass (`rubric.md`, a fresh
   subagent) on each of the seven specs, twice. Pass when the seeded defect is
   reported as `blocking` in at least 5 of the 6 seeded specs on both runs,
   and the clean control gets at most 1 `blocking` finding per run. The table
   of hits is reported in the PR.
7. **End-to-end check.** After implementation, run the new `/spec-gate` on
   this spec in the feature worktree. Report its verdict and round count in
   the PR, and commit its gate record. Then `spec-lint.py --verify-record` on
   this spec exits 0. (Spec 2 will be gated the same way when it is written;
   that is not part of this PR.)
8. **The suite and lint pass.** `pytest` and
   `ruff check plugin tests; ruff format --check plugin tests` pass, locally
   and in CI.
