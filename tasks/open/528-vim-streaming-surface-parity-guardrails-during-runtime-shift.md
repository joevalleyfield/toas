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
