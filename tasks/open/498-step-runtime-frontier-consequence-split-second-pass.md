# 498 Step Runtime Frontier Consequence Split Second Pass

## Objective
Decompose `src/toas/runtime/step_runtime.py` frontier consequence execution path into smaller, named seams that keep orchestration thin and branch behavior explicit.

## Why
`_execute_frontier_consequences` remains a top hotspot in AST/code-survey rankings. It still combines command dispatch outcomes, record writing, and projection-facing consequence stitching.

## Scope
- split `_execute_frontier_consequences` into focused helpers for:
  - operator-command handling path
  - assistant/tool-call path
  - consequence write/return shaping
- keep `run_step` orchestration contract unchanged
- add targeted tests for extracted helper branches

## Out Of Scope
- changing durable record semantics
- changing transcript projection format contracts

## Done When
- `_execute_frontier_consequences` is materially slimmer and delegates cohesive responsibilities
- new helper seams are directly covered by tests
- targeted parity tests and full suite pass

## Related
- `400` decomposition umbrella
- `495` first extraction slice for replay/runtime
- `470` operator-API seam alignment (behavior parity)
