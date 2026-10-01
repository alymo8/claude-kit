# Gate: Spec gate: linter and independent reviewer

- **Spec:** docs/superpowers/specs/2026-09-30-spec-gate-design.md
- **Spec SHA-256:** 4d69976c1c9d1f40a9b3489c768f1aa709fb94805ee87a15e5b40ac863465794
- **Verdict:** pass
- **Date:** 2026-09-30
- **Rounds:** 2

## Key decisions

- Two layers: a deterministic linter plus a fresh-context reviewer, rather
  than either alone (Decisions)
- A gate pass needs the user's one-line OK; invoking `/ship` is that OK, and
  `/ship` then sets Status to `approved` (Purpose, Decisions, `/ship` changes)
- The gate's verdict and key decisions replace the user's full read of a spec
  (ADR 0015)
- A new reviewer subagent each round, no conversation context, at most 3
  rounds (SKILL.md)
- Decision findings always go to the user and fail the gate (SKILL.md)
- The spec hash ignores only the first Status bullet (Hash mode)
- Gate records are tracked files in `docs/superpowers/gates/` (Decisions)
- `/ship` step 0 requires a valid record, runs the gate when needed, and a
  failed gate is a stop rule (`/ship` changes)
- Enforced through `CLAUDE.md` and `/ship`; the superpowers plugin is not
  edited; plans are not gated (Scope)
- The reviewer eval is manual, not in CI: at least 5/6 seeded defects caught
  on both runs, at most 1 blocking finding on the control (Success criteria)
- Plugin version 0.5.2 → 0.6.0 (Scope)

## Findings fixed

- round 1 [blocking] Line number for "missing" violations undefined: L1–L3
  report line 1, L4 the Scope heading line
- round 1 [blocking] L7 item text undefined: first line plus following lines
  up to the next top-level item, nested sub-items included
- round 1 [minor] `--root` shown for `--verify-record` too
- round 1 [minor] `???` matched literally; "higher level" means fewer `#`
- round 1 [minor] default spec is the file name that sorts last
- round 1 [minor] skill test file named (`tests/test_spec_gate_skill.py`)
- round 1 [minor] added a success criterion (and test) for the docs wiring
- round 2 [minor] `/ship` step 0 sets Status to `approved` on a pass
- round 2 [minor] an unfixable lint violation is a decision finding
- round 2 [minor] dropped "like the other kit scripts" (render-spec.py needs
  `markdown`)
- round 2 [minor] verify-record success output stated (`ok: <record>`)
- round 2 [minor] L1 and the hash use the first Status bullet
- round 2 [minor] `rubric.md` is authoritative over the spec's summary
- code review: L5 matches TBD/TODO/FIXME in upper case only ("a todo app" is
  not a placeholder); `/ship` step 0 marks an already-gated spec `approved`.
  Hash updated after these edits; no gate finding was reopened.

## Open

- none
