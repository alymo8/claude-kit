---
name: capture-learnings
description: Use when /ship or /ship-fast reaches its PR step, or when a feature or change is finished by hand before its branch merges. Writes the session's learnings (gotchas, commands that work, conventions, decisions, the user's corrections) to the repo's CLAUDE.md, knowledge/, an ADR or auto-memory, as one commit on the feature branch, and returns a Learnings summary for the caller's report.
---

# Capture learnings

Runs once per feature, on its feature branch, before the PR is opened (or,
for a manual finish, before the branch merges). The learnings ride in the
feature's PR and are visible in its diff, so there is no approval pause: do
not ask the user to confirm them.

## Steps

1. **Collect candidates** from the work on this feature: the user's
   corrections and stated preferences; commands that failed before one
   worked; surprises (CI failures with a non-obvious cause, platform
   quirks, things that look wrong but are intentional); conventions the
   user set. Include what reached this session through subagent and task
   reports and the CI fix loop, not only what happened in this context.
   Also read the branch's handoff file when present
   (`.claude/handoffs/<branch>.md`, with `/` in the branch written as `_`),
   because a feature may span sessions.
2. **Filter.** Keep a candidate only if a competent newcomer to the repo
   would otherwise waste time on it or get it wrong. Drop anything the
   commit messages, the diff, the spec, the plan or an existing ADR already
   says. Drop anything already recorded at its destination: read the
   destination first, and update an existing entry instead of adding a
   duplicate. On a rerun or resume this drops what an earlier run wrote,
   so nothing new means no commit. Zero learnings is a valid result: write
   nothing and return `none`. Run `git fetch origin` first and read each
   destination on `origin/main` too (`git show origin/main:<path>`): a
   parallel run may already have merged the same learning there.
3. **Route** each kept learning by kind:

   | Kind | Destination |
   |---|---|
   | Repo command, gotcha, or convention | The repo's root `CLAUDE.md`, under the matching heading of the kit's project template: Setup / prerequisites; Build, run, test; Conventions; Gotchas. If the file lacks that heading, append it at the end of the file. |
   | Durable finding about the domain or the code | `knowledge/<topic>.md` (the existing file on the topic, else a new one), linked from `CLAUDE.md` only if every session needs it. |
   | A decision with alternatives that a later change could reopen | A new ADR under `knowledge/decisions/`, in the format of the repo's `knowledge/decisions/0000-template.md` (else its `knowledge/decisions/README.md`, else its newest ADR), numbered one above the highest number in `knowledge/decisions/` on either HEAD or `origin/main`. If `knowledge/decisions/README.md` has an index table, add the ADR's index row. |
   | A preference about how Claude should work that holds beyond this repo | Auto-memory: the session's memory directory and its `MEMORY.md` index, following the session's memory instructions. Never a tracked file. |

   Fallbacks:
   - No root `CLAUDE.md`: create it holding only the new entries under
     their headings.
   - `CLAUDE.md` would have more than 100 lines after the addition (a file
     already over that limit always qualifies): put the entry in
     `knowledge/` and link it from `CLAUDE.md` instead. If the repo has no
     `knowledge/` folder, create `knowledge/<topic>.md` for the overflow
     only; this rule wins over the next one.
   - The repo has no `knowledge/` folder (and `CLAUDE.md` stays within the
     limit): put durable findings in `CLAUDE.md` under `## Gotchas`.
   - The repo has no `knowledge/decisions/` folder, or the branch is a
     `poc/` branch (a `/ship-fast` POC, where ADRs are not required): write
     no ADR; list the decision in the summary as `not written:`.
   - The session has no auto-memory directory: list preference learnings
     in the summary as `not written:`.
4. **Write and commit.** Entries are terse and imperative, with exact
   commands in code spans or fences. Never write secrets, credentials,
   connection strings or personal data, and no names of other private
   repos or of user accounts, in any repo (visibility can change). For
   auto-memory, re-read `MEMORY.md` right before adding the pointer line,
   and add one line rather than rewriting the file: parallel runs may
   write it at the same time. Commit the repo files on the feature branch
   as one commit with the subject `Capture learnings` and the session's
   attribution line. Auto-memory writes are not committed. If no repo file
   changed, make no commit.
5. **Return** the Learnings summary for the caller's report:
   - one line per written learning: `<destination>: <learning>`;
   - one line per decision or preference listed instead of written,
     starting `not written:`;
   - when nothing was written: `none`, then each dropped candidate with
     the step-2 rule that dropped it.

   If the branch already has a `Capture learnings` commit from an earlier
   run, start the summary with that commit's entries (from `git show`),
   each starting `already written:`, so a resumed run's report still lists
   them.
