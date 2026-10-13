# Gate: Team setup: a teammate on any OS works the way the kit's owner does

- **Spec:** docs/superpowers/specs/2026-10-13-team-setup-design.md
- **Spec SHA-256:** c5c8e52859b7b259455bc84617dcc651f98f7687d3bd64f4f2417c0458fc8caf
- **Verdict:** pass
- **Date:** 2026-10-13
- **Rounds:** 1 discovery + 0 verification (re-gate after a wording fix; the previous run took 2 discovery rounds)

## Key decisions

- One spec, one PR, one release (0.24.0) for all four gaps; the owner chose this by running `/ship` on the whole spec after the first gate run asked.
- The teammate both uses and contributes to the kit, so contributor rules are in scope.
- One cross-platform Python installer: junction on Windows, symlink elsewhere; `install.ps1` becomes a wrapper; amends ADR 0005 (ADR 0033). No marketplace.
- `python` 3.11+ is a hard installer check: exit 1 with nothing changed on disk. `hooks.json` keeps `python`, with no `python3` fallback.
- Superpowers is checked and the install command is printed; it is never installed automatically. Missing `git` or `gh` only warns.
- A SessionStart hook injects the workspace `CLAUDE.md` minus "Developing the kit", only outside the kit root and outside kit worktrees. It is on by default, `CLAUDE_KIT_WORKSPACE_RULES=0` turns it off, and it costs about 2k to 2.5k tokens per session in those repos (ADR 0034).
- Three rules move from the owner's memory into `CLAUDE.md`. The public-repo and fold-into-flow rules go under "Developing the kit". The owner's three memory files are deleted after merge (ADR 0035).
- `/ship` keeps its autonomous squash-merge with no PR approval, and `docs/setup.md` says so plainly.
- No macOS CI job and no syncing of personal settings.

## Findings fixed

- round 1 [blocking] The setup guide's clone step collided with the public-repo grep: the guide may use the repo's public URL, and criterion 2 strips the repo's own `owner/name` slug (read from `gh repo view`) before grepping.
- round 1 [blocking] The hook double-loaded the rules in kit worktrees outside the kit root: it is now silent when `git rev-parse --git-common-dir` resolves to `<root>/.git`; paths are compared with `normcase`; a temp-kit worktree test was added.
- round 1 [minor] "matches today's install.ps1": the claim now notes that the error says "link" instead of "junction".
- round 2 [minor] README execution-policy note: the README scope item says it moves to `docs/setup.md`.
- (first gate run, same day) The ERROR text names the `--python` value; private repo names come from `gh repo list --visibility private`; ADR 0035 was added for the moved rules; an existing install continues to the status line and superpowers steps; the hook header names `<root>`; the token estimate was corrected.

- re-gate [blocking, found by the plan gate] A private repo name in Scope Out: reworded as "personal memories about other projects"; the unpushed spec commit was rewritten.
- re-gate round 1 [minor] ADR 0005 index title: Scope In says the title is unchanged.

## Plan questions

- Where does the manual live check run? From the main checkout after merge, not from the feature worktree. (Success criteria)
- Does the switch table read each default from its source file (for example `context_nudge.py`)? (Setup guide)

- Does the `CLAUDE_KIT_*` docs scan read only git-tracked text files, skipping stale `__pycache__` bytecode? (Testing)
- What syntax floor does `install.py` keep (no 3.10+ syntax at module level), so that an older `python3` still reaches the version error? (Installer)
- On Windows, how does the installer detect and read a junction on Python 3.11 (`os.readlink`, with no `is_junction`), and how are paths normalised for comparison? (Installer)
- How does the dangling-link test create its link portably (`mklink /J` on Windows, a symlink elsewhere)? (Testing)
- Are the git and gh warnings tested with a stripped PATH? (Testing)
- Does `/ship`'s clean-up do the after-merge memory clean-up, or does the owner do it by hand? (Rules moved from memory)

## Open

- none
