# Learning decay: prune stale learnings at ship Implementation Plan

- **Status:** approved
- **Date:** 2026-11-16

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `claude-kit:capture-learnings` prune the `CLAUDE.md`, `knowledge/` and auto-memory entries a feature made wrong (a new step 4, **Prune**), and give the `audit` / `audit-deep` checklist a staleness check for `knowledge/` docs.

**Architecture:** Markdown only, plus string-assertion tests. `plugin/skills/capture-learnings/SKILL.md` gains step 4 and new summary lines (old steps 4–6 become 5–7); `plugin/skills/audit/rules.md` section 4 gains one bullet (both audits read section 4). An ADR, a convention sentence, a README clause, a minor version bump and the spec index finish the change. A manual scenario run in a scratch repo checks the behaviour.

**Tech Stack:** Markdown, pytest, ruff, git.

**Spec:** `docs/superpowers/specs/2026-11-15-learning-decay-design.md`

Spec gate record: `docs/superpowers/gates/2026-11-15-learning-decay-design.md`

- Nothing is frozen in this change (spec D7): this plan has no `**Frozen:**` bullet.

## Context for the executor

This repo is claude-kit, a Claude Code plugin under `plugin/`. `tests/helpers.py`
exports `PLUGIN` (`REPO / "plugin"`) and `REPO`. Skill tests read the skill's text
and check substrings; `tests/test_capture_learnings_skill.py` has `flat()`, the body
with every whitespace run collapsed to one space, so wrapped phrases match.

Setup: `pip install "markdown~=3.10" "pytest>=8" "ruff~=0.16"`. Full checks:
`pytest`, `ruff check plugin tests`, `ruff format --check plugin tests`.

Gotchas (from `knowledge/kit-dev-gotchas.md`): test code must fit ruff's
88-character lines; edit test files with the Edit tool, not bash heredocs; run
plain `pytest` (not `-q`) to see the pass count; `ruff format --check` also
formats `.md` files' Python fences; `test_relative_markdown_links_resolve`
checks every tracked `.md` (plans included), so never write a bracketed name
followed by a parenthesised `.md` path unless the link resolves; a skill at
20,000 bytes or more fails `tests/test_skill_size.py` (`capture-learnings` is
about 8,000 bytes today; measure with `git show HEAD:<path> | wc -c`).

Decisions already made (spec): prune at ship, not confidence stamps (D1);
auto-memory in scope (D2); delete a memory only when nothing in it stays true,
never edit feedback or user memories (D3); ADRs never edited (D4); audits never
read memory (D5); no approval pause, `--auto` or not (D6); nothing frozen (D7).
Out of scope: `/ship`, `/ship-fast`, `/ship-many`, `plugin/references/ship-finish.md`
and the PR-body reference are not changed.

## Global Constraints

