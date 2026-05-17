# 528 Vim Streaming Surface Parity Guardrails During Runtime Shift

## Objective
Protect existing Vim streaming/operator behaviors while runtime ownership and primary-path transport semantics evolve.

## Why
Runtime architecture shifts are high risk for Vim integration regressions, especially around async/watch/cancel interplay and run-region rendering.

## Scope
- preserve behavior for:
  - `ToasStep`
  - `ToasStepAsync`
  - `ToasWatch` (poll + `--follow`)
  - `ToasCancel`
  - `ToasStepHere`
- add/strengthen integration assertions around streaming updates, terminal-state handling, and run-region lifecycle
- ensure parity checks run alongside primary-path migration slices

## Done When
- explicit parity coverage exists for all listed Vim surfaces
- runtime shifts under `525` do not regress listed Vim behaviors

## Related
- `525` umbrella
- `483` streaming fixes

## Progress
- added dedicated `ToasCancel` parity regression in `tests/vim/streaming_cancel_command_parity.vader`:
  - verifies Vim issues one cancel RPC request for active run and `ToasWatch --follow` converges to terminal `cancelled`.
  - keeps cancel/watch interplay behavior explicit at the Vim surface while runtime ownership shifts continue.
- added `ToasStep`/`ToasStepHere` parity regression in `tests/vim/streaming_step_and_step_here_parity.vader`:
  - verifies both surfaces start async runs via the same step-async path and preserve step-here tail reattachment behavior.
  - confirms step-here watch completion still projects assistant terminal content.
- added `ToasWatch` poll/follow mode parity regression in `tests/vim/streaming_watch_poll_follow_parity.vader`:
  - verifies default `ToasWatch` sends `mode=poll` and `ToasWatch --follow` sends `mode=follow`.
  - verifies both mode paths surface expected chunks in Vim buffer projection.
