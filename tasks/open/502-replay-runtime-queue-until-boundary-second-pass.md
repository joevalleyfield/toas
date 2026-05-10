# 502 Replay Runtime Queue-Until-Boundary Second Pass

## Objective
Decompose `src/toas/runtime/operator_command_extract_replay.py::_run_queue_until_boundary` into smaller helpers with clearer queue-state transitions.

## Why
AST rerank still flags `_run_queue_until_boundary` (~92 lines) as a high-complexity replay runtime hotspot.

## Scope
- split candidate collection, boundary decisioning, and render/projection phases
- keep replay output and queue semantics unchanged
- add focused tests for extracted helper branches and boundary edge conditions

## Done When
- `_run_queue_until_boundary` is materially slimmer and delegates cohesive helpers
- targeted replay/operator-command tests and full suite pass

## Related
- `400` decomposition umbrella
- `495` replay queue edges first split
