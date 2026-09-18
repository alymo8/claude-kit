---
name: lean-context
description: Use before exploring a codebase, reading files, or running anything with long output (tests, builds, logs, git). Keeps the main context small so every later turn stays cheap.
---

# Lean context

The cost of a session is context size times turn count. Everything a tool
returns stays in context for every later turn. Exploration output that was
needed once is the biggest avoidable cost, so read narrowly and keep the main
thread for conclusions.

## Rules

1. **Decide what you need before reading.** A symbol, a line range, or the
   shape of a file. For an unknown file, check its line count first, then read
   a range. Read a file whole only when it is under about 200 lines.
   Example: `wc -l src/app.ts`, then `sed -n '120,180p' src/app.ts`.
2. **Search, don't sweep.** `grep -n` with two or three lines of context and a
   cap; never chain `cat` over several files to "get an overview".
   Example: `grep -n -C2 'createUser' -r src | head -40`.
3. **Broad questions go to an Explore subagent.** "Every caller of X", "how does
   subsystem Y fit together": ask for conclusions plus `file:line` pointers,
   not dumps. The subagent's context is discarded; yours stays lean.
4. **Long output goes to a file first.** Redirect tests, builds and logs to the
   scratchpad, then `tail` and `grep` for failures. The full log stays on disk
   if it is needed later.
   Example: `pnpm test > "$SCRATCH/test.log" 2>&1; tail -40 "$SCRATCH/test.log"`.
5. **Never echo what you just wrote**, and never re-read a file to confirm an
   edit; the tool result already confirmed it.
6. **Write down what you learned** in the plan or the handoff instead of
   re-deriving it later in this session or the next one.
7. **Watch the meter.** The status line shows context size; a nudge appears at
   300k tokens and every 100k after. Finish the current step, run `/handoff`,
   then `/clear`.

## Why

Measured across 67 sessions: Bash was 82% of tool output, and cat, sed, grep,
ls and find sweeps were most of that. Re-reads of the same file were rare; the
waste was whole files read into a context that then lived for hundreds of
turns. Details: `conventions/session-hygiene.md` in the kit.
