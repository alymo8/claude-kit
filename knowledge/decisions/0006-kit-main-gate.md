# ADR 0006: Kit `main` gate: CI on every push; PRs for feature work

- **Status:** accepted
- **Date:** 2026-09-14

## Context
The engineering-practices convention wants a protected `main` with CI, AI and
human review on every change. This repo is a solo preferences repo where many
changes are one-line convention edits; a full PR gate on each would be friction
without benefit. The convention itself says to scale to the project.

## Decision
CI (`ruff`, `pytest` on Ubuntu and Windows) runs on every push and PR.
Feature-sized changes (anything with a spec) go through a branch and PR with CI
green. One-line doc fixes may be committed directly to `main`. No branch
protection is enabled.

## Consequences
Breakage is always visible; the ceremony matches the change. If a second
contributor ever appears, enable protection and supersede this ADR.
