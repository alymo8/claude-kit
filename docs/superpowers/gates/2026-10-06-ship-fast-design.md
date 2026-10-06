# Gate: `/ship-fast`: a light path from spec to PR for hour-sized POCs

- **Spec:** docs/superpowers/specs/2026-10-06-ship-fast-design.md
- **Spec SHA-256:** 31541427fa5b99f73ce1151f62f0a40a65b9252bcd29df499b7b26a085321a03
- **Verdict:** pass
- **Date:** 2026-10-06
- **Rounds:** 2 discovery + 0 verification

## Key decisions

- Input is a spec file; neither the spec gate nor the plan gate runs, and the spec's Status is left unchanged.
- A spec without acceptance criteria is a stop; `/ship-fast` never invents them.
- It ends at an open PR with green CI; the user merges. No `main` verification; the command never names the merge command.
- A `**Repo:** new <name> <stack>` header scaffolds a repo and creates a private GitHub repo; invoking the command approves `gh repo create --private`.
- One `code-review low --fix` pass replaces `/ship`'s review round, plus TDD on the core path and a smoke run through the `run` skill.
- Unsettled scope, behaviour, interface or data choices stop and ask; "how" choices are assumed and listed under Assumptions in the PR.
- A light task list (1–5 tasks, `parallel-plan.py` format) replaces a writing-plans plan; parallel execution through the unchanged `parallel-tasks`.
- Branch prefix `poc/`; local worktree and branch are removed while the PR is open; the remote branch stays.
- PR CI red after 2 fix attempts is a stop (`/ship` allows 3).
- For a newly created repo the baseline test run is skipped.
- The live toy run creates and then deletes a real private GitHub repo, with the user confirming the delete.

## Findings fixed

- round 1 [blocking] The baseline-red stop rule fires on every `**Repo:** new` run: step 2 skips the baseline for a repo created in step 1; the stop rule names existing repositories only.
- round 1 [minor] parallel-tasks wording misses the intro line: every mention of `/ship` in SKILL.md changes.
- round 1 [minor] Forbidden `gh pr merge` string vs. user guidance: Out no longer names the merge command.
- round 1 [minor] plugin.json description not updated: Scope adds the description mention.
- round 2 [minor] Stop rule misses the stack init command: added.
- round 2 [minor] No check for the manifest description: SC3 checks it contains `/ship-fast`.
- round 2 [minor] "as in `/ship`" overstated: dropped.

## Plan questions

- Which target does the `code-review` skill get for the branch's commits (it takes a diff, PR, branch or path, not a range), and how are non-correctness fixes from `--fix` dropped? (Steps, step 6)
- Which `--parent` does `scaffold.py` get, and what path is `<repo>` in `gh repo create --source <repo>`? (Steps, step 1)
- Are the stack init outputs (`pyproject.toml`, lockfiles) committed before `gh repo create --push`? (Steps, step 1)
- Does cleanup delete `.claude/handoffs/poc_<slug>.md` if present? (Steps, step 8)
- Does a rerun after a stop resume (existing worktree, branch, scaffold folder, task list), or is continuation only via the handoff? (Approval and stops; Steps 1–3)
- How is the branch's command loaded for SC5 (e.g. `claude --plugin-dir <worktree>/plugin`), where is the toy spec written, and does SC5 run before or after merge? (Success criteria 5)
- Is a red first `main` CI run on a freshly scaffolded repo (pytest exits 5, no tests) accepted and reported, or avoided? (Steps, step 1)

## Open

- none
