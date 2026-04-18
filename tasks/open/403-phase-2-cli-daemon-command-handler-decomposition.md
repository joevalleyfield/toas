## Goal

Decompose `cli.py` and `daemon.py` command/handler clusters into focused modules with explicit ownership boundaries.

## Why Now

`cli.py` and `daemon.py` remain high-churn orchestration surfaces where size/coupling still hide behavior risk and coverage signal.

## Scope

- implement first extraction slices aligned to `400` target shape:
  - CLI: dispatch vs command handlers vs rendering helpers
  - daemon: server lifecycle vs op handlers vs run-state bookkeeping vs lane routing
- preserve current command names, RPC semantics, and output contracts
- add module-local tests for moved handler logic to reduce reliance on monolith integration paths
- remove only safe dead wiring after parity tests pass

## Intended Behavior

- handler code becomes directly testable without full CLI/daemon bootstraps
- transport concerns and operation semantics are separated cleanly

## Constraints

- no semantic drift in async/watch/cancel/backend flows
- keep fallback lane behavior and daemon lifecycle contracts intact
- stage movement by cohesive clusters, not broad file churn

## Done When

- first command/handler clusters are moved for both CLI and daemon
- compatibility imports keep legacy entry paths stable
- moved behavior is covered by focused tests in new module locations

## Progress

- first concrete extraction slice opened: `405` (CLI async/rpc lifecycle command handler cluster)
- `405` completed and closed:
  - extracted async/rpc lifecycle handler cluster into `src/toas/cli_async_commands.py`
  - retained compatibility wrappers in `cli.py` with unchanged command/output behavior
  - added direct module tests in `tests/test_cli_async_commands.py` and achieved `100%` coverage for the new module
- next concrete extraction slice opened: `406` (daemon op-dispatch orchestration extraction)
- `406` completed and closed:
  - extracted daemon request dispatch orchestration into `src/toas/daemon_op_dispatch.py`
  - kept `toas.daemon.handle_request` and `_safe_op_call` as compatibility wrappers
  - added direct module tests in `tests/test_daemon_op_dispatch.py` and achieved `100%` coverage for the new module
- next daemon request-contract extraction slice landed:
  - extracted daemon payload validation and op-validator mapping to `src/toas/daemon_request_contract.py`
  - kept `toas.daemon` compatibility aliases for `_validate_*` helpers and `_OP_PAYLOAD_VALIDATORS` wiring
  - added direct module tests in `tests/test_daemon_request_contract.py`
- next daemon local-op extraction slice landed:
  - extracted local-op dispatch/workdir/default-op helpers to `src/toas/daemon_local_ops.py`
  - kept `toas.daemon` compatibility wrappers for `_run_op_capture_stdout`, `_request_workdir`, and `_handle_default_op`
  - added direct module tests in `tests/test_daemon_local_ops.py`

## Next Slices (Small-Model Handoff)

1. Chunk 1: daemon backend lifecycle extraction
- Scope: extract managed backend lifecycle helpers from `daemon.py` into `src/toas/daemon_backend_lifecycle.py`.
- Move: `_has_active_runs`, `_health_ok`, `_managed_backend_status`, `_managed_backend_start`, `_managed_backend_stop`, `_managed_backend_restart`.
- Compatibility: keep wrapper/alias names in `daemon.py` unchanged.
- Tests: add `tests/test_daemon_backend_lifecycle.py` for status/start/stop/restart + health-fail + active-run guard.
- Verification: `uv run pytest`.
- Commit message: `refactor: extract daemon backend lifecycle helpers with compatibility wrappers`.

2. Chunk 2: daemon run-store extraction
- Scope: extract async run store/watch/cancel state logic into `src/toas/daemon_run_store.py`.
- Move: `AsyncRun`, `_RUNS`, `_RUNS_LOCK`, `_emit_stream_event`, `_watch_async_step`, `_cancel_async_step`.
- Compatibility: keep `daemon.py` wrappers preserving `_watch_async_step` / `_cancel_async_step` call sites.
- Tests: add `tests/test_daemon_run_store.py` for event sequence, offset/since_seq, terminal/already-terminal cancel paths.
- Verification: `uv run pytest`.
- Commit message: `refactor: extract daemon run store and watch/cancel helpers`.

3. Chunk 3: daemon async-runner extraction
- Scope: extract subprocess/warm runner execution into `src/toas/daemon_async_runner.py`.
- Move: `_stream_process_output`, `_wait_for_process`, `_start_async_step`, `_start_async_step_warm`.
- Compatibility: keep wrapper functions in `daemon.py` and preserve behavior parity.
- Tests: add direct module tests for stream emission and terminal-event invariants.
- Verification: `uv run pytest`.
- Commit message: `refactor: extract daemon async runner helpers`.

4. Chunk 4: daemon handlers map extraction
- Scope: extract op-handler map assembly into `src/toas/daemon_handlers.py`.
- Move: `_handle_status`, `_handle_step_async*`, `_handle_watch`, `_handle_cancel`, `_handle_backend_*`, `_OP_HANDLERS`.
- Compatibility: keep `handle_request` API stable in `daemon.py`.
- Tests: add `tests/test_daemon_handlers.py` for handler-map keys and routing targets.
- Verification: `uv run pytest`.
- Commit message: `refactor: extract daemon op handlers map`.

5. Chunk 5: daemon process-control extraction
- Scope: extract daemon pid/socket lifecycle helpers into `src/toas/daemon_process_control.py`.
- Move: `_pid_path`, `_vim_port_path`, `_read_pid`, `_is_pid_running`, stale-endpoint cleanup helpers, related process checks.
- Compatibility: keep `daemon.py` wrappers used by daemon start/stop/status command surfaces.
- Tests: add `tests/test_daemon_process_control.py` for pid parsing, liveness checks (mocked), and stale-endpoint cleanup.
- Verification: `uv run pytest`.
- Commit message: `refactor: extract daemon process-control helpers`.

6. Chunk 6: task closure/bookkeeping
- Scope: finalize `403` bookkeeping after the above slices land.
- Update: progress notes in this task and corresponding `docs/roadmap.md` entries.
- Completion action: close `403` explicitly if scope is complete, otherwise open the next follow-on with clear boundaries.
- Verification: `uv run pytest`.
- Commit message: `tasks/docs: update 403 progress after daemon decomposition slices`.
