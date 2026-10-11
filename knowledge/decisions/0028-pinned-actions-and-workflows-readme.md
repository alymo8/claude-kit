# ADR 0028: Pinned actions, Dependabot, and a workflows README

- **Status:** accepted
- **Date:** 2026-10-10

## Context
Scaffolded repos referenced GitHub Actions by moving tags (`@v4`), so a
repointed or broken release reached every repo on its next run. Which checks
to mark required, and that a required check must never be path-filtered on
`pull_request`, lived only in people's heads.

## Decision
- Every action in the scaffold templates and the kit's own workflows is
  pinned to a commit SHA with its full version tag as a comment. A monthly,
  grouped Dependabot config (`github-actions` only) keeps the pins current,
  in the template and the kit (byte-identical).
- Each scaffolded repo gets `.github/workflows/README.md`: the check names
  (`build-test`, `gitleaks` required; `review` advisory), the `gh api`
  command for branch protection, and the editing rules. A comment above
  each required check's `pull_request:` forbids a `paths:` filter.
- Branch protection is documented, never applied by the kit.
- No scheduled (cron) runs until a dependency or SAST scanner exists to
  justify them.

## Consequences
- At most one Dependabot PR a month per repo.
- In the kit, Dependabot bumps only `.github/workflows`, not the copies
  under `plugin/templates`. A test requires one pin per action across both,
  so the kit's Dependabot PR fails until the bump is copied into the
  templates in the same PR.
- Adopted repos get the README and Dependabot file when missing, with a
  warning when their own `ci.yml` may not match the README's check names.
- Already-scaffolded repos are not patched.
