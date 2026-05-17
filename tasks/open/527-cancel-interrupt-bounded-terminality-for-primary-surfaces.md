# 527 Cancel/Interrupt Bounded Terminality for Primary Surfaces

## Objective
Enforce bounded cancel/interruption completion for primary surfaces, with explicit escalation behavior when graceful cancellation does not complete.

## Why
Indefinite "cancelling" states (especially on Windows) are operationally unacceptable and undermine user trust.

## Scope
- define and enforce cancel-to-terminal bound (baseline: 10s)
- ensure `watch`/stream consumers observe deterministic terminal transition
- ensure escalation path triggers when graceful stop exceeds bound
- verify subsequent run cleanliness after forced termination path

## Done When
- tests assert bounded terminality across primary surfaces
- no known stuck-cancelling path remains in supported lanes
- targeted cross-platform validation is captured (including Windows where relevant)

## Related
- `525` umbrella
- `483`, `485`, `509`

## Progress
- added cancel-timeout baseline enforcement in daemon run-store:
  - `TOAS_CANCEL_TERMINAL_TIMEOUT_S` (default `10s`) defines the cancel-to-terminal bound.
  - `watch_async_step` now enforces forced-cancel escalation for overdue `cancelling` runs.
  - escalation path attempts hard kill and transitions lingering `cancelling` state to terminal `cancelled` with explicit error context.
- added focused tests in `tests/test_daemon_run_store.py`:
  - overdue `cancelling` run is force-terminated and reported terminal
  - pre-timeout `cancelling` run is not force-terminated
- added CLI async-consumer terminality assertions in `tests/test_cli_async_commands.py`:
  - cancel command prints terminal `cancelled` status when returned by daemon
  - follow-watch loop exits deterministically on `cancelled` terminal status after prior `cancelling`
- added daemon integration-level terminality assertions in `tests/test_daemon.py`:
  - `_watch_async_step` force-escalates overdue `cancelling` runs to terminal `cancelled`
  - `_watch_async_step` preserves non-terminal `cancelling` status before timeout threshold