- Public repo: no machine username or private repo names in tracked files; grep the diff before committing.
- Summary line formats, verbatim: `pruned: <file>: <old entry, shortened> → <new entry | removed>`, `memory: <file>: <resolved | rewritten | deleted>: <why>`, `not written: ADR <NNNN> may be superseded: <why>`, `not written: memory <file> may conflict: <why>`.
- Prune input command, verbatim: `git diff --name-status origin/main...HEAD`.
- `knowledge/decisions/` is excluded from both Prune and the audit staleness check.
- Audit staleness date command, verbatim: `git log -1 --format=%cs -- <path>`, marked `inferred (from: git log)`.
- `capture-learnings/SKILL.md` stays under 20,000 bytes.
- ADR number: one above the highest in `knowledge/decisions/` on `origin/main` at implementation time (0047: `origin/main` already has `0046-installer-detects-os.md`, #62).
- Version: `0.32.0`. The spec says "minor version bump (0.31.0)", but `origin/main` already ships `0.31.1` (#60, #62); the next minor is `0.32.0`. If `origin/main` has moved past `0.31.x` at implementation time, take the next minor above it. A rebase conflict in `plugin.json` or `tests/test_plugin_manifest.py` resolves to this version; one in `knowledge/decisions/README.md` keeps both rows, `origin/main`'s first.

## Plan-level answers to the spec gate's plan questions

- **Zero learnings still prunes (Task 1):** step 2's sentence becomes "Zero learnings is a valid result: write nothing new; step 4 still runs, and step 7 returns `none` only when step 4 pruned nothing either." It still contains "write nothing", so `test_none_is_a_valid_result` is unchanged.
- **Where Prune edits land (Task 1):** Prune edits files in place during step 4; step 6 commits them in the same `Capture learnings` commit as the new entries (step 6's commit sentence names "step 4's prune edits").
- **Reading `origin/main` (Task 1):** yes. Prune reads each target on `origin/main` too (`git show origin/main:<path>`) and skips an entry already fixed there, because a parallel run may have pruned it and the rebase brings that fix.
- **Nested `knowledge/` docs (Tasks 1 and 2):** both Prune and the audit read `knowledge/**/*.md`, excluding `knowledge/decisions/`.
- **Files a doc "describes" (Task 2):** both the repo paths named in its body and the repo paths in its `sources:` frontmatter; the doc is flagged when its `last_updated` is older than the newest of their last-commit dates.
- **Multi-entry finding fields (Task 2):** **Where** and **Evidence** cite the first stale entry (the `last_updated` line when the date comparison is the only stale item); **Confidence** is `verified` only when every listed entry is verified, else `inferred (from: git log)`; **Impact** lists every stale entry with its line and its own confidence.
- **Section 4's applicability (Task 2):** the section-4 intro gains the sentence "The Stale learnings bullet under "Is it built well" also applies to a repo that has only a `knowledge/` folder."
- **`/ship-many` conflicts (no task):** no change; the spec puts `ship-finish.md` out of scope. Prune's `origin/main` read (above) makes a conflicting prune rare; a conflict on a rewritten or removed entry falls under `ship-finish.md`'s "other files as before" and is resolved by reading both sides. Listed under Review Focus.
- **Scenario setup (Task 4):** the run is a fresh general-purpose subagent told to follow the skill as a hand run (no `--auto`), to treat `<scratch>/memory/` as the session's auto-memory directory and never touch any other memory directory. The branch's commit subject, `Fix count() off-by-one`, and the diff tell it the bug is fixed; no spec is needed.
- **Resolved memory item (Task 1):** the item's line is rewritten in place as `done <YYYY-MM-DD> (<ref>): <item>`, where `<ref>` is `#<PR number>` when a PR exists, else the branch name (`/ship` runs the skill before opening the PR). Example: `- pending: fix the count() off-by-one` becomes `- done 2026-11-16 (feat/fix-count): fix the count() off-by-one`. The `MEMORY.md` line's hook replaces the item's "pending" wording with the same `done <date> (<ref>)` phrase.

## Review Focus

- A learning written in this same run that happens to name a path the diff renamed: it is never pruned (pinned by `test_prune_spares_this_runs_learnings` in Task 1).
- A stale-looking entry about a file the feature did not touch: left alone (pinned by `test_prune_stays_within_the_diff` in Task 1, and by Task 4's no-false-prune check).
- A feedback memory that seems to conflict with the diff: never edited, only reported as `not written: memory ...` (pinned by `test_prune_never_edits_feedback_or_user_memory` in Task 1, and by Task 4).
- Two `/ship-many` children pruning the same entry: the second skips it after reading `origin/main` (pinned by `test_prune_reads_origin_main` in Task 1); a real rebase conflict is resolved by hand under `ship-finish.md`, which this plan does not change.
- A repo with a `knowledge/` folder and no other Claude config: the audit still runs the staleness bullet (pinned by `test_rules_staleness_check` in Task 2).

---

### Task 1: Prune step in capture-learnings

**Files:**
- Modify: `plugin/skills/capture-learnings/SKILL.md` (frontmatter description, step 2, new step 4, renumbered steps 5–7)
- Test: `tests/test_capture_learnings_skill.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: step headings `4. **Prune.**`, `5. **Harden.**`, `6. **Write and commit.**`, `7. **Return**`, and the summary line formats in Global Constraints. Task 4 runs this text.

- [ ] **Step 1: Write the failing tests**

Replace `test_harden_step_sits_between_route_and_commit` and add the new tests at the end of `tests/test_capture_learnings_skill.py`:

```python
def test_harden_step_sits_between_route_and_commit():
    text = flat()
    assert (
        text.index("3. **Route**")
        < text.index("4. **Prune.**")
        < text.index("5. **Harden.**")
        < text.index("6. **Write and commit.**")
        < text.index("7. **Return**")
    )


def test_description_mentions_pruning():
    description = frontmatter(body())["description"]
    assert "prunes entries the feature made stale" in description


def test_prune_reads_the_feature_diff():
    assert "`git diff --name-status origin/main...HEAD`" in flat()


def test_prune_reads_origin_main():
    text = flat().split("4. **Prune.**", 1)[1].split("5. **Harden.**", 1)[0]
    assert "git show origin/main:<path>" in text
    assert "already fixed there" in text


def test_prune_skips_adrs():
    text = flat()
    assert "`knowledge/decisions/` excluded" in text
    assert "ADRs are never edited" in text
    assert "not written: ADR <NNNN> may be superseded: <why>" in text


def test_prune_never_edits_feedback_or_user_memory():
    text = flat()
    assert "`type: feedback` and `type: user`: never edit or delete" in text
    assert "not written: memory <file> may conflict: <why>" in text
    assert "only when nothing in it stays true" in text


def test_prune_memory_edits_are_exact_replacements():
    text = flat()
    assert "exact replacement" in text
    assert "re-reading the file right before each edit" in text


def test_prune_stays_within_the_diff():
    text = flat()
    assert "leave it alone, even if it looks stale for another reason" in text


def test_prune_spares_this_runs_learnings():
    assert "Never prune a learning routed in step 3 of this run" in flat()


def test_prune_has_no_approval_pause():
    text = flat().split("4. **Prune.**", 1)[1].split("5. **Harden.**", 1)[0]
    assert "with and without `--auto`" in text


def test_summary_reports_prune_edits():
    text = flat()
    assert "`pruned: <file>: <old entry, shortened> → <new entry | removed>`" in text
    assert "`memory: <file>: <resolved | rewritten | deleted>: <why>`" in text
    assert "no learning was written and nothing was pruned" in text
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pytest tests/test_capture_learnings_skill.py`
Expected: the 11 tests above FAIL (no `4. **Prune.**` yet); the other existing tests PASS.

- [ ] **Step 3: Edit `plugin/skills/capture-learnings/SKILL.md`**

Make these edits; keep every other sentence as it is. Quoted replace targets are whitespace-flattened: several span a line break in the file, so match them across the wrap and re-wrap the result to the file's width and 3-space indent.

1. Frontmatter `description`: replace `as one commit on the feature branch, and returns` with `as one commit on the feature branch, prunes entries the feature made stale, and returns`.
2. Step 2: replace `Zero learnings is a valid result: write nothing and return `none`.` with `Zero learnings is a valid result: write nothing new; step 4 still runs, and step 7 returns `none` only when step 4 pruned nothing either.`
3. Insert this step after step 3's fallbacks list and before Harden, with the same 3-space continuation indent as the other steps:

```markdown
4. **Prune.** Fix the entries this feature made wrong. Inputs: the
   feature's changed files, `git diff --name-status origin/main...HEAD`
   (renames and deletions included; step 2 already ran `git fetch origin`),
   plus the spec and plan when present. Edit files in place now; step 6
   commits them. Read each target on `origin/main` too
   (`git show origin/main:<path>`) and skip an entry already fixed there: a
   parallel run may have pruned it. Step 2's filter does not apply here.
   Never prune a learning routed in step 3 of this run.
   - **Repo files:** the root `CLAUDE.md`, every nested `CLAUDE.md` in a
     directory the diff touched or an ancestor of one, and every
     `knowledge/**/*.md` doc (`knowledge/decisions/` excluded) that names a
     changed, renamed or deleted path, or a command, script, flag or
     setting the diff changed. For each entry (a bullet, a table row or a
     short paragraph): if it names a path the diff deleted or renamed,
     repoint it to the new path, or remove it if the thing is gone; if it
     states a command, flag, setting or behaviour the diff changed,
     rewrite it to the new truth, or remove it if the feature made it moot
     (a gotcha the feature fixed); otherwise leave it alone, even if it
     looks stale for another reason. Edits are terse and imperative. A
     touched `knowledge/` doc gets `last_updated: <today>`.
   - **ADRs are never edited.** If the diff contradicts an accepted ADR and
     the feature added no ADR that supersedes it, add the summary line
     `not written: ADR <NNNN> may be superseded: <why>`.
   - **Auto-memory**, only when the session has an auto-memory directory:
     read its `MEMORY.md` and the memory files whose name, description or
     body names this repo, the feature's branch, spec or PR, or a skill or
     command the diff changed.
     - `type: project`: when this feature resolves an open item the memory
       records (a pending check, a next step, a deferred item), rewrite
       that item in place as `done <YYYY-MM-DD> (<ref>): <item>`, where
       `<ref>` is `#<PR number>` once a PR exists, else the branch name,
       and give its `MEMORY.md` line the same `done <date> (<ref>)`
       wording. When the feature contradicts the memory's main fact, rewrite
       the fact. Delete the file and its `MEMORY.md` line only when nothing
       in it stays true.
     - `type: feedback` and `type: user`: never edit or delete; a code
       change does not invalidate a preference. If the diff seems to
       conflict with one, add the summary line
       `not written: memory <file> may conflict: <why>`.
     - Reference memories: rewrite a pointer the diff moved; otherwise
       leave them alone.
     - Follow the session's memory instructions. Edit by exact replacement
       of the lines that change, re-reading the file right before each
       edit, never by rewriting the whole file: `/ship-many` children may
       write memory at the same time. Memory edits are not committed, so
       the summary lines are their only record.

   Prune runs the same with and without `--auto`, with no approval pause.
   A rerun finds nothing left to prune in what an earlier run fixed.
```

4. Renumber `4. **Harden.**` → `5. **Harden.**`, `5. **Write and commit.**` → `6. **Write and commit.**`, `6. **Return**` → `7. **Return**`.
5. In step 6 (Write and commit): replace `including `knowledge/review-standards.md` when step 4 wrote to it,` with `including `knowledge/review-standards.md` when step 5 wrote to it, and step 4's prune edits,`.
6. In step 7 (Return): replace `one line per `harden (...)` line from step 4` with `one line per `harden (...)` line from step 5`. The final bullet order is: written-learning lines, then `pruned:`, then `memory:`, then `not written:`, then `none`, then the `Hardening:` block. Insert these two bullets right after the written-learning bullet:

```markdown
   - one line per prune edit to a repo file:
     `pruned: <file>: <old entry, shortened> → <new entry | removed>`;
   - one line per memory edit:
     `memory: <file>: <resolved | rewritten | deleted>: <why>`;
```

   so the existing `not written:` bullet now follows them, and change its text to `one line per decision or preference listed instead of written, and per step-4 ADR or memory conflict, starting `not written:`;`. Change the `none` bullet's opening from `when nothing was written: `none`` to `when no learning was written and nothing was pruned: `none``.
7. In step 7's rerun paragraph, replace `start the summary with that commit's entries (from `git show`)` with `start the summary with that commit's entries and prune edits (from `git show`)`.
8. Grep the file for every remaining `step <n>` and confirm each points at the step it means under the new numbering (`step 2`, `step 3`, `step 4` = Prune, `step 5` = Harden, `step 6`, `step 7`).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_capture_learnings_skill.py tests/test_skill_size.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/capture-learnings/SKILL.md tests/test_capture_learnings_skill.py
git commit -m "capture-learnings: prune entries the feature made stale"
```

---

### Task 2: Audit staleness check

**Files:**
- Modify: `plugin/skills/audit/rules.md` (section 4 intro and "Is it built well")
- Test: `tests/test_audit_skills.py`

**Depends on:** none

**Interfaces:**
- Consumes: nothing.
- Produces: the `Stale learnings` bullet, read by `audit` (Pass 3) and `audit-deep` (phase C) through section 4.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_audit_skills.py`:

```python
def test_rules_staleness_check():
    rules = " ".join(read(AUDIT / "rules.md").split())
    section = rules.split("## 4.", 1)[1].split("## 5.", 1)[0]
    built_well = section.split("### Is it built well", 1)[1]
    assert "Stale learnings" in built_well
    assert "`last_updated`" in built_well
    assert "git log -1 --format=%cs -- <path>" in built_well
    assert "inferred (from: git log)" in built_well
    assert "not `knowledge/decisions/`" in built_well
    assert "only a `knowledge/` folder" in section
```

- [ ] **Step 2: Run it to verify it fails**

Run: `pytest tests/test_audit_skills.py::test_rules_staleness_check`
Expected: FAIL with `IndexError` or `AssertionError` (no `Stale learnings` yet).

- [ ] **Step 3: Edit `plugin/skills/audit/rules.md`**

1. At the end of section 4's intro paragraph (after `` `inferred`, and says so.``), add: `The Stale learnings bullet under "Is it built well" also applies to a repo that has only a `knowledge/` folder.`
2. Under `### Is it built well`, insert right after the CLAUDE.md bullet:

```markdown
- Stale learnings: in every `knowledge/**/*.md` doc (not
  `knowledge/decisions/`; `CLAUDE.md` files stay with the CLAUDE.md bullet
  above), flag paths, commands, scripts, flags and settings that do not exist
  in the tree or that the code contradicts, and a doc whose `last_updated` is
  older than the last commit to a file it describes (the repo paths it names
  and those in its `sources:`; `git log -1 --format=%cs -- <path>`), marked
  `inferred (from: git log)`. One finding per doc: **Where** and **Evidence**
  cite the first stale entry (the `last_updated` line when the date is the
  only one), **Confidence** is `verified` only when every listed entry is,
  and **Impact** lists every stale entry with its line and its own
  confidence.
```

The audits stay read-only and never read auto-memory; add nothing about memory.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_audit_skills.py`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/audit/rules.md tests/test_audit_skills.py
git commit -m "audit: flag stale knowledge/ docs"
```

---

### Task 3: ADR, docs, version and spec index

**Files:**
- Create: `knowledge/decisions/0047-prune-learnings-at-ship.md` (number per Global Constraints)
- Modify: `knowledge/decisions/README.md` (index row)
- Modify: `conventions/project-memory.md` ("Capturing learnings" section)
- Modify: `README.md` (`plugin/` bullet)
- Modify: `plugin/.claude-plugin/plugin.json` (`version`)
- Modify: `tests/test_plugin_manifest.py` (`test_version_is_0_30_0`)
- Modify: `docs/superpowers/README.md` (regenerated)

**Depends on:** none

**Interfaces:**
- Consumes: nothing (the ADR describes the behaviour Tasks 1 and 2 add, from the spec).
- Produces: nothing later tasks use.

- [ ] **Step 1: Update the version test (failing)**

In `tests/test_plugin_manifest.py`, rename `test_version_is_0_30_0` to `test_version_is_0_32_0` and change its assertion to `assert data["version"] == "0.32.0"`.

Run: `pytest tests/test_plugin_manifest.py::test_version_is_0_32_0`
Expected: FAIL with the current version string against `'0.32.0'` (`'0.31.0'` on this branch, `'0.31.1'` after a rebase onto `origin/main`).

- [ ] **Step 2: Bump `plugin/.claude-plugin/plugin.json`**

Set `"version": "0.32.0"`. Leave `description` unchanged.

Run: `pytest tests/test_plugin_manifest.py`
Expected: all PASS.

- [ ] **Step 3: Write the ADR**

Run `git fetch origin` and `git ls-tree --name-only origin/main knowledge/decisions/` to confirm the highest number (0046 on origin/main today → use 0047; if a newer one exists, take the next free number and use it in every path, title, index row and commit below). Create `knowledge/decisions/0047-prune-learnings-at-ship.md` in the format of `knowledge/decisions/0000-template.md`: title `# ADR 0047: Prune learnings at ship`, `- **Status:** accepted`, `- **Date:** <today>`, then:

- **Context:** capture-learnings only adds; entries in `CLAUDE.md`, `knowledge/` and auto-memory go stale (moved paths, changed commands, fixed gotchas, done "pending" items) and sessions trust them. The idea came from an external setup's confidence-scored instincts (ideas only).
- **Decision:** the five decisions, one short paragraph or bullet each: D1 prune at ship inside capture-learnings, limited to what the feature's diff changed, instead of per-entry confidence or "last confirmed" stamps (stamps cost tokens every session and decay useful notes); a sweep-only approach was rejected because it runs only when someone audits; the audits add a `knowledge/` staleness check for between ships. D2 a ship step may edit the user's auto-memory, because project memories collect the most stale pending items. D3 a memory is deleted only when nothing in it stays true, feedback and user memories are never edited or deleted, and every memory edit is reported. D4 ADRs are never edited; a contradiction is reported as `not written: ADR <NNNN> may be superseded`. D5 the audits never read auto-memory, because their reports are repo files and memory contents must not land in a repo.
- **Consequences:** Prune edits are learnings, not hardening, so ADR 0043's rule that automated runs never change code or process files on their own still holds; no approval pause (the PR diff reviews repo edits, the summary reviews memory edits); memory edits are uncommitted and cannot be undone, which is why deletion is narrow; post-merge, the next three `/ship` runs' `pruned:` and `memory:` lines are checked by hand, and one wrong removal means revisiting D3 or narrowing Prune.

Write it in prose; do not link to the spec with a bracketed-name-plus-path link unless the path resolves from `knowledge/decisions/`.

- [ ] **Step 4: Add the index row**

Append to the table in `knowledge/decisions/README.md`:

```markdown
| [0047](0047-prune-learnings-at-ship.md) | Prune learnings at ship | accepted | <today> |
```

- [ ] **Step 5: Update `conventions/project-memory.md`**

In `## Capturing learnings`, after the sentence ending `never a tracked file.`, insert: `The same run prunes what the feature made stale: entries in this file, in `knowledge/` and in project memories that name a path it moved or deleted, or a command, setting or behaviour it changed. ADRs are never edited.`

- [ ] **Step 6: Update `README.md`**

In the `plugin/` bullet, inside the parenthesis that follows the skill list, replace `and compares them by domain)` with `and compares them by domain; `capture-learnings` also prunes the `CLAUDE.md`, `knowledge/` and project-memory entries a feature made stale)`.

- [ ] **Step 7: Regenerate the spec index**

Run: `python plugin/scripts/spec-index.py docs/superpowers`
Expected: `docs/superpowers/README.md` has rows for `2026-11-15-learning-decay-design.md` and `2026-11-16-learning-decay.md`.

- [ ] **Step 8: Run the full checks**

Run: `pytest`, then `ruff check plugin tests`, then `ruff format --check plugin tests`
Expected: all tests PASS (none failing), ruff reports no errors and no files to reformat.

- [ ] **Step 9: Commit**

```bash
git add knowledge/decisions/0047-prune-learnings-at-ship.md knowledge/decisions/README.md conventions/project-memory.md README.md plugin/.claude-plugin/plugin.json tests/test_plugin_manifest.py docs/superpowers/README.md
git commit -m "ADR 0047, docs and 0.32.0 for learning decay"
```

---

### Task 4: Scenario check (success criteria 2 and 3)

**Files:** none in the repo (no commit). Scratch files go in a folder outside the repo (the session's scratchpad, else the system temp directory), referred to below as `<scratch>`; delete it when done.

**Depends on:** Task 1

**Interfaces:**
- Consumes: the Prune step text from Task 1 (`plugin/skills/capture-learnings/SKILL.md` in this worktree, `<worktree>` below).
- Produces: a scenario result block for the PR body.

- [ ] **Step 1: Build the scratch repo and memory**

1. `git init --bare --initial-branch=main <scratch>/origin.git`, then `git clone <scratch>/origin.git <scratch>/scratch-repo`, then `git -C <scratch>/scratch-repo switch -c main` (the machine's `init.defaultBranch` may be `master`).
2. In `<scratch>/scratch-repo` on `main`, commit (with `-c user.name=t -c user.email=t@example.com` if no identity is set):
   - `scripts/old.sh`: `echo build`.
   - `src/count.py`: `def count(items):\n    return len(items) - 1\n`.
   - `docs/notes.txt`: `notes`.
   - `CLAUDE.md`:

     ```markdown
     # Scratch repo

     ## Build, run, test
     - Build with `scripts/old.sh`.

     ## Conventions
     - Keep `docs/notes.txt` in plain ASCII.

     ## Gotchas
     - `count()` in `src/count.py` returns one less than the item count; add 1 at call sites.
     ```

   Push with `git -C <scratch>/scratch-repo push -u origin main`, so `origin/main` exists.
3. `git switch -c feat/fix-count`; `git mv scripts/old.sh scripts/new.sh`; change `src/count.py` to `return len(items)`; commit with subject `Fix count() off-by-one`.
4. Create `<scratch>/memory/`:
   - `project_scratch_repo.md`: frontmatter `name: scratch-repo state`, `description: scratch-repo open items`, `type: project`; body lines `- pending: fix the count() off-by-one` and `- first live run pending`.
   - `feedback_tabs.md`: frontmatter `name: tabs in shell scripts`, `description: indent shell scripts with tabs`, `type: feedback`; body `Indent shell scripts with tabs.`
   - `MEMORY.md`, these two lines:

```markdown
- [scratch-repo state](project_scratch_repo.md) — pending: fix the count() off-by-one; first live run pending
- [Tabs in shell scripts](feedback_tabs.md) — indent shell scripts with tabs
```

5. Record `sha256sum <scratch>/memory/feedback_tabs.md`.

- [ ] **Step 2: Run the skill in hand mode**

Dispatch a fresh general-purpose subagent with this prompt (paths filled in):

"Work in the git repo `<scratch>/scratch-repo`, on branch `feat/fix-count`. Read `<worktree>/plugin/skills/capture-learnings/SKILL.md` and follow it as a hand run (no `--auto`). Treat `<scratch>/memory/` as the session's auto-memory directory; never read or write any other memory directory. This session has no learnings beyond the branch's commits and diff. Decline the offer to build mechanical proposals. Return the Learnings summary verbatim."

- [ ] **Step 3: Verify against the criteria**

Run: `git -C <scratch>/scratch-repo diff main HEAD -- CLAUDE.md`
Expected: the `scripts/old.sh` entry and the `count()` gotcha are gone, a `+` line names `scripts/new.sh`, and no `-` or `+` line touches `docs/notes.txt` or `# Scratch repo`. Removing the now-empty `## Gotchas` heading is allowed.

All must hold:
- `git -C <scratch>/scratch-repo show HEAD:CLAUDE.md`: names `scripts/new.sh`, not `scripts/old.sh`; the `count()` gotcha is gone; the line ``- Keep `docs/notes.txt` in plain ASCII.`` is byte-identical to `main`'s (`git diff main HEAD -- CLAUDE.md` shows no change on it). (criterion 3)
- `project_scratch_repo.md` reads `- done <today> (feat/fix-count): fix the count() off-by-one` and still has `- first live run pending` unchanged; its `MEMORY.md` line reads:

```markdown
- [scratch-repo state](project_scratch_repo.md) — done <today> (feat/fix-count): fix the count() off-by-one; first live run pending
```

- `sha256sum` of `feedback_tabs.md` equals the value from Step 1.
- The summary has a `pruned:` line for the path repoint and one for the gotcha removal, and a `memory:` line marking the item `resolved`.

If any check fails, fix the Task 1 text and rerun Steps 1–3 in a fresh `<scratch>`.

- [ ] **Step 4: Record the result**

Return verbatim in the task report (the PR body carries them under a `Scenario check` heading): the subagent's summary, the `git diff main HEAD -- CLAUDE.md` output, the final `project_scratch_repo.md` and `MEMORY.md`, and the two `sha256sum` values. Then delete `<scratch>`. No commit.

- [ ] **Step 5: Record the post-merge check (success criterion 4)**

If the session has an auto-memory directory, write a `type: project` memory file `learning-decay-feature.md` (name `Learning decay feature`, description `capture-learnings Prune step; post-merge check pending`) whose body says: "Prune step in capture-learnings and audit staleness check (ADR 0047, v0.32.0). Pending: check every `pruned:` and `memory:` line in the next three real `/ship` runs by hand; one wrong removal means revisiting D3 or narrowing Prune." If there is no auto-memory directory, put that pending check in the final report instead. Add this line to its `MEMORY.md`, re-reading `MEMORY.md` right before the edit:

```markdown
- [Learning decay feature](learning-decay-feature.md) — Prune step v0.32.0; post-merge check over next 3 /ship runs pending
```

Run: `grep -n "learning-decay-feature.md" <memory dir>/MEMORY.md`
Expected: one matching line, and `<memory dir>/learning-decay-feature.md` exists (or, with no memory directory, the pending check is in the final report).
