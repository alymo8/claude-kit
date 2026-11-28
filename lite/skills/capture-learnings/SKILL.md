---
name: capture-learnings
description: Use when /ship or /ship-fast reaches its PR step, or when a feature or change is finished by hand before its branch merges. Writes the session's learnings (gotchas, commands that work, conventions, decisions, the user's corrections) to the repo's CLAUDE.md, knowledge/, an ADR or auto-memory, as one commit on the feature branch, prunes entries the feature made stale, and returns a Learnings summary and hardening proposals for the caller's report.
argument-hint: [--auto]
---

# Capture learnings

Runs once per feature, on its feature branch, before the PR is opened (or,
for a manual finish, before the branch merges). The learnings ride in the
feature's PR and are visible in its diff, so there is no approval pause: do
not ask the user to confirm them.

## Mode

With the argument `--auto` (passed by `/ship` and `/ship-fast`),
never build a mechanical proposal:
report it in the `Hardening:` block only. Without it (a hand run), after
returning the summary, offer once to build the mechanical proposals, and
build them only on a yes, as a separate commit with its tests.

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
   nothing new; step 4 still runs, and step 7 returns `none` only when
   step 4 pruned nothing either. Run `git fetch origin` first and read each
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
   - Root `CLAUDE.md` is only `@AGENTS.md`: every rule here that names the
     root `CLAUDE.md` (routing, line limit, links) applies to the root
     `AGENTS.md`; write to the root `AGENTS.md` instead and leave the stub
     unchanged.
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
4. **Prune.** Fix the entries this feature made wrong. Inputs: the
   feature's changed files, `git diff --name-status origin/main...HEAD`
   (renames and deletions included; step 2 already ran `git fetch origin`),
   plus the spec and plan when present. Edit files in place now; step 6
   commits them. Read each target on `origin/main` too
   (`git show origin/main:<path>`) and skip an entry already fixed there: a
   parallel run may have pruned it. Step 2's filter does not apply here.
   Never prune a learning routed in step 3 of this run.
   - **Repo files:** the root `CLAUDE.md`, every nested `CLAUDE.md` in a
     directory the diff touched or an ancestor of one (a `CLAUDE.md` that
     is only `@AGENTS.md`: read and edit the `AGENTS.md` beside it), and every
     `knowledge/**/*.md` doc (`knowledge/decisions/` excluded) that names a
     changed, renamed or deleted path, or a command, script, flag or
     setting the diff changed. For each entry (a bullet, a table row or a
     short paragraph): if it names a path the diff deleted or renamed,
     repoint it to the new path, or remove it if the thing is gone; if it
     states a command, flag, setting or behaviour the diff changed,
     rewrite it to the new truth, or remove it if the feature made it moot
     (a gotcha the feature fixed); otherwise leave it alone, even if it
     looks stale for another reason. Edits are terse and imperative. A
     touched `knowledge/` doc gets `last_updated: <today>`.
   - **ADRs are never edited.** If the diff contradicts an accepted ADR and
     the feature added no ADR that supersedes it, add the summary line
     `not written: ADR <NNNN> may be superseded: <why>`.
   - **Auto-memory**, only when the session has an auto-memory directory:
     read its `MEMORY.md` and the memory files whose name, description or
     body names this repo, the feature's branch, spec or PR, or a skill or
     command the diff changed.
     - `type: project`: when this feature resolves an open item the memory
       records (a pending check, a next step, a deferred item), rewrite
       that item in place as `done <YYYY-MM-DD> (<ref>): <item>`, where
       `<ref>` is `#<PR number>` once a PR exists, else the branch name,
       and give its `MEMORY.md` line the same `done <date> (<ref>)`
       wording. When the feature contradicts the memory's main fact, rewrite
       the fact. Delete the file and its `MEMORY.md` line only when nothing
       in it stays true.
     - `type: feedback` and `type: user`: never edit or delete; a code
       change does not invalidate a preference. If the diff seems to
       conflict with one, add the summary line
       `not written: memory <file> may conflict: <why>`.
     - Reference memories: rewrite a pointer the diff moved; otherwise
       leave them alone.
     - Follow the session's memory instructions. Edit by exact replacement
       of the lines that change, re-reading the file right before each
       edit, never by rewriting the whole file.
       Memory edits are not committed, so
       the summary lines are their only record.

   Prune runs the same with and without `--auto`, with no approval pause.
   A rerun finds nothing left to prune in what an earlier run fixed.
