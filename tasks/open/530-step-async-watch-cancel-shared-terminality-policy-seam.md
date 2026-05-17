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
