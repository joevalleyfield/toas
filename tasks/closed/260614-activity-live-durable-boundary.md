Filed as: 260614-activity-live-durable-boundary
FKA:
AKA: activity durability boundary; live run state; stream replay facts; crash recovery activity state
Legacy index:

keywords: runtime, investigation, historical, architecture, activity, stream, durability, host

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

## Investigation Note

This task left inception for a documentation/discovery slice. The goal was to
name current activity state ownership before changing host, reconnect,
cancellation, or stream replay behavior.

## Known Facts

- Host liveness is not activity terminality.
- `run_done` is whole-run terminality; child lane done events are not.
- Active-run evidence can block backend stop/restart without transferring
  terminality ownership to backend lifecycle.
- Current async run truth lives primarily in the in-memory `AsyncRun` map.
- Watch/subscribe replay is currently in-process replay from that run state,
  not crash-surviving activity recovery.
- Session host attachment/liveness has a workspace-local record, but that
  record must not become activity outcome truth.

## Unknowns

- Which activity records should be durable beyond current run events.
- Which stream events are replayable after crash vs only reconnect.
- How cancellation convergence should be represented across restart.

## Current State Ownership Table

| State item | Current home | Mutated by | Derived/read by | Cache/replay status | Across restart/reconnect/crash |
| --- | --- | --- | --- | --- | --- |
| Run registry | `runtime.async_activity_store_impl._RUNS` | activity creation/register paths | watch, cancel, active-run checks, adapters | live process memory | reconnect works only while the owning process keeps the run; crash loses registry |
| Run identity/workdir/mode | `AsyncRun.run_id`, `workdir`, `run_mode` | run creation | watch/subscribe responses, diagnostics, event writers | live metadata | lost with `_RUNS` unless separately recorded by activity events |
| Process handle | `AsyncRun.process` | worker/start path, cancellation/finalization paths | cancel and active-run logic | live-only handle | never durable; crash loses direct control |
| Run status | `AsyncRun.status` | worker/finalization/cancel policy | watch/subscribe, active-run blocking, lifecycle envelopes | live status with terminal events emitted into stream | reconnect reads current live status; crash recovery is not specified |
| Aggregate output bytes | `AsyncRun.output` | reader/worker stream capture | legacy watch `chunk`/`next_offset` consumers | live compatibility stream | reconnect can resume by offset while live; crash loses aggregate output unless represented elsewhere |
| Stream events | `AsyncRun.events` plus `event_seq` | `emit_stream_event` and finalization | watch/subscribe, envelope adapters, Vim/local-host streams | replayable in memory by `since_seq` | reconnect can replay while live; crash-surviving replay is not currently promised |
| Lane terminality | stream events with lane/phase, especially `run_done` | finalization/event emission | event classification, subscribe completion, renderers | event-derived | child-lane done survives only as in-memory event unless separately persisted; only `run_done` is whole-run terminality |
| Cancellation request | `cancel_requested`, `cancel_requested_at`, status `cancelling` | cancel command/policy | watch, active-run checks, finalization | live transition state | crash behavior is unspecified; no durable cancellation intent contract yet |
| Terminal record flags | `terminal_event_emitted`, `terminal_record_written` | finalization | idempotency guards | live idempotency state | crash may lose idempotency memory unless durable record write completed |
| Terminal durable event | graph write via terminal record writer | finalization path | durable history/audit | durable fact when written | survives restart after write; does not reconstruct full stream by itself |
| Stream policy flags | `stream_thinking_enabled`, `stream_prompt_progress_enabled` | run creation from effective policy | watch responses/rendering | live run metadata | lost with run unless policy can be recomputed; not current activity recovery state |
| Activity metadata | `AsyncRun.meta`, answer byte counters | stream emission/finalization | invariants such as missing answer payload and projection completion | live invariant support | crash loses invariant context unless reflected in durable records |
| Subscriber cursor | request `offset`/`since_seq`, `SubscribeReadState` | client/transport caller | subscribe runtime and watch responses | client/transport state | reconnect can resume while live if cursor is retained; crash loses server-side stream backing |
| Session host record | `.toas/session-host.json` | session host supervision | host reuse/stale detection | workspace-local attachment record | survives host process exit until stale/cleared; must not decide activity terminality |

## Boundary Findings

- Activity Lifecycle currently owns live run truth, stream replay while live,
  cancellation convergence while live, and terminal event emission.
- Durable State owns only facts that are explicitly written, such as terminal
  activity records. It does not currently own complete stream replay.
- Transport/subscribe clients own cursors (`offset`, `since_seq`) but not the
  meaning of terminality.
- Session Host Supervision owns attachment and liveness records; host loss is
  an input to future policy, not an activity result.
- The system has a strong reconnect contract for live process continuity and a
  deliberately weaker crash-recovery contract for activity streams.

## Candidate Decisions

- Treat in-memory stream replay as a live Activity Lifecycle feature, not as
  durable history.
- Treat crash-surviving activity replay as unresolved until a concrete product
  workflow needs it.
- Preserve the invariant that `run_done` is the only whole-run terminal stream
  event.
- Do not let host stale-record cleanup mark activities succeeded, failed, or
  cancelled.
- If cancellation must survive restart, define a durable cancellation-intent
  record before changing cancellation behavior.

## Resolution: 2026-06-15

- Classified the current activity state surface into live-only, durable,
  replayable-in-memory, derived, and transport/client cursor state.
- Promoted the key guidance into `docs/runtime-direction.md` and
  `docs/runtime-ownership.md`: watch/subscribe replay is a live reconnect
  feature, not a crash-surviving stream replay contract.
- Parked crash-surviving activity stream replay until a concrete workflow needs
  it.
- Preserved the host/activity invariant: session host liveness and stale host
  records must not decide activity success, failure, or cancellation.
- Preserved the terminality invariant: only `run_done` is whole-run terminality.

## Evidence

Done because:

- live, durable, replayable, derived, and transport cursor state are classified
- crash-surviving stream replay is explicitly parked rather than implied
- runtime ownership/direction docs now carry the boundary as contributor
  guidance
