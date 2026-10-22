# Plan gate: Docker Desktop disk upkeep on Windows Implementation Plan

- **Plan:** docs/superpowers/plans/2026-10-21-docker-disk-upkeep.md
- **Plan SHA-256:** 649e707a027ede723102b87434931b506aaa3841b4ded1c6fb7cf8965e4b046b
- **Spec:** docs/superpowers/specs/2026-10-21-docker-disk-upkeep-design.md
- **Spec SHA-256:** 7c208255ba21e9d2d2c4beaeaf6f1f3d943806e2dfa245cf029738e075bb96c7
- **Verdict:** pass-with-decisions
- **Decisions approved:** 2026-10-21
- **Approved by:** /ship (auto)
- **Date:** 2026-10-21
- **Rounds:** 3 discovery + 0 verification

## Plan-introduced decisions

- `docker-disk.py` gets a `--path` flag that prints only the chosen disk path (or nothing) and exits 0; `/docker-compact` reads the disk path from it, so the two default paths live only in the script (Task 1, Task 2).
- `/docker-compact` stops after step 1 when the script's line says `skipped` (not Windows, or no disk found) (Task 2).
- `/docker-compact` stops before writing `compact.txt` if the disk path has a non-ASCII character, and tells the user to run diskpart by hand; `compact.txt` is written with `Set-Content -Encoding ascii` (Task 2).
- diskpart outcome: an error from `Start-Process -Verb RunAs -ErrorAction Stop` counts as a declined UAC prompt (nothing compacted); `ExitCode` 0 is success; any other code or an empty result is a failure (Task 2).
- The Docker total is known only when all four `docker system df` rows parse with units `B`, `kB`, `MB`, `GB` or `TB`; a missing row or any other unit gives `docker ?`, not a partial sum (Task 1).
- Criterion 3 is not a stop rule: if Docker Desktop is not running, or the machine is not Windows, the PR records it as "not run" with the reason and the script's output (Task 5).

## Findings fixed

- round 1 [blocking] ship.md status-line call not limited to Docker tasks: the step 11 insert now begins "If the task used Docker, then run", and the test asserts it.
- round 1 [minor] "not a stop rule" assertion passed on existing text: asserts "its verdict is not a stop rule".
- round 1 [minor] invisible BOM in `running_distros`: written as the `\ufeff` escape.
- round 1 [minor] call order in `main`: states `read_disk`, then `used_bytes()`, then `docker_bytes()`.
- round 1 [minor] criterion 7 had no pointer: Task 5 notes `/ship` delivers it.
- round 2 [blocking] no test for `sparse yes` in the status line: added `test_status_line_sparse_yes_no`.
- round 2 [minor] invisible BOM still present: replaced with the escape and a note to use it in source.
- round 2 [minor] ship.md indentation wording: markers at column 0, continuation lines indented 4.
- round 2 [minor] UAC-declined detection: `-ErrorAction Stop` added; an empty result is a failure.
- round 2 [minor] Windows test setup: fixtures create an empty `docker_data.vhdx` under `tmp_path`.
- round 3 [minor] `None` from `run` in `used_bytes`/`docker_bytes`: both return `None` without passing it on.
- round 3 [minor] test patched global `os.stat`: `read_disk` calls module-level `_stat`, which tests patch.

## Open

- none
