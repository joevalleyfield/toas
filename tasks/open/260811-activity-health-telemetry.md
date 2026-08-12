Filed as: 260811-activity-health-telemetry
FKA:
AKA: bounded activity health; stall detection telemetry; run health snapshot; transport stall summary
Legacy index:

keywords: runtime, transport, vim, async, stream, telemetry, logging, defaults, inception, performance

Parent: `260614-architecture-follow-through-coordination`
Depends on:
Blocks:
Blocked by:
Related: `260602-transport-equivalence-certification`; `260530-shell-lane-spawn-semantics`

# Bounded Activity Health Telemetry For Stall Detection

Define and implement a low-volume activity-health signal that makes runtime and
transport stalls diagnosable without using always-on wire logs as the normal
observability surface.

## Current Reality

Host I/O and Vim local-host paths write verbose wire/trace records by default.
Those records mix ordinary frame traffic with error-shaped messages and have no
shared severity contract. The stdlib logging threshold does not govern these
files.

The activity protocol already has ephemeral `telemetry` and `heartbeat` kinds.
The activity lifecycle/store owns live run state, while Vim already tracks
last activity, no-progress ticks, frame/byte counts, and decode/apply timing.
Subscribe also has timeout and no-progress outcomes.

## Desired Reality

Normal operation exposes a bounded, structured health summary for active runs
and completed stall/failure investigations. It should answer whether a run is
progressing, where it is spending time, and whether transport or consumer
backlog is accumulating, without persisting every frame.

Wire payload tracing remains an explicit opt-in forensic facility. Ordinary
health telemetry has a clear severity/status model and does not depend on
parsing human-oriented log files.

## Gap Analysis

- No shared health snapshot schema spans host, activity lifecycle, and Vim.
- Existing counters are mostly local implementation state or are serialized
  through verbose trace files.
- Host diagnostic event names and Vim message prefixes imply severity but do not
  provide machine-readable severity, filtering, or aggregation semantics.
- The efficient sampling/update policy is not yet defined.

## Existing Seam Disposition

The first survey gives the following provisional adapt/ignore/replace matrix:

| Existing seam | Disposition | Rationale |
| --- | --- | --- |
| `event_classification.py` `telemetry` / `status` kinds | **Adapt** | Reuse the existing ephemeral event taxonomy, but define a bounded health payload and severity/state vocabulary instead of inventing a logging channel. |
| `event_classification.py` `heartbeat` kind | **Ignore for first slice** | A heartbeat proves liveness/keepalive, not useful progress or stall cause. Keep its protocol meaning separate from health assessment. |
| `AsyncRun` timestamps, status, `meta`, answer-byte count, and `emit_stream_event()` | **Adapt** | Activity Lifecycle already sees the authoritative producer-side transitions and can update counters/snapshots without serializing every event. Avoid growing `meta` into an untyped second schema. |
| `stream_subscribe_runtime.py` cursor and completion results | **Adapt** | `idle_timeout`, `request_deadline`, event sequence, and offsets are valuable consumer/transport observations, but subscribe must not decide activity health or terminality. |
| `session_host_stream_bridge.py` `stream_subscribe_*` timing and no-event observations | **Adapt** | Preserve these as transport-edge inputs to a bounded snapshot; move their regular aggregation out of debug-log parsing. |
| `stream_pacing_summary.py` | **Replace input path; adapt statistics** | Its percentile/batch ideas are useful, but it currently reconstructs pacing from stdlib log text. Feed equivalent bounded records or snapshots directly instead. |
| `cancel_latency_summary.py` | **Adapt later / keep separate initially** | Cancellation latency is a useful health dimension, but it has a distinct lifecycle and existing offline summary. Do not make it a prerequisite for the first stall snapshot. |
| Vim `s:toas_watch_debug_update()`, run metrics, phase timings, and lane health | **Adapt as consumer observations** | These already measure decode/apply/render pressure and repeated lane failures. They should map to the shared contract without becoming producer truth. |
| Vim and host wire-log writers | **Ignore for regular health; retain opt-in** | They are high-volume forensic traces with no severity contract. They should not be sampled, parsed, or made authoritative by the health path. |
| `error_log()` and terminal error records | **Adapt as severe evidence** | Keep fatal/terminal error reporting separate from health telemetry, while correlating it by run/activity id when a health snapshot transitions to failed/critical. |
| Lifecycle/watch/envelope adapters | **Adapt after contract** | They are the natural exposure points for a snapshot, but only after Activity Lifecycle defines its meaning and update cadence. |

