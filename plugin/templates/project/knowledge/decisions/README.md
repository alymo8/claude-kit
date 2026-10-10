# Decisions

Architecture Decision Records for {{project_name}}: one decision per numbered file,
the next number for a new one, never deleted, superseded instead. Template:
[`0000-template.md`](0000-template.md).

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

## Index

| # | Title | Status | Date |
|---|-------|--------|------|
