Filed as: 260614-runtime-owned-backend-lifecycle-architecture
FKA:
AKA: backend lifecycle ownership; runtime-owned managed backend lifecycle; backend daemon/RPC exception follow-up
Legacy index:

keywords: runtime, architecture, active, backend, lifecycle, ownership, daemon, rpc, 525

# Runtime-Owned Backend Lifecycle Architecture

## Current Reality

Backend lifecycle commands (`backend_status`, `backend_start`, `backend_stop`, `backend_restart`) remain daemon/RPC-oriented. The daemon transport assembly injects backend lifecycle handlers into runtime-owned request dispatch, while stdio host request handling intentionally builds a runtime-local handler with backend lifecycle unavailable.

`525` closed primary-path ownership for `step`, `step --async`, `watch`, and `cancel`, but explicitly left backend lifecycle as a daemon/RPC exception.

Current call path:

- `toas backend ...` dispatches through `cli_dispatch` into `cli.run_backend`.
- `cli.run_backend` delegates to `cli_async_commands.run_backend`, which always requires daemon RPC mode before sending `backend_status`, `backend_start`, `backend_stop`, or `backend_restart`.
- Runtime request handler assembly knows the backend lifecycle operations, but only as injected functions.
- Daemon assembly wires those injected functions to daemon-owned managed backend state.
- `daemon.backend_lifecycle` owns the actual process slot, lock, health check, start/stop/restart mechanics, and backend lifecycle event writes.
- Local stdio host request handling deliberately installs unavailable backend lifecycle handlers, so backend lifecycle is not part of the daemon-free local host surface today.

## Desired Reality

Backend lifecycle ownership should be an explicit architecture decision rather than an exception hidden inside closed runtime-ownership work. If managed backend lifecycle is part of the operator's primary local runtime, its ownership should move to a runtime-owned boundary with daemon/RPC acting as transport or compatibility.

The selected target is a runtime-owned, workspace-scoped managed backend lifecycle core. Daemon RPC and local/stdio host surfaces should call that core as adapters; the daemon should not be the source of truth for managed backend process ownership.

## Gap Analysis

The current split is coherent for closing `525`, but it leaves the highest-leverage remaining runtime ownership question unresolved:

- who owns managed backend process lifecycle?
- should stdio host/local runtime be able to start/stop/status backends?
- should daemon lifecycle handlers become adapters over runtime-owned process lifecycle?
- what are the ownership, teardown, health-check, and cross-session semantics?

Discovery read:

- Backend lifecycle is not just request-handler assembly cleanup. The command surface is user-visible and currently fails when RPC mode is off.
- The current managed process state is a single daemon-process global (`_MANAGED_BACKEND`), even though payloads carry `workdir`. That is workable for daemon-era behavior but too implicit for runtime ownership.
- Async local execution already has session-host identity and owner-coupled lifecycle semantics. Backend process lifecycle is different: it should be shared at workspace/backend-config scope, not owned by a single editor session host.
- The durable `backend_lifecycle` records are already graph-owned facts. Moving process ownership into runtime should preserve those records and keep daemon envelope/legacy response shapes stable.

Worst current sins to address in the implementation phase:

- daemon is the only process owner for a primary operator capability
- process state is singleton rather than explicitly workspace/config scoped
- `toas backend ...` cannot operate in `TOAS_RPC_MODE=off`
- local request handler has backend lifecycle operations registered but intentionally unavailable
- tests validate daemon internals more directly than the desired runtime boundary

## Known Facts

- `525` is closed and should not be reopened for broad backend lifecycle work.
- `toas backend ...` currently remains RPC/daemon-oriented.
- Runtime request dispatch and handler policy are now runtime-owned.
- Daemon assembly still injects backend lifecycle handlers.
- `400` can carry mechanical decomposition, but the backend lifecycle ownership decision is architectural.
- The compatibility response contract for backend lifecycle operations is already dual-shape: legacy top-level fields plus envelope fields.

## Unknowns

