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
   before building it. Each question the spec does not answer is a `blocking`
   finding.
2. **Ambiguity.** Find requirements with two reasonable readings that lead to
   different code or behaviour. Quote the requirement and state both readings.
3. **Contradictions** between sections, including Design versus Decisions
   versus Success criteria versus Scope.
4. **Code claims.** Check every statement about existing code, files,
   functions, commands or behaviour against the repository (open the files,
   search for the names). A false claim is `blocking`.
5. **Checkability.** For each success criterion, say how it would be checked.
   A criterion with no objective check is `blocking`.
6. **Scope size.** If the dry-run plan has more than 15 tasks, or covers two
   or more independent subsystems that could ship separately, raise a
   `blocking` finding proposing the split.
7. **Key decisions.** List the decisions the spec makes about scope,
   architecture, product boundary, data or irreversible actions, or the
   interpretation of the request. These are not findings; the user confirms
   them.

## Severity

- `blocking`: an implementer would have to guess or stop, or would build the
  wrong thing.
- `minor`: wording or clarity that does not change what gets built.

Do not pad. A spec with no blocking problems gets no blocking findings.

## Output format

Return exactly this, and nothing before or after it:

```
## Dry-run plan
1. <task> — questions: <q1>; <q2> | none

## Findings
### [blocking] <title>
- **Line:** <spec line number or section>
- **Problem:** <what is wrong, quoting the spec>
- **Fix:** <a concrete change to the spec>

### [minor] <title>
- **Line:** ...
- **Problem:** ...
- **Fix:** ...

## Key decisions
- <decision> (<section>)
```

Write `none` under Findings when there are no findings.
