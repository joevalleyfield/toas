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
