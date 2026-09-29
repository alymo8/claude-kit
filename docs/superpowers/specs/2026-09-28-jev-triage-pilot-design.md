# jev triage pilot: an opt-in System-1 judge on every prompt

- **Status:** implemented
- **Date:** 2026-09-28

## Purpose

Jev is TypeSafe AI's "System One" judgment model: one API call returns calibrated
probabilities (`Choice`, `Score`, `Noul`) for several questions about a piece of
text in roughly 150–300 ms. Public write-ups report large savings from putting it
in front of an agent's LLM to make routing decisions.

In Claude Code that saving does not transfer: the kit does not own the agent loop,
so Claude runs every turn regardless. What jev *can* do from the kit's hooks is
**steer** Claude: judge each prompt cheaply and, when warranted, add a one-line
hint. The two workspace rules most often missed are the ones a per-prompt judge
can see coming:

- a **new feature** request should start with the pre-flight branch check;
- an **underspecified** prompt, or one that hinges on a **key decision**, should
  get a clarifying question or an explicit confirmation before work starts.

This pilot tries that, **off by default**, and measures whether it helps. It is
built so that it can be stopped cheaply at any stage if the evidence says no.

## Scope

**In:**

- A `UserPromptSubmit` hook, `plugin/hooks/jev_triage.py`, controlled by one env
  flag with three modes: `off` (default), `shadow`, `active`.
- A local JSONL log of every judgment.
- An evaluation script, `plugin/scripts/jev-eval.py`, with `replay`, `score` and
  `report` subcommands.
- A staged evaluation (replay → shadow → active) with go/no-go gates agreed in
  advance (see Success criteria).
- An ADR (0012) and a short "Trying jev" section in the kit docs.

**Out:**

- Using jev inside the user's own agent projects (the pattern the source post
  describes). That is a separate effort per project.
- OpenRouter's `typesafe/jev-router`. It is a model picker that returns a normal
  chat completion, not judgment probabilities, so it cannot drive triage.
- Self-hosted OpenJev. Nothing in the design prevents adding it later.
- Other jev uses considered and deferred: skill-routing hints, a prompt-injection
  guard on fetched content, rubric gates inside `/ship`.
- Blocking prompts. The hook only ever adds context; it never rejects input.
- Any change to behaviour when the flag is unset.

## Design

### Switch

`CLAUDE_KIT_JEV` selects the mode. Unset, empty, or any unrecognised value means
`off`. Values are case-insensitive.

| Mode | Calls jev | Logs | Adds context |
|---|---|---|---|
| `off` | no | no | no |
| `shadow` | yes | yes | no |
| `active` | yes | yes | yes, for scores at or above threshold |

In `off` the hook returns before importing anything beyond the standard library,
so the kit behaves exactly as today.

The API key is read from `TYPESAFE_API_KEY`. Thresholds default to `0.65` and can
be overridden per question with `CLAUDE_KIT_JEV_T_UNDERSPECIFIED`,
`CLAUDE_KIT_JEV_T_NEW_FEATURE`, `CLAUDE_KIT_JEV_T_KEY_DECISION` (floats in
`[0, 1]`; an unparsable value falls back to the default).

### Questions

One `system_one` call per prompt with three `Noul` questions. The question
definitions (key, instructions, `true`/`false` criteria, hint text) live in one
module-level constant in `jev_triage.py`; `jev-eval.py` imports it, so the hook and
the evaluation always judge the same thing.

| Key | Asks | Hint added in `active` |
|---|---|---|
| `underspecified` | Would acting on this prompt need information it does not give (target, scope, expected result)? | `jev triage: this prompt looks underspecified; ask one focused clarifying question before acting.` |
| `new_feature` | Is this a request to build a new feature or capability (not a question, fix, or chore)? | `jev triage: this looks like a new feature; run the pre-flight branch check (CLAUDE.md) before starting.` |
| `key_decision` | Does doing this hinge on a choice about scope, architecture, product boundary, or an irreversible action? | `jev triage: this may hinge on a key decision; surface it by name with options and a recommendation, and get explicit confirmation.` |

Hints that fire are joined into one `additionalContext` string. The hook emits no
`systemMessage`; the user sees hints only in the log and report, so the pilot does
not add terminal noise.

### Client

