# Template CI Hardening Implementation Plan

- **Status:** approved
- **Date:** 2026-10-10

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin every GitHub Action in the scaffold templates and the kit's own
workflows to a commit SHA, add a monthly grouped Dependabot config, add a
workflows README that names the required checks, extend the scaffolder's
closing output, record ADR 0028, and bump the plugin to 0.19.0.

**Architecture:** Template and workflow file edits pinned by structure tests
in `tests/test_templates.py`; one small output change in
`plugin/scripts/scaffold.py` pinned by `tests/test_scaffold.py`. A live
check on a throwaway GitHub repo closes the work.

**Tech Stack:** GitHub Actions YAML, Dependabot, Python 3.11+ pytest, ruff,
`gh` CLI.

**Spec:** `docs/superpowers/specs/2026-10-10-template-ci-hardening-design.md`

## Context for a cold start

- Repo root: the worktree you are in (branch `feat/template-ci-hardening`).
  Run commands from the repo root in Git Bash.
- Test and lint (from `CLAUDE.md`): `pytest`, `ruff check plugin tests`,
  `ruff format --check plugin tests`.
- `tests/helpers.py` exports `PLUGIN` (the `plugin/` dir), `load_module`,
  `run_script`.
- `tests/test_templates.py` already defines `PROJECT`, `TEMPLATES`,
  `SECRET_SCAN`, `KIT_SECRET_SCAN` and `_yaml_lines(text)` (lines that do not
  start with `#` after `lstrip`). Reuse them.
- `tests/test_scaffold.py` has its own `EXPECTED` list and a `repo` fixture
  (a git repo with `CLAUDE.md`, `.gitignore` and one spec, committed).
- The checkout uses `core.autocrlf=true`; files that must be byte-identical
  are produced by copying one file onto the other (`cp`), never by typing
  both.

## Global Constraints

- Pinned form: `uses: owner/repo@<40-hex SHA> # vX.Y.Z`. SHAs were resolved
  on 2026-10-10 (newest release tag in the current major; annotated tags
  dereferenced) and each returns 200 from `gh api repos/<o>/<r>/commits/<sha>`:

  | Action | Tag | SHA |
  |---|---|---|
  | `actions/checkout` | v4.4.0 | `11d5960a326750d5838078e36cf38b85af677262` |
  | `astral-sh/setup-uv` | v5.4.2 | `d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86` |
  | `pnpm/action-setup` | v4.4.0 | `fc06bc1257f339d1d5d8b3a19a8cae5388b55320` |
  | `actions/setup-node` | v4.4.0 | `49933ea5288caeca8642d1e84afbd3f7d6820020` |
  | `anthropics/claude-code-action` | v1.0.248 | `1d6de8cb0c237e7c15e9e1bdf973826ebae490cc` |
  | `actions/setup-python` | v5.6.0 | `a26af69be951a213d495a4c3e4e4022e16d87065` |

- No line of any workflow changes except `uses:` lines and the no-paths
  comment.
- The kit's `.github/workflows/secret-scan.yml` stays byte-identical to the
  template; the kit's `.github/dependabot.yml` is byte-identical to the
  template's.
- ADR number 0028 (0027 is taken by `0027-adr-triggers.md`).
- Plugin version `0.19.0` (from `0.18.0` on `main`).
- The live-check repo's name and run URLs never appear in tracked files or
  the PR body.

## Review Focus

- A `uses:` line indented as `      - uses:` (list item) must be matched: the
  pin test uses `re.search`, not `re.match`. Pinned in Task 1's test.
- A `uses:` inside a YAML comment (the claude-review header, or a future
  commented example) must not be checked. Pinned: Task 1 skips comment lines.
- The placeholder template `ci.yml` (`jobs: {}`, no `steps:`) must not fail
  the "at least one pinned line" check. Pinned: the check applies only to
  files with a `steps:` key.
- An adopted repo whose own `ci.yml` exists must get the check-names warning;
  one whose `ci.yml` was created by adopt must not. Pinned: Task 3 tests both.
