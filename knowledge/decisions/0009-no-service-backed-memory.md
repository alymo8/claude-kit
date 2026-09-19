# ADR 0009: No service-backed memory in the kit

- **Status:** accepted
- **Date:** 2026-09-18

## Context
Token spend was attributed to rediscovery, and a knowledge-graph memory
(database plus an extraction model on every write) was considered. Measurement
showed same-file re-reads are rare; the loss is carry-over between sessions and
context that grows for hundreds of turns.

## Decision
The kit stays files plus Python hooks: a handoff file for carry-over, the
knowledge layer for durable facts, no daemon, no index service, no ingestion
cost.

## Consequences
Zero setup on a new machine and nothing to keep running. Recall across projects
relies on the knowledge layer and Claude Code's own memory directory. Revisit
only if a re-measurement shows recall, not carry-over, as the dominant cost.
