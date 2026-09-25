---
name: lean-context
description: Use before exploring unfamiliar code or running anything with long output (tests, builds, logs). Keeps the main context small without trading away understanding of the code you work on.
---

# Lean context

The cost of a session is context size times turn count, and everything a tool
returns stays in context. The waste is output that was never needed: sweeps over
files you did not have to understand, and logs nobody reads past the failure.
Understanding the code you change is not waste; the restart cap (`/handoff`,
then `/clear`) is what limits how long it is carried.

## Rules

1. **Read in full what you work on.** Read a file whole before you edit, debug
   or review it; partial reads miss imports, invariants and local conventions.
   For files you only consult, judge: a large generated, vendored or data file
   gets a line count and a range, ordinary source gets read.
   Example: `wc -l dist/bundle.js`, then `sed -n '120,180p' dist/bundle.js`.
2. **Search, don't sweep, and never cut silently.** Count matches first; cap
   output only when the count is large, and say so. When the task needs every
   occurrence (a rename, "all callers of X"), read them all.
   Example: `grep -rc 'createUser' src | grep -v ':0'`, then `grep -rn -C2 'createUser' src`.
3. **Explore subagents are for locating, not understanding.** Send "where is X
   defined / used" sweeps across many files to one, asking for `file:line`
   pointers. Anything you will reason about or change, read yourself.
4. **Long output goes to a file first.** Redirect tests, builds and logs to the
   scratchpad, then look for the *first* failure as well as the summary; the
   root cause is usually the earliest error, not the last.
   Example: `pytest > "$SCRATCH/test.log" 2>&1; grep -n -m5 -E 'FAIL|Error' "$SCRATCH/test.log"; tail -15 "$SCRATCH/test.log"`.
5. **Never echo what you just wrote**, and never re-read a file to confirm an
   edit; the tool result already confirmed it.
6. **Write down what you learned** in the plan or the handoff instead of
   re-deriving it later in this session or the next one.

When a rule and correctness pull apart, correctness wins: read more.

## Why

Measured across 67 sessions: Bash was 82% of tool output, and cat, sed, grep,
ls and find sweeps were most of that. Re-reads of the same file were rare; the
waste was output carried for hundreds of turns, which the restart cap addresses.
Reading narrowly for its own sake trades quality for tokens the cap already
saves (ADR 0011). Details: `conventions/session-hygiene.md` in the kit.
