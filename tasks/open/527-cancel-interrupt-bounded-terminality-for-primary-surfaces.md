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
