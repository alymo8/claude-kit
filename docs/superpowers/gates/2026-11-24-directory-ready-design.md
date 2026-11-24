# Gate: Directory-ready plugin, a sibling default for `/new-project`, and a `git mv` plan check

- **Spec:** docs/superpowers/specs/2026-11-24-directory-ready-design.md
- **Spec SHA-256:** 2f6126dd4fd1bd3e4c3f1b1ffa876d9e443306732d516c67da9cc71892f4f9c8
- **Verdict:** pass
- **Date:** 2026-11-24
- **Rounds:** 2 discovery + 0 verification

## Key decisions

- The repo is made checklist-clean and the portal steps are written down; the owner submits, fills in the contact email and gives the acknowledgements (D1)
- Inside a foreign git repo, `/new-project` defaults to the folder that holds that repo's main checkout; a repo at a filesystem root exits 2 and asks for `--parent` (D2)
- One spec and one PR for three independent parts, the split considered and rejected (D3)
- Version 1.2.0; whichever of this and the hook-quoting PR merges second rebases the exact-version test (D4)
- The directory checklist is a pytest file in CI, scoped to `git ls-files plugin` (D5)
- ADR 0055 records the directory route and the sibling default; ADR 0052 is marked extended (D6)
- The Stop hook drops its `${CLAUDE_PROJECT_DIR}` argument and `spec-index.py` reads the variable itself; every hook command must fit a strict regex, and a misfit stops the build (D8)
- `plugin.json`'s description is unchanged; the README's directory install line waits until the listing is live (Scope Out)
- Nothing is frozen (D7)

## Findings fixed

- round 1 [blocking] Rule ID P10 already used: the new check is `P11-git-mv-add` throughout.
- round 1 [blocking] Stop hook breaks the directory's hook rule: the Stop hook drops its second variable, `spec-index.py` reads `CLAUDE_PROJECT_DIR`, and the regex no longer widens to fit (Design 9, D8, Scope, tests).
- round 1 [blocking] Trailing-slash case contradicted Design: the criterion now expects a flag.
- round 1 [blocking] Three subsystems in one spec: D3 records that the split was considered and rejected by the user.
- round 1 [minor] Source of the install.py note: points at the contributor note in `docs/setup.md`.
- round 1 [minor] ADR 0052 status: marked extended by 0055.
- round 1 (plan questions settled as clear) `git add` before `git mv` is not checked; `git mv -f a b` has source `a`.
- round 2 [minor] Plugin-cache claim: limited to rules 1 to 3.
- round 2 [minor] Criterion 3 judgement: a flagged plan needs a hand-checked line as evidence.
- round 2 [minor] 0052 status format: both the index row and the ADR file's Status line, with the wording given.
- round 2 [minor] Decision order and placement: D8 after D7; the Stop hook is its own Design item 9.

## Plan questions

- Does `default_parent` raise `SystemExit(2)` for the root-repo case, or return a sentinel `main` turns into exit 2? (Design 5)
- Is `main_checkout`'s fallback (non-`.git` common dir returns the path itself) accepted under rule 3? (Design 5)
- Does rule 3 pass the `--show-toplevel` result to `main_checkout`, and is a subfolder case tested? (Design 5)
- Are submodule and home-folder repos accepted as they are under rule 3, or guarded? (Design 5)
- What should `tests/test_plugin_manifest.py::test_stop_hook_regenerates_spec_index` assert once the argument is gone? (Design 9)
- Which forms does P11 match: bare `git mv`/`git add` only, spans in any prose, `git -C x add`, `git add <src>/file`? (Design 6)

## Open

- none
