# 489 Daemon Self-Shell Elimination via Operator API

## Objective
Eliminate daemon/runtime subprocess paths that shell out to `toas` itself where direct operator API calls can provide equivalent behavior.

## Why
With core 470 seam work in place and 469 closed, remaining high-value motivation is runtime simplification:
- reduce redundant process hops
- improve latency and streaming consistency
- reduce behavioral divergence across warm/cold/CLI paths
- simplify failure handling and observability

## Scope
In scope:
- audit daemon/runtime paths for self-shell subprocess invocation patterns (`uv run toas ...` / `toas ...`)
- classify each path:
  - must remain subprocess (isolation/cancellation contract)
  - eligible for operator API replacement
- migrate at least one high-value eligible path to direct operator API use with parity tests

Out of scope:
- removing subprocess usage that is contractually required for cancellation/isolation
- broad redesign of daemon protocol surfaces

## Deliverables
- inventory of self-shell call sites and disposition
- one or more migrated paths using operator API seams
- parity/regression tests for migrated paths
- notes on any retained subprocess paths and rationale

## Inventory (2026-05-09)

### Candidate self-shell call sites (daemon/runtime)

1. `src/toas/daemon/async_runner.py` (`start_async_step`)
- Current behavior:
  - resolves command via `step_subprocess_command_fn()`
  - launches `subprocess.Popen(command, ...)` where command is `toas step` (or `python -m toas.cli step` fallback)
- Classification: `eligible_for_migration`
- Rationale:
  - this is self-shell invocation of TOAS from TOAS daemon runtime
  - warm lane already proves in-process operator execution shape is viable
  - parity can be validated with existing async/watch/cancel test surfaces

2. `src/toas/daemon/facade_helpers.py` (`step_subprocess_command`)
- Current behavior:
  - builds self-shell command (`toas step` or module fallback)
- Classification: `retire_with_migration`
- Rationale:
  - helper exists only to support (1); if (1) is migrated, this becomes removable or cold-compat-only shim

### Subprocess paths explicitly out-of-scope for this task

1. `src/toas/tools_cluster/shell_ops.py`
- Classification: `must_remain_subprocess`
- Rationale:
  - user/model-intended shell execution contract, not daemon self-shell recursion

2. `src/toas/daemon/backend_lifecycle.py`, `src/toas/daemon/server_lifecycle.py`
- Classification: `must_remain_subprocess`
- Rationale:
  - process lifecycle management for daemon/backend, not operator self-shell step execution

3. `src/toas/acceptance_harness.py`, `src/toas/bench.py`
- Classification: `non-runtime-supporting`
- Rationale:
  - harness/bench utilities, not daemon/runtime operator consequence path

## First migration slice

- Target: replace cold `step_async` self-shell spawn path with direct operator API execution under daemon control while preserving:
  - run-store/watch stream contracts
  - cancellation semantics
  - tool/progress event emission parity
- Initial strategy:
  - introduce an in-process cold worker entry that preserves current stream event protocol
  - keep current warm lane intact; migrate cold lane first behind parity tests

## Done When
- at least one meaningful self-shell path is removed in favor of operator API
- migrated path has explicit parity tests
- remaining retained self-shell paths are documented with rationale

## Related
- 470 operator API seam and CLI-thin wrapper migration
- 483 command stdout streaming to Vim plugin (closed)
- 485 shell-lane purpose unification (closed)
