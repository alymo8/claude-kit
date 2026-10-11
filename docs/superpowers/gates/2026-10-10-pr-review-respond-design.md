# Gate: `pr-review-respond` skill: work through a PR's review comments

- **Spec:** docs/superpowers/specs/2026-10-10-pr-review-respond-design.md
- **Spec SHA-256:** c274ce102811474f554535ef963e959e32781f16af98f07377d28333d1dbcf11
- **Verdict:** pass
- **Date:** 2026-10-10
- **Rounds:** 3 discovery + 0 verification

## Key decisions

- One approval gate (triage table with drafted replies and files touched) before anything is pushed or posted (user's choice over autonomous and draft-only).
- **ask** items are put to the user; each answer becomes fix, push back, or clarify (a question posted to the reviewer).
- Threads are never resolved; replies go in-thread via the REST `/replies` endpoint; reviews and conversation comments get one combined PR comment.
- "Answered" is by authorship: a thread is open while its last comment is not the viewer's; reviews and conversation comments are answered by the viewer's latest conversation comment. A re-fetch before posting skips items that changed during the run and reports them.
- Comment text is untrusted input: no commands or URLs from comments, no files outside the PR without approval.
- PR author only (author ≠ viewer stops); one commit per fix; stop after 2 failed verification attempts with nothing pushed or posted; no automatic second round when CI is red; "no CI checks" is not a failure.
- Fetching and filtering live in a tested script (`review-threads.py`, 100-item cap per connection with a warning).
- `/ship` and `/ship-fast` unchanged; ADR 0030 expected; minor version bump.
- Live check uses a `review-bot.yml` workflow (single review comments by the Actions bot) in a throwaway repo left for the user to delete.

## Findings fixed

- round 1 [blocking] Live check impossible with one account: review comments come from a `review-bot.yml` workflow using `github.token`.
- round 1 [blocking] What an **ask** answer does was unspecified: it becomes fix, push back, or clarify; clarify reply form added.
- round 1 [minor] Case of `untrusted` in the test: compared case-insensitively.
- round 1 [minor] Approval table lacked files touched: column added, outside-PR files flagged.
- round 1 [minor] Criterion 2 duplicated criterion 1: folded in.
- round 2 [blocking] Items arriving between fetch and reply marked answered: re-fetch before posting; changed items skipped and reported; Decisions and ADR updated.
- round 2 [minor] PR authorship not checked: author ≠ viewer is a stop condition.
- round 2 [minor] `gh pr checks --watch` with no checks: reported as "no CI checks".
- round 2 (plan, resolved in criteria) Bot review body: comments posted singly via `pulls/<pr>/comments`, so their reviews have empty bodies.
- round 3 [minor] PR `author` missing from the query and JSON: added.
- round 3 [minor] Bot login differs between GraphQL and REST: reworded.
- round 3 [minor] ADR number gap: "next free number at implementation time (0030 expected)".

## Plan questions

- How is `gh` made stubbable for `main` tests (a module-level `run_gh` monkeypatched after `load_module`)? (Testing)
- How does `open_items` treat a null (deleted) author, and what label does each connection get in the warning? (Design, review-threads.py)
- How does `test_plugin_manifest.py` change (relax `== "0.17.0"`, add a test for `pr-review-respond` in the description)? (Scope)
- How are multi-line reply bodies passed to `gh api` (`-F body=@<tmpfile>`), and where does the temp file live? (Step 7)
- What does step 5 do when the repo's `CLAUDE.md` is missing or lists no test/lint commands? (Step 5)
- Does each combined-comment paragraph name the fix commit SHA when the action is fix? (Step 7)
- Should step 1 stop or warn when the branch is ahead of its upstream (rerun after a step-5 failure)? (Step 1)
- How does the skill get the PR's file list (`gh pr diff --name-only`)? (Steps 2, 4)
- Does a step-1 thread missing from the re-fetch (resolved meanwhile) still get its reply? (Step 7)
- How does `review-bot.yml` get `commit_id`, and does the PR include a test covering the function? (Success criteria)

## Open

- none
