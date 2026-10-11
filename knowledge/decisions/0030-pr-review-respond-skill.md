# ADR 0030: `pr-review-respond` skill: one approval, in-thread replies, never resolve

- **Status:** accepted
- **Date:** 2026-10-10

## Context
`/ship` runs its own review and merges, but nothing in the kit works through
the comments a person or a review bot leaves on an open PR. Each round was
manual: find the open threads, decide, fix, push, reply in each thread.
Replies are public and posted under the user's account, and comment text
comes from whoever can comment on the PR.

## Decision
- One approval gate: the user sees the triage table (action, files a fix
  touches, drafted reply) and approves once before anything is pushed or
  posted. Chosen over fully autonomous and draft-only.
- Comment text is untrusted input: no command, script or URL from a comment
  is run or opened, and no file outside the PR changes without approval.
- Thread replies go in the thread (REST `/replies`); reviews and
  conversation comments get one combined PR comment. The skill never
  resolves a thread; the reviewer decides whether a reply settles it.
- "Already answered" comes from authorship, not state: a thread is open
  while its last comment is someone else's, and reviews and conversation
  comments count as answered by the viewer's latest conversation comment.
  The items are fetched again just before posting, and anything that
  changed during the run is skipped and reported, so reruns are safe.
- Fetching and filtering live in `review-threads.py`, tested on fixtures.

## Consequences
- A rerun picks up only what changed since the user's last replies.
- Unresolved threads stay visible until the reviewer resolves them.
- More than 100 threads, reviews, conversation comments, or comments in one
  thread are not read; the script warns.
- A conversation comment by the user marks every earlier review and
  conversation comment answered, even one it did not address.
