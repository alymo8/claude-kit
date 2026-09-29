# Phase E: architecture and design

Audit architecture and design. Where a security-relevant boundary issue comes
up, note it in one line and leave the detail to phase D.

Cover:

- **Overall architecture:** describe the actual structure, not the
  aspirational one, and note where the code contradicts the stated or implied
  architecture, including anything claimed in README or CLAUDE.md.
- **Antipatterns:** god objects, god modules, circular dependencies,
  copy-paste duplication, premature abstraction, abstraction that leaks its
  implementation, business logic in controllers or handlers, config sprawl.
- **Coupling and cohesion:** which modules cannot be changed independently,
  and which change together in git history despite being nominally separate
  (use the churn data in the repo map).
- **Boundaries:** is there a clear separation between transport,
  orchestration, domain logic and I/O, or do they interleave?
- **State and concurrency:** shared mutable state, race conditions, missing
  locks, assumptions that only one instance runs, in-process state that breaks
  on horizontal scaling.
- **Scalability limits:** the first thing that breaks at 10x current load, and
  why.
- **Cost and latency hotspots:** for model-backed paths, per-run token spend,
  prompt caching (present or absent), redundant model calls, sequential calls
  that could run in parallel, context bloat. Elsewhere, N+1 queries, unbounded
  result sets, synchronous work that should be queued.
- **Failure modes:** what happens when a dependency is slow or down:
  timeouts, circuit breakers, graceful degradation, partial-failure handling.
- **Extensibility:** how hard is it to add a new tool, model provider or data
  source? Trace which files a developer would have to touch.

End with `## What is missing` and `## Top 10`, ranked by severity then effort.
