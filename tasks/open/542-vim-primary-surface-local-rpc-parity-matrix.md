# 542 Vim Primary-Surface Local/RPC Parity Matrix

## Goal
Establish explicit behavior parity and intentional divergence checks for Vim primary surfaces across local-first and RPC compatibility modes.

## Why
Vim is a must-preserve surface under `525`; parity needs to be provable and intentionally scoped, especially around streaming and cancellation terminality.

## Scope
In scope:
- `ToasStep`
- `ToasStepAsync`
- `ToasWatch` (poll and `--follow`)
- `ToasCancel`
- `ToasStepHere`
- local-first vs RPC mode behavior expectations
- focused integration/system assertions where meaningful

Out of scope:
- broad Vim UX redesign

## Done When
- parity matrix is documented and test-backed for critical behaviors
- intentional divergences are explicit and justified
- cancellation/terminality behavior is validated in both modes

## Related
- `525`
- `527`
- `530`
- `533`
