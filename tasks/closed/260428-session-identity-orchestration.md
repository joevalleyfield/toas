Filed as: 463-session-identity-orchestration-and-buffer-mapping
FKA: 463-session-identity-orchestration-and-buffer-mapping
AKA: session identity; multi-buffer; session mapping
Legacy index: 463

keywords: surface, historical, research, identity, session, duplicate

# Session Identity Orchestration and Buffer Mapping

Define and implement named/multi-buffer session identity semantics (for example `.toas/session-<name>.md`) while preserving canonical `events.jsonl` authority.

## Disposition

Superseded and closed on 2026-07-16. This task was opened as the follow-on
from `456`, but its intended surface-identity semantics were implemented and
closed under `561` before this older placeholder was brought forward.

`561` delivered durable `surface_bind` / `surface_select` mappings, explicit
`--surface` targeting, auditable rebind provenance, surface-local continuity
guards, and single-surface compatibility. The remaining question is not this
task's missing implementation; it is whether the landed alias/binding layer
continues to justify itself beyond explicit transcript paths. That retirement
question remains documented in
`docs/notes/2026-06-19-surface-binding-retirement-and-replacement-shape.md`.

## Historical Why

`456` established configurable transcript paths; next step is ergonomic multi-buffer identity and selection.

## Historical Scope

- define session-identity mapping model (slot/name/path)
- implement selection and persistence semantics
- clarify lineage/head/anchor interactions under identity switches
- add tests for deterministic selection and compatibility defaults

## Historical Done When

- operators can switch among named/slot session identities deterministically
- identity changes are observable and test-covered
- compatibility with existing single-transcript workflows is preserved

## Completion Evidence

- [x] `tasks/closed/561-multi-active-transcripts-independent-control-surfaces-over-shared-graph.md`
  records the completed durable mapping, targeting, provenance, and regression
  work.
- [x] The implementation and tests named by `561` remain present in the graph,
  CLI, operator API, and runtime path-resolution surfaces.
- [x] This duplicate task no longer directs the transcript-parallelism parent
  toward already-landed work.
