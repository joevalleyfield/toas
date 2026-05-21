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
