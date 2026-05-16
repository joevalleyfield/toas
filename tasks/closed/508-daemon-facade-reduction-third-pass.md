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
- extracted request-dispatch and payload-validation wiring cluster from `daemon/__init__.py` into new focused module `daemon/facade_dispatch_ops.py`:
  - `build_payload_validators`
  - `build_op_handlers_map`
  - `handle_default_op_wrapper`
  - `safe_op_call_wrapper`
  - `handle_request_wrapper`
- rewired facade request path (`_handle_default_op`, `_OP_HANDLERS`, `_OP_PAYLOAD_VALIDATORS`, `_safe_op_call`, `handle_request`) to delegate through `facade_dispatch_ops` while preserving error-shaping and RPC contract behavior
- extracted managed-backend state operation wrapper cluster from `daemon/__init__.py` into new focused module `daemon/facade_backend_state_ops.py`:
  - `managed_backend_status`
  - `managed_backend_start`
  - `managed_backend_stop`
  - `managed_backend_restart`
- rewired `_managed_backend_status`, `_managed_backend_start`, `_managed_backend_stop`, and `_managed_backend_restart` to delegate through `facade_backend_state_ops` while preserving shared state-bridge semantics in `_with_managed_backend_state`
- added focused tests for backend-state seam delegation and argument threading:
  - `tests/test_daemon_facade_backend_state_ops.py`
- extracted local-op wrapper cluster from `daemon/__init__.py` into new focused module `daemon/facade_local_ops.py`:
  - `run_op_capture_stdout_wrapper`
  - `request_workdir_wrapper`
  - `handle_default_op_wrapper`
- rewired `_run_op_capture_stdout`, `_request_workdir`, and `_handle_default_op` to delegate through `facade_local_ops`, preserving request workdir scoping and default op stdout/debug behavior
- consolidated request-dispatch assembly in `facade_dispatch_ops` via `build_dispatch_runtime` (single seam returning handlers + payload validators)
- rewired `daemon/__init__.py` to use the unified dispatch-runtime seam, reducing direct assembly wiring while preserving `_OP_HANDLERS` / `_OP_PAYLOAD_VALIDATORS` compatibility surface
