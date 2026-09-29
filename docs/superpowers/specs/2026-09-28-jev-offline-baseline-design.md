# jev pilot: label without a key, and a no-jev baseline from history

- **Status:** implemented
- **Date:** 2026-09-28
- **Extends:** `docs/superpowers/specs/2026-09-28-jev-triage-pilot-design.md`
  (the pilot spec; everything not changed here still holds)

## Purpose

The jev triage pilot shipped, but every evaluation step needs a
`TYPESAFE_API_KEY` before anything happens:

- `replay` judges each sampled prompt before writing `labels.csv`, and stops
  with `missing_key` without one, so nothing can be labelled yet;
- the "regular" side of the comparison is `shadow` mode, which also calls jev.

Hand-labelling ~60 prompts is the slow, human part of the pilot, and it does not
need jev. And the question "how often do the workspace rules slip today?" can be
answered from past sessions without jev at all. This change moves both off the
critical path, so the only step left waiting for the key is scoring.

## Scope

**In:**

1. `replay --no-judge`: sample and write `labels.csv` for labelling, with the
   score columns empty and no network access.
2. `replay --rescore`: later, fill the score columns of an existing
   `labels.csv` with jev, keeping every label.
3. `replay --since YYYY-MM-DD`: sample only prompts typed on or after a date.
4. A new `session_id` column in `labels.csv`, so each labelled prompt can be
   traced back to its transcript.
5. A new `baseline [labels.csv]` subcommand: the no-jev baseline, computed from
   history with your labels as ground truth.
6. Docs: README "Trying jev" steps, and a note in ADR 0012.

**Out:**

- Any change to the hook, its questions or its log format.
- Labelling assistance of any kind (e.g. an LLM pre-filling labels): the labels
  are the ground truth and stay human.
- Changing the Replay or Shadow gates.

## Design

### `labels.csv` gains `session_id`

Columns become `id, project, session_id, prompt, s_underspecified,
s_new_feature, s_key_decision, latency_ms, input_tokens, output_tokens,
label_underspecified, label_new_feature, label_key_decision`. `session_id` is
the transcript file's stem. `score` reads columns by name, so it is unaffected.
No `labels.csv` exists yet, so there is nothing to migrate.

### `replay` options

- `--since YYYY-MM-DD`: keep only prompts whose record `timestamp` (ISO-8601,
  present on every transcript record) is on or after the date. A record without
  a timestamp is kept only when `--since` is not given. The README suggests
  `--since 2026-08-01`, the date the pre-flight rule entered `CLAUDE.md`, so the
  baseline does not count sessions from before the rules existed.
- `--no-judge`: skip `judge`. The score, latency and token columns are written
  empty. This works with no key and no SDK and makes no network call.
- `--rescore`: do not sample. Read the existing `labels.csv` (the same tolerant
  reader `score` uses: BOM, ANSI, semicolons), judge every row's `prompt`, and
  overwrite only the score, latency and token columns. The `id`, `project`,
  `session_id`, `prompt` and `label_*` values are kept as they are. The file is
  written back as UTF-8 with BOM and commas, via a temporary file and a rename,
  so an interrupted or failed run never damages your labels. `missing_key` or
  `missing_sdk` on the first row exits 1 with the file untouched. A row whose
  call fails (bad key, timeout) keeps its previous scores; if every row fails
  the file is left untouched, and any failure makes the command exit 1 with a
  count. Columns you added (e.g. notes) are kept after ours. If the file is
  locked (open in Excel) it says so before calling jev, and a lock at write
  time leaves the results in `labels.csv.tmp`. `--rescore` cannot be combined
  with `--no-judge`, `--n`, `--seed` or `--since`. `--since` must be a
  `YYYY-MM-DD` date (UTC).
- The overwrite guard stays: plain `replay` or `replay --no-judge` refuses to
  replace an existing `labels.csv` without `--force`. `--rescore` never needs
  `--force`, because it keeps the labels.

### `baseline [labels.csv]`

