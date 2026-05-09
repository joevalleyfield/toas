# 491 Daemon Async Runner Post-Warm Retirement Pass

## Objective
Remove retired warm-runner scaffolding from daemon async execution now that canonical async execution runs in-process via operator API.

## Why
`src/toas/daemon/async_runner_warm.py` is an orphan artifact after 489 and adds conceptual drift without providing behavior.

## Scope
- remove `src/toas/daemon/async_runner_warm.py`
- clean any imports/callers/tests if present
- validate daemon async parity with focused and full test runs

## Done When
- warm-runner module is removed
- no live imports or test references remain
- daemon async tests and full suite pass

## Status
Complete (2026-05-09).

Notes:
- Removed `src/toas/daemon/async_runner_warm.py` (retired post-489 artifact).
- Verified no live source/test imports remained.
- Historical spike artifacts may still mention the removed path, which is expected and non-runtime.

## Related
- 400 decomposition umbrella
- 489 daemon self-shell elimination
