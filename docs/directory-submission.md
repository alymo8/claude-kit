# Submitting agent-kit to Anthropic's plugin directory

Anthropic's plugin directory is managed at `claude.ai/directory/manage`; one
listing reaches claude.ai, Cowork and Claude Code. The repo is kept
checklist-clean by `tests/test_directory_ready.py`; the submission itself is
the repository owner's to make. This guide walks through the portal in order.

## Before you start

- You need a paid claude.ai plan to open the directory portal.
- From a checkout of `main`, run both checks and fix anything they report
  before you submit:

  ```
  claude plugin validate ./plugin --strict
  pytest tests/test_directory_ready.py
  ```

  `claude plugin validate` checks the manifest only; the pytest file checks
  the rest of the pre-submission checklist (README, licence, file limits,
  hook commands, reserved words in the name).

## Source

- **Repository:** `alymo8/claude-kit` (public, on github.com).
- **Plugin path:** `plugin`
- **Tracked branch:** `main`

Each commit on the tracked branch is scanned, then a reviewer publishes the
version.

## Validate

The portal validates the source before you can go on.

- **A warning:** fix it in the repo, merge the fix to `main`, push, then run
  Validate again. Do not work around a warning in the portal text.
- **A hold:** a reviewer reads the submission. Answer the reviewer's question
  in the portal; change the repo only if the answer needs it.

## Listing details

Drafted text; edit it in the portal as you like.

- **One-line summary:** Spec-driven workflow for Claude Code: specs, gates,
  worktrees, review and merge.
- **Short description:** agent-kit turns a spec into a merged pull request:
  it gates specs and plans, builds in git worktrees, reviews the diff against
  the spec, and ships with `/ship`. Session hooks keep handoff files and nudge
  you before the context grows expensive. It also scaffolds new projects with
  shared conventions.
- **Keywords:** `spec-driven`, `workflow`, `specs`, `code-review`,
  `git-worktrees`, `conventions`

## Data handling

Drafted answers, taken from the Network section of
[`plugin/README.md`](../plugin/README.md). Check them against that section
before you submit, in case it has changed.

- **Does the plugin collect or send data?** No telemetry. Nothing is sent to
  the plugin's authors or any third party.
- **Does it make network calls?** Hooks open no network connection, with one
  exception: the SessionEnd hook `handoff_snapshot.py` runs `gh pr view` (a
  GitHub API call with the user's own `gh` sign-in) when the current branch
  has an upstream and `gh` is installed, to record the branch's pull-request
  URL in a local handoff file. Commands and skills the user invokes call
  GitHub through the user's own `git` and `gh`: `/ship`, `/ship-many` and
  `/ship-fast` fetch, push branches and open pull requests (`/ship` and
  `/ship-many` also merge them); the `pr-review-respond` skill reads review
  threads (`scripts/review-threads.py`, one `gh api graphql` query) and posts
  replies; `audit-deep` runs `gh run list`; `present` runs `gh pr view`.
  `/ship-many` starts headless `claude -p` sessions (`scripts/ship-child.py`).
- **What does it store locally?** Handoff files under `.claude/handoffs/` in
  the user's repo (git state and the last few prompts of the session), the
  spec index `docs/superpowers/README.md`, and a small context-nudge marker
  file in the session's scratchpad or temp folder.
- **Credentials:** the plugin reads none and stores none; `gh` and `git` use
  the user's existing sign-in.

## Compliance

The contact email and the compliance acknowledgements are the owner's to fill
in, in the portal. This guide does not fill them in, and the repo does not
store them.

## After publishing

- Every version bump on `main` is scanned and reviewed again before it is
  published, so keep `tests/test_directory_ready.py` passing.
- Once the listing is live, add the directory route to the Install section of
  the repo `README.md`, as a separate change.
