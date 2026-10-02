# Spec grill: an opt-in interview before the spec is written

- **Status:** implemented
- **Date:** 2026-10-01

## Purpose

Specs fail in two ways that the kit only catches late:

1. **Whole areas are never considered** (failure modes, security, rollout,
   data that cannot be undone). Nothing walks a checklist of areas, so a gap
   is noticed only if someone happens to think of it.
2. **Decisions are made silently.** Brainstorming asks clarifying questions
   until the model feels it understands, then the spec fills the rest with
   guesses. The spec gate (ADR 0015) finds some of these afterwards as
   decision findings, and `/ship` stops on the rest.

This work adds a **grill**: a structured interview that runs after the
brainstorming design summary and before the spec is written. It is adapted
from the `grilling` skill in `mattpocock/skills` (MIT). It walks the agreed
design as a tree of decisions plus a fixed **coverage checklist**, asks the
user every open decision in numbered rounds with a recommended answer each,
looks facts up instead of asking, and ends only when the user confirms a
shared understanding. The spec then records the result in a required
`## Coverage` section, which `spec-lint.py` checks.

The grill is **opt-in**: off unless `CLAUDE_KIT_GRILL=1`, following the
env-switch pattern of ADR 0014. The spec gate stays as the backstop.

## Scope

**In:**

- `plugin/skills/grill/SKILL.md` (new): the grill procedure, invocable as
  `/grill [topic]`.
- `plugin/skills/grill/coverage.md` (new): the coverage checklist; the single
  source of the area names that the linter reads.
- `plugin/hooks/grill_inject.py` (new): SessionStart hook that injects the
  grill rule when `CLAUDE_KIT_GRILL=1`.
- `plugin/hooks/hooks.json`: register `grill_inject.py` under SessionStart,
  in its own group with no matcher, like `lean_context_inject.py`.
- `plugin/scripts/spec-lint.py`: new rule `L9-coverage`, plus its docstring
  entry.
- `CLAUDE.md` (workspace): one sentence appended to "Designing a spec":
  "With `CLAUDE_KIT_GRILL=1`, the `claude-kit:grill` skill runs between the
  design summary and the spec (ADR 0019); its rounds and the
  shared-understanding confirmation are the only pause." The existing text of
  that section, including "no approval pause between design sections", stays
  unchanged.
- `conventions/spec-driven-development.md`: the grill stage between Brainstorm
  and Spec, and the `## Coverage` section format.
- `README.md`: the grill in the feature list, and in the workflow diagram's
  `decide` subgraph a new node `grill["Grill (opt-in)<br/>decisions +
  coverage"]:::gate` with the edge chain `brain --> dec --> spec --> sgate --> sok`
  becoming `brain --> dec --> grill --> spec --> sgate --> sok`.
- `knowledge/decisions/0019-spec-grill-opt-in.md` (new) and a row for it in
  `knowledge/decisions/README.md`.
- `plugin/.claude-plugin/plugin.json`: version 0.10.0 → 0.11.0 and "grill" in
  the description.
- Tests: `tests/test_grill_inject.py` (new), `tests/test_grill_skill.py` (new),
  additions to `tests/test_spec_lint.py` and `tests/test_plugin_manifest.py`.

**Out:**

- Editing `superpowers:brainstorming` (not ours). The grill is wired in by the
  injected rule, as the spec gate is wired in by `CLAUDE.md`.
- Backfilling `## Coverage` into specs dated before 2026-10-01.
- Teaching the spec-gate reviewer rubric to judge the quality of Coverage
  entries (for example, whether an N/A reason is true). Possible follow-up.
- Grilling implementation plans.
- A cap on the number of questions or rounds; the user steers by saying
  "wrap up".
- Installing Matt Pocock's skills themselves.

## Design

### Flow

With the switch on, spec design runs:
brainstorm (questions, approaches, one design summary) → **grill** → user
confirms shared understanding → write spec (with `## Coverage`) → spec gate →
user signs off. With the switch off, the grill step is skipped and nothing
else changes; `/grill` still works when invoked by hand.

### The switch

`CLAUDE_KIT_GRILL`, set under `env` in `~/.claude/settings.json`, effective
from the next session. Exactly `"1"` means on; unset or any other value means
off. It controls two things only: the injected rule and lint rule `L9-coverage`.
The skill stays model-invocable either way, because the injected rule needs
the model to call it.

