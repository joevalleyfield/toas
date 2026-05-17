# 538 Local-First Acceptance Scenario Validation

## Goal
Add acceptance-level validation that exercises local-first async lifecycle behavior end-to-end and confirms operator-facing contracts.

## Why
Unit/integration assertions are in place (`533`), but we need a durable acceptance signal that local-first mode behaves correctly in real workflow shape.

## Scope
In scope:
- acceptance scenario variant for local async backend mode
- verify operator-visible lifecycle contract (`run_id/status`, watch progression, terminality)
- keep runtime deterministic enough for CI use

Out of scope:
- broad acceptance harness redesign
- unrelated workflow scenario expansion

## Done When
- at least one local-first acceptance scenario passes reliably
- scenario is documented and reproducible
- full suite remains green

## Progress
- Added `@S4 @local_first_async_lifecycle` scenario to `tests/acceptance/features/complete_change_request.feature`.
- Added step coverage in `tests/acceptance/steps/test_complete_change_request_steps.py` that drives:
  - local backend selection (`TOAS_ASYNC_BACKEND_MODE=local`, `TOAS_RPC_MODE=off`)
  - `step --async` lifecycle start contract (`run_id/status`)
  - `watch` progression contract (`running` poll signal + streamed chunk visibility + terminal follow behavior)
- Verified acceptance file passes under acceptance marker:
  - `uv run pytest tests/acceptance/steps/test_complete_change_request_steps.py -m acceptance --no-cov -q`
- Remaining blocker before close: unrelated `tests/test_cli_smoke.py` failures in full suite (`ModuleNotFoundError: No module named 'toas'` from `uv run toas ...` in scratch workspace).

## Transition Note
- Local async backend lifecycle (`step --async` -> `watch`/`cancel`) is process-bound today when `TOAS_ASYNC_BACKEND_MODE=local` because run state lives in in-memory `run_store`.
- Consequence for acceptance shape:
  - lifecycle continuity assertions for local mode must execute within a single process (in-process command handlers), or
  - use RPC-backed mode when multi-process CLI hops are intentional.
- This is a migration seam under `525`/`532`/`538`: subprocess command parity is not equivalent to local-backend lifecycle continuity until runtime-owned persistent state spans those command boundaries.

## Related
- `525` umbrella
- `533`, `534`, `537`
