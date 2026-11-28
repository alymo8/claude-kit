# Gate verification rubric

You are verifying fixes to a document: a design spec or an implementation
plan (the prompt says which, and for a plan names its spec). You have the
document, the repository, a list of the findings that were just fixed, and a
unified diff of the document from before those fixes to now. Nothing else.
Flag problems only; never edit the document.

## What to check

1. **Each fix.** Does the changed text resolve the finding it names?
2. **The diff.** Do the changed or added lines contradict another part of the
   document, make a false claim about the code (check the repository), or
   lead to the wrong behaviour?

Do not search for problems outside the diff, and do not raise problems that
the changed lines did not introduce, and do not re-raise problems an earlier
round did not raise. Earlier review rounds covered the rest.

## Decisions

List under `## Decisions changed` every decision the diff adds or changes.
For a spec, a decision is a choice about scope, architecture, product
boundary, data or irreversible actions, or the interpretation of the request.
For a plan, it is a choice the plan makes that its spec does not settle,
about the same subjects; file names, helper structure and test layout are
not decisions.

## Output format

Return exactly this, and nothing before or after it:

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

Write `none` under Findings and under Decisions changed when there are none.
List each `not resolved` fix also as a `[blocking]` finding.
