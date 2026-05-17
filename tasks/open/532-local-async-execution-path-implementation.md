# 532 Local Async Execution Path Implementation

## Goal
Implement the first real ownership-first local async execution path for `step --async` while preserving current RPC-backed behavior for existing operators until cutover is complete.

## Why
`531` completed governance and migration-control scaffolding (`async_backend_mode`, strict cutover guard, compliance matrix), but local async execution is still placeholder-only. This slice starts the actual runtime ownership migration.

## Scope
In scope:
- first real local backend path for `step --async` (start/run-id/status contract)
- preserve current default behavior (`rpc`) and existing CLI/Vim compatibility
- keep `watch`/`cancel` local paths explicit follow-on unless minimally required by the first step slice
- targeted tests + full-suite parity

Out of scope:
- full daemon removal
- complete local `watch`/`cancel` migration in one pass
- transport/protocol redesign

## Done When
- `step --async` has a real local execution path behind the existing backend-mode seam
- default (`rpc`) behavior remains unchanged
- strict cutover controls remain functional
- full suite passes

## Related
- `525` post-envelope runtime ownership and primary-path de-daemonization
- `531` ownership/RPC-exception governance seam
