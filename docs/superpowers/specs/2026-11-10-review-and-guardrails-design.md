# Two-axis review, surgical diffs, frozen evaluators, Merge Danger and a hardening retro

- **Status:** approved
- **Date:** 2026-11-10

## Purpose

`/ship` lands a spec on `main` with no check-ins, so its review step is the
last net before merge. Today that net is one broad reviewer (the
subagent-driven-development final review, or `superpowers:requesting-code-review`
on a resumed run). It does not check the repo's own written rules line by
line, does not check the diff against the spec for scope creep, and has no
rule that stops an implementer from editing the acceptance tests until they
pass. Mistakes found during a feature are recorded as learnings, but nothing
turns a repeated mechanical mistake into a check that catches it next time.

This change borrows five ideas from public skill repos, rewritten for the
kit (no text copied wholesale):

1. **Hardening retro** (from the `retro` skill in mattpocock/skills):
   `claude-kit:capture-learnings` gains a step that sorts the session's
   mistakes into mechanical ones (proposed as a lint rule, hook, test or CI
   check) and judgement calls (written to a standards file only the
   reviewer reads), and scans `CLAUDE.md` for bloat and no-op rules.
2. **Two-axis review** (from mattpocock/skills `code-review`): a new
   `claude-kit:review` skill runs a standards reviewer and a spec reviewer
   as two parallel fresh-context subagents; `/ship` step 6 runs it on every
   run.
3. **Surgical diffs and simplicity** (from the karpathy guidelines in
   multica-ai/andrej-karpathy-skills): new rules in
   `conventions/engineering-practices.md`, checked by the standards
   reviewer. The plugin itself is not installed.
4. **Frozen evaluator** (from karpathy/autoresearch, where the eval is
   read-only to the agent): a spec or plan can freeze its acceptance tests
   or eval harness; a diff check enforces it and a violation stops `/ship`.
5. **Merge Danger** (from mattpocock/skills `pr`): `/ship` and `/ship-fast`
   PR bodies, and the project PR template, state the door (one-way or
   two-way), the blast radius and the smallest visual of the change.

## Scope

