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
- capability-first sequencing is respected:
  - local-host Vim happy path lands before additional exclusivity hardening beyond current baseline

## Status (2026-05-24)
- Primary objective is materially landed:
  - Vim default transport is now `local_host`
  - subscribe push lifecycle consumption is in place
  - key local-host parity regressions are covered
- This task now serves as a contributing parity ledger and close/reframe candidate under task `553`.

## Related
- `525`
- `527`
- `530`
- `533`

## Parity Matrix (2026-05-18)

| Surface | Current transport | Must-preserve behavior | Existing validation | Gap / follow-on |
| --- | --- | --- | --- | --- |
| `ToasStep` | RPC (`step_async` nonblocking path via helper) | starts run, renders stream incrementally, terminal convergence | `tests/vim/streaming_step_and_step_here_parity.vader`, `tests/vim/streaming_incremental_watch.vader` | add local-host channel mode coverage for same behavior |
| `ToasStepAsync` | RPC (`step_async`) | returns/stores `run_id`, watch-compatible | `tests/vim/streaming_incremental_watch.vader`, `tests/vim/streaming_dual_lane_parity.vader` | add explicit local/rpc mode parity assertions |
| `ToasWatch` poll | RPC (`watch`) | one-shot snapshot with cursor advance | `tests/vim/streaming_watch_poll_follow_parity.vader` | add local-host transport parity test |
| `ToasWatch --follow` | RPC (`watch`) | incremental updates until terminal state | `tests/vim/streaming_watch_poll_follow_parity.vader`, `tests/vim/streaming_cancel_terminality.vader` | add local-host transport parity test |
| `ToasCancel` | RPC (`cancel`) | transitions run into cancellation lifecycle and terminal convergence through watch | `tests/vim/streaming_cancel_command_parity.vader`, `tests/vim/streaming_cancel_terminality.vader` | add local/rpc parity assertions with bounded terminality |
| `ToasStepHere` | RPC (`step_async` start + watcher render) | preserves tail insertion and same stream shape as `ToasStep` | `tests/vim/streaming_step_and_step_here_parity.vader` | add local-host parity path |

## Intentional Divergence (Updated)
- CLI and Vim now both run local-first on primary paths by default.
- RPC remains an explicit compatibility opt-back lane and retirement-governance concern (`541`), not a primary default.

## Follow-on Slices Spawned From 542 (Historical)
1. Vim transport mode seam:
   - add explicit plugin transport mode selector (rpc vs local-host channel), default was RPC pre-cutover.
2. Vim local-host channel adapter:
   - implement request path for `step_async`/`watch`/`cancel` over persistent local runtime-host channel.
3. Vim parity tests by transport mode:
   - extend Vader/integration tests to run matrix rows in both transport modes.
4. Cutover slice:
   - make local-host channel default for Vim with explicit RPC opt-back.

## Reframed Direction (2026-05-21)
- Poll/follow semantics are now treated as compatibility surfaces, not the primary model.
- Primary direction is a canonical async event-stream protocol in host/runtime:
  - explicit subscribe/resume semantics by sequence/cursor
  - push-capable transport behavior for clients that support it
  - poll/follow adapters layered on top of the same core stream state machine
- Vim implementation work under `542` should prioritize transport/client adaptation onto the canonical stream model rather than growing separate watch semantics in plugin logic.

## Progress
- 2026-05-18: mapped Vim primary surfaces to current RPC callsites and existing Vader validation.
- 2026-05-18: documented intentional CLI/Vim divergence and explicit closure condition.
- 2026-05-21: capability-first bootstrap slice landed for Vim-managed host lifecycle:
  - Vim now proactively ensures an editor-owned `toas host serve` subprocess via `job_start` before `ToasStep` execution.
  - owner env (`TOAS_OWNER_KIND`, `TOAS_OWNER_ID`) is applied before host startup.
  - existing `VimLeavePre` owner-matched `toas host stop` cleanup remains in place.
  - this advances ownership coupling while preserving current RPC transport path for step/watch/cancel.
- 2026-05-21: transport-policy seam landed with RPC UI compatibility preserved:
  - added `g:toas_transport_mode` (default `rpc`)
  - added request wrapper seam so async start ops can be policy-shaped without changing render/watch UX
  - `rpc_local_backend` mode now injects `backend_mode=local` for async start ops (`step_async*`) while keeping existing progressive run-region streaming/watch/cancel behavior unchanged.
