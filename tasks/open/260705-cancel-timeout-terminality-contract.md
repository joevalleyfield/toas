Filed as: 260705-cancel-timeout-terminality-contract
FKA:
AKA: cancel timeout semantics; cancellation terminality; async cancel grace period
Legacy index:

keywords: runtime, hardening, inception, contract, cancel, async, watch, stream

Parent: `260614-architecture-follow-through-coordination`
Related: `260614-model-backend-failure-handoff`; `260620-host-stdio-reasoning-terminality-ux`; `260705-host-subscribe-terminal-event-parity`

# Cancel Timeout Terminality Contract

## Current Reality

The async run store currently has a meaningful distinction between:

- cancellation requested
- still cancelling within the configured grace window
- forced terminalization after `TOAS_CANCEL_TERMINAL_TIMEOUT_S`

That distinction is carrying real contract weight in `watch`, follow, and host
stream consumers. A peeled follow-on experiment tried to make cancelled runs
become terminal immediately by backdating `cancel_requested_at`, which would
collapse the grace-period contract into a synthetic timeout.

The architecture notes make the ownership pressure explicit:

- Activity Lifecycle owns status, stream events, cancellation state, and
  terminality
- subscriber cursors and transport envelopes are carriers, not terminality
  owners
- Session Host Supervision must not decide activity success, failure, or
  cancellation

So the question is not only whether the current timing feels bad. It is also
whether an operator-facing convergence problem is being "solved" by mutating
the lifecycle owner's semantic clock.

## Desired Reality

TOAS should have an explicit cancellation terminality contract:

- the configured cancel timeout should continue to mean real elapsed grace time
- follow/watch/subscribe should not need timestamp fiction just to surface a
  useful terminal shape
- if transport UX wants a more eager cancelled projection, that should be
  expressed deliberately rather than by mutating timeout semantics

If the current `cancelling` interval is operationally untenable, the fix should
separate:

- lifecycle truth owned by Activity Lifecycle
- subscriber or host-facing convergence signals owned by an explicit adapter
  layer
- final terminal cancellation owned by the lifecycle domain

## Scope

- define what states and events are allowed between `cancelling` and
  `cancelled` under the documented lifecycle ownership model
- decide whether operator-facing convergence needs a separate affordance from
  the store's timeout policy
- reject fixes that make transport or host layers de facto owners of cancel
  terminality
- land only the smallest implementation and tests needed to preserve that
  contract

## Non-Goals

- broad redesign of async run storage
- backend process lifecycle redesign outside cancellation semantics
- opportunistic host-stream shape changes unrelated to cancel timeout meaning

## Exit Evidence

- [ ] the intended cancel timeout semantics are written down in task/docs/tests
- [ ] cancellation no longer depends on backdating timestamps to achieve a
  desired terminal shape
- [ ] watch/follow/subscribe tests cover the chosen behavior without semantic
  ambiguity
- [ ] the chosen behavior is attributable to the Activity Lifecycle owner
  rather than to transport or host-side semantic drift
