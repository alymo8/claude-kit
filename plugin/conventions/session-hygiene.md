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

Tokens are not dollars: a cache read costs a twentieth of fresh input on Opus
5.5 ($0.20 against $4 per million tokens), so a long context is cheaper than
its token count suggests. It still dominates the bill, because every turn reads
it again.
Re-measured in dollars at Opus 5.5 list prices across 235 sessions<!-- full-only --> (`token-report.py --all --dollars`)<!-- /full-only -->:

| Measure | Value |
|---|---|
| Cost as recorded | $2,004 |
| Share of cost: cache reads / cache writes / output | 62% / 23% / 15% |
| Restart with a 45k handoff at 300k | $1,542 (23% less) |
| Restart with a 45k handoff at 150k | $1,263 (37% less) |

The saving in dollars is smaller than in tokens but still large, so the
restart cap stays.

## Principles

1. **A session is a unit of work, not a day.** End it at a natural boundary: a
   task done, a plan step complete, a decision made.
2. **Restarting must be cheap.** A handoff file carries the in-flight state; the
   knowledge layer, ADRs and plans carry everything durable. Nothing important
   lives only in the conversation.
3. **Keep the main context for what the work needs.** Read in full the code you
   change, search instead of sweeping, send long output to disk first (the
   `agent-kit:lean-context` skill). Understanding is not waste; the restart
   cap limits how long it is carried (ADR 0011).
   <!-- full-only -->
   The rule is on by default;
   `CLAUDE_KIT_LEAN_CONTEXT=0` plus a `Skill(agent-kit:lean-context)` deny
   switches it off (ADR 0014). The kit map, injected at session start, gives the
   plugin root and the absolute paths of these playbooks from any repo;
   `CLAUDE_KIT_KIT_MAP=0` switches it off (ADR 0032).
   <!-- /full-only -->
<!-- full-only -->
4. **Keep dead ends through a compaction.** A PreCompact hook tells the
   compaction summary to keep the approaches already tried and why they failed,
   open problems and confirmed decisions; `CLAUDE_KIT_PRECOMPACT=0` switches it off.
5. **Make growth visible.** The status line shows context size at zero cost; a
   nudge at 300k tokens (then every 100k) says when to hand off.
<!-- /full-only -->

## The handoff file

`<work-tree>/.claude/handoffs/<branch>.md`, gitignored, under 80 lines. Written
by `/handoff`;
<!-- full-only -->
its State section is refreshed automatically at session end; it is
injected automatically on the next `startup` or `clear` on the same branch while
its Written date is younger than seven days (the session-end refresh does not
move that date, so an old task is not revived).
<!-- /full-only -->
<!-- lite-only (agent-kit-lite only; agent-kit ignores this block)
the next session reads it when you ask it to.
-->
Sections: Task, State (generated), Done this session,
Next, Files that matter, Commands that work, Suggested skills, Open questions,
Moved to durable homes. `/handoff <focus>` tailors it to what the next session
will do. It never holds secrets or personal data, since every later session on
the branch <!-- full-only -->loads it<!-- /full-only --><!-- lite-only (agent-kit-lite only; agent-kit ignores this block) may read it -->.

What does **not** belong in it: findings (go to `knowledge/`), decisions (go to
an ADR), changes of plan (go to the plan). The `/handoff` command asks about
these first. `.claude/handoffs/` may be emptied at any time; a removed worktree
takes its handoffs with it.

## The routine

1. Start: <!-- full-only -->read the injected handoff<!-- /full-only --><!-- lite-only (agent-kit-lite only; agent-kit ignores this block) read the branch's handoff file -->, verify its State against `git status`.
2. Work with the `lean-context` skill<!-- full-only -->; keep an eye on the status line<!-- /full-only -->.
3. <!-- full-only -->When the nudge appears<!-- /full-only --><!-- lite-only (agent-kit-lite only; agent-kit ignores this block) When the context grows large -->, finish the current step.
4. `/handoff`, then `/clear`. Repeat.

<!-- full-only -->
## Re-measuring

`python <kit>/plugin/scripts/token-report.py --all` prints the numbers above for
every project on this machine, plus the restart simulation. `--dollars` adds
the cost and the simulation in dollars (`--prices INPUT WRITE READ OUTPUT` for
another model's rates). Run it after a few weeks of use, and again when a new
model changes the prices, and compare with the tables at the top.
<!-- /full-only -->

## Definition of done

- A handoff exists whenever a branch is mid-flight at the end of a session.
- No session ends above the nudge threshold without a handoff.
- A fresh session on the branch can continue from the handoff alone.
- Findings, decisions and plan changes made during the session are in their
  durable homes, not only in the handoff.
