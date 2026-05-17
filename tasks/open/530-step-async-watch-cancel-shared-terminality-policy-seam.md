# 530 Step Async / Watch / Cancel Shared Terminality Policy Seam

## Goal
Create one authoritative terminality-policy seam for async run lifecycle (`step --async`, `watch`, `cancel`) so bounded cancellation behavior is consistent and testable across primary paths.

## Why
`525` requires explicit, bounded cancellation/terminal semantics. Current behavior is correct in many cases but spread across multiple run-store paths, which increases drift risk and makes future `step` ownership work harder.

## Scope
In scope:
- centralize cancellation-timeout/forced-cancel terminal transition policy in `daemon/run_store.py`
- route `watch` and `cancel` code paths through that shared seam
- preserve existing protocol/envelope response shape
- add/adjust tests for:
  - graceful cancel transition
  - forced-cancel escalation after timeout
  - exactly-once terminal event semantics
  - subsequent-run cleanliness after forced cancel

Out of scope:
- major transport/protocol redesign
- broad CLI UX changes
- daemon removal (tracked under `525`)

## Done When
- one shared policy seam governs forced-cancel terminality checks
- all async lifecycle paths consume that seam where applicable
- full test suite passes with no contract regressions
- roadmap reflects this slice as active under `525`

## Progress
- opened and implemented first seam slice:
  - introduced shared cancellation terminality policy seam in `daemon/run_store.py`:
    - `_apply_cancellation_terminality_policy(run)`
  - routed both `watch_async_step()` and `cancel_async_step()` through that shared seam
  - kept lifecycle/protocol response shape stable
  - added targeted coverage proving `cancel` also enforces timed-out cancellation terminal transition:
    - `tests/test_daemon_run_store.py::test_cancel_async_step_applies_timed_out_cancellation_policy_before_status_check`
  - validated with:
    - `uv run pytest -q tests/test_daemon_run_store.py --no-cov`
    - `uv run pytest -q -n 14`
- implemented second seam slice:
  - introduced `_finalize_terminal_event_once(run)` as the single terminal-event emission seam in `daemon/run_store.py`
  - `finalize_terminal_state()` now delegates terminal event emission to that seam and remains authoritative for durable terminal record writing
  - forced-cancel path in `_apply_cancellation_terminality_policy()` now reuses the same seam (no duplicated terminal-event construction logic)
  - added interleaving test to verify exactly-once terminal event + exactly-once terminal write when forced-cancel finalizes before later finalize calls:
    - `tests/test_daemon_run_store.py::test_forced_cancel_then_finalize_terminal_state_keeps_single_done_event_and_single_write`
  - validated with:
    - `uv run pytest -q tests/test_daemon_run_store.py --no-cov`
    - `uv run pytest -q -n 14`
- implemented third seam slice (lifecycle-boundary tightening):
  - introduced explicit terminal record seam in `daemon/run_store.py`:
    - `_finalize_terminal_record_once(run, write_run_event_fn=...)`
  - introduced explicit combined finalization seam:
    - `_finalize_terminal_state_once(run, write_run_event_fn=...)`
  - `finalize_terminal_state()` now delegates through the combined seam (single authoritative path for event+record finalization)
  - added interleaving guard test for potential double-write concern:
    - `tests/test_daemon_run_store.py::test_finalize_terminal_state_interleaving_with_pre_emitted_done_event_writes_once`
  - revalidated no duplicate terminal side effects in forced-cancel interleavings:
    - `tests/test_daemon_run_store.py::test_forced_cancel_then_finalize_terminal_state_keeps_single_done_event_and_single_write`
  - validated with:
    - `uv run pytest -q tests/test_daemon_run_store.py tests/test_daemon_async_runner.py --no-cov`
    - `uv run pytest -q -n 14` (rerun green after one unrelated flaky pass)
