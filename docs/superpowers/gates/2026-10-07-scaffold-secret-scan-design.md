# Gate: Scaffold secret scan: gitleaks CLI instead of gitleaks-action

- **Spec:** docs/superpowers/specs/2026-10-07-scaffold-secret-scan-design.md
- **Spec SHA-256:** cf9d30feaaa761bd9c62f8ea280cae00a0c61f892c6ad4920cff99e1d419454b
- **Verdict:** pass
- **Date:** 2026-10-07
- **Rounds:** 2 discovery + 0 verification

## Key decisions

- Replace `gitleaks/gitleaks-action@v2` with the gitleaks CLI in both the scaffold template and the kit's own workflow; PR comments, the job summary and the license requirement go away.
- Pin gitleaks 8.30.1 with a hardcoded SHA-256; upgrades are manual (Dependabot cannot bump it).
- Scan the full history of the checked-out ref only (`--log-opts="HEAD"`) on every run, PRs included; a committed secret keeps that branch red until removed or allowlisted, and a leak on one branch does not turn `main` red.
- The workflow token gets only `contents: read`.
- The kit's own `secret-scan.yml` stays byte-identical to the template, enforced by a test.
- Existing scaffolded repos are not patched; `docs/audit/setup-audit.md` is left as written.
- The live check creates a throwaway private GitHub repo, pushes a fake secret to a branch, and leaves the repo for the user to delete; its name and run URLs are reported in the session only.

## Findings fixed

- round 1 [blocking] Scan covers all fetched refs: added `--log-opts="HEAD"`, rewrote the Behaviour bullet, added a Decision and the test string.
- round 1 [blocking] False parity claim with the old action: Behaviour now states the change; Decisions accepts it.
- round 1 [blocking] Private repo names in a public repo: removed private repo names and run IDs; criterion 5 reports name and URLs in the session only.
- round 1 [minor] Throwaway repo name unspecified: criterion 3 names `secret-scan-check`, checked with `gh repo view` first; criterion 4 runs after criterion 3.
- round 2 [minor] Kit copy already identical: Scope and Kit copy reworded to "updated to stay identical".

## Plan questions

- Should the permissions test match a column-0 `permissions:` line followed by an indented `contents: read`, or parse the YAML (PyYAML is not a dev dependency)? (Testing)
- When does the live check run (worktree's scaffold before merge, or `main` after), with which entry point and stack, in which local path, and is the local checkout deleted afterwards? Should `gh api .../actions/permissions/workflow` record `default_workflow_permissions: read` as evidence? (Success criteria 3)
- Should gitleaks 8.30.1 run locally over the kit history before pushing, to catch false positives on the first full-history scan? (Success criteria 2)
- Is a push run enough for the negative check, or must a PR be opened too? (Success criteria 4)
- Does this change bump the plugin version (e.g. 0.13.1)? (Scope)

## Open

- none
