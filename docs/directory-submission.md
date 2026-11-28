# Submitting agent-kit-lite to Anthropic's plugin directory

Anthropic's plugin directory is managed at `claude.ai/directory/manage`; one
listing reaches claude.ai, Cowork and Claude Code. The directory takes hooks
and scripts only from Verified organizations, so it lists `agent-kit-lite`, a
Markdown-only plugin built into `lite/` from `plugin/`
([ADR 0058](../knowledge/decisions/0058-directory-lite-plugin.md)). The full
`agent-kit` stays on this repo's own marketplace. The submission itself is
the repository owner's to make. This guide walks through the portal in order.

## Before you start

- You need a paid claude.ai plan to open the directory portal.
- From a checkout of `main`, run both checks and fix anything they report
  before you submit:

  ```
  claude plugin validate ./lite --strict
  pytest tests/test_lite_build.py tests/test_directory_ready.py
  ```

  `claude plugin validate` checks the manifest only; the pytest files check
  that `lite/` matches the build and holds only files the directory accepts,
  and the rest of the pre-submission checklist (README, licence, file limits,
  reserved words in the name).
- The portal takes the icon (`lite/.claude-plugin/icon.png`) only the first
  time you save or submit the plugin; after that it is final.

## Source

- **Repository:** `alymo8/claude-kit` (public, on github.com).
- **Plugin path:** `lite`
- **Plugin name:** `agent-kit-lite`
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

- **One-line summary:** Spec-driven workflow for Claude Code: gated specs and
  plans, review, and /ship from spec to pull request.
- **Short description:** agent-kit-lite turns a spec into a pull request: it
  gates specs and plans, builds in git worktrees, reviews the diff against the
  spec, ships with `/ship` and `/ship-fast`, and writes handoffs so the next
  session can continue. It has no hooks and no scripts; the full kit, with
  session hooks, is on the repository's own marketplace.
- **Keywords:** `spec-driven`, `workflow`, `specs`, `code-review`,
  `git-worktrees`, `conventions`

## Data handling

Drafted answers, taken from the Data and network section of
[`lite/README.md`](../lite/README.md). Check them against that section
before you submit, in case it has changed.

- **Does the plugin collect or send data?** No telemetry. Nothing is sent to
  the plugin's authors or any third party.
- **Does it make network calls?** It has no hooks, so nothing runs on its
  own. Commands and skills the user invokes call GitHub through the user's
  own `git` and `gh`: `/ship` and `/ship-fast` fetch, push branches and open
  pull requests (`/ship` also merges them); the `pr-review-respond` skill
  reads review threads with one `gh api graphql` query and posts replies.
- **What does it store locally?** Handoff files under `.claude/handoffs/` in
  the user's repo, written when the user runs `/handoff`.
- **Credentials:** the plugin reads none and stores none; `gh` and `git` use
  the user's existing sign-in.

## Compliance

The contact email and the compliance acknowledgements are the owner's to fill
in, in the portal. This guide does not fill them in, and the repo does not
store them.

## After publishing

- Every version bump on `main` is scanned and reviewed again before it is
  published, so keep `tests/test_lite_build.py` passing.
- Rerun `python scripts/build-lite.py` after each `plugin/` change and commit
  the regenerated `lite/` with it.
- Once the listing is live, add the directory route to the Install section of
  the repo `README.md`, as a separate change.
