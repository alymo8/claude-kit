# Gate: Gates converge: a verification round and a narrower blocking bar

- **Spec:** docs/superpowers/specs/2026-10-02-gate-verification-round-design.md
- **Spec SHA-256:** a4ecf894fe03481ad8b39bbea98b353894582e1dfb540a98bcb9ceced130fb44
- **Verdict:** pass
- **Date:** 2026-10-02
- **Rounds:** 3 discovery + 1 verification (verification run by hand from the new design, at the user's request)

## Key decisions

- Spec gate gets both changes (six blocking classes plus `[plan]`, and
  verification rounds); the plan gate gets verification rounds and a
  Plan-questions check only (Decisions; Scope Out)
- `blocking` is limited to six classes: wrong-build, contradiction,
  false-claim, uncheckable, open-what, too-large; "how" questions become
  `[plan]` findings that never affect the verdict (Design, Spec rubric)
- Plan questions live in the spec's gate record, not the spec; `/ship`
  step 3 and plan-gate check 7 carry them forward (Decisions)
- At most 3 discovery + 2 verification rounds, 5 in total per gate;
  verification is scoped to the diff of the last fixes (Decisions)
- One shared `verify.md` in `spec-gate/` (Decisions)
- No verification when decision findings exist; the gate fails and reruns
  from step 1 (Decisions)
- Step numbering 1–7 is kept in both gates, so `/ship` and `/ship-many`
  references do not change (Design)
- Plan-introduced decisions = last discovery round's list plus each
  verification round's `## Decisions changed`, so `pass-with-decisions`
  still fires (Design, Plan gate)
- `spec-lint.py` unchanged; existing records not rewritten; ADR 0020
  supersedes the "up to three rounds" sentences of ADRs 0015/0016 without
  editing them (Scope Out; Docs)
- Plugin 0.12.0 (Scope In)

## Findings fixed

- round 1 [blocking] false count of gate records: "five spec gate records"
- round 1 [blocking] step renumbering: both gates keep steps 1–7 with the
  same names; verification lives inside step 4 "Repeat, then verify"
- round 1 [blocking] plan decisions lost when the last round is a
  verification: `verify.md` gains `## Decisions changed`, merged into the
  decisions for verdict and record in both gates
- round 1 [minor] frontmatter descriptions specified; ADR 0020 supersedes
  0015/0016 round sentences; verification decision findings fail the gate;
  verification snapshot names
- round 2 [blocking] scope-size findings had no class: sixth class
  `too-large`; ambiguity maps to `open-what` or `plan`
- round 2 [minor] plan-gate verdict/record wording replaced explicitly;
  one fenced verify output block; `git diff --no-index` exit 1 expected;
  criterion 7 runs steps 1–6 and need not reach verification; criterion 6
  reruns once on failure
- round 3 [blocking] criteria 6 and 7 would have run the old installed gate:
  both now name the worktree's `rubric.md`/`verify.md`/`SKILL.md` and follow
  the steps by hand
- round 3 [minor] full plan-gate verification prompt; fixes/diff file names;
  report wording "D discovery + V verification rounds"; criterion 6 failure
  is a `/ship` stop with handoff; spec-lint claim includes Decisions-approved
 

## Open

- none (verification round 1: all five round-3 fixes resolved, no new
  findings, no decisions changed)