For each labelled row it finds the transcript by `session_id`, matches the
prompt text to its turn, and derives the same *asked*, *preflight* and
*corrected* outcomes as `report`, using the same definitions and turn-sequence
window. The only difference is that **your labels, not jev's scores, decide
which prompts count**:

| Measure | Population | Miss |
|---|---|---|
| Pre-flight miss rate | rows with `label_new_feature = 1` and a code edit in the turn sequence | the check was not run before the first code edit |
| Did-not-ask rate | rows with `label_underspecified = 1` or `label_key_decision = 1` | Claude neither used AskUserQuestion nor ended its reply with a question |
| Correction rate | labelled-positive rows (any label = 1), and all other labelled rows as a contrast | the next prompt was a correction, or the user interrupted |

Output: each measure as `k/n (pct)`, plus the rows skipped because the label was
blank, the transcript is missing, or the prompt was not found in it. It also
writes `baseline.csv` (one row per matched prompt: id, labels, asked, preflight,
corrected) next to `labels.csv`, so you can check the heuristics by hand. It
needs no key and makes no network call. Known limits: a prompt typed twice in
one session matches its first occurrence; and prompts are matched by exact
text, so saving `labels.csv` from Excel as plain (ANSI) "CSV" instead of
"CSV UTF-8" turns non-Latin characters into `?` and those rows show up as
"not found".

### How the pieces fit

1. `replay --no-judge --since 2026-08-01`, then label the 60 rows by hand.
2. `baseline`: how often the rules slip today. No jev, no key.
3. Once you have a key: `replay --rescore`, then `score` (the Replay gate, as
   before).
4. `shadow`, then `active`, as before. `report`'s active-mode miss rate can now
   be read against the baseline as well as against shadow.

## Decisions

| Decision | Chosen | Rejected, and why |
|---|---|---|
| Where labelling lives | Split `replay` into sample (`--no-judge`) and score (`--rescore`) | Separate `sample`/`judge` subcommands: more surface for the same thing |
| Baseline ground truth | Your labels | jev's scores (shadow mode): the baseline would inherit jev's errors and need the key |
| History window | `--since` on replay, suggested 2026-08-01 | All history: counts sessions from before the rules existed as misses |
| Safety of `--rescore` | Temporary file and rename; labels never rewritten from memory | In-place write: a crash mid-run could lose hand-labelling work |
| **Active gate** (needs your confirmation) | Unchanged: active is compared with shadow, as in the pilot spec; the baseline is an extra reference in the write-up | Replace shadow with the baseline as the gate: cheaper (skips 1–2 weeks of shadow), but compares labelled history with live jev-flagged prompts, which are different populations |

## Success criteria

### Build is done and correct when

- `pytest` passes, including new tests, with no network access:
  - `replay --no-judge` writes the sampled rows with empty score, latency and
    token columns and a correct `session_id`. It works with no key and with
    `typesafe_sdk` blocked, and never calls `judge`;
  - `replay --since` keeps only prompts on or after the date and drops prompts
    before it;
  - `replay --rescore` fills the scores and keeps every label and other column
    exactly as they were, including on a semicolon/ANSI file re-saved by Excel;
    on `missing_key` it exits 1 and the file is byte-for-byte unchanged;
  - `--rescore` combined with `--no-judge` is rejected with exit 2 (argparse);
  - `baseline` computes the three measures and their counts on a fixture of
    labels plus transcripts, skips and counts rows with a blank label, a missing
    transcript, or a prompt not found in the transcript, and writes
    `baseline.csv`;
  - the existing `score` tests still pass with the new column.
- `ruff check plugin tests` and `ruff format --check plugin tests` pass.
- CI is green on ubuntu and windows.
- A manual check on this machine: `replay --no-judge --n 60 --since 2026-08-01`
  with no key writes up to 60 rows, and `baseline` on the unlabelled file runs
  and reports every row as skipped (blank labels). I run this and report the row
  counts only, never prompt text.
- No private repository names, usernames or real prompts in tracked files.
