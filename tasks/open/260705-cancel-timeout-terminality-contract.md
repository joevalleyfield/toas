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

So the question is no longer only whether the current timing feels bad. It is
also whether escalation from graceful cancellation to forced termination is
being owned by the right actor.

## Desired Reality

TOAS should have an explicit cancellation terminality contract:

- first cancel means "request cooperative shutdown"
- a run may truthfully remain `cancelling` while that graceful shutdown is in
  progress
- escalation to forced termination should be an explicit operator action
- the configured cancel timeout, if retained, should be a safety backstop
  rather than the main user-facing escalation path
- follow/watch/subscribe should not need timestamp fiction just to surface a
  useful terminal shape

## Code Reality Notes

Current code ownership already mostly matches the intended contract:

- `src/toas/runtime/async_activity_store_impl.py` owns the timeout-based
  transition from `cancelling` to `cancelled` in
  `_apply_cancellation_terminality_policy()`
- that policy only applies once `cancel_requested_at` exists and real elapsed
  time exceeds `TOAS_CANCEL_TERMINAL_TIMEOUT_S`
- `watch_async_step()` and `cancel_async_step()` both consult that policy
  before serving status, so transport consumers do not need to invent their own
  timeout semantics
- terminal event emission is still lifecycle-owned via
  `_finalize_terminal_event_once()` / `_finalize_terminal_state_once()`, which
  always emit `run_done` and may additionally emit `llm_done`

That means the main remaining mismatch is not just timeout tuning. It is that
the current fallback timeout still carries too much of the practical
user-facing escalation burden.

If the current `cancelling` interval is operationally untenable, the fix should
separate:

- lifecycle truth owned by Activity Lifecycle
- operator intent about graceful vs forceful cancellation
- final terminal cancellation owned by the lifecycle domain

## Intended Direction

The likely contract should become:

- first cancel request puts a running activity into `cancelling`
- a second cancel request against an already-`cancelling` activity escalates to
  forced termination
- an explicit future force-cancel command may exist, but "cancel twice means
  force" is a good first operator contract
- timeout-based terminalization remains available as a last-resort cleanup path
  if graceful cancellation never converges

This keeps escalation user-owned instead of timeout-owned.

## Scope

- define what states and events are allowed between `cancelling` and
  `cancelled` under the documented lifecycle ownership model
- define how operator escalation from graceful to forced cancellation is
  expressed
- reject fixes that make transport or host layers de facto owners of cancel
  terminality
- land only the smallest implementation and tests needed to preserve that
  contract

## Non-Goals

- broad redesign of async run storage
- backend process lifecycle redesign outside cancellation semantics
- opportunistic host-stream shape changes unrelated to cancel timeout meaning

## Likely Follow-Through

The strongest next closure for this task is probably a small contract-and-tests
slice:

- documenting graceful cancel, `cancelling`, and escalation semantics in the
  runtime docs and/or test language
- ensuring tests clearly distinguish `cancelling` grace-period truth from final
  `cancelled` terminality
- adding or tightening behavior around repeated cancel requests so escalation is
  explicit
- resisting any "faster cancel UX" fix that works by mutating lifecycle
  timestamps or silently bypassing lifecycle-owned terminal events

## Exit Evidence

- [ ] graceful cancel semantics are written down in task/docs/tests
- [ ] escalation from graceful to forced cancellation has an explicit operator
  contract
- [ ] timeout-based forced terminalization is clearly backstop behavior rather
  than primary UX
- [ ] watch/follow/subscribe tests cover the chosen behavior without semantic
  ambiguity
- [ ] the chosen behavior is attributable to the Activity Lifecycle owner
  rather than to transport or host-side semantic drift
