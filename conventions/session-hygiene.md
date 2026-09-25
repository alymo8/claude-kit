# Session hygiene

How a working session starts, how long it runs, and how it ends, so that every
turn stays cheap without losing anything a later session needs.

## The cost model

A session's cost is **context size times turn count**. Every turn re-sends the
whole context, and everything a tool returns stays in it. Measured across 67
sessions in five repos before this convention existed:

| Observation | Value |
|---|---|
| Average context per API call | 260k tokens |
| Median assistant turns per session | 181 (max 704) |
| Context at the end of the longest sessions | 300k to 850k tokens |
| Share of tool output from Bash | 82%, mostly cat / sed / grep / ls / find |
| Same-file re-reads within a session | 7 in total |

Sessions ran long because starting fresh lost everything except `CLAUDE.md`.
Simulating "restart with a 45k-token handoff at 300k" cut input tokens by 42%;
at 150k, by 65%.

## Principles

1. **A session is a unit of work, not a day.** End it at a natural boundary: a
   task done, a plan step complete, a decision made.
2. **Restarting must be cheap.** A handoff file carries the in-flight state; the
   knowledge layer, ADRs and plans carry everything durable. Nothing important
   lives only in the conversation.
3. **Keep the main context for what the work needs.** Read in full the code you
   change, search instead of sweeping, send long output to disk first (the
   `claude-kit:lean-context` skill). Understanding is not waste; the restart
   cap limits how long it is carried (ADR 0011).
4. **Make growth visible.** The status line shows context size at zero cost; a
   nudge at 300k tokens (then every 100k) says when to hand off.

## The handoff file

`<work-tree>/.claude/handoffs/<branch>.md`, gitignored, under 80 lines. Written
by `/handoff`; its State section is refreshed automatically at session end; it is
injected automatically on the next `startup` or `clear` on the same branch while
younger than seven days. Sections: Task, State (generated), Done this session,
Next, Files that matter, Commands that work, Open questions, Moved to durable
homes.

What does **not** belong in it: findings (go to `knowledge/`), decisions (go to
an ADR), changes of plan (go to the plan). The `/handoff` command asks about
these first. `.claude/handoffs/` may be emptied at any time; a removed worktree
takes its handoffs with it.

## The routine

1. Start: read the injected handoff, verify its State against `git status`.
2. Work with the `lean-context` skill; keep an eye on the status line.
3. When the nudge appears, finish the current step.
4. `/handoff`, then `/clear`. Repeat.

## Re-measuring

`python <kit>/plugin/scripts/token-report.py --all` prints the numbers above for
every project on this machine, plus the restart simulation. Run it after a few
weeks of use and compare with the table at the top.

## Definition of done

- A handoff exists whenever a branch is mid-flight at the end of a session.
- No session ends above the nudge threshold without a handoff.
- A fresh session on the branch can continue from the handoff alone.
- Findings, decisions and plan changes made during the session are in their
  durable homes, not only in the handoff.
