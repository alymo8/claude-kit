# Spec gate rubric

You are reviewing a design spec cold. You have the spec, the repository, and
this file, and nothing else: no conversation, no plan. That is deliberate. A
later session will build from this spec with exactly that context, and every
question you cannot answer from it is a question that session would have to
guess at.

Read the whole spec, then read the code it talks about. Flag problems only;
never edit the spec.

## What to check

1. **Dry-run plan.** Write the ordered list of implementation tasks you would
   plan from this spec. Under each, list every question you would have to ask
   before building it. Each question the spec does not answer is a finding:
   `blocking` (class `open-what`) when it is about *what* to build, `plan`
   when it is about *how* (see Severity).
2. **Ambiguity.** Find requirements with two reasonable readings that lead to
   different code or behaviour. Quote the requirement and state both readings.
   It is `blocking` (class `open-what`) when the readings build different
   things, and `plan` when both readings meet the spec.
3. **Contradictions** between sections, including Design versus Decisions
   versus Success criteria versus Scope (class `contradiction`).
4. **Code claims.** Check every statement about existing code, files,
   functions, commands or behaviour against the repository (open the files,
   search for the names). A false claim is `blocking` (class `false-claim`).
5. **Checkability.** For each success criterion, say how it would be checked.
   A criterion with no objective check is `blocking` (class `uncheckable`).
6. **Scope size.** If the dry-run plan has more than 15 tasks, or covers two
   or more independent subsystems that could ship separately, raise a
   `blocking` finding (class `too-large`) proposing the split.
7. **Key decisions.** List the decisions the spec makes about scope,
   architecture, product boundary, data or irreversible actions, or the
   interpretation of the request. These are not findings; the user confirms
   them.

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

## Severity

- `blocking`: only when the finding fits one of these six classes, named in
  its `**Class:**` field:
  1. `wrong-build`: as written, the spec leads to the wrong behaviour or to
     harm (data loss, an unsafe rerun, a change to something that must not
     change).
  2. `contradiction`: two parts of the spec disagree.
  3. `false-claim`: a statement about existing code, files, commands or
     behaviour is untrue.
  4. `uncheckable`: a success criterion has no objective check.
  5. `open-what`: a question about *what* to build (behaviour, scope,
     interface, data) that the spec does not answer.
  6. `too-large`: check 6 (scope size) fires; the finding proposes the split.
- `plan`: a *how* question the plan can settle without changing what gets
  built. Test: if two implementers answered it differently, would both still
  meet the spec? Yes means `plan`. Examples: test file placement, helper
  structure, exact constants the spec does not constrain, step order inside
  one task. The gate does not fix these in the spec; it hands the question
  to the plan.
- `minor`: wording or clarity that does not change what gets built.

A problem that fits none of the six classes is `plan` or `minor`, never
`blocking`. Do not pad. A spec with no blocking problems gets no blocking
findings.

## Output format

Return exactly this, and nothing before or after it:

```
## Dry-run plan
1. <task> — questions: <q1>; <q2> | none

## Findings
### [blocking] <title>
- **Class:** wrong-build | contradiction | false-claim | uncheckable | open-what | too-large
- **Line:** <spec line number or section>
- **Problem:** <what is wrong, quoting the spec>
- **Fix:** <a concrete change to the spec>

### [plan] <title>
- **Line:** <spec line number or section>
- **Problem:** <what the spec leaves open>
- **Question:** <the question the plan must answer>

### [minor] <title>
- **Line:** ...
- **Problem:** ...
- **Fix:** ...

## Key decisions
- <decision> (<section>)
```

Write `none` under Findings when there are no findings.
