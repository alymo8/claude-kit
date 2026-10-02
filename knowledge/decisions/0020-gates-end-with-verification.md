# ADR 0020: Gates end with a verification round; blocking is a fixed set of classes

- **Status:** accepted
- **Date:** 2026-10-02

## Context
The spec gate escalated to the user most of the time. Of the five spec gate
records in the kit, three needed more than 3 rounds (blocking findings per
round: 3-2-1-1, 4-3-2 then a rerun, 2-4-4-2-1-1), and real projects showed
the same pattern: counts fall but rarely reach zero, and the gate fails with
nothing for the user to decide. Two causes: every unanswered implementation
question was `blocking`, so each fresh reviewer sampled a different subset of
an unbounded set of "how" questions while each fix added new surface; and
round 3's fixes were never re-reviewed, so any round-3 finding meant `fail`.

## Decision
The spec rubric limits `blocking` to six classes (wrong-build, contradiction,
false-claim, uncheckable, open-what, too-large). A "how" question the plan
can settle is a `[plan]` finding: not fixed in the spec, listed under
`## Plan questions` in the spec's gate record, answered by `/ship`'s plan
writer and checked by the plan gate. Both gates run up to 3 discovery rounds;
when the last one's blocking findings were fixed, up to 2 verification rounds
(a shared `spec-gate/verify.md`) check only those fixes and their diff, so at
most 5 rounds in all. Step numbers stay 1–7 in both gates. This supersedes
the "up to three rounds" sentences of ADRs 0015 and 0016, which are not
edited.

## Consequences
The user is asked only for real decisions or for a fix that stays wrong
after verification. A gate can cost up to 5 reviewer subagents. A question
can be misclassified as `[plan]`; the plan gate's Plan-questions check is the
backstop. Verification reviewers see the findings they verify, so they may
anchor on them; discovery reviewers stay context-free.
