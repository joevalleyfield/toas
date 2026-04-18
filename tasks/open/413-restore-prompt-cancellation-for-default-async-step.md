## Goal

Restore prompt, user-visible cancellation responsiveness for default `toas step --async` runs during model generation.

## Why Now

`ToasCancel` currently acknowledges cancellation but warm in-process async runs can continue generation until completion, making cancel arrive too late to matter operationally.

## Scope

- make default `step_async` execution route through the subprocess-backed async path
- preserve explicit warm execution path via `step_async_warm`
- update daemon tests to reflect default routing behavior

## Intended Behavior

- `toas cancel <run_id>` can terminate in-flight default async generation promptly
- warm path remains available only when explicitly requested

## Constraints

- preserve RPC response shapes for `step_async`, `step_async_warm`, and `cancel`
- no history mutation semantics changes outside cancellation timing

## Done When

- default `step_async` is backed by subprocess execution
- routing tests pass for `step_async` and `step_async_warm`
- regression report reproducer no longer shows delayed cancellation for default async runs

## Progress

- updated `src/toas/daemon.py` so `step_async` now dispatches to `_start_async_step` (subprocess-backed)
- updated `tests/test_daemon.py` `step_async` routing expectation to target `_start_async_step`
