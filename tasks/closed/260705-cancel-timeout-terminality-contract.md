Filed as: 260705-cancel-timeout-terminality-contract
FKA:
AKA: cancel timeout semantics; cancellation terminality; async cancel grace period
Legacy index:

keywords: runtime, hardening, inception, contract, cancel, async, watch, stream

Parent: `260614-architecture-follow-through-coordination`
Related: `260614-model-backend-failure-handoff`; `260620-host-stdio-reasoning-terminality-ux`; `260705-host-subscribe-terminal-event-parity`; `260711-watch-chunk-contract-retirement`

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

## Spike Refinement

The spike clarified that "two-stage cancel" and "three possible mechanics" are
different concepts.

The operator experience should stay two-stage:

- stage 1: "I am suspicious / impatient / getting ready to cancel"
- stage 2: "no, really stop now"

But the runtime mechanisms underneath can differ by path:

- some paths have only a cooperative stop
- some paths have a cooperative stop and a harder stop
- some paths may eventually have a distinct pre-stop observation state plus a
  cooperative stop

So the design truth is not "cancel means the same mechanism everywhere." It is:

- the user gesture is always two-stage
- each runtime path truthfully maps those two stages onto the strongest
  mechanisms it actually has
- when a path does not really have three distinct capability tiers, one layer
  necessarily collapses
- we should not invent a third visible user-facing tier until reality actually
  presents one

For the current in-process LLM-close path, the spike suggests a different
two-stage interpretation from the current implementation:

- first cancel may want to mean "enter an observation / suspicion window"
  rather than "immediately send close"
- second cancel can mean "spend the real stop mechanism now"
- if no progress resumes during the observation window, the runtime can then
  spend the real stop mechanism and move on

That is a materially different contract from the current
"close first, then linger in `cancelling`" behavior, so it should be treated as
an explicit follow-on design/implementation slice rather than quietly folded
into timeout tuning.

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

## Progress Notes

- 2026-07-16: Claimed for the final parity-evidence slice. The target is one
  lifecycle-originated forced-cancel run observed consistently through poll,
  follow, and subscribe projection; no host-side terminal synthesis is in
  scope.
- repeated cancel now has a runtime-owned first implementation:
  `cancel_async_step()` treats a second cancel request against an already
  `cancelling` run as immediate forced termination
- that escalation path returns terminal `cancelled` status immediately instead
  of waiting for `TOAS_CANCEL_TERMINAL_TIMEOUT_S`
- timeout-based forced terminalization remains as fallback cleanup when no
  explicit operator escalation occurs
- the default fallback window is temporarily stretched to 10 seconds for spike
  observation so we can see whether in-process LLM cancellation converges on
  its own before the backstop fires
- spike observation suggests the in-process LLM path accepts close promptly but
  does not naturally unwind to terminality on its own; that points to a real
  runtime seam rather than mere timeout impatience
- first implementation work has now started on that path-specific split:
  - first cancel on a close-capable in-process LLM run records cancel intent
    without sending close immediately
  - if no LLM/projection byte activity arrives for 10 seconds after that
    intent, the runtime spends the real close mechanism
  - a second cancel request spends the close mechanism immediately
- spike design notes now distinguish:
  - the stable two-stage operator contract
  - the path-dependent collapse of underlying capability layers
- focused run-store and CLI tests now cover graceful first cancel and
  repeated-cancel escalation
- Vim local-host cancel now refuses to reconcile from stale non-terminal
  fallback frames; a host-backed regression test covers the
  `push_complete(reason=request_deadline)` case that previously could wipe out
  the live LLM turn during cancel reconciliation
- Vim terminal cancel/success reconciliation now consumes semantic
  `watch.events` directly during terminal backfill, so an empty legacy
  `chunk` no longer delays or prevents final assistant projection replacement
- follow-on task `260711-watch-chunk-contract-retirement` now captures the
  broader contract cleanup: this task should fix immediate cancel/finalization
  correctness bugs without trying to retire the legacy `watch.chunk` surface in
  the same change
- 2026-07-16: Completed the final parity-evidence slice. One lifecycle-owned
  forced cancel now has explicit coverage through poll, follow, and subscribe
  projection; existing host-bridge coverage proves it forwards `run_done`
  without fabricating terminal semantics.

## Exit Evidence

- [x] graceful cancel semantics are written down in task/docs/tests
- [x] escalation from graceful to forced cancellation has an explicit operator
  contract
- [x] timeout-based forced terminalization is clearly backstop behavior rather
  than primary UX
- [x] watch/follow/subscribe tests cover the chosen behavior without semantic
  ambiguity
- [x] the chosen behavior is attributable to the Activity Lifecycle owner;
  host/transport forward the lifecycle event and terminal status without
  inventing terminal semantics

## Completion Evidence

- [x] focused lifecycle, subscribe-parity, and host-bridge tests: `131 passed`
- [x] full suite: `2706 passed, 9 deselected`, `100.00%`
