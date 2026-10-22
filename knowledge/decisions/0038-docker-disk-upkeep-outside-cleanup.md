# ADR 0038: Docker disk upkeep runs outside the per-feature clean-up

- **Status:** accepted
- **Date:** 2026-10-21

## Context
Docker Desktop's `docker_data.vhdx` grows and does not shrink unless the
distro is sparse. On 2026-10-21 it was 38.7 GB for about 9.7 GB of data;
diskpart got it down to 9.5 GB. The bloat is machine-wide, not caused by one
feature. Compacting stops Docker and needs a UAC prompt, which conflicts with
`/ship`'s no-check-in run.

## Decision
- The `/ship` and `/ship-fast` clean-up only reports the line printed by
  `plugin/scripts/docker-disk.py`.
- Compaction is the user-only `/docker-compact` command.
- The sparse flag is the prevention and compaction is the repair; the user
  applies both.
- The compaction threshold (file > 1.5 x used and file - used > 2 GiB) is
  measured against the space used inside the disk, not `docker system df`,
  which counted 1.6 GiB against 3.2 GiB used.

## Consequences
- Growth is noticed at each Docker-using `/ship`.
- Nothing is reclaimed without the user.
- macOS, Linux and moved disks get a skipped line.
