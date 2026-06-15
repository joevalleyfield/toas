Filed as: 260614-activity-live-durable-boundary
FKA:
AKA: activity durability boundary; live run state; stream replay facts; crash recovery activity state
Legacy index:

keywords: runtime, investigation, inception, architecture, activity, stream, durability, host

# Activity Live/Durable State Boundary

## Current Reality

Activity Lifecycle owns run ids, status, stream events, offsets, cancellation,
terminality, and replay windows. Some of that state is live process memory;
some is durable or replayable; some is projected through transports.

The architecture names this split, but does not yet inventory which activity
facts survive restart, reconnect, or crash.

Parent: `260614-architecture-follow-through-coordination`

## Desired Reality

Activity state should be classified as:

- live-only
- durable fact
- replayable event
- derived projection
- transport/client cursor

Host death, subscriber reconnect, cancellation, and terminal event replay should
all have clear state owners.

## Inception Note

This task is intentionally inception-only. It should become active when host,
reconnect, cancellation, or stream replay work needs a state table before code
changes.

## Known Facts

- Host liveness is not activity terminality.
- `run_done` is whole-run terminality; child lane done events are not.
- Active-run evidence can block backend stop/restart without transferring
  terminality ownership to backend lifecycle.

## Unknowns

- Which activity records should be durable beyond current run events.
- Which stream events are replayable after crash vs only reconnect.
- How cancellation convergence should be represented across restart.

## Evidence

Ready to leave inception when:

- a slice needs live/durable/replayable activity state classification
- the state table can name tests or traces for host death, reconnect, and
  cancellation convergence
