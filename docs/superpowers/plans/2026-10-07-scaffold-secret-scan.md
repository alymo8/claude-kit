# Scaffold Secret Scan Implementation Plan

- **Status:** approved
- **Date:** 2026-10-07

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `gitleaks/gitleaks-action@v2` with the pinned, checksum-verified
gitleaks 8.30.1 CLI in the scaffold template's `secret-scan.yml` and the kit's
own copy, pin both with tests, bump the plugin to 0.13.1, then prove it on a
throwaway GitHub repo.

**Architecture:** Two byte-identical YAML files (template and kit copy).
Three structure tests in `tests/test_templates.py` pin them. No Python script
changes: `plugin/scripts/scaffold.py` already copies the template unchanged.
A live check scaffolds a new repo from this branch's template and watches
its GitHub Actions runs.

**Tech Stack:** GitHub Actions YAML, Python 3.11+ pytest, ruff, `gh` CLI.

**Spec:** `docs/superpowers/specs/2026-10-07-scaffold-secret-scan-design.md`

## Context for a cold start

- Repo root: the worktree you are in (branch `feat/scaffold-secret-scan`).
  Commands run from the repo root in Git Bash.
- Test and lint commands (from `CLAUDE.md`):
  `pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.
- The template lives at
  `plugin/templates/project/.github/workflows/secret-scan.yml`; the kit's
  own copy at `.github/workflows/secret-scan.yml`. Today they are identical
  and run `gitleaks/gitleaks-action@v2`.
- `tests/test_templates.py` defines `PROJECT = PLUGIN / "templates" / "project"`
  (`PLUGIN` comes from `tests/helpers.py`, the `plugin/` directory).
- `tests/test_plugin_manifest.py::test_description_mentions_ship_fast`
  asserts `data["version"] == "0.13.0"`; the version lives in
  `plugin/.claude-plugin/plugin.json`.
- The kit repo is public. Never write the GitHub username or private repo
  names into tracked files; get the owner at runtime with
  `gh api user -q .login`.

## Global Constraints

- gitleaks version `8.30.1`; SHA-256 of `gitleaks_8.30.1_linux_x64.tar.gz`:
  `551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb`.
- Scan command: `./gitleaks git --redact --verbose --log-opts="HEAD" .`
- Workflow permissions: only `contents: read`.
- The kit's `.github/workflows/secret-scan.yml` is byte-identical to the
  template.
- The throwaway repo's name and run URLs are reported in the session only,
  never in tracked files or the PR body.

## Review Focus

1. Checksum mismatch or failed download must fail the job, never pass the
   scan: pinned by `sha256sum -c` and `curl -sSfL`, checked in Task 1's
   test (`sha256sum -c` required), and the YAML uses no `|| true`.
2. A secret on one branch must not turn `main` red: `--log-opts="HEAD"`,
   pinned by Task 1's test and exercised by Task 2 step 6.
3. The root-commit push (a brand new repo) must be green: Task 2 step 3.
4. A PR on a repo whose token is read-only must be green: Task 2 step 4.
5. The template and kit copy drifting apart: Task 1's byte-equality test.

## Answers to the gate's plan questions

- Permissions test: line-based, no YAML parser (PyYAML is not a dev
  dependency). After dropping comment lines, there must be a column-0
  `permissions:` line whose indented block contains `contents: read`
  (Task 1).
- Live check: runs after Task 1 is committed, before the PR merges, using
  this worktree's `plugin/scripts/scaffold.py` (so it uses the branch's
  template). Python stack, parent directory is a fresh temporary directory
  outside the repo, deleted at the end. `gh api .../actions/permissions/workflow`
  is recorded as evidence (Task 2).
- Local gitleaks run over the kit history: not needed as a separate step.
  The branch's own push CI is the new workflow's first full-history scan
  of the kit, and it runs before the merge (Task 3 step 1; a finding there
  stops the work and is reported).
- Negative check: a push run on a branch is enough; no PR (Task 2).
- Version: bump to `0.13.1` (every kit PR bumps the version) (Task 1).

---

### Task 1: Pinned gitleaks CLI workflow, tests and version bump

**Files:**
- Modify: `plugin/templates/project/.github/workflows/secret-scan.yml` (full rewrite)
- Modify: `.github/workflows/secret-scan.yml` (full rewrite, identical bytes)
- Modify: `plugin/.claude-plugin/plugin.json` (`"version"`)
- Test: `tests/test_templates.py` (append three tests)
- Test: `tests/test_plugin_manifest.py` (version literal)

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the template file that Task 2's scaffolded repo receives.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_templates.py`:

