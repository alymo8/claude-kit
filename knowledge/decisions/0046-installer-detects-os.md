# ADR 0046: The installer detects the OS and never asks

- **Status:** accepted
- **Date:** 2026-11-15

## Context
The kit has to install on Windows, macOS and Linux, and the fix for a missing
`python` differs per OS. On macOS `python` is often absent (only `python3`),
and the old advice to alias it does not reach hooks, which run in a
non-interactive shell.

## Decision
`plugin/install.py` detects the OS from `sys.platform`, prints it, and gives
that OS's fix. It never asks the user which device they are on. When `python`
is missing it stops and prints the fix, changing nothing; on macOS it names
the Homebrew `libexec/bin` folder to add to `PATH` in `~/.zprofile` when one
exists. Hooks keep calling `python`.
Rejected: asking the user for the OS, or detecting and then confirming
(redundant prompts, wrong answers possible, blocks scripted installs);
creating a `python` symlink and editing the shell profile for the user
(changes their setup without review).

## Consequences
Installs need no prompts on any OS. A Mac user still adds one `PATH` line by
hand. Session rules that differ per OS (opening files) list each OS's command
and rely on Claude Code telling the session its platform.
