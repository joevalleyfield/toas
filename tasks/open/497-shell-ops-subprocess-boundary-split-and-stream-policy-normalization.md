# 497 Shell Ops Subprocess Boundary Split And Stream Policy Normalization

## Objective
Further decompose `src/toas/tools_cluster/shell_ops.py` so subprocess execution, stream-emission policy, and shell-shape adapters are separated into focused helpers/modules.

## Why
`shell_ops.run_subprocess` remains one of the highest branch-density hotspots after recent 400-series slices. This keeps streaming/timeout behavior hard to reason about and slows targeted testing.

## Scope
- extract subprocess lifecycle internals from `run_subprocess` into focused helpers (or a focused submodule)
- isolate stream flush policy decisions from command-shape adaptation (`shell`, `shell_script`, user-intent shell)
- preserve existing behavior and policy boundaries between user-intent and model-callable shell lanes
- add/adjust direct tests for extracted helper seams

## Out Of Scope
- changing shell authorization/policy semantics
- introducing a long-lived shell lane in this task

## Done When
- `run_subprocess` no longer carries mixed responsibilities for process setup + read loop + policy shaping
- helper/module boundaries are explicit and directly tested
- targeted parity tests and full suite pass

## Related
- `400` decomposition umbrella
- `485` shell-lane purpose unification
- `483` streaming behavior debug/fix
