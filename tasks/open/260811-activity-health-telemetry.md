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

- Which layer should calculate each metric and which layer should own severity
  classification.
- Whether snapshots should be exposed through status/subscribe responses,
  explicit inspection commands, durable activity facts, or a combination.
- Thresholds for warning/critical stall states across LLM, tool, projection,
  and transport phases.
- Whether the first regular surface should be a status snapshot, a telemetry
  event, or a compact subscribe completion payload.

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

- Tests prove health state distinguishes progress, idle/no-progress, backlog,
  transport loss, and terminal failure.
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

## Open Fronts

- Choose the first operator-facing inspection surface.
- Decide which health facts, if any, become durable records.
- Establish default thresholds and retention limits.

## Next Actions

1. Trace the current activity-store and subscribe state into a metric ownership
   matrix.
2. Draft the minimal health snapshot and threshold/state contract.
3. Compare the existing `stream_pacing_summary`, cancellation summary, and Vim
   timing surfaces against that contract.
4. Open narrow implementation follow-ons once the contract has a clear owner
   and test story.
