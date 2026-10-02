# Coverage checklist

The grill walks every area below, and the spec's `## Coverage` section
answers each one. `spec-lint.py` (rule `L9-coverage`) reads the area names
from the bold labels under `## Areas`, so editing this list changes the grill
and the lint together.

## Areas

- **Purpose and success:** What outcome, for whom, and how is "done and
  correct" checked?
- **Scope boundary:** What is explicitly out, and what is deferred?
- **Interfaces:** Which commands, files, APIs or formats do others depend on,
  and do any change?
- **Data and irreversible actions:** What is written, deleted, migrated or
  published, and can it be undone?
- **Failure modes:** What happens on bad input, partial failure, or a missing
  dependency?
- **Security and secrets:** What is trusted, and what touches credentials or
  external input?
- **Testing:** Which tests prove each success criterion?
- **Rollout and compatibility:** What existing users, files or settings are
  affected, and how is the change switched on?
- **Docs and decisions:** Which docs change, and which choices deserve an
  ADR?

## Coverage section format

```
## Coverage

- **Purpose and success:** Purpose; Success criteria.
- **Security and secrets:** N/A: reads only files in the repo, no credentials.
```

One bullet per area, named exactly as above (case does not matter). The text
says where the spec addresses the area, or `N/A` followed by the reason. An
entry may wrap onto indented continuation lines.
