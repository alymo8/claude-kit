# ADR 0049: `/ship-many` children run through a runner with a time limit, one resume and keep-awake

- **Status:** accepted
- **Date:** 2026-11-18

## Context
[ADR 0018](0018-ship-many-headless-children.md) runs each `/ship-many` spec as
a headless `claude -p` child. The first real run (2026-11-16 to 11-18) shipped
two specs, but no child finished in one go and each restart was by hand:

1. Print mode killed a child's background test run after 10 minutes (the
   print-mode wait ceiling, `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS`), and the
   child ended before its PR.
2. The 2-hour limit was not enforced: the Bash tool ignores the timeout of a
   `run_in_background` command, and one child ran about 7 hours.
3. Two transient API `ENOTFOUND` network drops each ended a child with no PR
   and no handoff.
4. Laptop sleep paused a child for 6 hours.
5. Two specs took the same ADR number, because a later wave started while an
   earlier child had ended unmerged.

## Decision
A new script, `plugin/scripts/ship-child.py`, runs each child and writes a
status file that `/ship-many` reads.

D1: children get `CLAUDE_CODE_PRINT_BG_WAIT_CEILING_MS=0`, because one setting
covers every backgrounded command a child runs and it made the hand resume
finish; rejected a `/ship` rule to keep suite runs in the foreground, since a
foreground Bash call is itself capped at 10 minutes and other background waits
stay exposed.
D2: the runner enforces 2 hours per attempt, at most 2 attempts, because a
script kills the whole process tree, works the same on Windows and macOS and
is unit-tested; rejected one shared 2-hour budget (a late resume would be
killed before it finishes) and a `timeout` wrapper (missing on macOS, leaves
grandchildren).
D3: the runner resumes once on any ending without a merged PR, a stop-rule
handoff or a timeout, because "no evidence the child stopped on purpose"
covers network drops, the print-mode kill and crashes alike; rejected matching
transient error patterns in the logs (misses new messages) and resuming more
than once (cost, and a second failure is likely not transient).
D4: the runner requests keep-awake per OS, because it needs no admin rights,
is released when the runner exits and needs nothing from the user; rejected
only documenting "keep the machine awake", since the failure was an unattended
run.
D5: no ADR-number reservation, because with D1 to D3 children that can finish
do so before the next wave, and `/ship` step 9's renumber rule handled the
collision with no user input; rejected reserving numbers in specs at gate time
(older specs would need editing and regating) and holding later waves behind
an unmerged child (breaks ADR 0018's "a failing child never stops the
others").
D6: `/ship` names its branch `feat/<slug>` from the spec file name, because
the runner needs the branch to find the worktree and handoff and a fixed rule
matches current practice; the slug rule is now a contract between `/ship` and
`ship-child.py`. Rejected having `/ship` print its branch somewhere for the
runner to read.

## Consequences
Children survive the print-mode ceiling, hung runs and one transient failure
without a hand restart, and `/ship-many` reports attempts and cost from the
status file. The worst case is 4 hours per child (two 2-hour attempts). A
closed laptop lid still sleeps the machine, since keep-awake does not override
the lid action. Rerunning `/ship-many` over a spec whose `feat/<slug>` branch
already exists from an earlier run stays a hand step.
