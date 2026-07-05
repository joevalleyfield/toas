Filed as: 260705-depends-on-relationship-field
FKA:
AKA: task dependency semantics; resolved prerequisite field; blocked-by specialization
Legacy index:

keywords: docs, tooling, implementation, historical, contract, task-schema, dependencies, workboard

Related: `260524-exploratory-work-representation-model`; `260524-auto-inferred-task-dependencies`; `260627-workboard-relationship-tree-builder`

# Depends On Relationship Field

Preserve durable prerequisite semantics in task metadata without overloading
`Blocked by:` past the point where the blocker has already been resolved.

## Current Reality

TOAS task files currently distinguish `Parent:`, `Blocks:`, `Blocked by:`, and
`Related:`.

That leaves a semantic gap:

- `Blocked by:` truthfully captures live gating
- removing a resolved blocker keeps the queue honest
- but removing it also discards the enduring "this task depends on that prior
  work" relationship unless it is preserved awkwardly in prose or `Related:`

## Desired Reality

Task metadata should be able to say both:

- this task depends on another task in a durable causal/prerequisite sense
- this task is currently blocked by an unresolved subset of those dependencies

`Blocked by:` should therefore become a specialization of a broader
`Depends on:` field rather than trying to carry both meanings by itself.

## Transformations

- added `Depends on:` to the canonical relationship-field guidance in
  `tasks/README.md`
- defined `Blocked by:` as the unresolved subset of `Depends on:`
- documented the expected transition when a blocker closes:
  remove it from `Blocked by:` and keep it under `Depends on:` only if the
  prerequisite relationship still matters
- added `Depends on:` to `tasks/task-template.md`
- taught `tasks/scripts/sync_workboard.py` to parse `Depends on:` and render
  non-blocking dependencies separately from active blockers
- refreshed open schema-design tasks that explicitly listed the supported
  relationship fields

## Evidence

- `tasks/README.md` now names `Depends on:` explicitly and defines its
  relationship to `Blocked by:`
- `tasks/task-template.md` exposes the field in the default authoring surface
- `tasks/scripts/sync_workboard.py` accepts and renders the field without
  conflating it with active blockers