**In:**
- `plugin/skills/review/SKILL.md` (new): the two-axis review skill (Design §2).
- `plugin/skills/review/standards-reviewer.md` (new): the standards reviewer prompt, with the smell baseline.
- `plugin/skills/review/spec-reviewer.md` (new): the spec reviewer prompt.
- `tests/test_review_skill.py` (new): structure tests for the review skill.
- `plugin/scripts/frozen-check.py` (new): the frozen-file diff check (Design §4).
- `tests/test_frozen_check.py` (new): unit tests for the script on temporary git repos.
- `plugin/references/pr-body.md` (new): the PR body rules for `/ship` and `/ship-fast` (Design §5).
- `plugin/commands/ship.md`: new stop rule, step 3 prompt line, step 4 constraint, frozen check before pushes, step 6 rewritten, step 7 body moved to the reference.
- `plugin/references/ship-finish.md`: frozen check after a rebase in step 9; step 12 reports the review axes (hardening proposals arrive through the Learnings summary it already reports).
- `plugin/commands/ship-fast.md`: a new stop rule for the frozen check.
- `plugin/references/ship-fast-finish.md`: frozen check before each push in step 7 and its CI fix loop; step 7 body points to `pr-body.md` (step 9 already reports the Learnings summary, which carries the hardening proposals).
- `plugin/skills/capture-learnings/SKILL.md`: new Harden step and summary lines (Design §1).
- `plugin/skills/spec-gate/rubric.md`: one new minor-finding check for a missing `Frozen:` line.
- `conventions/engineering-practices.md`: new "Surgical diffs and simplicity" subsection and Definition of done bullet (Design §3).
- `conventions/spec-driven-development.md`: the `**Frozen:**` field and the read-only rule (Design §4).
- `conventions/knowledge-layer.md`: one bullet naming the reviewer-only standards file (Design §1).
- `.github/PULL_REQUEST_TEMPLATE.md` (the kit's own copy, identical today) and `plugin/templates/project/.github/PULL_REQUEST_TEMPLATE.md`: a visual comment under `## What`, a `## Merge danger` section, the qualifier "introduced by the change" on the dead-code checkbox, and a new checkbox "The diff is surgical: every changed line traces to the spec or task".
- `tests/test_ship_command.py`, `tests/test_ship_fast_command.py`, `tests/test_capture_learnings_skill.py`, `tests/test_spec_gate_skill.py`, `tests/test_templates.py`: assertions for the new text (Testing).
- `knowledge/decisions/0041-two-axis-review-in-ship.md` (new), `knowledge/decisions/0042-frozen-evaluator-diff-check.md` (new), `knowledge/decisions/0043-harden-in-capture-learnings.md` (new), `knowledge/decisions/0044-surgical-diffs-and-simplicity.md` (new), `knowledge/decisions/0045-merge-danger-in-pr-bodies.md` (new), and their rows in `knowledge/decisions/README.md`.
- `README.md`: `review` added to the skills list; one sentence on the frozen check.
- `plugin/.claude-plugin/plugin.json`: minor version bump and the review skill named in the description.
- `tests/test_plugin_manifest.py`: the pinned version test follows the bump.
- `docs/superpowers/README.md`: index rows for this spec and its plan (regenerated by `spec-index.py`).

**Out:**
- Installing the multica-ai/andrej-karpathy-skills plugin, or any other
  third-party skill.
- Changing superpowers skills (subagent-driven-development, its final
  reviewer, `requesting-code-review`). The kit only adds its own review
  next to them and passes constraints through the slots they already have.
- Building mechanical checks automatically under `/ship` or `/ship-fast`
  (D3). They are proposed only.
- Deleting or rewriting `CLAUDE.md` rules automatically; the bloat scan
  reports only.
- A PreToolUse hook that blocks edits to frozen files (D5).
- `/ship-fast`'s quick review: it keeps the `code-review` skill (D6).
- `/ship-many`: it runs `/ship` per spec and inherits every change here
  without edits.
- The duplicate-function audit pass (a separate spec,
  `2026-11-10-duplicate-functions-audit-design.md`).
- Creating `knowledge/review-standards.md` in this repo; the first
  capture-learnings run that has a judgement-call finding creates it.

## Design

### 1. Harden step in `claude-kit:capture-learnings`

A new step 4, **Harden**, runs between today's Route (step 3) and Write and
commit (today's step 4, renumbered 5; Return becomes 6). Its inputs are the
same candidates step 1 collected, plus every review finding fixed in this
feature (from the review reports that reached the session) and every CI
failure's cause. Step 2's filter rules still apply (drop what is already
recorded at its destination).

For each **mistake** (something done wrong and then corrected, by a review,
CI, a failed command or the user), classify it:

- **Mechanical:** a fixed pattern a tool could detect without judgement: a
  banned API or import, a file-location or naming rule, a forbidden string,
  a missing file, a format. It becomes a proposal:
  `harden (mechanical): <mistake> → <lint rule | hook | test | CI check> in <file>: <the rule>`.
  Prefer extending a check the repo already has (read its lint config, test
  layout and `.github/workflows/` first); a check that exists but is not
  wired into CI or a pre-commit/pre-push hook is itself the proposal.
- **Judgement call:** needs reading the code in context (consistency with
  nearby code, naming that fits the domain, how much abstraction is
  enough). It is written to `knowledge/review-standards.md`, one terse
  imperative bullet under a `## Rules` heading, in the same `Capture
  learnings` commit. If the file does not exist, create it with
  frontmatter (`title: Review standards`, `status: stable`,
  `last_updated: <today>`, `sources: []`, as the knowledge-layer
  convention requires) and, if `knowledge/README.md` exists, a row in
  its map (that index is not loaded at session start), one line
  saying it is read by the standards reviewer of `claude-kit:review` and
  not by implementers, then `## Rules`. Never link this file from
  `CLAUDE.md` or any file an implementer loads at session start.

Then two report-only scans:

- **Steering bloat:** read the repo's root `CLAUDE.md` (and any nested
  `CLAUDE.md`). Flag each rule that is a no-op (restates default behaviour
  or something a tool already enforces), a duplicate, one that should be a
  check (mechanical), or one that should move to `knowledge/review-standards.md`
  (judgement, only relevant at review). Line:
  `harden (steering): <file>:<line> <no-op | duplicate | to-check | to-standards>: <why>`.
  Do not edit these files for this scan.
- **Navigation and information access:** when the session spent many
  tool calls finding a file, or lacked a piece of information (a log, a
  service's state), propose a pointer or an access path:
  `harden (navigation): <what was hard to find> → <pointer to add, where>`.

Mechanical proposals are never built in this step when the skill runs
under `/ship` or `/ship-fast`, including `/ship-many` children (D3). When
the user invokes the skill by hand,
after returning the summary it offers once to build the mechanical
proposals; it builds only on a yes, as a separate commit with its tests.

The Return step's summary gains a `Hardening:` block after the learnings
lines: one line per harden line above, or `Hardening: none`. Lines written
to `knowledge/review-standards.md` appear among the learnings as
`knowledge/review-standards.md: <rule>`.

### 2. `claude-kit:review` skill

Frontmatter: `name: review`; description: use when `/ship` reaches step 6,
or when the user asks for a review of a branch or diff against its spec and
the repo's rules; runs a standards reviewer and a spec reviewer as two
parallel fresh-context subagents and reports them side by side.
`argument-hint: [base-ref] [spec.md] [plan.md]`.

Steps:

1. **Pin the diff.** Base is the first argument, else `origin/main`.
   Confirm `git rev-parse <base>` resolves and `git diff <base>...HEAD` is
   non-empty; otherwise report that and stop. Record the commit list
   (`git log <base>..HEAD --oneline`).
2. **Find the spec.** The spec and plan arguments if given; else a plan
   under `docs/superpowers/plans/` on this branch whose `**Spec:**` line
   names a spec, else the newest spec changed on the branch. No spec found:
   the spec reviewer is skipped and the report says `Spec: no spec found`.
3. **Find the standards.** The repo's root `CLAUDE.md`,
   `knowledge/review-standards.md`, `CONTRIBUTING.md`, any
   `CODING_STANDARDS.md`, and the engineering-practices playbook (the
   repo's `conventions/engineering-practices.md`, else the path from the
   kit map). Only files that exist.
4. **Dispatch both reviewers in one message**, as new general-purpose
   subagents with no model override and no conversation context. Each
   prompt is the content of its prompt file with these filled in: the
   repo root, the diff command (`git diff <base>...HEAD`), the commit list,
   and either the standards file paths or the spec and plan paths. The
   standards reviewer also gets the output of `frozen-check.py` on the
   spec and plan (Design §4), run by this skill before dispatch; it
   never judges a frozen path from the raw diff, because files created
   on the branch and approved changes show there as changes.
   The spec reviewer is told that process files (the spec, plan, gate
   records, ADRs and `docs/superpowers/README.md`) are never scope
   creep.
5. **Report.** `## Standards` and `## Spec`, each the reviewer's findings
   lightly cleaned, never merged or reranked across axes. Then one line:
   findings per axis and the worst finding within each axis.

`standards-reviewer.md` tells the reviewer to read the standards files and
the diff, and to report each finding as: file and hunk, the rule broken
(standards file and quoted rule, or the baseline item), `hard` or
`judgement`, and a one-line fix. Hard findings are breaches of a written
repo rule. Baseline findings are always `judgement`, and a written repo
rule that endorses something wins over the baseline (suppress it). Skip
what a linter or formatter in the repo already enforces. Under 400 words.
The baseline it carries, in the kit's own wording:

- the 12 Fowler smells: Mysterious Name, Duplicated Code, Feature Envy,
  Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery,
  Divergent Change, Speculative Generality, Message Chains, Middle Man,
  Refused Bequest; each with one line on what it looks like in a diff and
  one on the usual fix;
- the surgical-diff and simplicity rules of Design §3, by name;
- the frozen rule: each `frozen: changed <path>` line in the
  `frozen-check.py` output it is given is a `hard` finding; nothing else
  about frozen paths is.

`spec-reviewer.md` tells the reviewer to read the spec (and plan) and the
diff, and report: (a) requirements missing or partial; (b) behaviour or
files in the diff the spec did not ask for (scope creep); (c) requirements
that look implemented but wrong. Each finding quotes the spec line. Under
400 words.

### `/ship` step 6

Step 6 becomes:

- If this session did not receive a final whole-branch review report in
  step 4 (for example a resumed run), first run
  `superpowers:requesting-code-review` on `origin/main..HEAD` and
  `superpowers:receiving-code-review`, as today.
- Then, on every run, run `claude-kit:review` with base `origin/main`, the
  spec and the plan. Fix every `hard` standards finding and every spec
  finding of kind (a) or (c) you can verify; remove scope creep (b) unless
  removing it breaks a requirement. Fix a `judgement` finding when the fix
  is small and clearly better; list the rest in the report. A finding that
  needs a scope, product or behaviour decision the spec does not settle is
  a stop rule, as today. Commit, re-run tests and lint, run the frozen
  check, push.

Step 12 reports the findings fixed and the judgement findings left, per
axis. The hardening proposals reach `/ship`'s step 12 and `/ship-fast`'s
step 9 reports through the Learnings summary's `Hardening:` block,
which both reports already include.

### 3. Surgical diffs and simplicity (`conventions/engineering-practices.md`)

A new subsection under §2 Coding standards, **Surgical diffs and
simplicity**:

- Every changed line traces to the spec, plan task or request. Do not
  reformat, rename or refactor code the change does not need.
- Unrelated dead code you notice: mention it (report or PR body); do not
  delete it.
- Remove only what your own change made unused (imports, variables,
  functions, files).
- No configurability nobody asked for, no abstraction with one caller, no
  error handling for cases that cannot happen.
- A change that deletes code and keeps the same behaviour is a win; prefer
  it to adding code.
- When the request is ambiguous, ask during design (brainstorming, spec).
  This never adds a check-in to `/ship` or `/ship-many`, whose approval
  covers the run (ADR 0018, ADR 0036): during execution, take the reading
  the spec most supports and note it.

The Definition of done gains: "The diff is surgical: every changed line
traces to the spec or task." Its existing "no dead code" wording, the
§2 bullet "No dead or commented-out code" and the PR templates'
checkbox all gain the qualifier "introduced by the change". The PR templates also gain the checkbox "The diff is surgical:
every changed line traces to the spec or task".

### 4. Frozen evaluator

**Field.** A spec or plan may carry, among its header bullets, a
`- **Frozen:**` bullet listing backticked repo-relative paths or globs: the
acceptance tests, eval harness or fixtures whose results decide "done".
`conventions/spec-driven-development.md` documents it: once the spec or
plan is approved, implementers never edit those files to make them pass
(a frozen file that does not exist yet is created once, exactly as the
plan gives it, and never changed after); a needed change goes back to
the user as a spec decision.

**Script.** `plugin/scripts/frozen-check.py <file.md> [<file.md> ...]
[--base REF] [--root DIR]`, standard library only, Python 3.11, in the
style of the other scripts (exit codes, `sys.stdout.reconfigure(encoding="utf-8")`).

- Reads the `- **Frozen:**` bullets (outside code fences) from every file
  given, and takes the union of their backticked spans as patterns.
- Base defaults to `git merge-base origin/main HEAD`; `--base REF` uses
  `git merge-base REF HEAD`.
- The frozen set: every path that matches a pattern (`fnmatch`, with `**`
  matching across `/`) among the paths in `git ls-tree -r --name-only` of
  the base or of `HEAD`, plus every path added anywhere in `base..HEAD`
  (`git log --diff-filter=A --name-only base..HEAD`), so a frozen file
  created on the branch and later deleted is still checked.
- For each frozen path, the **snapshot commit** is: the base if the path
  exists there; else the first commit in `base..HEAD` that adds it
  (`git log --diff-filter=A --reverse`). A later commit in `base..HEAD`
  whose message has a trailer line `Frozen-change-approved: <path>` moves
  the snapshot to that commit.
- Violation: `git diff --quiet <snapshot> HEAD -- <path>` is non-zero
  (changed or deleted).
- Output: no Frozen bullet in any file → `frozen: none declared`, exit 0.
  No violations → `frozen: ok (<n> files)`, exit 0. Violations → one line
  `frozen: changed <path> since <short snapshot>` each, exit 1. Bad usage,
  an unreadable file or a git failure → a message on stderr, exit 2.
- A pattern that matches no file is reported as
  `frozen: warning: no file matches <pattern>` and is not a violation.

**`/ship`.** A new stop rule: `frozen-check.py` exits 1. Report the
changed paths; the user answers by approving the change (the main session
then commits with a `Frozen-change-approved: <path>` trailer per path, and
only then) or by revising the spec. Implementers and subagents never write
that trailer.
- Step 3's plan prompt gains one sentence: copy the spec's `**Frozen:**`
  bullet into the plan header, adding any test or eval file whose full
  content the plan writes and that a success criterion depends on.
- Step 4: the global constraints passed to each implementer and task
  reviewer include "Files under Frozen (`<list>`) that exist are
  read-only. One that does not exist yet is created once, exactly as
  the plan gives it, and never changed after that commit. Report any
  other needed change as a blocker."
- Before every `git push` in steps 5, 6 and 9, run
  `python "${CLAUDE_PLUGIN_ROOT}/scripts/frozen-check.py" <spec> <plan>`
  (fallback `~/.claude/skills/claude-kit/scripts/frozen-check.py`).

**`/ship-fast`.** Before each push in `ship-fast-finish.md` step 7 and
its CI fix loop, the same check on its spec (its task list carries no
Frozen bullet); exit 1 is a new stop rule there too.

**`spec-gate`.** `rubric.md` gains one minor-finding check: a spec whose
Success criteria name a test or eval file (or a test suite the change adds)
but which has no `- **Frozen:**` bullet. The fix is to add one, or to say
in Decisions why nothing is frozen.

### 5. Merge Danger and the PR body

`plugin/references/pr-body.md` (new) holds the PR body rules. `ship.md`
step 7 replaces its body sentence with a pointer to it
(`${CLAUDE_PLUGIN_ROOT}/references/pr-body.md`, with the
`~/.claude/skills/claude-kit/references/pr-body.md` fallback);
`ship-fast-finish.md` step 7 does the same. The reference has a shared part
and one list per command.

Shared parts, in this order in both bodies:

- **Summary:** two to five lines, then the smallest visual that shows the
  change: pseudocode, a call tree, a file tree, a Mermaid diagram, or a
  `diff` sketch of one of those. One visual, two at most; none for a
  change that is only text, where a short before/after quote is used.
- **Merge danger:**
  `**Door:** one-way | two-way` with one line why. One-way when merging
  does something reverting the PR cannot undo: the irreversible test of
  `/ship` step 3a (deletes, overwrites or migrates data not regenerable
  from the repo, rewrites published history, or changes something outside
  the repo). Otherwise two-way.
  `**Blast radius:** <one word>` (for example `none`, `docs`, `one-command`,
  `all-sessions`, `consumers`) with one line on what could break.
- **Hardening proposals:** the `Hardening:` lines from capture-learnings;
  omitted when `none`.

`/ship` body order: Summary; links to the spec, plan and plan gate record;
Plan decisions section (unchanged rules); Merge danger; Review (the
findings per axis fixed and left, one line each); Hardening proposals;
Verification; attribution. `/ship-fast` body order: Summary; Acceptance
criteria with evidence; Decisions; Assumptions; Cut; Merge danger;
Hardening proposals; links; Verification; attribution (its existing items
unchanged).

`PULL_REQUEST_TEMPLATE.md` gains, after `## What`, a comment asking for the
smallest visual, and a `## Merge danger` section with `**Door:**` and
`**Blast radius:**` lines and a one-line comment explaining each.

### ADRs

- **0041 Two-axis review in `/ship`:** step 6 always runs
  `claude-kit:review` in addition to the superpowers final review; the two
  axes are reported apart. Amends ADR 0037: step 6 adds two diff-only
  reviewer subagents on every run. Alternatives: replace the final review; run it
  only when the final review did not run.
- **0042 Frozen evaluator as a diff check and a stop rule:** the
  `Frozen:` field, the snapshot rule and the trailer. Alternative: a
  PreToolUse hook (ADR 0007 makes hooks exit 0, so it cannot block).
- **0043 Harden step in capture-learnings:** mechanical mistakes proposed
  (not built) under `/ship`; judgement calls to a reviewer-only standards
  file; steering scan report-only. Alternatives: a separate `/retro`
  skill; `/ship`'s clean-up step.
- **0044 Surgical diffs and simplicity:** the Design §3 rules become a
  workspace convention and part of the Definition of done, checked by the
  standards reviewer; "ask when unsure" is limited to design.
  Alternative: install the karpathy-guidelines plugin, which duplicates
  most kit rules and loads every session.
- **0045 Merge Danger in PR bodies:** `/ship` and `/ship-fast` PR bodies
  and the project PR template state the door, the blast radius and the
  smallest visual; one-way uses step 3a's irreversible test.
  Alternative: keep the PR body as it is.

Numbers are taken from `origin/main` at implementation time
(`git ls-tree --name-only origin/main knowledge/decisions/`); 0040 is held
by another approved spec, so if any of 0041 to 0045 is taken on
`origin/main`, use the next free
numbers and update every reference in this change.

### Version

`plugin.json` gets the next minor version above the one on `origin/main`
when the plan is written; `test_version_is_*` in
`tests/test_plugin_manifest.py` is renamed and updated to it. On a rebase
conflict, take the next minor above `origin/main`'s.

### Size limits

`ship.md` must stay under 20,000 bytes (`tests/test_skill_size.py`); aim
for at most 18,500 after this change. If it would exceed that, move step 6's
text to `plugin/references/ship-review.md` with the same pointer pattern.
Prose added inside a `ship.md` step stays indented 3 spaces.

## Decisions

- **D1. Two specs; the user chose this split.** This spec carries the
  five Purpose items as one coherent review-and-guardrails change: the
  standards reviewer checks the surgical rules, the frozen check and
  the standards file the Harden step writes, and one version bump and
  one `/ship` run cover them. The duplicate-function audit pass is its
  own spec. Both ship with one `/ship-many` run, which puts them in
  successive waves because both change `plugin.json`, `README.md` and
  the manifest test. Rejected: one spec for everything; one spec per
  item, which would mean more version bumps and more `ship.md`
  conflicts for one coherent change.
- **D2. Retro extends capture-learnings.** It already runs at `/ship` and
  `/ship-fast` step 7, and the repo prefers folding into an existing step.
  Rejected: a separate `/retro` skill; `/ship`'s clean-up.
- **D3. Mechanical fixes are proposed, not built, under `/ship`.**
  Building a lint rule or hook inside a feature PR breaks the surgical-diff
  rule and grows the PR's scope. A hand run may build them after one yes.
- **D4. The two-axis review runs in addition to the final review.** The
  final review hunts bugs; the two axes check written rules and the spec.
  Cost: about two diff-only subagents per run, which shifts the lean-`/ship`
  token baseline. Rejected: replacing the final review; running only when
  it did not run.
- **D5. Frozen files are enforced by a diff check, not a hook.** Hooks
  always exit 0 (ADR 0007) and cannot block an edit; a diff check before
  each push catches every path, including subagents in task worktrees.
- **D6. `/ship-fast` gets Merge Danger and the frozen check, and keeps its
  quick `code-review`.** It is for POCs with no review round. Its spec
  interview does not add a `Frozen:` bullet; the check acts only when the
  user adds one by hand, and otherwise prints `frozen: none declared`.
- **D7. The snapshot moves only on a `Frozen-change-approved:` trailer
  written by the main session after the user approves.** (My call.)
  Rejected: editing the spec's Frozen bullet to unfreeze a path, which
  changes the spec hash and forces a re-gate of spec and plan for a
  one-file change.
- **D8. Reviewer-only standards live at `knowledge/review-standards.md`.**
  (My call.) It follows the knowledge layer and is never linked from
  `CLAUDE.md`. Rejected: a root `CODING_STANDARDS.md`, which the review
  skill still reads when a repo has one.
- **D9. Reviewers run on the session's model, with no override.** (My
  call.) As `/ship`'s other subagents.
- **D10. Nothing is frozen in this change.** (My call.) Its tests are
  structure tests that evolve with the text they check.

## Testing

`tests/test_frozen_check.py` builds temporary git repos (`git init`, a
`main` branch as base, commits on a feature branch; `--base main`) and
runs the script with `subprocess`:

- No Frozen bullet → `frozen: none declared`, exit 0.
- A frozen file present at the base and untouched → `frozen: ok (1 files)`,
  exit 0.
- A frozen file present at the base and modified on the branch → exit 1,
  the path in the output.
- A frozen file present at the base and deleted on the branch → exit 1.
- A frozen file created on the branch and never edited after → exit 0.
- A frozen file created on the branch and edited in a later commit →
  exit 1.
- A frozen file created on the branch and deleted in a later commit →
  exit 1.
- The same edit in a commit with `Frozen-change-approved: <path>` → exit 0;
  a further edit after it → exit 1.
- A glob (`tests/acceptance/**`) matches nested files; a pattern matching
  nothing prints the warning and exits 0.
- Bullets in two files (spec and plan) are united.
- A Frozen bullet inside a code fence is ignored.
- A missing input file → exit 2.

`tests/test_review_skill.py`:

- Frontmatter `name: review` and a description.
- `SKILL.md` names both prompt files, dispatches both reviewers in one
  message, and has `## Standards` and `## Spec` in its report.
- `standards-reviewer.md` names all 12 smells, says `judgement`, says the
  repo's rules override the baseline, names each Design §3 rule, and
  ties the frozen rule to `frozen-check.py` output. `SKILL.md` runs
  `frozen-check.py` and says process files are never scope creep.
- `spec-reviewer.md` names missing requirements, scope creep and wrong
  implementations, and asks for the spec line to be quoted.

Additions to existing tests:

- `test_ship_command.py`: the frozen stop rule is in the Stop rules
  (normalised whitespace); step 6 names `claude-kit:review`; step 4
  names the read-only Frozen constraint; `frozen-check.py` appears; the
  command text (with references inlined) names `pr-body.md`, `Door` and
  `Blast radius`.
- `test_ship_fast_command.py`: `frozen-check.py` and `pr-body.md` appear;
  `code-review` is still the quick review.
- `test_capture_learnings_skill.py`: the skill has `Harden`, `mechanical`,
  `judgement`, `knowledge/review-standards.md`, `Hardening:`, and says the
  steering scan does not edit.
- `test_spec_gate_skill.py`: `rubric.md` mentions `Frozen`.
- `test_templates.py`: both PR templates have `Merge danger`, `Door`,
  `Blast radius` and `surgical`.

## Success criteria

1. `pytest` passes, including the tests above; check: `pytest`.
2. `ruff check plugin tests` and `ruff format --check plugin tests` are
   clean; check: run both.
3. Every SKILL.md and command stays under 20,000 bytes and `ship.md` is at
   most 18,500; check: `pytest tests/test_skill_size.py` and `wc -c
   plugin/commands/ship.md`.
4. `frozen-check.py` on this change's own spec and plan prints
   `frozen: none declared` or `frozen: ok`; check: run it from the feature
   worktree before the PR.
5. Live check after merge: run `claude-kit:review` on the merged change
   (`<squash-commit>~1` as base, this spec and its plan) and record the
   finding counts per axis in `/ship`'s final report message; check:
   that message lists them.
6. No username or private repo name is in the diff; check:
   `git diff origin/main | grep -i -E "<pattern>"` returns nothing, where
   `<pattern>` is the machine's username plus every name from
   `gh repo list --visibility private --json name -q ".[].name"`, joined
   with `|`.
7. The PR is squash-merged by `/ship` with green CI; check: `gh pr checks`
   and `/ship`'s step 10 verification.
