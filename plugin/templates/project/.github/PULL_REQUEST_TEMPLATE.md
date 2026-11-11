## What

<!-- one paragraph: what changes and why; link the spec / ADR if there is one -->

<!-- then the smallest visual that shows the change: pseudocode, a call tree, a file tree, a Mermaid diagram or a diff sketch; for a text-only change, a short before/after quote -->

## Merge danger

**Door:** one-way | two-way
<!-- one-way when reverting the PR cannot undo what merging does (data deleted, overwritten or migrated, published history rewritten, something outside the repo changed); otherwise two-way -->

**Blast radius:**
<!-- one word (none, docs, one-command, all-sessions, consumers), then one line on what could break -->

## Definition of done

- [ ] Behaviour is covered by tests (test-first, or the divergence is a named carve-out)
- [ ] Formatter and linter clean; no dead or commented-out code introduced by the change
- [ ] The diff is surgical: every changed line traces to the spec or task
- [ ] CI green
- [ ] Spec status / ADR updated if a decision changed or the work is now implemented
- [ ] `CLAUDE.md` updated if a command, layout, or convention it documents changed
