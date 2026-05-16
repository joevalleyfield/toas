# 508 Daemon Facade Reduction Third Pass

## Objective
Further thin `src/toas/daemon/__init__.py` by extracting one cohesive transport/bootstrap wrapper cluster into focused daemon module seams.

## Why
`daemon/__init__.py` is still large and branchy despite prior shim retirement and helper extraction; reducing residual façade density will improve maintainability and test targeting.

## Scope
- extract one cohesive wrapper/bootstrap cluster from `daemon/__init__.py`
- preserve daemon CLI/runtime behavior and RPC contracts
- add focused tests for extracted seam behavior where missing
- keep import compatibility stable for current callers

## Done When
- `daemon/__init__.py` is materially slimmer for chosen cluster
- targeted daemon tests and full suite pass
- progress notes capture moved boundary and parity evidence

## Related
- `400` decomposition umbrella
- `494` daemon compatibility wrapper retirement
- `503` daemon run-store watch async-step phase split

## Progress
- extracted shared managed-backend state synchronization helper in daemon facade:
  - `_with_managed_backend_state`
- rewired `_managed_backend_status`, `_managed_backend_start`, `_managed_backend_stop`, and `_managed_backend_restart` to delegate through the shared helper
- added focused tests validating restoration of facade/backend shared state on both success and exception paths
- extracted async-step streaming wrapper cluster from `daemon/__init__.py` into new focused module `daemon/facade_async_ops.py`:
  - `emit_tool_events_from_line`
  - `stream_process_output`
  - `wait_for_process`
  - `start_async_step`
  - `watch_async_step_op`
  - `cancel_async_step_op`
- rewired facade wrappers (`_emit_tool_events_from_line`, `_stream_process_output`, `_wait_for_process`, `_start_async_step`, `_watch_async_step`, `_cancel_async_step`) to delegate through `facade_async_ops` while preserving existing RPC/CLI behavior and contracts
