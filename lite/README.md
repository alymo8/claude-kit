# agent-kit-lite

agent-kit-lite is the Markdown-only edition of
[agent-kit](https://github.com/alymo8/claude-kit), a spec-driven workflow
for Claude Code. It gates specs and plans with fresh-context reviewers,
takes an approved spec to a merged pull request with `/ship` (or to an open
pull request with `/ship-fast` for a proof of concept), writes handoff files
between sessions, reviews a branch against its spec, and ships the
workspace conventions it follows. It has no hooks and no scripts: every
step is done by Claude reading these files and running `git` and `gh`.

## Requires

- The superpowers plugin: see its install page at
  https://github.com/obra/superpowers. The skills here call its skills.
- `git` and `gh`, signed in, for `/ship`, `/ship-fast` and `pr-review-respond`.

## What's inside

- Skills: `spec-gate`, `plan-gate`, `grill`, `review`, `capture-learnings`,
  `lean-context`, `present`, `pr-review-respond`, `audit`, `teach`, and
  `workspace-rules` (the conventions as one skill).
- Commands: `/ship`, `/ship-fast` and `/handoff`.
- The six convention playbooks in the plugin's `./conventions/` folder.

## Lite and full

The full agent-kit, on the repository's own marketplace, adds session
hooks (handoff injection, a context nudge, the workspace rules at every
session start), scripts behind the lint, frozen and citation checks,
parallel plan tasks, a runner that ships several specs at once, project
scaffolding and more. In lite,
those checks are done by reading, tasks run one at a time, and a new
session reads its handoff when you ask it to.

## Always-on rules

Nothing loads the workspace rules on its own in lite. Claude loads the
`workspace-rules` skill for feature work; to keep the rules in every
session, import that skill's `SKILL.md` from your own `CLAUDE.md` with an @
line pointing at the installed plugin's `skills/workspace-rules/SKILL.md`.

## Data and network

No telemetry, and nothing is sent to the plugin's authors. The commands
and skills reach GitHub only through your own `git` and `gh` when you run
them. Handoff files are written under `.claude/handoffs/` in your repository
when you run `/handoff`.

## License

MIT, see `LICENSE`.
