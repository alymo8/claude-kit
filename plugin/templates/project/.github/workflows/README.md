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