The hook uses the official `typesafe-sdk` (PyPI, `>=0.7`; depends on httpx2,
pydantic, tenacity), not `judgment-base-agent`, which requires `google-adk[eval]`
and pandas and is far too slow to import in a per-prompt hook. The SDK is imported
only when the mode is `shadow` or `active`. It is an **optional, per-machine
install** (`pip install "typesafe-sdk>=0.7"`), not a kit requirement.

The call goes through one function, `judge(prompt: str) -> Judgment` (scores and
usage), which is the seam tests replace. It uses a 1.5 s client timeout and
disables SDK retries, so the worst case stays well inside the hook's 3 s entry
timeout in `hooks.json`.

Confirmed against `typesafe-sdk` 0.7.2: the sync
`TypeSafeClient(timeout=1.5, retry=RetryPolicy(max_retries=0)).system_one(
state=prompt, questions={key: Noul(instructions=..., criteria={"true": ...,
"false": ...})})` returns `nouls[key].noul`, `usage` and `model`.

### Data flow

1. Claude Code runs the hook with the `UserPromptSubmit` event on stdin.
2. Mode `off` → exit 0, no output.
3. Otherwise clean `prompt` (strip `<system-reminder>` and `<pasted_content …>`
   blocks); if the cleaned text is empty, starts with `/` or `<`, or has fewer
   than 3 words (replies such as "lgtm"), exit 0 without calling jev. Replay
   applies the same filter, so both judge the same prompts.
4. Call `judge(prompt)`, timing it.
5. Append one record to the log.
6. Mode `active` and at least one score ≥ its threshold → print
   `{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
   "additionalContext": "<hints>"}}`.
7. Exit 0.

### Log

Path: `~/.claude/claude-kit/jev/log.jsonl` (outside every repository, so nothing
is ever committed; the kit repo is public). The directory is created on first
write. One JSON object per line:

| Field | Content |
|---|---|
| `ts` | ISO-8601 UTC timestamp |
| `session_id` | from the event |
| `project` | basename of the event's `cwd` |
| `mode` | `shadow` or `active` |
| `prompt` | full prompt text |
| `scores` | `{underspecified, new_feature, key_decision}` floats, or `null` on error |
| `thresholds` | the thresholds in effect |
| `fired` | list of question keys at or above threshold (recorded in both modes) |
| `injected` | `true` only when context was actually emitted |
| `latency_ms` | wall time of `judge` |
| `usage` | SDK usage object if present, else `null` |
| `error` | `null`, or a short string (`missing_sdk`, `missing_key`, `timeout`, `api_error: …`) |

### Failure handling

Follows ADR 0007: the hook always exits 0 and never blocks a prompt. Missing SDK,
missing key, timeout, API error, malformed event, or an unwritable log each result
in: one line on stderr prefixed `[claude-kit] jev triage`, a log record with
`error` set where the log is writable, no `additionalContext`, exit 0.

### Evaluation script: `plugin/scripts/jev-eval.py`

Standard library plus the hook module; `replay` needs `typesafe-sdk`. All outputs
go to `~/.claude/claude-kit/jev/`.

- **`replay [--n 60] [--seed 0]`.** Walks `~/.claude/projects/*/*.jsonl`, extracts
  user-typed prompts (records with `type == "user"` whose content is text written
  by the user), and drops tool results, `<system-reminder>`-only and other
  harness-injected content, slash commands, and prompts under 3 words. Deduplicates,
  samples `n` prompts stratified by project, judges each with `judge`, and writes
  `labels.csv` with columns `id, project, prompt, s_underspecified, s_new_feature,
  s_key_decision, latency_ms, input_tokens, output_tokens, label_underspecified,
  label_new_feature, label_key_decision`. Label columns are empty for the user to fill with `1`/`0`.
  Refuses to overwrite an existing `labels.csv` unless `--force`.
- **`score [labels.csv]`.** For each question: precision, recall and F1 at the
  configured threshold; a sweep of thresholds 0.50–0.90 in steps of 0.05; p50/p95
  latency; call count and token totals from usage (cost = calls × the
  per-evaluation price on the TypeSafe dashboard). Rows with an empty
  label are skipped and counted. Prints the Replay gate result as `PASS` or `FAIL`
  with the failing metrics.