- 2026-05-21: protocol reframing agreed for next slice:
  - stop expanding parallel poll/follow behavior in Vim/plugin as a first-class path
  - move toward canonical host async stream core and consume it from Vim
  - retain existing poll/follow only as adapter/compatibility behavior until stream-first path is proven
- 2026-05-23: local-host follow watch now has push-first subscribe consumption path:
  - added local-host subscribe frame reader in plugin for `ToasWatch --follow` under `g:toas_transport_mode='local_host'`.
  - consumes `stream_subscribe` push lifecycle frames (`push_ack`/`push_event`/`push_complete`) and renders deltas immediately.
  - fallback to compatibility watch polling path is preserved when subscribe path is unavailable/fails.
  - added Vader coverage: `tests/vim/streaming_local_host_subscribe_follow.vader`.
  - validation:
    - `vim -Nu NONE -n -es -S tests/vim/run_vader.vim`: new local-host subscribe follow suite passes; one unrelated existing RPC suite failure remains (`streaming_dual_lane_parity.vader`: `rpc channel not open`).
- 2026-05-23: dual-lane parity coverage migrated from brittle RPC-only dependency to local-host push-first path:
  - removed `tests/vim/streaming_dual_lane_parity.vader` (RPC-channel brittle shape).
  - added `tests/vim/streaming_local_host_dual_lane_parity.vader` preserving behavioral intent (incremental dual-lane visibility/parity) under local-host push-follow semantics.
  - full Vader suite now passes cleanly with push-first local-host tests included.
- 2026-05-23: local-host cancel parity and terminality coverage added:
  - added `tests/vim/streaming_local_host_cancel_command_parity.vader`.
  - added `tests/vim/streaming_local_host_cancel_terminality.vader`.
  - these validate cancellation request path plus follow-watch terminal convergence under local-host push-follow semantics.
  - validation:
    - `vim -Nu NONE -n -es -S tests/vim/run_vader.vim` -> `18/18` suites, `57/57` assertions.
- 2026-05-23: watch-pump ingress/decode parity hardening for local-host follow streaming:
  - fixed decode gate so a single complete ingress line is decoded immediately (prevents idle-tick starvation when queue depth is exactly one).
  - hardened push-frame acceptance in decode for active-run context when `request_id`/`payload.run_id` are absent on frames.
  - added regression coverage:
    - `tests/vim/streaming_local_host_decode_accepts_push_without_ids.vader`
    - `tests/vim/streaming_local_host_single_line_decode_gate.vader`
- 2026-05-24: local-host subscribe host flush path fixed and Vim default cutover landed:
  - runtime host stdio `stream_subscribe` handling now emits push frames incrementally (`push_ack`/`push_event`/`push_complete`) as they are produced instead of buffering full-frame lists before response write.
  - preserves existing immediate-reject contract (`unknown_run_id` returns single `ok=false` frame without prior `push_ack`).
  - Vim plugin default transport flipped to `g:toas_transport_mode='local_host'` with explicit RPC opt-back still available via config.
  - targeted validation:
    - `uv run pytest tests/test_runtime_session_host_process.py -q --no-cov` (`24 passed`)

## Remaining Gaps (2026-05-24)

1. RPC compatibility lane remains intentionally available:
   - default is now local-host; keep RPC opt-back stable while collecting soak evidence.
2. Parity matrix execution by transport mode:
   - retain enough dual-lane checks to prevent compatibility drift while avoiding redundant suites.
3. Cutover soak evidence:
   - keep gathering evidence that local-host default remains stable for progressive rendering, run-id lifecycle behavior, and cancellation terminality.

## Execution Sequence Addendum (Historical, Completed)
1. Implement Vim local-host request adapter over persistent host channel for `step_async`/`cancel` plus stream consumption. Completed.
2. Map existing watch UX to stream-core adapter behavior (compatibility poll/follow preserved externally). Completed.
3. Run parity matrix test lanes in both `rpc` and local-host modes. Substantially completed; keep lean compatibility coverage.
4. Flip Vim default to local-host with explicit RPC opt-back only after parity evidence is green. Completed.
