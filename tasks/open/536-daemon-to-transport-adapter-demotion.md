# 536 Daemon-To-Transport Adapter Demotion

## Goal
Demote daemon from lifecycle authority to optional transport adapter by delegating async operations to shared runtime-owned APIs.

## Why
To make RPC near-transparent, daemon behavior must match local runtime behavior through shared implementation rather than parallel authority paths.

## Scope
In scope:
- refactor daemon async handlers to delegate to shared runtime-owned APIs
- retain envelope/status compatibility for current RPC clients
- remove/flatten authority-only daemon branches where redundant

Out of scope:
- complete daemon deletion
- editor/frontend strategy changes

## Done When
- daemon async ops are adapter/delegation-first
- RPC payload contracts remain compatible
- duplicated daemon authority logic is reduced/removed

## Related
- `525` umbrella
- `535`

## Progress
- 2026-05-17: Routed daemon module `_RUNS` surface import through `runtime.async_activity_store_api` instead of direct `daemon.run_store` import, continuing adapter-first demotion while preserving daemon test/debug visibility.
