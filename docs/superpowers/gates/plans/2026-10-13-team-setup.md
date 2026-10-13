# Plan gate: Team setup Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-13-team-setup.md
- **Plan SHA-256:** c67f6d7957edb93c1900f7f64f6982cb1a0997030c7ab0a3b63338a268ae1f42
- **Spec:** docs/superpowers/specs/2026-10-13-team-setup-design.md
- **Spec SHA-256:** c5c8e52859b7b259455bc84617dcc651f98f7687d3bd64f4f2417c0458fc8caf
- **Verdict:** pass-with-decisions
- **Date:** 2026-10-13
- **Rounds:** 4 discovery + 0 verification (3 rounds, then 1 more after the spec was re-gated)
- **Decisions approved:** 2026-10-13

## Plan-introduced decisions

- The `/ship` session does the after-merge work outside the repo, at the end of its step 11. It deletes the owner's three auto-memory files (`no-suggest-repo-deletion.md`, `claude-kit-public-no-private-names.md`, `fold-into-existing-flow-steps.md`), removes their `MEMORY.md` lines and updates `kit-map-and-team-setup.md`, with no hand-off to the owner. The spec does not say who does it.
- Success criterion 3 is split in two. The `/ship` session re-runs `install.py` and runs the hook script directly from the main checkout. The session-level part (after `/reload-plugins`, rules present outside the kit and absent inside it) is reported as pending for the owner. If local `main` was not fast-forwarded, the whole live check is pending.

## Findings fixed

- round 1 [blocking] The after-merge live check assumed local `main` was fast-forwarded: added the rule to skip and report pending when it was not.
- round 1 [minor] Nested code fence in the `docs/setup.md` block: the outer fence is now four backticks.
- round 1 [minor] Env-switch scan narrower than the spec: now reads every tracked file under `plugin/` and skips undecodable ones.
- round 2 [blocking] `install.py` failed ruff UP031: the percent format became an f-string.
- round 2 [blocking] The session-level part of criterion 3 was neither done nor handed off: the plan reports it as pending, with the owner's steps.
- round 2 [minor] The after-merge work sat outside the `/ship` steps: tied to the end of step 11, before the step 12 report.
- round 2 [minor] The live-check command was bash only: a PowerShell form was added.
- round 2 [minor] `ruff format` also rewraps `install.py`: Task 1 Step 6 runs it first.
- round 3 [blocking] Task 6 would hit a private repo name in the spec: the spec line was reworded (the unpushed commit rewritten) and the spec re-gated.
- round 3 [minor] "amend ... with a new commit": now "commit the fix as a new commit".
- round 4 [minor] The status-line test did not check the key: it now parses JSON and asserts `statusLine`.
- round 4 (decision removed) The setup guide carried ADR 0006's one-line-fix exemption over to the teammate: the guide now says changes go through a branch and a PR.

## Open

- none
