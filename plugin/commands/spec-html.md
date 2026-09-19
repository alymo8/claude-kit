---
description: Render a spec or plan to its HTML view and open it in the browser (latest spec/plan when no path is given)
disable-model-invocation: true
---

Render the spec/plan to HTML and open it. Run exactly one command and reply with
one line naming the opened file:

    python "${CLAUDE_PLUGIN_ROOT}/scripts/open-spec.py" $ARGUMENTS

(Fallback if the variable is not expanded:
`~/.claude/skills/claude-kit/scripts/open-spec.py`.)

- With a path argument (`.md` or `.html`), that file is rendered and opened.
- With no argument, the most recently modified file under
  `docs/superpowers/specs/` or `docs/superpowers/plans/` of the current repo is used.
- If it exits non-zero, report its stderr and stop; do not open anything by hand.
