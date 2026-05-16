# 519 Envelope Adoption For Daemon Status And Backend Lifecycle

## Objective
Extend envelope-aware adapterization to daemon status/back-end lifecycle response flows so non-watch operational responses share envelope-first compatibility semantics.

## Why
`518` covered async step/cancel lifecycle. Remaining daemon operational responses (`status`, `backend_*`) still rely on legacy-only payload semantics.

## Scope
- add envelope adapterization for `status` and one backend lifecycle response family
- keep existing legacy fields and CLI output unchanged
- add focused parity tests for envelope + legacy dual-shape behavior

## Out of Scope
- protocol big-bang replacement
- frontend UX changes
- daemon removal

## Done When
- `status` and at least one `backend_*` response include envelope-compatible payload
- consumers preserve output parity while tolerating envelope-first data
- tests cover both legacy and envelope paths

## Initial Slices
1. Inventory daemon status and backend lifecycle payload shapes.
2. Reuse/extend lifecycle envelope adapter for selected ops.
3. Wire daemon handlers and one consumer path with legacy parity retained.
4. Add targeted tests + full-suite validation.

## Related
- `515` protocol envelope v0 + durability map (closed)
- `517` transport abstraction (closed)
- `518` envelope adoption beyond watch for step/cancel (closed)
- `470` operator API seam migration

## Progress
- completed slice 1 inventory:
  - reviewed daemon response seams for `status` and backend lifecycle (`backend_status`)
  - selected migration target: daemon `status` + `backend_status` response shaping
- completed slices 2/3:
  - extended lifecycle adapter module:
    - `src/toas/runtime/async_lifecycle_envelope_adapter.py` with status-envelope helper
  - wired daemon handlers:
    - `src/toas/daemon/handlers.py::handle_status`
    - `src/toas/daemon/handlers.py::handle_backend_status`
  - retained legacy response fields while adding envelope-compatible payload
- completed slice 4 validation:
  - updated focused tests for dual-shape parity:
    - `tests/test_daemon_handlers.py`
    - `tests/test_daemon.py`
    - `tests/test_daemon_async_runner.py`
    - `tests/test_daemon_run_store.py`
    - `tests/test_cli_async_commands.py`
    - `tests/test_runtime_async_lifecycle_envelope_adapter.py`
  - full suite green:
    - `uv run pytest -q -n 14`
