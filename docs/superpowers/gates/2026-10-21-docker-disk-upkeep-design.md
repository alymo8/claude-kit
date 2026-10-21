# Gate: Docker Desktop disk upkeep on Windows

- **Spec:** docs/superpowers/specs/2026-10-21-docker-disk-upkeep-design.md
- **Spec SHA-256:** 7c208255ba21e9d2d2c4beaeaf6f1f3d943806e2dfa245cf029738e075bb96c7
- **Verdict:** pass
- **Date:** 2026-10-21
- **Rounds:** 3 discovery + 1 verification

## Key decisions

- Compaction stays out of the per-feature clean-up; `/ship` and `/ship-fast` add only a report-only status line (never a stop rule), and compaction is a separate on-demand `/docker-compact` command (Purpose, D5, ADR 0038)
- `/docker-compact` is user-only (`disable-model-invocation: true`), asks before stopping Docker, needs one UAC prompt, offers `--set-sparse` as a separate yes/no, never prunes or removes objects, and uses a fixed `%TEMP%\dcompact` folder it deletes afterwards (Design)
- Compact threshold: file > 1.5 × used and file − used > 2 GiB (D1)
- Used is measured inside the disk (`df` in `docker-desktop`), not `docker system df` (D4)
- The status script is read-only and never starts the `docker-desktop` distro; used is `?` when it is down (D7)
- The sparse bit comes from file attributes, not `fsutil` (D6)
- The kit never changes Docker Desktop or WSL settings automatically; the sparse flag and the build-cache cap are setup notes (Scope Out)
- Windows only, the two default disk paths; macOS, Linux and moved disks print a skipped line (Scope Out)
- `/ship-fast` runs the status script only when the task used Docker (Design)
- No live compaction in this change (D2); ADR 0038; minor bump to 0.27.0; delivery via spec gate then `/ship` (D3)

## Findings fixed

- round 1 [blocking] ship-fast prune sentence is lower case: Testing now checks each file's actual text.
- round 1 [blocking] `/docker-compact` behaviour when compaction is not suggested: it says so and continues to the ask; the user decides.
- round 1 [minor] MAX_PATH rationale: reworded to the observed failure plus diskpart quoting.
- round 1 [minor] CLAUDE.md "on Windows" wording: the script reports only on Windows.
- round 1 [minor] criterion 6 placeholder: the pattern is now built from `$env:USERNAME` and `gh repo list --visibility private`.
- round 2 [blocking] threshold tests contradicted D1 at exactly 1.5×: the "suggested" case is now over 1.5×.
- round 2 [minor] criterion 3 preconditions: Docker Desktop running; the Docker reading is summed in decimal units and converted to GiB.
- round 2 [minor] units of the Docker figure: 1.7 GB decimal, about 1.6 GiB.
- round 2 [plan-adjacent] unknown values print as `<label> ?` with no unit.
- round 3 [blocking] `/docker-compact` user-only: `disable-model-invocation: true`, added to the user_only test set.
- round 3 [minor] allow-list test added to Testing.
- round 3 [minor] `/ship-fast` call only when the task used Docker.

## Plan questions

- Where does `/docker-compact` get the disk path: does it resolve the two default paths itself, or does the script expose the path it chose (for example a flag)? (Design: docker-compact step 6)
- Should `/docker-compact` stop after step 1 when the script reports no disk found? (Design: docker-compact step 1)
- Which tool and encoding write `compact.txt` (ASCII, no BOM, so diskpart parses line 1)? (Design: docker-compact step 6)
- How does the command tell diskpart success, failure and a declined UAC prompt apart (`-PassThru` plus `ExitCode`, or size before/after)? (Design: docker-compact steps 7–9)
- How is `docker system df` parsed: a regex per row or `--format`, which size tokens are accepted, and are unknown units "does not parse"? Keep it consistent with criterion 4's allow-list. (Design: script step 6)
- If Docker Desktop is not running when `/ship` reaches criterion 3's dry run, record it as not run in the PR or stop? (Success criteria 3)
- The CLAUDE.md sentence must keep the injected workspace rules under `test_size_cap` (9,500 characters; about 9,076 today). (Design: CLAUDE.md)

## Open

- none
