# Plan gate: Vibe native plugin Implementation Plan

- **Plan:** docs/superpowers/plans/2026-11-23-vibe-plugin.md
- **Plan SHA-256:** f459b3a468355af165d532ea06c475654760d9b00a5a366adb49bca27dd158e4
- **Spec:** docs/superpowers/specs/2026-11-23-vibe-plugin-design.md
- **Spec SHA-256:** 646de5dc3959d05721d0fdad2ca7e0a7a4989b00f4c6c8372b4f9479bb9e9b56
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-11-23
- **Approved by:** /ship (auto)
- **Date:** 2026-11-23
- **Rounds:** 2 discovery + 0 verification

## Plan-introduced decisions

- `tests/test_vibe_plugin.py` is frozen with a plan-level `- **Frozen:**` bullet, because the plan writes its full content and success criterion 1 depends on it (the spec's D6 froze nothing at spec level).
- The two Vibe hooks set no `timeout` key, like today's user block; the live run checks that a session start completes (Task 1).
- An unreadable or malformed `~/.codex/hooks.json` or `~/.cursor/hooks.json` counts as in use: the old skill links are kept and the warning printed. A missing file counts as not in use (Task 2).
- A link named like a kit skill that points outside the current checkout is kept and reported with a `Kept <name>: ...` line, not removed (Task 2).
- The standalone `vibe_plugin.py --out DIR` also refuses an unmarked target folder (the check lives in `build`); its default `--python` is `python` (Task 1).
- When any swap fails, every plugin already swapped (and the one whose swap failed) goes back to its previous copy, so no mixed state is left (Task 1).
- The copied Claude `hooks/hooks.json` (which the copy's `run.py` reads) and `commands/` stay in the Vibe copy, assuming Vibe ignores them; the live run checks this and the executor stops if it does not (Task 1, Task 4).

## Findings fixed

- round 1 [blocking] Suggested setup.md wording broke the case-sensitive "rerun the installer after updating" test: the example rewording now keeps the phrase lowercase.
- round 1 [minor] Swap rollback wording missed the plugin whose rename failed: answer 5 now restores it too.
- round 1 [minor] Task 2 interfaces: dropped `runner_command` from Consumes; added `agents_block(..., runner)` to Produces.
- round 1 [minor] Live check grepped only the current marker: now greps `(agent|claude)-kit hooks`.
- round 2 [minor] Task 2 Step 3 expected every new test to fail: notes that `test_vibe_removes_dangling_kit_link` already passes.
- round 2 [minor] setup.md Vibe sentences left stale: Next-steps line split; `--skills-dir` and relinking clarified for Vibe.

## Open

- none
