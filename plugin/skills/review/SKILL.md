---
name: review
description: Use when /ship reaches step 6, or when the user asks for a review of a branch or diff against its spec and the repo's rules. Runs a standards reviewer and a spec reviewer as two parallel fresh-context subagents and reports them side by side.
argument-hint: [base-ref] [spec.md] [plan.md]
---

# Review

Two reviewers, two axes, one report: does the diff follow the repo's rules
(standards), and does it do what the spec asked (spec). Each runs as a new
general-purpose subagent with no conversation context, so neither inherits
your view of the work.

## Steps

1. **Pin the diff.** Base = the first argument, else `origin/main`.
   `git rev-parse <base>` must resolve and `git diff <base>...HEAD` must be
   non-empty; otherwise report that and stop. Record
   `git log <base>..HEAD --oneline`.
2. **Find the spec.** Use the arguments. Else a plan under
   `docs/superpowers/plans/` changed on the branch whose `**Spec:**` line
   names a spec. Else the newest (by file name) spec in
   `git diff --name-only <base>...HEAD -- docs/superpowers/specs/`. If none,
   skip the spec reviewer and report `Spec: no spec found`.
3. **Find the standards.** The root `CLAUDE.md`, `knowledge/review-standards.md`,
   `CONTRIBUTING.md`, any `CODING_STANDARDS.md`, and the engineering-practices
   playbook (the repo's `conventions/engineering-practices.md`, else the path
   from the kit map). Only files that exist.
4. **Frozen check.** Run
   `python <this skill's directory>/../../scripts/frozen-check.py <spec> [<plan>] --base <base>`
   (fallback: `~/.claude/skills/claude-kit/scripts/frozen-check.py`) and keep
   its whole output for the standards reviewer. With no spec and no plan, skip
   it and use `Frozen: skipped (no spec or plan)`. On exit 2, put the stderr in
   the output line given to the reviewer; it is not a finding.
5. **Dispatch both reviewers in one message**, as new general-purpose
   subagents, no `model` override, no conversation context. Each prompt is its
   file's content (`standards-reviewer.md`, `spec-reviewer.md`, in this
   skill's directory) with the placeholders filled: `<repo root>`,
   `<diff command>` (`git diff <base>...HEAD`), `<commit list>`; for the
   standards reviewer also `<standards files>` and `<frozen-check output>`; for
   the spec reviewer also `<spec path>` and `<plan path or none>`. Tell both
   that process files are never scope creep: the spec, the plan, gate
   records, ADRs, `docs/superpowers/README.md`, and files changed by the
   branch's `Capture learnings` commit.
6. **Report.** `## Standards` then `## Spec`, each the reviewer's findings
   lightly cleaned, never merged or reranked across axes; then the frozen
   line; then one line:
   `Findings: standards <n> (worst: <finding>), spec <n> (worst: <finding>)`.
