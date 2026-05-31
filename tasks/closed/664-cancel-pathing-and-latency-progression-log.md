# 661 Cancel Pathing And Latency Progression Log

## Goal
Capture the end-to-end progression of cancel behavior investigation and fixes across Vim plugin, stdio host transport, runtime cancellation policy, and integration tests.

## Why
Conversation compaction split the implementation history across turns. This log preserves the technical sequence, decisions, and resulting behavior so future work does not need to reconstruct context from scattered commits/logs.

## Timeline
- 2026-05-30: Verified nested log path issue (`.toas/.toas/...`) and confirmed missing/ambiguous evidence came from reading the wrong log root.
- 2026-05-30: Added explicit Vim cancel instrumentation in `vim/plugin/toas.vim`:
  - `CANCEL_ENTRY`
  - `CANCEL_SELECTED`
  - `CANCEL_RESPONSE`
  - `CANCEL_ERROR`
  - forced immediate log flush on cancel paths.
- 2026-05-30: Confirmed transport-level cancel dispatch was real (`op:"cancel"` observed in wire logs).
- 2026-05-30: Fixed Vim workdir normalization ambiguity and nested-path behavior:
  - robust `.toas` root stripping in workdir normalization
  - normalization on all workdir resolution branches (global override, `.toas` probe, config probe, cwd fallback)
  - self-healing writeback of polluted `g:toas_workdir` values.
- 2026-05-30: Added raw/effective workdir visibility to cancel logs to prove payload correctness.
- 2026-05-30: Added cancellation latency instrumentation and summary plumbing in runtime/CLI surfaces.
- 2026-05-30: Expanded integration coverage for stdio-host + llm-like stand-in/subprocess cancel flow and mid-pipeline realness.
- 2026-05-30: Tuned cancellation policy to keep lifecycle shape (`cancelling -> cancelled`) with short grace default.
- 2026-05-30: Set `TOAS_CANCEL_TERMINAL_TIMEOUT_S` default to `0.5` seconds.

## Key Findings
- Cancel failures were initially obscured by nested log-root pathing and subscribe retry cadence noise.
- Vim plugin was dispatching cancel correctly once instrumented.
- Host/runtime were receiving cancel; user-visible delay was often grace/terminalization policy, not dispatch failure.
- "Never saw cancelling" reports can be true at UI level even when protocol-level `cancelling` exists briefly.

## Final Policy Shape
- `cancel` call returns `status=cancelling` immediately.
- runtime attempts graceful terminate first.
- if still not terminal after timeout window, runtime force-terminalizes (`cancelled`) and emits terminal stream state.
- default timeout window: `0.5s` (`TOAS_CANCEL_TERMINAL_TIMEOUT_S` override remains supported).

## Evidence Patterns
Graceful cancellation signature:
- cancel response payload `status=cancelling`
- terminal `llm_done` payload `status=cancelled`
- no forced-timeout error text.

Forced cancellation signature:
- cancel response payload `status=cancelling`
- terminal `llm_done` payload `status=cancelled`
- terminal error includes `cancel timed out; forced termination`.

## Scope Artifacts
Primary touched surfaces in this progression included:
- `vim/plugin/toas.vim`
- `src/toas/runtime/async_activity_store_impl.py`
- `src/toas/runtime/session_host_process.py`
- `src/toas/runtime/async_step_runtime_worker.py`
- `src/toas/runtime/cancel_latency_summary.py`
- `src/toas/cli.py`
- `src/toas/cli_dispatch.py`
- `tests/test_runtime_host_stdio_llm_standin_integration.py`
- `tests/test_cli_demo_async_client.py`
- `tests/test_daemon_run_store.py`
- `tests/test_runtime_async_activity_store_api.py`
- `tests/test_daemon.py`

## Done When
- historical sequence is preserved in one task artifact
- linked from active local-first async policy task for discoverability
- no behavior changes are required by this log itself
