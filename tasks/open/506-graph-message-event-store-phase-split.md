# 506 Graph Message/Event Store Phase Split

## Objective
Decompose high-branch durable history paths in `src/toas/graph.py` into focused helper seams so message-event append/query/lineage operations are easier to reason about and test.

## Why
`graph.py` remains one of the largest/highest-pressure modules (`~1000+` lines) and still dominates both complexity and coverage-miss noise; it is now the top decomposition target under `400`.

## Scope
- split one cohesive cluster from `graph.py` (message/event append or query path) into focused helper units/modules
- keep durable record semantics and on-disk history invariants unchanged
- add targeted tests for extracted helper branches and error paths
- preserve existing API surface for callers during this slice

## Done When
- selected `graph.py` cluster is materially slimmer and delegated to cohesive seams
- targeted graph tests and full suite pass with parity
- task progress is stitched with exact touched boundaries

## Related
- `400` decomposition umbrella
- `374` coverage-led refactor pass
