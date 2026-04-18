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