### `plugin/hooks/grill_inject.py`

Same shape as `lean_context_inject.py`: reads the env var, and when on prints
SessionStart JSON with `additionalContext` set to this rule:

> Spec grill is on (CLAUDE_KIT_GRILL=1). When designing a spec, after
> presenting the design summary and before writing the spec, run the
> `claude-kit:grill` skill on the agreed design. Write the spec only after the
> user confirms a shared understanding, and give it a `## Coverage` section in
> the format the skill describes.

When off it prints nothing. It always exits 0 (ADR 0007); an exception is
reported on stderr as `[claude-kit] grill inject error: ...`.

### `plugin/skills/grill/coverage.md`

A `## Areas` section with one bullet per area, `- **<Name>:** <guiding
question>`. The nine areas, in order:

1. **Purpose and success:** what outcome, for whom, and how is "done and
   correct" checked?
2. **Scope boundary:** what is explicitly out, and what is deferred?
3. **Interfaces:** which commands, files, APIs or formats do others depend on,
   and do any change?
4. **Data and irreversible actions:** what is written, deleted, migrated or
   published, and can it be undone?
5. **Failure modes:** what happens on bad input, partial failure, or a
   missing dependency?
6. **Security and secrets:** what is trusted, what touches credentials or
   external input?
7. **Testing:** which tests prove each success criterion?
8. **Rollout and compatibility:** what existing users, files or settings are
   affected, and how is the change switched on?
9. **Docs and decisions:** which docs change, and which choices deserve an
   ADR?

The file also states the `## Coverage` format below. The linter reads area
names from this file, so adding an area updates both the grill and the lint.

### `plugin/skills/grill/SKILL.md`

Frontmatter: `name: grill`, a description that says to use it when the
injected grill rule applies or the user asks to be grilled, and
`argument-hint: [topic]`. The body credits `mattpocock/skills` `grilling`
(MIT) and defines:

1. **Tree.** The decisions the agreed design makes or leaves open, plus each
   area in `coverage.md`. With no design in the conversation, the topic in
   `$ARGUMENTS` is the subject.
2. **Facts versus decisions.** Facts are the grill's job: read the repo or
   dispatch an Explore subagent; never ask the user what can be looked up.
   Only the questions that depend on a running lookup wait for it. An area may
   be closed as N/A without asking **only** when a fact settles it, and the
   fact is stated. Every decision goes to the user; the grill never answers
   its own decision questions.
3. **Rounds.** Each round asks the whole frontier (every open decision whose
   prerequisites are settled) and nothing that depends on another question in
   the same round. Format, questions separated by `---`:

   ```
   ❓ **Q1 - <title>**: <question, with options when there are any>

   ➡️ <recommended answer and one-line reason>
   ```

   If the user's instructions ask for one question at a time, ask one per
   message instead.
4. **End.** When the frontier is empty, post a grill summary: the decisions
   settled (question → answer), and each coverage area as addressed (where in
   the design) or N/A (the reason). Ask the user to confirm a shared
   understanding, and wait. Do not write the spec or act until they confirm.
5. **Hand-off.** The settled decisions go into the spec's `## Decisions`; the
   coverage list becomes its `## Coverage` section.

### `## Coverage` section format

```
## Coverage

- **Purpose and success:** Purpose; Success criteria.
- **Security and secrets:** N/A: reads only files in the repo, no credentials.
```

One bullet per area, named exactly as in `coverage.md` (case-insensitive).
The text says where the spec addresses the area, or `N/A` followed by a
reason.

### Lint rule `L9-coverage`

Applies only when `CLAUDE_KIT_GRILL` is exactly `1` **and** the spec's Date
value parses with `datetime.date.fromisoformat` to a date on or after
2026-10-01 (the constant `COVERAGE_FROM`). A Date that fails to parse skips
L9; a malformed one is already reported by L2. Plans are never checked.

An entry's text is the rest of its label line after the label plus its
indented continuation lines. Bullets for areas not in `coverage.md` are
ignored; when an area is listed twice, the first bullet is checked.
Violations:

- no `## Coverage` H2 section (one violation, line 1);
- an area from `coverage.md` with no `- **<Name>:**` bullet in that section
  (one violation per area, at the section heading);