```python
SECRET_SCAN = PROJECT / ".github" / "workflows" / "secret-scan.yml"
KIT_SECRET_SCAN = PLUGIN.parent / ".github" / "workflows" / "secret-scan.yml"


def _yaml_lines(text):
    return [line for line in text.splitlines() if not line.lstrip().startswith("#")]


def test_secret_scan_uses_pinned_cli():
    text = SECRET_SCAN.read_text("utf-8")
    assert "gitleaks-action" not in text
    assert re.search(r"GITLEAKS_VERSION: \d+\.\d+\.\d+\b", text)
    assert re.search(r"GITLEAKS_SHA256: [0-9a-f]{64}\b", text)
    for needle in (
        "sha256sum -c",
        "gitleaks git",
        '--log-opts="HEAD"',
        "fetch-depth: 0",
    ):
        assert needle in text, needle


def test_secret_scan_declares_read_only_permissions():
    lines = _yaml_lines(SECRET_SCAN.read_text("utf-8"))
    start = lines.index("permissions:")
    block = []
    for line in lines[start + 1 :]:
        if line and not line[0].isspace():
            break
        block.append(line.strip())
    assert "contents: read" in block
    assert all(not entry or entry == "contents: read" for entry in block), block


def test_kit_secret_scan_matches_template():
    assert KIT_SECRET_SCAN.read_bytes() == SECRET_SCAN.read_bytes()
```

In `tests/test_plugin_manifest.py`, in `test_description_mentions_ship_fast`,
change `assert data["version"] == "0.13.0"` to
`assert data["version"] == "0.13.1"`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_templates.py tests/test_plugin_manifest.py -q`
Expected: `test_secret_scan_uses_pinned_cli` fails (`gitleaks-action` present),
`test_secret_scan_declares_read_only_permissions` fails (`ValueError`:
`'permissions:' is not in list`), `test_description_mentions_ship_fast`
fails (0.13.0 != 0.13.1). `test_kit_secret_scan_matches_template` passes
already (files identical today); that is expected.

- [ ] **Step 3: Write the workflow**

Write this exact content (trailing newline) to
`plugin/templates/project/.github/workflows/secret-scan.yml`. Line endings
don't matter: git stores LF in the index either way (`core.autocrlf=true`
here), and the test compares the two working-tree files, which `cp`
keeps identical. Then copy it byte for byte: `cp plugin/templates/project/.github/workflows/secret-scan.yml .github/workflows/secret-scan.yml`.

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

In `plugin/.claude-plugin/plugin.json` change `"version": "0.13.0"` to
`"version": "0.13.1"`.

- [ ] **Step 4: Run the full suite and lint**

Run: `pytest -q && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass. If `ruff format --check` flags `tests/test_templates.py`,
run `ruff format tests/test_templates.py` and re-run.

- [ ] **Step 5: Commit**

```bash
git add plugin/templates/project/.github/workflows/secret-scan.yml .github/workflows/secret-scan.yml plugin/.claude-plugin/plugin.json tests/test_templates.py tests/test_plugin_manifest.py
git commit -m "Secret scan: pinned gitleaks CLI instead of gitleaks-action

Fixes the 403 on the first PR of a new repo (read-only token) and the
failure on the first push (root commit has no parent). Bump to 0.13.1."
```

### Task 2: Live check on a throwaway repo (spec success criteria 3-5)

**Files:**
- None in the repo. Everything happens in a temporary directory outside it
  and on GitHub. Nothing is committed.

**Depends on:** Task 1

**Interfaces:**
- Consumes: the Task 1 template, through this worktree's
  `plugin/scripts/scaffold.py`.
