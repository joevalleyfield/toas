# 368: Reduce async step latency via execution-lane ladder

- **Status**: Open

## Summary

The async path currently feels slower than direct synchronous RPC even when placeholder projection appears promptly. Current evidence indicates the dominant cost is the `step_async` request path and process startup overhead, not initial watch timer delay.

The runtime should treat async as the primary lane and degrade through explicit fallbacks while preserving non-zero capability.

## Action

- Implement explicit async lane order and fallback policy: `default -> warm -> cold -> synchronous`.
- Define lane semantics:
  - `default`: asynchronous messaging as primary UX path.
  - `warm`: pre-started worker/subprocess path to avoid per-step spawn cost.
  - `cold`: on-demand subprocess path for compatibility/isolation fallback.
  - `synchronous`: final deterministic fallback.
- Add health-driven demotion/promotion rules and record fallback reason when lane changes.
- Preserve semantic parity across lanes (history records, result projection, cancellation behavior, error shaping).
- Improve observability:
  - selected lane per run
  - fallback/demotion cause
  - timing breakdown (step_async request latency, spawn/setup time, first-watch latency, completion time)
- Treat watch interval tuning as secondary optimization after lane causality and fallback correctness are established.

## Progress

- Added first-pass observability in Vim plugin:
  - lane and fallback metadata (`g:toas_last_step_lane`, `g:toas_last_step_fallback_reason`)
  - timing telemetry (`g:toas_last_step_timing`) with `step_async_rpc_ms`, `watch_timer_ms`, `first_watch_ms`, `total_ms`
  - debug commands: `:ToasLane`, `:ToasFallback`, `:ToasTiming`
- Added lane-selector and demotion state machine in Vim step path:
  - configured lane order defaults to `default -> warm -> cold -> synchronous`
  - per-lane failure counters with cooldown-based temporary demotion
  - fallback reason chain retained in `g:toas_last_step_fallback_reason`
  - lane health inspection via `:ToasLaneHealth`
- Added daemon routing stub for warm lane op (`step_async_warm`) to preserve protocol compatibility while warm backend internals are implemented.
- Implemented first warm backend internals in daemon:
  - `step_async_warm` now executes `cli.run_step_local` in a background worker thread without subprocess spawn
  - preserves async run/watch contract (`run_id`, `watch` status/chunk flow, run records)
  - warm cancel behavior remains cooperative (no hard preemption equivalent to subprocess terminate)
- Rewired control plane so messaging default can run warm-first:
  - daemon `step_async` now maps to warm executor
  - explicit cold subprocess lane remains available as `step_async_cold`
  - Vim cold fallback path now requests `step_async_cold`
- Fixed warm-path streaming parity:
  - warm worker now applies `TOAS_STREAM_STDOUT`, `TOAS_STREAM_THINKING`, and `TOAS_STREAM_PROMPT_PROGRESS` env toggles from runtime policy before running `cli.run_step_local`
- Fixed warm-path incremental stream behavior:
  - warm worker now forwards stdout writes directly into async run buffers/events during execution (instead of capture-at-end buffering), restoring prompt progress, thinking deltas, and streamed output in Vim watch UI
- Fixed async failure visibility in Vim sentinel rendering:
  - when daemon reports terminal `error` with no streamed chunk, watcher now injects `[run failed] ...`/`[run cancelled] ...` text into the run block instead of showing an empty failed sentinel
- Restored prompt-count projection from streamed text path in Vim:
  - watcher now derives `progress:` display from carriage-return-updated run text (`prompt n/m ...`) when present, in addition to explicit daemon `prompt_progress` events
- Adjusted watch polling profile for short-run responsiveness:
  - first 5 polls at `20ms`
  - subsequent polls at `100ms`
  - preserves lower steady-state polling cost while improving first-result pickup for short runs
- Added per-run async stream-policy telemetry and Vim projection:
  - daemon `step_async*` start/watch payloads now include `stream_policy` (`thinking`, `prompt_progress`)
  - Vim run sentinel now shows `stream: thinking=on|off prompt_progress=on|off` for immediate lane/config diagnostics