5. **Harden.** Inputs: step 1's candidates plus every review finding
   fixed in this feature (from the review reports that reached this
   session) and every CI failure's cause; step 2's filter still applies.
   Classify each mistake (something done wrong, then corrected by a
   review, CI, a failed command or the user):
   - **Mechanical:** a fixed pattern a tool could detect without
     judgement (a banned API or import, a file-location or naming rule, a
     forbidden string, a missing file, a format). Write the line
     `harden (mechanical): <mistake> → <lint rule | hook | test | CI check>
     in <file>: <the rule>`. Prefer extending an existing check: read the
     lint config, the test layout and `.github/workflows/` first. An
     existing check not wired into CI or a pre-commit/pre-push hook is
     itself the proposal.
   - **Judgement call:** needs reading the code in context. Add one terse
     imperative bullet under `## Rules` in `knowledge/review-standards.md`,
     in the same `Capture learnings` commit. If the file is missing, create
     it with frontmatter `title: Review standards`, `status: stable`,
     `last_updated: <today>`, `sources: []`, then one line saying it is
     read by the standards reviewer of `agent-kit-lite:review` and not by
     implementers, then `## Rules`; if `knowledge/README.md` exists, add a
     row for it in its map. Never link this file from `CLAUDE.md` or any
     file an implementer loads at session start.

   Then two report-only scans:
   - **Steering bloat:** read the root and nested `CLAUDE.md` files; flag
     rules that are no-ops, duplicates, better as a check (to-check) or
     better in the standards file (to-standards):
     `harden (steering): <file>:<line> <no-op | duplicate | to-check |
     to-standards>: <why>`. Do not edit these files for this scan.
   - **Navigation and information access:** what was hard to find:
     `harden (navigation): <what was hard to find> → <pointer to add,
     where>`.
6. **Write and commit.** Entries are terse and imperative, with exact
   commands in code spans or fences. Never write secrets, credentials,
   connection strings or personal data, and no names of other private
   repos or of user accounts, in any repo (visibility can change). For
   auto-memory, re-read `MEMORY.md` right before adding the pointer line,
   and add one line rather than rewriting the file: parallel runs may
   write it at the same time. Commit the repo files, including
   `knowledge/review-standards.md` when step 5 wrote to it, and step 4's
   prune edits, on the feature branch as one commit with the subject
   `Capture learnings` and the session's attribution line. Auto-memory
   writes are not committed. If no repo file changed, make no commit.
7. **Return** the Learnings summary for the caller's report:
   - one line per written learning: `<destination>: <learning>` (a rule
     written to the standards file appears as
     `knowledge/review-standards.md: <rule>`);
   - one line per prune edit to a repo file:
     `pruned: <file>: <old entry, shortened> → <new entry | removed>`;
   - one line per memory edit:
     `memory: <file>: <resolved | rewritten | deleted>: <why>`;
   - one line per decision or preference listed instead of written, and
     per step-4 ADR or memory conflict, starting `not written:`;
   - when no learning was written and nothing was pruned in the repo or in
     memory: `none`, then
     each dropped candidate with the step-2 rule that dropped it;
   - after the learnings lines, a `Hardening:` block with one line per
     `harden (...)` line from step 5, or `Hardening: none`.

   If the branch already has a `Capture learnings` commit from an earlier
   run, start the summary with that commit's entries and prune edits (from
   `git show`), each starting `already written:`, so a resumed run's
   report still lists them.