- **`report [--since YYYY-MM-DD]`.** Joins log records with their session
  transcripts (by `session_id`) and, for each logged prompt, derives:
  - *asked*: Claude's next reply used `AskUserQuestion` or its final text ends in
    `?`;
  - *preflight*: for prompts where `new_feature` fired, a Bash/PowerShell call
    containing `git branch --show-current` or `git fetch` appears before the first
    `Write`/`Edit` of that turn sequence; `n/a` (excluded from the miss rate)
    when the turn made no `Write`/`Edit`;
  - *corrected*: the user's next prompt starts with a correction marker (`no`,
    `don't`, `do not`, `actually`, `stop`, `wait`, `that's not`,
    case-insensitive);
  - tokens per session, reusing the parsing in `plugin/scripts/token-report.py` (loaded by path, as the tests already do for hyphenated scripts).

  Prints, per mode (`shadow`, `active`): prompts logged, share that fired per
  question, convention-miss rate on fired prompts (fired `new_feature` without
  *preflight*; fired `underspecified`/`key_decision` without *asked*), correction
  rate, median tokens per session, p50/p95 added latency, error rate. Writes
  `spotcheck.csv` with 20 random fired prompts and their derived outcomes so the
  user can check the heuristics by hand.

## Decisions

| Decision | Chosen | Rejected, and why |
|---|---|---|
| Pilot target | Prompt triage on `UserPromptSubmit` | Skill-routing hints, injection guard, `/ship` rubric gates: deferred so one pilot keeps the evaluation clean |
| Backend | TypeSafe hosted API | OpenRouter `jev-router`: a model picker returning completions, not judgment scores. Self-hosted OpenJev: a 26B model, too much setup for a trial |
| Client | `typesafe-sdk` directly, lazily imported | `judgment-base-agent`: pulls `google-adk[eval]` and pandas, too slow per prompt. Raw HTTP: wire format undocumented |
| Default | Off; one env flag with `shadow`/`active` | On by default: user asked for opt-in; prompts leave the machine only while enabled |
| Evaluation | Staged replay → shadow → active with gates | Straight A/B: noisy for one user and exposes Claude to unvalidated hints. Replay only: says nothing about behaviour change |
| Effect of a hint | Add context only | Blocking or rewriting prompts: too invasive for a pilot |
| Privacy | Full prompt text logged locally only; sent to TypeSafe only when mode ≠ off | Hashing prompts: makes labelling and spot-checks impossible |

## Success criteria

### Build is done and correct when

- `pytest` passes, including new tests that use an injected fake `judge` and make
  no network calls:
  - `off` (unset, empty, unknown value): no import of `typesafe_sdk`, no output, no
    log write;
  - `shadow`: log record written with all fields, no stdout;
  - `active`: `additionalContext` contains exactly the hints for scores ≥
    threshold; none when all are below;
  - threshold env overrides, including an unparsable value falling back to 0.65;
  - slash-command and empty prompts are skipped without calling `judge`;
  - timeout, API error, missing SDK and missing key each exit 0 with no stdout and
    an `error` in the log;
  - `replay` extraction on a fixture transcript keeps typed prompts and drops tool
    results, system reminders and slash commands;
  - `score` computes known precision/recall on a hand-made CSV and prints the right
    `PASS`/`FAIL`;
  - `report` derives *asked*, *preflight* and *corrected* correctly on a fixture
    transcript plus log.
- `ruff check plugin tests` and `ruff format --check plugin tests` pass.
- `hooks.json` registers the hook on `UserPromptSubmit` with `timeout: 3`, and
  existing plugin-manifest tests still pass.
- With the flag unset, a manual session shows no change and no log file is
  created.
- One live smoke call (needs the user's `TYPESAFE_API_KEY`): `CLAUDE_KIT_JEV=shadow`
  plus one prompt produces a log record with three scores and no error.
- No private repository names or usernames in tracked files.

### Pilot gates (evaluated after the build merges)

| Stage | Measure | Go to next stage when |
|---|---|---|
| Replay | ~60 hand-labelled past prompts; `jev-eval.py score` | precision ≥ 0.8 and recall ≥ 0.6 for `underspecified` and `new_feature`; p95 latency ≤ 500 ms |
| Shadow (~1–2 weeks) | `jev-eval.py report` | false-alarm rate ≤ 15% on the spot-check, and at least 5 real convention misses on fired prompts |
| Active (~1–2 weeks, compared with shadow) | `jev-eval.py report` | convention misses on fired prompts drop ≥ 50% with no rise in correction rate |

Failing a gate ends the pilot (or sends it back to tune thresholds and question
wording once). The outcome, pass or fail, is recorded in ADR 0012.
