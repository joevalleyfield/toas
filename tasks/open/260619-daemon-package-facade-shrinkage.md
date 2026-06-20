Filed as: 260619-daemon-package-facade-shrinkage
FKA:
AKA: daemon package facade; daemon __init__ cleanup; import surface shrinkage
Legacy index:

keywords: runtime, investigation, active, legacy, surface, daemon, facade, transport

# Daemon Package Facade Shrinkage

Parent: `260614-architecture-follow-through-coordination`
Related: `260615-legacy-surface-retirement-inventory`

## Current Reality

`src/toas/daemon/__init__.py` still acts as a package-level facade and legacy
import surface for daemon adapter modules.
The CLI no longer imports the package root for daemon start/stop/status; it
calls `src/toas/daemon/server_lifecycle.py` directly.

## Desired Reality

The daemon package should be as thin as possible, with any remaining package
facade behavior justified by concrete import or compatibility needs.

## Gap Analysis

- We need current import consumers named explicitly.
- We need to distinguish transport-adapter behavior from actual facade
  necessity.
- We need a bounded shrinkage target rather than a vague "remove legacy"
  goal.

## Known Facts

- `src/toas/cli.py` now imports `src/toas/daemon/server_lifecycle.py`
  directly for daemon start/stop/status.
- `docs/runtime-ownership.md` treats `daemon/__init__.py` as a package facade
  around daemon adapter modules.
- Daemon transport and server behavior should remain adapter-oriented, not
  semantic ownership.
- Tests that used to assume bare `session.md` could seed daemon step execution
  were updated to create the configured transcript path explicitly.

## Unknowns

- Which imports can be redirected to concrete daemon modules directly.
- Whether any public package-level symbols still need to be preserved.
- How much of the facade can be trimmed without breaking CLI or tests.

## Investigations

- Enumerate the package-level symbols and their consumers.
- Identify direct-module imports that could replace package facade access.
- Determine which parts, if any, must remain for compatibility.
- Check whether the remaining package-root tests are asserting behavior that
  genuinely belongs at the package boundary or whether any more can be retargeted
  to concrete daemon submodules.

## Evidence

Ready to leave active work when:

- the actual package-facade consumers are named
- any keep-vs-remove decisions are bounded by tests
- the daemon package no longer carries unrelated legacy convenience exports

## Inventory Findings

The package root currently has one clearly required execution entry point and a
mix of real boundary behavior plus wrapper-only plumbing.

### Keep

- `main`
  - required by `src/toas/daemon/__main__.py`
- `handle_request`
  - stable RPC dispatch entry point for the daemon package boundary
- `serve_forever`, `start`, `stop`, `status`
  - real daemon lifecycle surface, still part of the package boundary

### Retarget

- `_run_op_capture_stdout`
- `_request_workdir`
- `_capture_stdout`
- `_write_run_event`
- `_thinking_stream_enabled`
- `_prompt_progress_stream_enabled`
- `_normalize_workdir`
- `_start_async_step`
- `_watch_async_step`
- `_cancel_async_step`
- `_stream_read_async_step`
- `_handle_status`
- `_handle_step_async`
- `_handle_step_async_cold`
- `_handle_watch`
- `_handle_stream_read`
- `_handle_stream_subscribe`
- `_handle_cancel`
- `_handle_backend_status`
- `_handle_backend_start`
- `_handle_backend_stop`
- `_handle_backend_restart`
- `_handle_default_op`
- `_safe_op_call`
- `_emit_stream_event`
- `_emit_tool_events_from_line`
- `_stream_process_output`
- `_wait_for_process`
- `_managed_backend_status`
- `_managed_backend_start`
- `_managed_backend_stop`
- `_managed_backend_restart`
- `_run_step_healthcheck`
- `_pid_path`
- `_vim_port_path`
- `_read_pid`
- `_is_pid_running`
- `_stale_socket_cleanup`

These should either move to the concrete module that owns the behavior or stop
being tested through `toas.daemon` if the only consumer is wrapper coverage.

### Drop If Unused

- `_ASYNC_OPS_WITH_PAYLOAD_ERRORS`
- `_OP_HANDLERS`
- `_OP_PAYLOAD_VALIDATORS`
- `_REQUEST_HANDLER_RUNTIME`
- `_BACKEND_LIFECYCLE`

These are internal wiring artifacts, not a meaningful public daemon API. If no
production consumer remains, they should disappear rather than stay as
export-only internals.

### Follow-Up Reading

- `src/toas/daemon/server_lifecycle.py`
- `src/toas/daemon/facade_async_ops.py`
- `src/toas/daemon/facade_process.py`
- `src/toas/runtime/request_handlers.py`
- `src/toas/runtime/model_backend_lifecycle.py`

## Progress Notes

- Added direct `server_lifecycle` coverage on real lifecycle branches rather
  than extending package-root wrapper tests:
  - `serve_forever` pid/vim-port creation and cleanup
  - stale socket cleanup delegation
  - `stop` no-pid and already-stopped cleanup paths
  - `status` non-Path endpoint behavior
  - `main` serve/start/stop/status/unknown/interrupt branches
- Picked off remaining `stream_pacing_summary` prefixed-log parsing edges.