- Produces: evidence (run URLs and conclusions) for the final report,
  reported in the session only.

**Shell state:** each shell call may start a fresh shell. Step 1 writes
`OWNER`, `NAME` and `PARENT` to `$HOME/.secret-scan-check.env` (outside the
repo). Every later step starts with the `PRELUDE` below, which reloads them,
refuses to continue if any is empty, and changes into the scaffolded repo:

```bash
. "$HOME/.secret-scan-check.env" && [ -n "$OWNER" ] && [ -n "$NAME" ] && [ -n "$PARENT" ] || exit 1
cd "$PARENT/$NAME" || exit 1
```

- [ ] **Step 1: Pick a free name and scaffold** (run from the repo root)

```bash
OWNER=$(gh api user -q .login)
NAME=secret-scan-check
n=2; while gh repo view "$OWNER/$NAME" >/dev/null 2>&1; do NAME="secret-scan-check-$n"; n=$((n+1)); done
PARENT=$(mktemp -d)
[ -n "$OWNER" ] && [ -n "$PARENT" ] || exit 1
printf 'OWNER=%s\nNAME=%s\nPARENT=%s\n' "$OWNER" "$NAME" "$PARENT" > "$HOME/.secret-scan-check.env"
python plugin/scripts/scaffold.py --name "$NAME" --stack python --parent "$PARENT"
diff --strip-trailing-cr "$PARENT/$NAME/.github/workflows/secret-scan.yml" plugin/templates/project/.github/workflows/secret-scan.yml && echo template-ok
```

Expected: scaffold exits 0, prints `template-ok`.

- [ ] **Step 2: Create the private repo and push `main`**

```bash
# PRELUDE
. "$HOME/.secret-scan-check.env" && [ -n "$OWNER" ] && [ -n "$NAME" ] && [ -n "$PARENT" ] || exit 1
cd "$PARENT/$NAME" || exit 1
gh repo create "$NAME" --private --source . --push
gh api "repos/$OWNER/$NAME/actions/permissions/workflow"
```

Expected: the repo is created and `main` pushed; the API prints
`"default_workflow_permissions":"read"`. Record it as evidence. If it
prints `write`, the 403 condition is not reproduced: note that in the
report and continue.

- [ ] **Step 3: First-push run is green (criterion 3)**

```bash
# PRELUDE
. "$HOME/.secret-scan-check.env" && [ -n "$OWNER" ] && [ -n "$NAME" ] && [ -n "$PARENT" ] || exit 1
cd "$PARENT/$NAME" || exit 1
SHA=$(git rev-parse HEAD)
until ID=$(gh run list --commit "$SHA" --workflow secret-scan.yml --json databaseId -q '.[0].databaseId') && [ -n "$ID" ]; do sleep 15; done
gh run watch "$ID" --exit-status
```

Expected: exit 0 (green). Keep the URL from `gh run view "$ID" --json url -q .url`.
The scaffolded `ci.yml` may fail because the python stack has no
`pyproject.toml` yet; that run is out of scope and is not counted.

- [ ] **Step 4: First PR run is green (criterion 3)**

```bash
# PRELUDE
. "$HOME/.secret-scan-check.env" && [ -n "$OWNER" ] && [ -n "$NAME" ] && [ -n "$PARENT" ] || exit 1
cd "$PARENT/$NAME" || exit 1
git switch -c harmless
echo "harmless change" > NOTES.txt
git add NOTES.txt && git commit -m "Harmless change"
git push -u origin harmless
gh pr create --title "Harmless change" --body "Live check for the secret-scan workflow."
SHA=$(git rev-parse HEAD)
until ID=$(gh run list --commit "$SHA" --workflow secret-scan.yml --event pull_request --json databaseId -q '.[0].databaseId') && [ -n "$ID" ]; do sleep 15; done
gh run watch "$ID" --exit-status
```

Expected: the `pull_request` run exits 0 (green). Keep its URL.

- [ ] **Step 5: Negative check, a fake secret turns the branch red (criterion 4)**