- an area bullet with no text after the label, or whose text is `N/A` with no
  reason after it (`N/A` matched case-insensitively; stripping `:`, `-`,
  `–`, `—` and spaces), reported at the bullet's line;
- `coverage.md` cannot be read: one violation naming the expected path, so a
  broken install is never silent.

The linter finds `coverage.md` at
`<spec-lint.py's folder>/../skills/grill/coverage.md`, which holds in the repo
and in the installed skills-dir junction (ADR 0005). Area names are the bold
labels of the bullets under `## Areas`. Other rules are unchanged.
`--hash` and `--verify-record` are unchanged.

## Decisions

- **A separate pass after the design, not a replacement for brainstorming's
  questions** (user's choice B). Brainstorming stays as it is; the grill walks
  the agreed design and the checklist.
- **Opt-in, off by default** (`CLAUDE_KIT_GRILL=1`). It is new and changes how
  spec design feels; the default can be flipped later in a new ADR.
- **The switch gates the injected rule and `L9-coverage`, not the skill.**
  `/grill` always works by hand; disabling the skill would also break the
  automatic stage.
- **Coverage is recorded in the spec and linted**, so downstream steps can
  see that the grill ran and what it concluded.
- **`L9-coverage` checks only specs dated on or after 2026-10-01**, so older
  specs never fail.
- **Rounds by default**, with the user's one-at-a-time instruction honoured.
- **Every spec is grilled when the switch is on**; the switch is the way out,
  so there is no per-spec skip.
- **One source for area names** (`coverage.md`, read by the linter) instead of
  a copy in the linter kept in sync by a test.

## Coverage

- **Purpose and success:** Purpose; Success criteria.
- **Scope boundary:** Scope, Out list.
- **Interfaces:** Design: the switch, the hook output, `L9-coverage`, the
  `## Coverage` format; `/grill` is a new command.
- **Data and irreversible actions:** N/A: writes only repo files under review;
  no deletes, migrations or publishing.
- **Failure modes:** Design: hook never raises and exits 0; unreadable
  `coverage.md` is a lint violation; a Date that does not parse as a
  calendar date skips `L9-coverage`.
- **Security and secrets:** N/A: reads repo files and one env var; no
  credentials or external input.
- **Testing:** Success criteria.
- **Rollout and compatibility:** Design, The switch: off by default, so
  nothing changes until a user opts in; old specs exempt by date.
- **Docs and decisions:** Scope In: `CLAUDE.md`, conventions, `README.md`,
  ADR 0019.

## Success criteria

1. `pytest` passes, including the new tests below, and `ruff check plugin
   tests` and `ruff format --check plugin tests` are clean.
2. `tests/test_grill_inject.py`: with `CLAUDE_KIT_GRILL=1` the hook exits 0
   and its `additionalContext` contains `claude-kit:grill`; unset, `0`, empty,
   `true` and `yes` each produce empty stdout and exit 0.
3. `tests/test_spec_lint.py` asserts, for a spec dated 2026-10-01 or later
   with `CLAUDE_KIT_GRILL=1`: a full `## Coverage` passes; a missing section,
   a missing area, an empty area and a bare `N/A` each report `L9-coverage`.
   It also asserts no `L9-coverage` when the switch is unset, when the Date is
   2026-09-30, and for a plan; and a violation naming the path when
   `coverage.md` is missing (the test points the linter at a temporary copy
   of the plugin folder without it). Every L9 test sets or deletes
   `CLAUDE_KIT_GRILL` itself (`monkeypatch` in-process, `clean_env` for CLI
   runs), so results never depend on the developer's settings.
4. `tests/test_grill_skill.py` checks that `SKILL.md` has `name: grill`, an
   `argument-hint`, the `➡️` round format, "shared understanding", the
   `coverage.md` reference and the MIT credit; and that `coverage.md` has
   exactly the nine areas, in order, under `## Areas`.
5. `tests/test_plugin_manifest.py` checks that `hooks.json` registers
   `grill_inject.py` under SessionStart and that the description mentions
   "grill".
6. Every existing spec under `docs/superpowers/specs/` lints with no
   `L9-coverage` violation with the switch on, verified by running
   `spec-lint.py` on each.
7. This spec passes `spec-lint.py` with `CLAUDE_KIT_GRILL=1` (it carries its
   own `## Coverage`) and passes the spec gate.