- Job-ID extraction must not silently find nothing. Pinned: Task 2's README
  test asserts the extracted set equals `{"build-test", "gitleaks", "review"}`.

## Answers to the gate's plan questions

- **Pin test matching:** per line of `read_text("utf-8").splitlines()`, skip
  lines whose `lstrip()` starts with `#`, and for lines containing `uses:`
  assert `re.search(PIN_RE, line)` (Task 1).
- **Job IDs:** extracted by indentation: after the `jobs:` line, every line
  of the form two spaces + identifier + `:` (regex `^  ([\w-]+):\s*$`) until
  the next non-indented line. The placeholder `ci.yml` (`jobs: {}`) yields
  none; the test asserts the union equals `{"build-test", "gitleaks",
  "review"}` so a broken extractor fails (Task 2).
- **Manifest test:** follow the existing pattern: replace
  `test_version_is_0_18_0` with `test_version_is_0_19_0` asserting
  `== "0.19.0"` (Task 4).
- **Adopt check line position:** after the `.gitignore` hint, immediately
  before `review with \`git status\`, then commit.` (Task 3).
- **README section:** the setup paragraph that introduces `/new-project` and
  `/adopt-conventions`; one sentence after the `/adopt-conventions` clause
  (Task 4).
- **ADR number:** 0027 is taken, so 0028 (Task 4).
- **Live check order:** scaffold with `--stack python` → `uv init` →
  `uv add --dev pytest ruff` → one passing test → commit → `gh repo create
  --private --source . --push` (Task 4).

---

### Task 1: Pin every action and add the no-paths comment

**Files:**
- Modify: `plugin/templates/project/.github/workflows/secret-scan.yml`
- Modify: `plugin/templates/project/.github/workflows/claude-review.yml`
- Modify: `plugin/templates/stacks/node/ci.yml`
- Modify: `plugin/templates/stacks/python/ci.yml`
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/secret-scan.yml`
- Test: `tests/test_templates.py`

**Depends on:** none

**Interfaces:**
- Produces: `KIT_WORKFLOWS`, `STACK_CIS`, `PIN_RE` and `_workflow_files()`
  in `tests/test_templates.py` (Task 2 uses `STACK_CIS`).

- [ ] **Step 1: Write the failing tests** (append to `tests/test_templates.py`)

```python
KIT_WORKFLOWS = PLUGIN.parent / ".github" / "workflows"
STACK_CIS = [TEMPLATES / "stacks" / s / "ci.yml" for s in ("node", "python")]
PIN_RE = re.compile(r"uses: [\w.-]+/[\w.-]+@[0-9a-f]{40} # v\d+(\.\d+){0,2}$")


def _workflow_files():
    return [
        *sorted((PROJECT / ".github" / "workflows").glob("*.yml")),
        *STACK_CIS,
        *sorted(KIT_WORKFLOWS.glob("*.yml")),
    ]


def test_actions_are_sha_pinned():
    for path in _workflow_files():
        lines = _yaml_lines(path.read_text("utf-8"))
        uses = [line for line in lines if "uses:" in line]
        for line in uses:
            assert PIN_RE.search(line), f"{path}: {line}"
        if any(line.strip() == "steps:" for line in lines):
            assert uses, f"{path} has steps but no pinned action"


def test_pull_request_has_no_paths_filter():
    for path in [SECRET_SCAN, *STACK_CIS]:
        lines = path.read_text("utf-8").splitlines()
        for line in _yaml_lines("\n".join(lines)):
            stripped = line.strip()
            assert not stripped.startswith(("paths:", "paths-ignore:")), path
        index = next(i for i, line in enumerate(lines) if line.strip() == "pull_request:")
        comments = []
        for line in reversed(lines[:index]):
            if not line.lstrip().startswith("#"):
                break
            comments.append(line)
        assert "`paths:`" in "\n".join(comments), path
```

(Run `ruff format tests` afterwards; it may rewrap the `next(...)` line.)

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_templates.py -k "sha_pinned or paths_filter" -v`
Expected: both FAIL (`@v4` does not match; no comment above `pull_request:`).