```bash
# PRELUDE
. "$HOME/.secret-scan-check.env" && [ -n "$OWNER" ] && [ -n "$NAME" ] && [ -n "$PARENT" ] || exit 1
cd "$PARENT/$NAME" || exit 1
git switch main
git switch -c leak
TOKEN=ghp_$(python -c "import secrets,string; print(''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(36)))")
printf 'GITHUB_TOKEN=%s\n' "$TOKEN" > config.env
git add config.env && git commit -m "Add config"
git push -u origin leak
SHA=$(git rev-parse HEAD)
until ID=$(gh run list --commit "$SHA" --workflow secret-scan.yml --json databaseId -q '.[0].databaseId') && [ -n "$ID" ]; do sleep 15; done
gh run watch "$ID" --exit-status; echo "exit=$?"
gh run view "$ID" --log-failed | grep -E "RuleID|Secret|REDACTED" | head
gh run view "$ID" --log | grep -c "$TOKEN"
```

Expected: `exit=1` (red); the log shows a finding (`RuleID: github-pat`)
with `REDACTED`; the last command prints `0` (the token never appears in
the log). Keep the run URL. Do not print `$TOKEN` in the report.

- [ ] **Step 6: `main` stays green (criterion 4)**

```bash
# PRELUDE
. "$HOME/.secret-scan-check.env" && [ -n "$OWNER" ] && [ -n "$NAME" ] && [ -n "$PARENT" ] || exit 1
cd "$PARENT/$NAME" || exit 1
gh run list --branch main --workflow secret-scan.yml -L 1 --json conclusion,url
```

Expected: `conclusion` is `success`. No new run on `main` was triggered by
the `leak` push.

- [ ] **Step 7: Clean up locally, leave the repo (criterion 5)**

```bash
. "$HOME/.secret-scan-check.env" && [ -n "$PARENT" ] && [ "$PARENT" != "/" ] || exit 1
cd "$HOME"
rm -rf "$PARENT" "$HOME/.secret-scan-check.env"
```

Leave the GitHub repo and its PR in place for the user to delete. Report
the repo name, the three run URLs and the permissions API output in the
session only.

### Task 3: Kit CI on the branch, the PR and `main` (spec success criterion 2)

**Files:**
- None changed. This task checks GitHub Actions runs of the kit repo.

**Depends on:** Task 1

**Interfaces:**
- Consumes: the Task 1 commit, pushed.
- Produces: run URLs for the PR body's Verification section and the report.

When `/ship` executes this plan, its steps 5 (push and CI), 7 (PR), 8 (green
PR CI) and 10 (verify `main`) do this task; check the expected outputs below
there. Run outside `/ship`, do the steps here.

- [ ] **Step 1: Push and check the branch's push run**

```bash
git push -u origin feat/scaffold-secret-scan
SHA=$(git rev-parse HEAD)
until ID=$(gh run list --commit "$SHA" --workflow secret-scan.yml --event push --json databaseId -q '.[0].databaseId') && [ -n "$ID" ]; do sleep 15; done
gh run watch "$ID" --exit-status
```

Expected: exit 0. This is the new workflow's first full-history scan of the
kit. If it reports a finding, do not add a `.gitleaksignore` entry or edit
history: stop and report the finding (rule, file, commit) to the user, since
allowlisting is outside the spec's scope.

- [ ] **Step 2: Open the PR and check its run**

Open the PR (under `/ship`, its step 7 does this with the spec title), then:

```bash
gh run list --commit "$(git rev-parse HEAD)" --workflow secret-scan.yml --json event,conclusion,url,headSha
```

Expected: at least one `push` and one `pull_request` entry for the latest
commit, both `"conclusion":"success"` (wait with `gh pr checks --watch` first).

- [ ] **Step 3: After the squash-merge, check `main`**

```bash
gh run list --branch main --workflow secret-scan.yml -L 1 --json conclusion,url,headSha
```

Expected: `headSha` is the squash commit and `conclusion` is `success`
(wait with `gh run watch <id> --exit-status` if it is still running).

- [ ] **Step 4: Commit**

Nothing to commit: this task changes no files. Paste the three run URLs into
the PR body's Verification section instead.
