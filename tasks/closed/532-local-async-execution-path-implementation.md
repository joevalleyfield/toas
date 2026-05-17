# 532 Local Async Execution Path Implementation

## Goal
Implement ownership-first local async lifecycle paths for `step --async`, `watch`, and `cancel` while preserving current RPC-backed behavior as default for existing operators until cutover is complete.

## Why
`531` completed governance and migration-control scaffolding (`async_backend_mode`, strict cutover guard, compliance matrix), but local async lifecycle execution was placeholder-only. This task executes the first concrete ownership migration for `step --async` + `watch` + `cancel`.

## Scope
In scope:
- local backend path for `step --async` (start/run-id/status contract)
- local backend path for `watch` (poll/follow status/chunk progression contract)
- local backend path for `cancel` (lifecycle status contract)
- preserve current default behavior (`rpc`) and existing CLI/Vim compatibility
- targeted tests + full-suite parity

Out of scope:
- full daemon removal
- transport/protocol redesign

## Done When
- `step --async`, `watch`, and `cancel` each have real local execution paths behind the existing backend-mode seam
- default (`rpc`) behavior remains unchanged
- strict cutover controls remain functional
- full suite passes

## Related
- `525` post-envelope runtime ownership and primary-path de-daemonization
- `531` ownership/RPC-exception governance seam

## Progress
- implemented first local execution slice:
  - `step --async` now has a real local-start path behind existing backend-mode seam:
    - when backend mode resolves to `local` and strict cutover guard is not enabled, async start is routed through daemon async-runner local start path (no RPC request needed for the start operation)
    - default backend mode remains `rpc`, preserving current behavior for existing operators and Vim flows
  - preserved switchable strict-cutover behavior:
    - `TOAS_ASYNC_LOCAL_STRICT_GUARD=1` still enforces explicit local-not-implemented guard exits
  - avoided import-cycle risk by lazy-loading daemon facade modules in local-start helper
  - added/updated tests:
    - local backend step path remains deterministic under test via helper monkeypatch
    - local-start helper wiring test validates facade callback wiring without heavy runtime side effects
  - validated with:
    - `uv run pytest -q tests/test_cli_async_commands.py --no-cov`
    - `uv run pytest -q -n 14`
- implemented second local execution slice:
  - `watch` now has a real local path behind the existing backend-mode seam:
    - when backend mode resolves to `local` and strict cutover guard is not enabled, watch requests route through in-process run-store watch operation (no RPC request needed)
    - default backend mode remains `rpc`, preserving current external behavior
  - strict cutover behavior preserved:
    - `TOAS_ASYNC_LOCAL_STRICT_GUARD=1` still enforces explicit local-not-implemented exits for watch
  - added/updated tests:
    - local watch mode avoids RPC and uses local watcher path
    - local watch helper wiring coverage
  - validated with:
    - `uv run pytest -q tests/test_cli_async_commands.py --no-cov`
    - `uv run pytest -q -n 14`
- implemented third local execution slice:
  - `cancel` now has a real local path behind the existing backend-mode seam:
    - when backend mode resolves to `local` and strict cutover guard is not enabled, cancel requests route through in-process run-store cancel operation (no RPC request needed)
    - default backend mode remains `rpc`, preserving current external behavior
  - strict cutover behavior preserved:
    - `TOAS_ASYNC_LOCAL_STRICT_GUARD=1` still enforces explicit local-not-implemented exits for cancel
  - added/updated tests:
    - local cancel mode avoids RPC and uses local cancel path
    - local cancel helper wiring coverage
  - validated with:
    - `uv run pytest -q tests/test_cli_async_commands.py --no-cov`
    - `uv run pytest -q -n 14`
