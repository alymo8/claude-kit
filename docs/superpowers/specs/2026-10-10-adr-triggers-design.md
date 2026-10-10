# ADR triggers: when a decision must, should, or need not get an ADR

- **Status:** approved
- **Date:** 2026-10-10

## Purpose

`conventions/decision-log.md` says to record a decision "whenever a choice is
significant and meant to stick". That leaves the call to judgment, and on
projects other than the kit the judgment drifts: ADRs stop being written.
This change replaces the judgment call with three explicit lists (MUST,
SHOULD, NOT REQUIRED), puts the same lists in every scaffolded repo, and makes
the spec gate check that a spec whose key decisions hit a MUST trigger
includes the ADR.

## Scope

**In:**
- `conventions/decision-log.md`: a new `## When to write one` section,
  replacing the paragraph that starts "Record a decision as an ADR whenever".
- `plugin/templates/project/knowledge/decisions/README.md`: the same three
  lists, between the opening paragraph and the index table.
- `plugin/skills/spec-gate/rubric.md`: a new check 8, **ADR triggers**.
- `tests/test_templates.py`: a test that the template lists match the
  convention's.
- `tests/test_spec_gate_skill.py`: a test that the rubric contains check 8.
- `knowledge/decisions/0027-adr-triggers.md` (new) and its row in
  `knowledge/decisions/README.md`. Use the next free number if 0027 is taken
  when this ships.
- `plugin/.claude-plugin/plugin.json` (minor version bump from the version on
  `main`), `tests/test_plugin_manifest.py` (the expected version), and
  `README.md` (one line naming the ADR triggers next to the spec gate).

**Out:**
- The plan gate. Plans add decisions too, but the plan gate already lists
  them for the user's sign-off; adding ADR checks there is a later change.
- Back-filling ADRs in existing repos.
- `/ship-fast`: it skips the gates by design (ADR 0024), so the check does
  not reach POCs.

## Design

### The three lists

The section text, identical in both files:

```markdown
## When to write one

**MUST** write an ADR when a decision:

- adopts, replaces or drops a framework, language, datastore, hosting
  platform, or external service or API the code depends on;
- changes an interface, data schema, or data retention that code or people
  outside the change rely on;
- chooses an authentication, authorization, security or privacy approach;
- changes how work is done in the repo: a workflow, a gate, a required CI
  check, or a convention;
- reverses or narrows an accepted ADR (write a new ADR and mark the old one
  `superseded`).

**SHOULD** write an ADR when a decision:

- picks one of several viable options and the rejected one was seriously
  considered, so someone could reasonably propose it again;
- is a deliberate workaround that looks wrong without its reason;
- departs from a workspace convention for this repo only.

**NOT REQUIRED:**

- choices that follow an existing ADR, convention or approved spec
  without changing it;
- internal details that are easy to reverse (names, file layout inside a
  module, private helpers);
- bug fixes and dependency version bumps;
- throwaway or `/ship-fast` POC repos, unless the POC is kept.

A decision that matches a NOT REQUIRED item needs no ADR, even if it also
matches a MUST or SHOULD trigger.
```

In `conventions/decision-log.md` the section replaces the paragraph
"Record a decision as an ADR whenever a choice is **significant and meant to
stick** … Routine, easily-reversed choices do not need one." The opening
paragraph stays.

In the template README the section goes after the opening paragraph,
followed by a new `## Index` heading directly above the index table, so the
section ends at a `## ` heading in both files. Everything else in the
template README is unchanged.

The kit's own `knowledge/decisions/README.md` is left as is: gating the kit
uses the fallback to its `conventions/decision-log.md` (see check 8).

### Spec gate check 8

Added to `plugin/skills/spec-gate/rubric.md` under `## What to check`, after
check 7, with this text:

```markdown
8. **ADR triggers.** Only when the repository has `knowledge/decisions/`
   (or the grandfathered `docs/decisions/`). For each key decision from
   check 7, decide whether it matches a MUST trigger under
   `## When to write one`. Read that section from the decisions directory's
   `README.md`; if the README has no such section, from
   `conventions/decision-log.md` in the repository, else from
   `../conventions/decision-log.md` (the workspace, one level up). If none
   of the three has the section, skip this check. A decision that matches a
   NOT REQUIRED item is not a match. If it matches and the spec's Scope In
   names no new or amended ADR file for it, that is a `blocking` finding of
   class `open-what`: quote the decision and the trigger it matches. Its
   fix is to add the ADR file to Scope In and a one-paragraph ADR summary
   to the Design. A SHOULD match is a `minor` finding that is reported
   only: never add an ADR to Scope In for it without the user.
   (In the kit repo, `conventions/decision-log.md` is the workspace
   convention itself.)
```

The spec gate's step 3 fixes a blocking finding itself when no
scope, product or behaviour choice is unsettled. A missing ADR for a MUST
match is such a case: the trigger list settles that the ADR is required. So
the gate adds the ADR to the spec, and the user sees it under the record's
"Findings fixed". `plugin/skills/spec-gate/SKILL.md` needs no change.

`open-what` already exists as a blocking class (the spec does not say
whether the ADR is part of the change). No new class is added, so the
severity rules and the gate record format are unchanged.

So a repo scaffolded before this change (no section in its README) falls
back to the workspace convention one level up. A repo cloned outside the
workspace with an old README skips the check, and so does a repo with
neither decisions directory.

### ADR 0027 (or the next free number)

`knowledge/decisions/0027-adr-triggers.md`, status `accepted`: context (ADR
discipline decays when the trigger is judgment), decision (the three lists,
and spec gate check 8 enforces MUST), consequences (specs that hit a trigger
carry an ADR; POCs are exempt because `/ship-fast` skips the gate).

## Decisions

- **Enforced in the spec gate, not only documented.** The user chose this.
  The gate adds a missing MUST ADR to the spec itself (listed under
  Findings fixed); SHOULD matches are only reported. Cost: specs grow an
  ADR file where they hit a MUST trigger.
- **Same lists in the convention and the template, tested equal.** The
  template copy travels with repos that are cloned outside the workspace.
- **Severity reuses `open-what`.** No change to the record format or the
  linter.
- **Plan gate unchanged** (see Out).

## Testing

- `tests/test_templates.py::test_adr_triggers_match_convention`: the text
  from `## When to write one` up to the next `## ` heading (or end of file) is
  identical in `conventions/decision-log.md` and the template's
  `knowledge/decisions/README.md`, and contains `**MUST**`, `**SHOULD**` and
  `**NOT REQUIRED:**`. The template README has `## Index` after the
  section.
- `tests/test_spec_gate_skill.py::test_rubric_checks_adr_triggers`: the
  rubric contains `**ADR triggers.**`, `knowledge/decisions/`,
  `When to write one`, `../conventions/decision-log.md` and `open-what`
  within check 8's paragraph.
- Existing `test_empty_index_template_matches_generator_output` is about the
  `docs/superpowers` index and is unaffected.

## Success criteria

1. `pytest`, `ruff check plugin tests` and `ruff format --check plugin tests`
   pass.
2. `pytest -k "adr_triggers"` runs the two new tests and both pass.
3. `conventions/decision-log.md` no longer contains the phrase
   "significant and meant to stick" (`grep` finds nothing).
4. A scaffold made with `scaffold.py --name t --stack python --parent <tmp>`
   has the `## When to write one` section in
   `knowledge/decisions/README.md`.
5. The ADR named in Scope In (0027, or the next free number if 0027 was
   taken) exists with a row in `knowledge/decisions/README.md`.
