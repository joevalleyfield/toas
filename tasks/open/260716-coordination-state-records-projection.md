Filed as: 260716-coordination-state-records-projection
FKA:
AKA: coordination state; cohort projection; procedure barrier records
Legacy index:

keywords: runtime, implementation, active, contract, projection, provenance, transcript

Parent: `260626-transcript-parallelism-design-pressures`
Depends on: `561`
Related: `260716-procedure-step-taxonomy`; `260626-events-jsonl-multiplicity-and-merge-provenance`

# Coordination-State Records and Read-Only Projection

## Claim

Claimed for implementation on 2026-07-16.

## Goal

Implement the explicit, append-only `coordination_state` fact model defined in
`docs/notes/2026-07-16-procedure-step-taxonomy.md`, plus a read-only grouping
view for coordinator inspection.

## Scope

- Add durable writer/query support for `coordination_state` records.
- Validate the four initial statuses and their required supporting fields.
- Resolve the latest valid state by tuple
  `(procedure_id, step_id, subject_surface_id)` without mutating earlier facts.
- Add an explicit operator declaration entry point and a read-only projection
  grouped by procedure, step, status, and cohort key.
- Render `blocked` and `off_track` entries as exception-lane rows.

## Invariants

- Existing `procedure` YAML assets remain static tool plans, not coordination
  state.
- `run_done`, tool results, transcript edits, and watcher events never create
  or advance coordination state implicitly.
- A `reached_barrier` record includes evidence or explicit operator attestation;
  `blocked` includes `needs`/`blocked_by`; `off_track` includes
  `exception_reason`.
- `cohort_key` is accepted only for `in_progress` and `reached_barrier`.
- The projection is derived and read-only; it is not a scheduler, queue, or
  claim mechanism.

## Allowed Write Surfaces

- `src/toas/graph.py` and focused `graph_*` helpers for durable schema/query
- `src/toas/runtime/` for explicit declaration semantics
- focused `cli_*` / operator-command wrappers for the user-facing entry point
- `tests/test_graph*.py`, `tests/test_runtime*.py`, and CLI tests
- `docs/capabilities.md` and the task/workboard surfaces

## Completion Evidence

- Deterministic tests cover append-only supersession, validation failures,
  cohort/exception grouping, and non-inference from a terminal activity event.
- The operator can explicitly write and inspect coordination state without
  involving an autonomous loop.
- Documentation distinguishes durable coordination facts from activity and
  watcher lifecycle output.
