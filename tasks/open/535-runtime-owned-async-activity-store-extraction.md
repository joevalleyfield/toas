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
