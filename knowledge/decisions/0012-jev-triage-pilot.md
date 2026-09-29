# ADR 0012: jev triage pilot is an opt-in third-party judge

- **Status:** accepted
- **Date:** 2026-09-28
- **Spec:** `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`

## Context
TypeSafe AI's jev returns calibrated yes/no probabilities for several
questions in one fast call. The kit cannot use it to replace model calls
(Claude Code owns the loop), but a `UserPromptSubmit` hook can judge each
prompt and add a hint when a workspace rule (pre-flight branch check, verify
key decisions) is likely to apply. Doing so sends prompt text to a third-party
API, and nothing yet shows that it helps.

## Decision
- The hook `plugin/hooks/jev_triage.py` is off unless `CLAUDE_KIT_JEV` is
  `shadow` (judge and log) or `active` (also add hints). Prompts leave the
  machine only in those modes.
- It calls the official `typesafe-sdk` directly (optional per-machine install),
  not `judgment-base-agent`, whose Google ADK and pandas imports are too slow
  for a per-prompt hook. OpenRouter's `typesafe/jev-router` returns
  completions, not judgments, so it cannot drive this.
- Judgments are logged locally to `~/.claude/claude-kit/jev/log.jsonl`, never
  in a repository.
- The pilot advances only through the spec's gates (replay, then shadow, then
  active), measured with `plugin/scripts/jev-eval.py`. A failed gate ends it.
  The outcome is appended to this ADR.

## Consequences
- With the flag unset the kit behaves exactly as before.
- In `shadow`/`active`, each prompt of 3+ words costs one jev evaluation and up
  to 1.5 s; failures are logged and the prompt passes unchanged (ADR 0007).

## Outcome
Pending: replay gate not yet run.