- [ ] **Step 3: Pin the `uses:` lines** with the SHAs from Global Constraints:

```
actions/checkout@v4             -> actions/checkout@11d5960a326750d5838078e36cf38b85af677262 # v4.4.0
astral-sh/setup-uv@v5           -> astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86 # v5.4.2
pnpm/action-setup@v4            -> pnpm/action-setup@fc06bc1257f339d1d5d8b3a19a8cae5388b55320 # v4.4.0
actions/setup-node@v4           -> actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4.4.0
anthropics/claude-code-action@v1 -> anthropics/claude-code-action@1d6de8cb0c237e7c15e9e1bdf973826ebae490cc # v1.0.248
actions/setup-python@v5         -> actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0
```

in all six files (template `secret-scan.yml`, `claude-review.yml`, both
stack `ci.yml`, kit `ci.yml`, kit `secret-scan.yml`).

- [ ] **Step 4: Add the no-paths comment** directly above `  pull_request:`
in the template `secret-scan.yml`, `stacks/node/ci.yml` and
`stacks/python/ci.yml`, at two-space indentation:

```yaml
  # Required check: never add a `paths:` filter under pull_request. A required
  # check that does not run stays "Expected" and blocks the merge forever.
  # The push trigger may be filtered.
```

Then `cp plugin/templates/project/.github/workflows/secret-scan.yml .github/workflows/secret-scan.yml`.

- [ ] **Step 5: Run the suite and lint**

Run: `pytest && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass (`test_kit_secret_scan_matches_template` included).

- [ ] **Step 6: Commit**

```bash
git add plugin/templates .github/workflows tests/test_templates.py
git commit -m "Pin workflow actions to SHAs; no-paths comment on required checks"
```

### Task 2: Dependabot config and the workflows README

**Files:**
- Create: `plugin/templates/project/.github/dependabot.yml`
- Create: `.github/dependabot.yml`
- Create: `plugin/templates/project/.github/workflows/README.md`
- Modify: `tests/test_templates.py` (`EXPECTED`, two tests)
- Modify: `tests/test_scaffold.py` (`EXPECTED`)

**Depends on:** Task 1

**Interfaces:**
- Consumes: `STACK_CIS` and `_yaml_lines` in `tests/test_templates.py`
  (Task 1 defines `STACK_CIS`).
- Produces: `plugin/templates/project/.github/workflows/README.md` and
  `plugin/templates/project/.github/dependabot.yml`, which scaffold now
  writes (Task 3 tests adopt mode against them).

- [ ] **Step 1: Write the failing tests.** In both `tests/test_templates.py`
and `tests/test_scaffold.py`, add to `EXPECTED` after
`".github/PULL_REQUEST_TEMPLATE.md",`:

```python
    ".github/dependabot.yml",
    ".github/workflows/README.md",
```

Append to `tests/test_templates.py`:

```python
DEPENDABOT = PROJECT / ".github" / "dependabot.yml"
KIT_DEPENDABOT = PLUGIN.parent / ".github" / "dependabot.yml"
WORKFLOWS_README = PROJECT / ".github" / "workflows" / "README.md"
JOB_RE = re.compile(r"^  ([\w-]+):\s*$")


def _job_ids(text):
    ids, in_jobs = [], False
    for line in _yaml_lines(text):
        if line.startswith("jobs:"):
            in_jobs = True
        elif line and not line[0].isspace():
            in_jobs = False
        elif in_jobs and (match := JOB_RE.match(line)):
            ids.append(match.group(1))
    return ids


def test_dependabot_matches_kit_and_is_monthly_grouped():
    assert KIT_DEPENDABOT.read_bytes() == DEPENDABOT.read_bytes()
    text = DEPENDABOT.read_text("utf-8")
    for needle in ("package-ecosystem: github-actions", "interval: monthly", "groups:"):
        assert needle in text, needle


