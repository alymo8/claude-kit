# ADR 0012: jev triage pilot is an opt-in third-party judge

- **Status:** moved
- **Date:** 2026-09-28 (moved 2026-09-29)

The jev triage pilot (a `UserPromptSubmit` hook that judged prompts with
TypeSafe's jev, its eval script and its task bench) was an experiment, not a
workspace convention. It moved out of the kit into a separate private repo
with its own plugin, code, docs and this decision's full record. The kit no
longer ships any jev code or hook.
