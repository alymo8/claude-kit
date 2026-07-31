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

## The four playbooks

| Playbook | What it governs |
|----------|-----------------|
| [Knowledge layer](knowledge-layer.md) | How research, findings, and context are captured as a version-controlled, human-readable knowledge base. |
| [Decision log (ADRs)](decision-log.md) | How locked-in decisions leave a durable, numbered trace. |
| [Spec-driven development](spec-driven-development.md) | The path from an idea to shipped code: brainstorm → spec → plan → build. |
| [Engineering practices](engineering-practices.md) | Test-first development, coding standards, and the code-review gate. |

## How they fit together

The knowledge layer is the **foundation** — the organized home for what a project
knows. The decision log is where choices made against that knowledge get **locked
in**. Spec-driven development is the **flow** that turns knowledge and decisions
into working software, and engineering practices are the **quality bar** every
change clears on the way to `main`. A healthy project keeps all four current: new
findings update the knowledge base, new choices land as ADRs, new work starts from
a spec, and every merge passes the practices gate.