def test_workflows_readme_names_every_job():
    readme = WORKFLOWS_README.read_text("utf-8")
    template_workflows = sorted((PROJECT / ".github" / "workflows").glob("*.yml"))
    jobs = set()
    for path in [*template_workflows, *STACK_CIS]:
        jobs |= set(_job_ids(path.read_text("utf-8")))
    assert jobs == {"build-test", "gitleaks", "review"}
    for job in jobs:
        assert f"`{job}`" in readme, job
    for path in template_workflows:
        assert path.name in readme, path.name
    for needle in ("paths:", "branches/main/protection", "Not included"):
        assert needle in readme, needle
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_templates.py tests/test_scaffold.py -v`
Expected: the two new tests, `test_project_template_has_exactly_the_expected_files`
and `test_new_project_has_every_file_and_one_commit` FAIL (files missing).

- [ ] **Step 3: Create `plugin/templates/project/.github/dependabot.yml`**

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

Then `cp plugin/templates/project/.github/dependabot.yml .github/dependabot.yml`.

- [ ] **Step 4: Create `plugin/templates/project/.github/workflows/README.md`**
with exactly this content:

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

(`../dependabot.yml` is plain code text, not a link, so the link checker in
`test_no_placeholders_remain_and_links_resolve` is unaffected.)

- [ ] **Step 5: Run the suite and lint**

Run: `pytest && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add plugin/templates .github/dependabot.yml tests
git commit -m "Dependabot for actions and a workflows README in the template"
```

### Task 3: Scaffold closing output

**Files:**
- Modify: `plugin/scripts/scaffold.py` (`scaffold_new` closing prints,
  `scaffold_adopt` hints)
- Test: `tests/test_scaffold.py`

**Depends on:** Task 2

**Interfaces:**
- Consumes: the template files `.github/workflows/README.md` and
  `.github/dependabot.yml` from Task 2.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_scaffold.py`)

```python
README_CHECK = "check .github/workflows/README.md: its required check names"


def test_new_project_points_at_required_checks(tmp_path):
    result = run_script(
        SCRIPT, "--name", "demo", "--stack", "python", "--parent", str(tmp_path)
    )
    assert result.returncode == 0, result.stderr
    assert "mark build-test and gitleaks as required checks" in result.stdout


def test_adopt_with_own_ci_warns_about_check_names(repo):
    ci = repo / ".github" / "workflows" / "ci.yml"
    ci.parent.mkdir(parents=True)
    ci.write_text("name: mine\n", encoding="utf-8")
    result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
    assert result.returncode == 0, result.stderr
    assert ci.read_text("utf-8") == "name: mine\n"
    assert (repo / ".github" / "dependabot.yml").exists()
    assert (repo / ".github" / "workflows" / "README.md").exists()
    assert README_CHECK in result.stdout
    out = result.stdout
    assert out.index(README_CHECK) < out.index("review with `git status`")


def test_adopt_without_ci_does_not_warn_about_check_names(repo):
    result = run_script(SCRIPT, "--adopt", "--stack", "python", "--dest", str(repo))
    assert result.returncode == 0, result.stderr
    assert README_CHECK not in result.stdout
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_scaffold.py -k "required_checks or check_names" -v`
Expected: the first two FAIL (lines not printed); the third PASSES.

- [ ] **Step 3: Implement.** In `scaffold_new`, after the existing
`then: /init …` print:

```python
    print(
        "then: mark build-test and gitleaks as required checks on main "
        "(see .github/workflows/README.md)."
    )
```

In `scaffold_adopt`, after the `.gitignore` hint block and before
`print("review with \`git status\`, then commit.")`:

```python
    workflows = Path(".github/workflows")
    if workflows / "README.md" in created and workflows / "ci.yml" in skipped:
        print(
            "check .github/workflows/README.md: its required check names "
            "must match your workflows' job IDs."
        )
```

- [ ] **Step 4: Run the suite and lint**

Run: `pytest && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/scripts/scaffold.py tests/test_scaffold.py
git commit -m "Scaffold output points at the required checks"
```

### Task 4: ADR 0028, version 0.19.0, README, live check

