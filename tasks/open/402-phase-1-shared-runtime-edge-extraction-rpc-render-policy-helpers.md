## Goal

Extract shared runtime edges used across `cli.py`, `daemon.py`, `step.py`, and `tools.py` so decomposition removes duplication before module splits.

## Why Now

Cross-cutting helper duplication inflates coupling and obscures ownership; extracting shared edges first lowers risk for later phase movement.

## Scope

- identify and extract shared helpers for:
  - RPC mode gating/request wrapping
  - result rendering/formatting adapters used by command and daemon surfaces
  - shell/workspace/config policy resolution helpers
- place extracted helpers in stable modules with clear ownership
- migrate first call sites in small slices while preserving behavior
- add direct unit tests for extracted helpers independent of command handlers

## Intended Behavior

- command/runtime modules depend on shared helpers instead of re-implementing edge logic
- later command-handler extraction becomes mostly movement and wiring

## Constraints

- no behavioral change at CLI/RPC transcript output boundaries
- no broad call-site rewrite in one pass; migrate incrementally
- maintain compatibility imports while call sites transition

## Done When

- at least one helper cluster from each edge category is extracted and adopted
- duplicate implementations are reduced in existing monolith modules
- helper-focused tests lock fallback/error contracts

## Progress

- extracted first shared helper cluster to new module `src/toas/runtime_edges.py`:
  - `require_rpc_enabled`
  - `rpc_request_or_exit`
- migrated CLI async/rpc lifecycle call sites to shared helpers (`run_step_async`, `run_watch`, `run_cancel`, `run_backend`)
- added direct unit coverage for the new shared module in `tests/test_runtime_edges.py`
