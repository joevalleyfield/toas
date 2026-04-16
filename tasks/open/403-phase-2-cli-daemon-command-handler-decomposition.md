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