**Files:**
- Create: `knowledge/decisions/0028-pinned-actions-and-workflows-readme.md`
- Modify: `knowledge/decisions/README.md` (one index row)
- Modify: `plugin/.claude-plugin/plugin.json` (`version`)
- Modify: `tests/test_plugin_manifest.py` (`test_version_is_0_18_0`)
- Modify: `README.md` (setup paragraph)

**Depends on:** Task 1, Task 2, Task 3

- [ ] **Step 1: Failing test.** In `tests/test_plugin_manifest.py` replace
`test_version_is_0_18_0` with:

```python
def test_version_is_0_19_0():
    plugin_json = PLUGIN / ".claude-plugin" / "plugin.json"
    data = json.loads(plugin_json.read_text(encoding="utf-8"))
    assert data["version"] == "0.19.0"
```

Run: `pytest tests/test_plugin_manifest.py -v` → FAIL. Set `"version":
"0.19.0"` in `plugin/.claude-plugin/plugin.json`; rerun → PASS.

- [ ] **Step 2: ADR.** Create
`knowledge/decisions/0028-pinned-actions-and-workflows-readme.md`:

```markdown
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
- Adopted repos get the README and Dependabot file when missing, with a
  warning when their own `ci.yml` may not match the README's check names.
- Already-scaffolded repos are not patched.
```

Append to `knowledge/decisions/README.md` after the 0027 row:

```markdown
| [0028](0028-pinned-actions-and-workflows-readme.md) | Pinned actions, Dependabot, and a workflows README | accepted | 2026-10-10 |
```

- [ ] **Step 3: README.** In `README.md` around line 100, the install
bullet says "`/adopt-conventions <node|python>` adds the missing pieces to
an existing one." (wrapped over two lines). Insert this sentence right
before "`/handoff` writes the per-branch handoff file", keeping the bullet's
two-space continuation indent and rewrapping at about 80 columns:

```markdown
Scaffolded CI pins every action to a commit SHA, Dependabot bumps the pins
monthly, and `.github/workflows/README.md` names the checks to require.
```

- [ ] **Step 4: Suite, lint, commit**

Run: `pytest && ruff check plugin tests && ruff format --check plugin tests`
Expected: all pass.

```bash
git add knowledge README.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py
git commit -m "ADR 0028, version 0.19.0, README line for hardened CI"
```

- [ ] **Step 5: Live check (spec success criterion 3; nothing committed).**
Pick a free name (`gh repo view "$(gh api user --jq .login)/ci-hardening-check"`
must fail; else add a suffix such as `-2`). In a scratch directory outside the repo:

```bash
NAME=ci-hardening-check   # or the suffixed free name
python <repo>/plugin/scripts/scaffold.py --name "$NAME" --stack python --parent <scratch>
cd <scratch>/"$NAME"
uv init
uv add --dev pytest ruff
mkdir -p tests && printf 'def test_ok():\n    assert True\n' > tests/test_ok.py
uv run ruff format . && git add -A && git commit -m "uv project and one test"
gh repo create "$NAME" --private --source . --push
gh run list --json name,status,conclusion,url
```

Runs take a few seconds to register: re-run `gh run list` every 15 s until
both the `ci` and `secret-scan` runs appear. Then watch each run
(`gh run watch <id> --exit-status`). Expected: `ci`
(`build-test`) and `secret-scan` (`gitleaks`) green. Leave the repo for the
user to delete; report its name and run URLs only in the session. Delete
the local scratch directory.

- [ ] **Step 6: SHA check (success criterion 4).** For each SHA in Global
Constraints: `gh api repos/<o>/<r>/commits/<sha> --jq .sha` exits 0.

- [ ] **Step 7: Success criterion 2 (kit CI with the pinned actions).** Push
`feat/template-ci-hardening` and open the PR (its body never names the
live-check repo or its run URLs). Run `gh pr checks --watch`. Expected:
`ci` passes on `ubuntu-latest` and `windows-latest`, and `secret-scan`
passes. (Under `/ship`, this is its CI and PR steps.)
