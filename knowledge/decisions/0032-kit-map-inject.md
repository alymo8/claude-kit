# ADR 0032: Kit map injected at session start

- **Status:** accepted
- **Date:** 2026-10-13

## Context
The workspace `CLAUDE.md` links to `conventions/` and `knowledge/decisions/`
relative to the kit root. Claude Code loads that file in a child repo, but
there those paths name folders inside the child, which do not exist. The
playbooks that define how we work were not reliably reachable from the repos
they govern; the spec-gate rubric and the lean-context rule patched this ad hoc.

## Decision
- A SessionStart hook (`kit_map_inject.py`, no matcher) injects a short kit
  map: the kit root, the rule that the workspace `CLAUDE.md`'s relative links
  resolve against it, the absolute path of each playbook (parsed from the
  table in `conventions/README.md`) and of the kit's ADR folder. Playbooks are
  read on demand.
- On by default; `CLAUDE_KIT_KIT_MAP=0` switches it off. With no
  `conventions/README.md` above `plugin/` it prints nothing.
- The spec-gate reviewer gets no session-start output, so the main session
  passes the decision-log path in the dispatch prompt, in place of the
  one-level-up fallback. This amends ADR 0027.
- No Read allow rule is added to user settings; an occasional permission
  prompt when Claude opens a kit file from a child repo is accepted.

## Alternatives
- `@` imports of the playbooks: about 8k tokens every session, and still
  tied to the folder layout.
- Copying the playbooks into child repos at scaffold time: drifts, and
  misses repos that never adopted the kit.

## Consequences
- One more always-on SessionStart injection of about 250 to 400 tokens.
- With the map switched off, the lean-context pointer names the
  session-hygiene playbook without a path; that is accepted.
