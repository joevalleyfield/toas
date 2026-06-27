Filed as: 260627-fail-closed-history-query-hardening
FKA:
AKA: fail-closed graph hardening; corrupt-history refusal; duplicate-id hardening
Legacy index:

keywords: runtime, hardening, inception, correctness, graph, projection, history, parity

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-event-log-fsck-contract`; `260627-history-surface-corruption-semantics`
Related: `260626-transcript-parallelism-design-pressures`; `260627-split-storage-rebuild-and-projection-parity`; `260627-segmented-event-index-and-lookup-hardening`

# Fail-Closed History Query Hardening

## Current Reality

Current graph/history code prefers to keep going when durable history is
structurally ambiguous. Duplicate ids are collapsed or skipped, and invalid
targets may yield empty or misleading outputs instead of an integrity refusal.

That behavior is especially risky now that TOAS is also carrying design
pressure toward broader transcript parallelism and richer history affordances.
Graph/query hardening should happen before TOAS treats durable history as a
more powerful reusable substrate.

## Desired Reality

History-facing surfaces should fail closed on fatal durable-history integrity
violations. They should not silently normalize duplicate ids or other graph
shape corruption into plausible but conflicting projections.

The implementation goal is narrow:

- route surfaces through one integrity gate
- refuse with deterministic diagnostics on fatal corruption
- preserve current happy-path semantics when history passes integrity checks

## Focus

- add integrity preflight at the right durable-state seam
- thread refusal behavior through `heads`, `history`, `transcript`,
  `llm-input`, `rebuild`, and `graph`
- align hot-log and logical-history readers on the same fail-closed policy
- add focused tests for duplicate-id corruption and related shape failures

## Exit Evidence

- focused implementation slice proving fatal corruption is refused
- regression coverage showing duplicate-id history no longer yields divergent
  surface-specific normalization
- explicit note that this hardening precedes broader parallel-affordance or
  history-affordance expansion

