# 515 Protocol Envelope v0 and Event Durability Map

## Objective
Define and adopt a first-cut runtime protocol envelope (`session`, `activity`, `event`, `cancel`) and an explicit durability map separating stream-only events from graph-durable records.

## Why
IPC simplification and runtime-host migration will churn unless protocol semantics are explicit first. This task establishes the stable contract needed before broader transport/supervision migration.

## Scope
- define protocol envelope v0 shape for runtime host/client transport
- define event category set and required correlation fields
- define cancellation semantics and downward propagation contract
- define durability classification:
  - durable (persist to graph/events)
  - ephemeral (stream-only)
  - projected (materialized transcript output only)
- map current daemon/watch/step outputs to the new classification
- add docs and focused tests for envelope validation/classification helpers

## Out of Scope
- full transport replacement or daemon removal
- complete supervision implementation
- full front-end migration (vim/web/etc.)

## Done When
- `docs/runtime-direction.md` references a concrete envelope v0 section (or linked note) with field-level definitions
- a durability map exists and is wired to current event classes
- tests assert envelope parsing/validation and durability classification behavior
- roadmap reflects this as the first carve-out toward IPC/runtime-host simplification

## Initial Slices
1. Add `docs/protocol-notes.md` section: envelope v0 (`session_id`, `activity_id`, `event_id`, `kind`, `ts`, `payload`, `final`, `cancel_of`).
2. Add a runtime classification helper module and unit tests.
3. Integrate helper into one production path (watch/step stream shaping) without changing user-visible output.
4. Add migration notes for follow-on transport abstraction task.

## Related
- `470` operator API seam migration
- `484` watch protocol semantics
- `488` multi-operator orchestration
- `489` daemon self-shell elimination (completed predecessor)

