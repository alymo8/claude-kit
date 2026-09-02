# Working conventions

The playbooks that describe how projects under this workspace are researched,
decided, specified, and built. They generalize a set of practices proven out in
earlier work into a default way of working for **new** projects.

**Scale to the project.** These are the full-strength defaults. For a small script
or a throwaway spike, apply a lighter-weight version — a single knowledge doc
instead of a tree, an inline decision note instead of a formal ADR — but reach for
the full shape as soon as a project has more than one contributor, outlives a
weekend, or makes choices worth remembering. Skipping should be a deliberate call,
not the path of least resistance.

## The playbooks

| Playbook | What it governs |
|----------|-----------------|
| [Knowledge layer](knowledge-layer.md) | How research, findings, and context are captured as a version-controlled, human-readable knowledge base. |
| [Decision log (ADRs)](decision-log.md) | How locked-in decisions leave a durable, numbered trace. |
| [Spec-driven development](spec-driven-development.md) | The path from an idea to shipped code: brainstorm → spec → plan → build. |
| [Engineering practices](engineering-practices.md) | Test-first development, coding standards, and the code-review gate. |
| [Project memory file](project-memory.md) | The checked-in `CLAUDE.md` at a repo's root: build/test commands, architecture, conventions, gotchas. |

## How they fit together

The knowledge layer is the **foundation** — the organized home for what a project
knows. The decision log is where choices made against that knowledge get **locked
in**. Spec-driven development is the **flow** that turns knowledge and decisions
into working software, and engineering practices are the **quality bar** every
change clears on the way to `main`. The project memory file is the **front door** —
the short, static, checked-in `CLAUDE.md` that tells anyone arriving cold how to
build, test, and navigate the repo, and points at the other three. A healthy project
keeps all five current: new findings update the knowledge base, new choices land as
ADRs, new work starts from a spec, every merge passes the practices gate, and the
memory file changes in the same PR as whatever made it stale.