- Whether workspace-owned state should be keyed only by normalized workdir or by normalized workdir plus backend configuration identity.
- Whether local stdio host should expose mutating backend lifecycle immediately or first expose status/observation only.
- How far teardown should go when an editor-owned session host exits if a managed backend is shared by shell and editor surfaces.
- Whether existing daemon-backed workflows rely on singleton cross-workspace behavior.

## Risks

- Moving lifecycle ownership prematurely may create process leaks or cross-session interference.
- Leaving ownership daemon-only may keep the runtime architecture balanced on an exception in the highest-leverage remaining area.
- Treating this as mere decomposition could miss policy decisions around process ownership, health checks, and teardown.

## Decisions

- Track this as a new focused architecture task rather than unfinished `525` scope.
- Keep current daemon/RPC backend lifecycle behavior stable while evaluating the move.
- Move toward a runtime-owned workspace lifecycle core, with daemon RPC and local/stdio host paths as adapters over that core.
- Do not make backend lifecycle session-host-owned. Session hosts may observe or invoke lifecycle operations, but shared managed backend state should not disappear merely because one editor/session host exits.
- Preserve current backend lifecycle response compatibility: top-level legacy fields remain, envelope payload remains preferred for envelope-aware consumers.
- Preserve active-run blocking semantics for stop/restart, but move the active-run query dependency into the runtime-owned boundary rather than leaving it daemon-specific.

## Implementation Path

1. ~~Extract `daemon.backend_lifecycle` process mechanics into `runtime.backend_lifecycle`, replacing the daemon singleton with an explicit workspace-scoped state object or registry.~~ Done: `src/toas/runtime/model_backend_lifecycle.py` introduces `ModelBackendLifecycle` with injected ports (`spawn_fn`, `health_probe_fn`, `event_writer_fn`, `active_runs_fn`, `sleep_fn`, `time_fn`), explicit `_BackendProcessState`, `BackendLifecycleRequest`/`BackendLifecycleResult` dataclasses, and `make_graph_event_writer`/`request_from_payload`/`result_to_dict` adapter helpers. Uses `logging.getLogger(__name__)` — first module in the stdlib logging adoption. Domain contract tests in `tests/test_model_backend_lifecycle.py` (34 tests, 100% coverage on new module). Daemon `backend_lifecycle.py` and its singleton are untouched; daemon rewiring is step 2.
2. Rewire daemon backend lifecycle facades to delegate to the runtime core while preserving existing response shapes and direct daemon tests as compatibility coverage.
3. Add a local `toas backend ...` path in `cli_async_commands.run_backend` for `TOAS_RPC_MODE=off` / local mode, keeping RPC available as compatibility transport.
4. Decide whether stdio host should enable all backend lifecycle ops immediately or stage status first; if staged, make unavailable mutations explicit in task-space.
5. Retarget tests from daemon internals to runtime lifecycle ownership, leaving daemon facade tests focused on adapter parity.

## Compatibility Requirements

- `toas backend start|stop|restart|status` output lines stay stable: `backend mode=<mode> status=<status> [pid=<pid>]` plus optional `detail: ...`.
- Daemon RPC operations continue to accept the current backend payload contract.
- Daemon RPC operations continue to return legacy top-level fields plus lifecycle/status envelopes.
- `backend.mode = external` remains non-mutating and reports/skips as it does today.
- Managed-local start still requires a non-empty command and honors configured `cwd`, `env`, `health_url`, and `health_timeout_s`.
- Stop/restart remain blocked while async runs are active.
- Backend lifecycle event records remain durable graph facts written under the requested workdir.

## Next Actions

- [x] Inventory current backend lifecycle call paths, state ownership, and tests.
- [x] Decide intended ownership model: daemon/service-owned, workspace runtime-owned, or session-host-owned.
- [x] Define compatibility requirements for `toas backend ...`, daemon RPC, and local-host/stdout users.
- [x] Split or implement the first slice: runtime lifecycle core extraction with daemon adapter parity.
- [ ] Rewire daemon facades to delegate to `ModelBackendLifecycle` (step 2).
- [ ] Add local `toas backend ...` path for `TOAS_RPC_MODE=off` (step 3).
- [ ] Retarget existing daemon backend lifecycle tests toward adapter parity (step 5).
