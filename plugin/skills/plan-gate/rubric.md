# Plan gate rubric

You are reviewing an implementation plan cold, against the spec it
implements. You have the plan, the spec, the repository and this file, and
nothing else: no conversation. That is deliberate. The executor will build
from this plan with exactly that context, and every question you cannot
answer from it is a question the executor would have to guess at.

Read the whole spec and the whole plan, then read the code the plan talks
about. Flag problems only; never edit the plan or the spec.

## What to check

1. **Coverage map.** For each In-scope item and each success criterion in the
   spec, name the task or tasks that deliver it. An unmapped item is
   `blocking`. Plan work that no spec item asks for is `blocking`
   (scope creep).
2. **Cold execution.** For each task, list what an executor with only the
   repository and this plan would have to ask before doing it. Each question
   the plan does not answer is `blocking`.
3. **Order.** A task that uses a file, function or command that only a later
   task creates is `blocking`.
4. **Code claims.** Check every existing path, function, command or behaviour
   the plan relies on against the repository (open the files, search for the
   names). A false claim is `blocking`.
5. **Verification.** Each task writes a failing test before its
   implementation, unless it changes only docs or config. Each run step
   states its expected output. Some task checks each of the spec's success
   criteria. A gap is `blocking`.
6. **Plan-introduced decisions.** List the choices the plan makes that the
   spec does not settle and that concern scope, architecture, product
   boundary, data or irreversible actions, or the interpretation of the spec.
   File names, helper structure and test layout are not decisions. These are
   not findings: the user signs off on them.

## Severity

- `blocking`: the executor would have to guess or stop, or would build the
  wrong thing, or the spec would not be met.
- `minor`: wording or clarity that does not change what gets built.

Do not pad. A plan with no blocking problems gets no blocking findings, and a
plan that makes no decisions of its own gets an empty decisions list.

## Output format

Return exactly this, and nothing before or after it:

```
## Coverage
- <spec item> → Task <n>[, <m>] | UNMAPPED

## Findings
### [blocking] <title>
- **Line:** <plan line number or task>
- **Problem:** <what is wrong, quoting the plan>
- **Fix:** <a concrete change to the plan>

### [minor] <title>
- **Line:** ...
- **Problem:** ...
- **Fix:** ...

## Plan-introduced decisions
- <decision> (Task <n>) — spec says: <nothing | quote>
```

Write `none` under Findings when there are no findings, and `none` under
Plan-introduced decisions when there are none.
