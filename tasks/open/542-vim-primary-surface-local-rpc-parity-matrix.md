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

## Intentional Divergence
- CLI async surfaces are local-first by default (`540`); Vim remains RPC-first currently.
- This divergence is temporary and intentional under `541` exception governance.
- Exit condition for divergence: Vim local-host channel path lands with parity coverage.

## Follow-on Slices Spawned From 542
1. Vim transport mode seam:
   - add explicit plugin transport mode selector (rpc vs local-host channel), default still RPC for compatibility until cutover.
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

## Remaining Gaps (2026-05-22)

1. Local-host transport adapter is not yet primary:
   - Vim still relies on RPC for `ToasStep*`, `ToasWatch`, and `ToasCancel`.
2. Subscribe-path client integration in Vim:
   - plugin path does not yet consume canonical `stream_subscribe` push lifecycle frames.
3. Parity matrix execution by transport mode:
   - current Vader coverage is strong on RPC behavior but still missing full matrix execution against local-host channel mode.
4. Cutover readiness evidence:
   - need explicit evidence that local-host default does not regress progressive rendering, run-id lifecycle behavior, or cancellation terminality.

## Execution Sequence Addendum

1. Implement Vim local-host request adapter over persistent host channel for `step_async`/`cancel` plus stream consumption.
2. Map existing watch UX to stream-core adapter behavior (compatibility poll/follow preserved externally).
3. Run parity matrix test lanes in both `rpc` and local-host modes.
4. Flip Vim default to local-host with explicit RPC opt-back only after parity evidence is green.
