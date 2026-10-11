# Template CI hardening: SHA-pinned actions, Dependabot, and a workflows README

- **Status:** approved
- **Date:** 2026-10-10

## Purpose

Repos scaffolded by the kit reference GitHub Actions by moving tags
(`actions/checkout@v4`). A tag can be repointed, so a compromised or broken
release reaches every repo on its next run. For client repos, pinning to a
commit SHA is the baseline. Pins go stale unless something bumps them, so the
template also gets a monthly, grouped Dependabot config for actions.

Two pieces of CI knowledge exist only in people's heads today:
- which check names to mark as required in branch protection;
- that a required check must never have a `paths:` filter on
  `pull_request`. A filtered check that does not run stays "Expected" and
  blocks the merge forever.

This change writes both down: a `.github/workflows/README.md` in every
scaffolded repo, and a comment above each `pull_request:` trigger.

## Scope

**In:**
- `plugin/templates/project/.github/workflows/secret-scan.yml` and
  `claude-review.yml`, and `plugin/templates/stacks/node/ci.yml` and
  `plugin/templates/stacks/python/ci.yml`: every `uses:` pinned (see Pinning). Add the
  no-paths comment (see No-paths comment) to `secret-scan.yml` and both stack
  `ci.yml` files.
- `.github/workflows/ci.yml` and `.github/workflows/secret-scan.yml` (the
  kit's own): pinned the same way. The kit's `secret-scan.yml` also gets
  the no-paths comment. `secret-scan.yml` stays byte-identical to
  the template (the existing `test_kit_secret_scan_matches_template` enforces
  this).
- `plugin/templates/project/.github/dependabot.yml` (new), and the same file
  at `.github/dependabot.yml` (new) in the kit, byte-identical.
- `plugin/templates/project/.github/workflows/README.md` (new).
- `plugin/scripts/scaffold.py`: one more line in new mode's closing output.
- `tests/test_templates.py`: `EXPECTED` gains the two new template files;
  new tests (see Testing).
- `tests/test_scaffold.py`: assert the new output lines (new and adopt mode).
- `knowledge/decisions/0028-pinned-actions-and-workflows-readme.md` (new)
  and its row in `knowledge/decisions/README.md`. Use the next free number if
  0028 is taken.
- `plugin/.claude-plugin/plugin.json` (minor version bump from `main`),
  `tests/test_plugin_manifest.py`, and `README.md` (one line on the
  hardened CI template).

**Out:**
- A scheduled (cron) run of any workflow. The user dropped it: without a
  dependency or SAST scanner, a weekly run of pinned tools on unchanged code
  finds almost nothing, and it emails failures from abandoned POCs.
- SAST (Semgrep) and dependency (Trivy) scanning: a separate, later spec.
- Setting branch protection automatically. The README gives the command; the
  user runs it.
- Turning on `claude-review.yml` (it stays `workflow_dispatch` only).
- Patching repos that were already scaffolded.
- Checking a live Dependabot run (it runs on GitHub's schedule, not on
  push).

## Design

### Pinning

Every `uses: owner/repo@ref` becomes
`uses: owner/repo@<40-hex SHA> # vX.Y.Z`:
- `ref` is replaced by the commit SHA of the **newest release tag in the
  same major version** as the current ref (for `@v4`, the newest `v4.x.y`).
- The comment is that full tag, which is the form Dependabot reads and
  updates.
- An annotated tag is dereferenced to its commit, for example:
  `gh api repos/<o>/<r>/git/ref/tags/<tag>`, then, if the object `type` is
  `tag`, `gh api repos/<o>/<r>/git/tags/<sha>` for the commit.
- If an action has no `vX.Y.Z` tag in that major version (only a moving
  `vN`), pin the SHA that `vN` points to now, with comment `# vN`.

Actions in scope:
- `actions/checkout`
- `astral-sh/setup-uv`
- `pnpm/action-setup`
- `actions/setup-node`
- `anthropics/claude-code-action`
- `actions/setup-python` (kit only)

No other line of the workflows changes, apart from the comment below.

### No-paths comment

Directly above the `pull_request:` line in `secret-scan.yml` and both stack
`ci.yml` files, at that line's indentation:

```yaml
  # Required check: never add a `paths:` filter under pull_request. A required
  # check that does not run stays "Expected" and blocks the merge forever.
  # The push trigger may be filtered.
```

### Dependabot

`plugin/templates/project/.github/dependabot.yml` and the kit's
`.github/dependabot.yml`:

```yaml
# Keeps the SHA-pinned actions in .github/workflows current: one grouped
# pull request a month bumps every action and its version comment.
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: monthly
    groups:
      actions:
        patterns: ["*"]
```

Only `github-actions`; npm/pip updates are out of scope.

### Workflows README

`plugin/templates/project/.github/workflows/README.md`, with this content
(the plan may reword sentences but must keep every table row, check name
and command):

````markdown
# CI workflows

| Workflow | Runs on | Check name | Required? |
|---|---|---|---|
| `ci.yml` | push to `main`, every pull request | `build-test` | yes |
| `secret-scan.yml` | every push and pull request | `gitleaks` | yes |
| `claude-review.yml` | manual only (`workflow_dispatch`) until enabled | `review` | no (advisory) |

`../dependabot.yml` opens one grouped pull request a month that bumps the
pinned actions.

## Making checks required

The required set lives in three places that must change together: the job
IDs in the workflow files, the table above, and branch protection on `main`.
To set branch protection (repo admin; on a free account, private repos need
GitHub Pro for branch protection), run in bash or Git Bash:

```bash
gh api -X PUT repos/{owner}/{repo}/branches/main/protection --input - <<'EOF'
{"required_status_checks": {"strict": false, "contexts": ["build-test", "gitleaks"]},
 "enforce_admins": false, "required_pull_request_reviews": null, "restrictions": null}
EOF
```

## Rules for editing workflows

- Never add a `paths:` filter to `pull_request` on a required check: a check
  that does not run stays "Expected" and blocks the merge forever.
- Pin every action to a full commit SHA with its version as a comment
  (`@<sha> # v4.2.2`). Dependabot keeps them current.
- Renaming or removing a required job means updating branch protection in
  the same change.

## Not included

- SAST and dependency vulnerability scanning: not set up yet.
- Deploy pipelines: per project.
- AI review: `claude-review.yml` stays manual until credentials are set up
  (see the comment at its top).
````

`{owner}` and `{repo}` are `gh api` placeholders, which it fills from the
current repo. They are single-brace, so the scaffolder's `{{...}}`
placeholder check does not touch them.

### Scaffold output

In `scaffold_new`, after the existing `then: /init …` line, print:

```
then: mark build-test and gitleaks as required checks on main (see .github/workflows/README.md).
```

Adopt mode writes every missing template file, as it does today, so it
also adds `.github/dependabot.yml` and `.github/workflows/README.md` when
they are missing. An adopted repo keeps its own `ci.yml`, whose job IDs may
differ from the README's. So when `.github/workflows/README.md` is created
and `.github/workflows/ci.yml` was skipped (already present), adopt mode
prints:

```
check .github/workflows/README.md: its required check names must match your workflows' job IDs.
```

`tests/test_scaffold.py` asserts that adopt mode, in a repo that already
has `.github/workflows/ci.yml`, creates both new files and prints that
line.

### ADR 0028

`knowledge/decisions/0028-pinned-actions-and-workflows-readme.md`, status
`accepted`, covering three things:
- actions are pinned to SHAs and kept current by monthly grouped Dependabot;
- required checks are documented in the workflows README and never
  path-filtered on `pull_request`;
- no scheduled runs until a scanner exists to justify them.

## Decisions

- **SHA pins with version comments.** Chosen over tags for supply-chain
  safety. Cost: Dependabot PRs.
- **Dependabot monthly, grouped, actions only.** The user chose this: at
  most one PR a month per repo.
- **No cron schedule.** The user dropped it (see Out).
- **Branch protection is documented, not applied.** It is an outward change
  to the remote repo and needs admin rights and, on private repos, GitHub
  Pro.
- **The kit pins its own workflows too.** It has its own Dependabot file, and
  `secret-scan.yml` stays identical to the template.

## Testing

In `tests/test_templates.py`:
- `test_actions_are_sha_pinned`: in every `*.yml` under
  `plugin/templates/project/.github/workflows/`,
  `plugin/templates/stacks/*/ci.yml` and `.github/workflows/`, every
  non-comment line containing `uses:` matches
  `uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+(\.\d+){0,2}$`, and at least one
  such line exists per file that has a `steps:` key.
- `test_pull_request_has_no_paths_filter`: in `secret-scan.yml` and both
  stack `ci.yml` files, the non-comment YAML has no line whose stripped text
  starts with `paths:` or `paths-ignore:`, and the block of consecutive comment
  lines directly above `pull_request:` contains `` `paths:` ``.
- `test_dependabot_matches_kit_and_is_monthly_grouped`: the template and kit
  `dependabot.yml` are byte-identical and contain
  `package-ecosystem: github-actions`, `interval: monthly` and `groups:`.
- `test_workflows_readme_names_every_job`: every job ID under `jobs:` in the
  template workflows and both stack `ci.yml` files (`build-test`, `gitleaks`,
  `review`) appears in the README in backticks, every workflow file name
  appears, and the README contains `paths:`, `branches/main/protection` and
  `Not included`.
- `EXPECTED` gains `.github/dependabot.yml` and
  `.github/workflows/README.md`.

In `tests/test_scaffold.py`: new-mode output contains
`mark build-test and gitleaks as required checks`. Adopt mode, in a repo
that already has `.github/workflows/ci.yml`, creates
`.github/dependabot.yml` and `.github/workflows/README.md` and prints the
`check .github/workflows/README.md` line.

## Success criteria

1. `pytest`, `ruff check plugin tests` and `ruff format --check plugin tests`
   pass.
2. The kit's own PR has green `ci` (both OS) and `secret-scan` runs with the
   pinned actions.
3. **Live check.** Scaffold a throwaway private repo with `--stack python` (a free name such as
   `ci-hardening-check`, checked with `gh repo view` first). Run
   `uv init` and `uv add --dev pytest ruff`, and add one passing test. Create
   the repo on GitHub and push `main`. Its `build-test` and `gitleaks` runs
   are green.
4. Every SHA in the pinned lines resolves to a commit in the action's repo:
   `gh api repos/<o>/<r>/commits/<sha>` returns 200 for each.
5. The throwaway repo is left for the user to delete. Its name and run URLs
   appear only in the session, never in tracked files or the PR body (the
   kit repo is public).
