# Scaffold secret scan: gitleaks CLI instead of gitleaks-action

- **Status:** approved
- **Date:** 2026-10-07

## Purpose

Every repo the kit scaffolds gets `.github/workflows/secret-scan.yml`, which
runs `gitleaks/gitleaks-action@v2`. In repos created since GitHub made the
workflow token read-only by default, it fails twice:

1. **First push to `main` fails.** The action scans the range
   `<first commit>^..<last commit>`. When the first commit is the root
   commit it has no parent, and git exits with `fatal: ambiguous argument`.
   Seen in `ship-fast-toy` and in another scaffolded POC repo.
2. **First pull request fails with 403.** On `pull_request` the action
   lists the PR's commits through the API. A read-only token without
   `pull-requests: read` gets `Resource not accessible by integration`.
   Seen in `ship-fast-toy`. Another POC repo avoided it only because its
   workflow was edited during the run.

The kit's own repo has an identical copy and passes. It is older, so its
default token permissions are still permissive, which is why the kit's CI
never caught either failure.

The fix replaces the action with the gitleaks CLI, pinned and
checksum-verified, scanning the full history. The CLI uses no GitHub API,
so it needs neither token permissions nor a license. It also scans no
commit range, so a root commit cannot break it.

## Scope

**In:**
- `plugin/templates/project/.github/workflows/secret-scan.yml`: rewritten
  as below.
- `.github/workflows/secret-scan.yml` (the kit's own copy): updated to
  stay byte-identical to the template.
- `tests/test_templates.py`: new tests (see Testing).

**Out:**
- Other template workflows (`ci.yml`, `claude-review.yml`) and the stack
  CI files.
- Automatic gitleaks version bumps. Dependabot cannot update a version
  inside a `run:` script; a bump is a manual edit of version plus checksum.
- `docs/audit/setup-audit.md`: a historical report, left as written.
- Existing scaffolded repos: not patched by this change.

## Design

### Workflow

Contents of both `secret-scan.yml` files:

```yaml
# Secret scanning with the gitleaks CLI over the full git history, on every
# push and pull request. Uses no GitHub API, so it needs no token
# permissions and no license. To upgrade, change GITLEAKS_VERSION and
# GITLEAKS_SHA256 together (the linux_x64 line of the release's
# checksums.txt).
name: secret-scan
on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  gitleaks:
    runs-on: ubuntu-latest
    env:
      GITLEAKS_VERSION: 8.30.1
      GITLEAKS_SHA256: 551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - name: Install gitleaks
        run: |
          tarball="gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
          curl -sSfL -o "$tarball" \
            "https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/${tarball}"
          echo "${GITLEAKS_SHA256}  ${tarball}" | sha256sum -c -
          tar -xzf "$tarball" gitleaks
          rm "$tarball"
      - name: Scan full history
        run: ./gitleaks git --redact --verbose --log-opts="HEAD" .
```

Behaviour:
- Every run scans all commits reachable from the checked-out ref (`HEAD`:
  the pushed commit, or on `pull_request` the PR's merge commit, which
  reaches both the PR's commits and the base branch). `--log-opts="HEAD"`
  is required: without it `gitleaks git` runs `git log --all`, and since
  `fetch-depth: 0` fetches every branch, a secret on any one branch would
  fail every run on every branch. If a
  secret is found, gitleaks exits 1 and the job fails. The log shows the
  finding with the secret redacted.
- If the checksum doesn't match, `sha256sum -c` exits non-zero and the job
  fails before gitleaks runs.
- If the download fails (`curl -f`), the job fails. A failed download never
  produces a passing scan.
- A secret committed to a branch fails every later run on that branch (and
  on branches that contain it) until it is removed from history or
  allowlisted (`.gitleaks.toml` or `.gitleaksignore`, both read by the CLI
  by default). Unlike the old action, which scanned only the pushed
  commits, the secret does not stop failing once a newer commit is pushed.

### Kit copy

`.github/workflows/secret-scan.yml` is byte-identical to the template today.
It is updated to match the new template, and a new test keeps the two in
sync.

## Decisions

- **CLI, not the action.** Adding `pull-requests: read` fixes only failure
  2, and the action still needs a license secret in org repos. The CLI fixes
  both failures and drops the license requirement. Cost: no PR comments or
  job summary from the action, which were already failing on new repos.
- **Pinned version, hardcoded checksum.** This verifies the binary against
  a value reviewed in this repo, not against a checksum file downloaded from
  the same release. Cost: manual upgrades.
- **Full history of the checked-out ref on every run, PRs included.** It's
  simple and has no range logic. Scaffolded repos are small, so a full scan
  takes seconds. Accepted behaviour change: a committed secret keeps the
  branch red until it is removed or allowlisted, where the old action went
  green again on the next push.
- **Checked-out ref only, not all refs.** A leak on one branch should not
  turn `main` and unrelated PRs red.
- **Only `contents: read`.** Checkout is the only API-backed step.

## Testing

Unit tests in `tests/test_templates.py`:
- `test_secret_scan_uses_pinned_cli`: the template contains no
  `gitleaks-action`; it contains `GITLEAKS_VERSION:` followed by an
  `X.Y.Z` version, `GITLEAKS_SHA256:` followed by exactly 64 hex characters,
  `sha256sum -c`, `gitleaks git`, `--log-opts="HEAD"`, and
  `fetch-depth: 0`.
- `test_secret_scan_declares_read_only_permissions`: the YAML text outside
  comments has a top-level `permissions:` block containing `contents: read`.
- `test_kit_secret_scan_matches_template`: the bytes of
  `.github/workflows/secret-scan.yml` equal the template's bytes.

## Success criteria

1. `pytest` passes (full suite), and `ruff check plugin tests` and
   `ruff format --check plugin tests` pass.
2. The kit's own PR for this change has a green `secret-scan` run on both
   `push` and `pull_request`, and so does the squash-merge push to `main`.
3. **Live check on a new repo.** Scaffold a throwaway private repo with
   the kit's scaffold, under a free name such as `secret-scan-check`
   (checked with `gh repo view` first; add a numeric suffix if taken),
   create it on GitHub (its default workflow
   permissions are `read`), and push `main`. That first-push run of
   `secret-scan` is green. Open a PR from a branch with one harmless commit;
   its `pull_request` run is green.
4. **Negative check**, run after criterion 3. On another branch of that
   repo, commit a fake
   secret that gitleaks' default rules detect (for example a generated
   `ghp_`-style GitHub token string). Its `secret-scan` run is red, and the
   log shows a finding with the value redacted. `main`'s latest run on
   that repo stays green.
5. The throwaway repo is left for the user to delete. Its name and run
   URLs are reported to the user in the session only, never in tracked
   files or the PR body (the kit repo is public).
