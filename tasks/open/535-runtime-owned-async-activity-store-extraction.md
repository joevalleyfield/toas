# 535 Runtime-Owned Async Activity Store Extraction

## Goal
Extract async activity/run state into a runtime-owned store API so CLI and daemon consume shared lifecycle ownership without daemon-specific authority assumptions.

## Why
Current local mode still routes through daemon run-store seams. We need a runtime-owned state surface to make daemon an adapter rather than the canonical owner.

## Scope
In scope:
- extract/store abstractions for async activity lifecycle state
- migrate CLI local async paths to runtime-owned store API
- keep daemon compatibility through adapter layers

Out of scope:
- full daemon removal
- protocol envelope redesign

## Done When
- runtime-owned async store API exists and is used by local async paths
- daemon uses adapter wrapper around the same API
- lifecycle contracts and tests remain green

## Related
- `525` umbrella
- `534`

## Progress
- 2026-05-17: Added runtime-owned async activity store seam at `src/toas/runtime/async_activity_store.py` and migrated local async watch/cancel call sites to consume it.
- 2026-05-17: Kept daemon compatibility by routing daemon facade async ops through the same runtime store seam.
- 2026-05-17: Migrated daemon async runner ownership primitives (`AsyncRun`, create/register, lifecycle finalization/event emit) to import from runtime async activity store seam instead of daemon run-store direct imports.
- 2026-05-17: Routed async runner runtime-flag/debug hook consumption (`asyncio_runtime_enabled`, `_debug_log`) through runtime async activity store seam, removing remaining direct `run_store` hook import from runner.
- 2026-05-17: Added stable runtime API facade `runtime/async_activity_store_api.py` and migrated daemon/CLI local async consumers to depend on the API module rather than backing implementation module imports.