## Known Facts / Assumptions / Unknowns

Known facts:

- Activity lifecycle owns run status, stream events, cancellation, and
  terminality; host liveness is a separate concern.
- `telemetry` and `heartbeat` are already described as ephemeral protocol
  concepts.
- Vim has enough local state to detect idle windows, decode pressure, and
  repeated resubscription without reading its wire log.

Assumptions:

- Health snapshots should be live/ephemeral by default, with only selected
  stall/failure summaries becoming durable or operator-visible.
- A monotonic clock and bounded counters are sufficient for first-pass stall
  detection; raw payload retention is not required.

Unknowns:

- Thresholds for warning/critical stall states across LLM, tool, projection,
  and transport phases.
- Whether a later push surface or durable activity record is needed after the
  read-oriented snapshot proves useful.

## Proposed V0 Contract

The first implementation should add an optional `health` object to the
existing run-scoped watch/stream-read response. It is a snapshot, not a new
event in the activity stream, so observing health does not advance `next_seq`
or create per-frame traffic.

The producer-owned core shape is:

```json
{
  "schema": "activity_health.v0",
  "state": "progressing",
  "severity": "info",
  "phase": "llm_answer",
  "reason": "recent_activity",
  "observed_at": "2026-08-11T12:00:00Z",
  "last_activity_at": "2026-08-11T11:59:58Z",
  "idle_ms": 2000,
  "event_seq": 42,
  "events_seen": 42,
  "output_bytes": 8192,
  "answer_bytes": 4096
}
```

Contract rules:

- `schema` is required and versioned.
- `state` is one of `progressing`, `idle`, `backlogged`, `transport_lost`,
  or `terminal`. `transport_lost` is valid only when an observer has supplied
  transport evidence; the producer must not infer it from a quiet interval.
- `severity` is one of `info`, `warning`, or `critical`; terminal success is
  `info`, terminal failure is `critical`, cancellation is `info` unless it
  crosses a cancellation-health threshold, and a thresholded stall or
  transport loss is `warning` until an explicit failure exists.
- `phase` is the latest authoritative lane/phase when known, otherwise
  `unknown`; the adapter must not invent a producer phase from a timeout.
- `reason` is a bounded machine-readable discriminator, initially
  `recent_activity`, `no_progress`, `consumer_backlog`, `subscribe_timeout`,
  `host_unavailable`, `terminal_success`, `terminal_failure`, or `cancelled`.
- `idle_ms` measures time since producer activity meaningful to the current
  phase. It is not the same as time since the last heartbeat or polling tick.
- `event_seq`, `events_seen`, `output_bytes`, and `answer_bytes` are monotonic
  producer counters for the activity lifetime. `event_seq` is the replay
  high-water mark; `events_seen` counts events retained/observed by the
  activity store.
- Timestamps are observational and may be absent only when no activity has
  occurred; counters remain bounded integers and raw payloads are excluded.

Transport/client adapters may add an `observer` object outside the core shape:

```json
{
  "observer": {
    "kind": "vim",
    "delivery_idle_ms": 1200,
    "pending_events": 0,
    "decode_ms": 3,
    "apply_ms": 5,
    "render_ms": 2,
    "resubscribe_count": 0
  }
}
```

`observer` is not producer truth and is omitted when the surface cannot
measure it. Host and Vim adapters may use different observer fields. An
observer may contribute `transport_lost`, `consumer_backlog`, and related
reasons, but must not rewrite producer phase or terminality.

V0 exposure is deliberately read-oriented:

- include `health` in `watch`/`stream_read` snapshots;
- expose the same snapshot through the host/envelope adapter where a status
  response already exists;
- let Vim render or inspect the snapshot through its existing debug/status
  surface;
- defer standalone `telemetry` events and durable health records until a
  consumer needs push updates or post-crash retention.

Update policy is event-boundary and read-boundary based, not timer- or
frame-log based. Recompute/update in memory on meaningful activity, terminal
transition, cancellation transition, and health reads. Do not emit or append a
record merely because a polling tick occurred. A future push surface may emit
only state transitions, threshold crossings, terminality, and a bounded
periodic refresh.

## Investigations

- Inventory activity-store, stream-subscribe, host, and Vim state already
  available for aggregation.
- Compare producer-side and consumer-side stall indicators so a quiet model,
  blocked host, slow Vim pump, and lost subscriber are distinguishable.
- Define a minimal versioned health snapshot and severity/state vocabulary.
- Measure update and serialization cost under high-frame-rate streams.
- Confirm that the existing `stream_pacing_summary` and Vim timing data can be
  reproduced from in-memory counters before retiring their log-derived input.

## Transformations

- Add a bounded health-state seam owned by Activity Lifecycle or its adjacent
  runtime health module.
- Emit or expose aggregate telemetry only on state changes, threshold
  crossings, terminality, or a bounded periodic cadence.
- Add transport adapters for host and Vim without making either adapter the
  semantic owner of run health.
- Make wire tracing and verbose per-frame diagnostics opt-in and clearly
  separate from health telemetry.
- Retain or replace existing offline summaries only after equivalent structured
  aggregate evidence is available.

## Evidence

- 2026-08-11: Implemented producer-owned `activity_health.v0` snapshots in
  existing watch/stream-read responses. The snapshot is read-only, does not
  advance `next_seq`, and does not append stream events or wire-log records.
- 2026-08-11: `tests/test_runtime_activity_health.py` reaches 100% targeted
  coverage; affected activity-store, watch, and subscribe-parity tests pass.
- 2026-08-11: Added producer-idle threshold evaluation. Inactivity below 5
  seconds remains informational; inactivity at or above 5 seconds becomes
  `idle/warning`, including activity that has gone quiet after progress.
- 2026-08-12: Added bounded Vim observer metrics to the existing watch-debug
  state and `ToasWatchHealth` inspection command: transport state, delivery
  idle time, pending events, decode/apply/render timings, and resubscribe count.
  These remain consumer observations and do not rewrite producer health.
- 2026-08-12: The focused Vim dual-consumer contract test passes with 15/15
  assertions covering the observer shape. The full Vader suite still reaches
  its pre-existing terminal projection catch-up failure and was not used as a
  passing signal for this slice.
- Current tests prove health state distinguishes progress, idle/no-progress,
  and terminal success/failure/cancellation; adapter tests remain needed for
  backlog and transport loss.
- Tests prove normal operation does not append one file record per frame.
- Host and Vim adapters expose equivalent health meaning for the same activity
  state.
- A focused stall reproduction produces a bounded actionable summary without
  enabling wire tracing.
- Existing protocol stdout purity, activity terminality, and transport parity
  contracts remain unchanged.

## Decisions

- Treat this as an activity-health/telemetry task, not a logging-format task.
- Keep raw wire logs as opt-in debugging evidence rather than the primary
  regular diagnostic channel.
- Use the existing watch/stream-read snapshot as the first exposure surface;
  do not add a new activity event kind for V0.
- Keep producer health and consumer/transport observations in separate core
  and `observer` sections.
- Make health reads observational: they must not advance event cursors or
  append durable records.
- Use a 5-second producer-idle warning threshold for V0; keep phase-specific
  and critical thresholds out of this slice until stall evidence exists.

## Open Fronts

- Validate the proposed state/reason/severity vocabulary against real stall
  reproductions.
- Decide the exact threshold defaults for `idle`, `backlogged`, and
  `transport_lost`.
- Revisit the 5-second default with real stall reproductions and phase-specific
  evidence.
- Add host-side observer measurements and validate Vim observer classifications
  against real backlog/transport-loss reproductions.
- Decide which health facts, if any, become durable records.
- Establish default thresholds and retention limits.

## Next Actions

1. Trace the current activity-store and subscribe state into a metric ownership
   matrix.
2. Compare the existing `stream_pacing_summary`, cancellation summary, and Vim
   timing surfaces against that contract.
3. Open narrow implementation follow-ons for adapter observer measurements and
   threshold policy once real stall reproductions establish their evidence.
