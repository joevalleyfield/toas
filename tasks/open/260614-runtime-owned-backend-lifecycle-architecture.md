Filed as: 260614-runtime-owned-backend-lifecycle-architecture
FKA:
AKA: backend lifecycle ownership; runtime-owned managed backend lifecycle; backend daemon/RPC exception follow-up
Legacy index:

keywords: runtime, architecture, active, backend, lifecycle, ownership, daemon, rpc, 525

# Runtime-Owned Backend Lifecycle Architecture

## Current Reality

Backend lifecycle commands (`backend_status`, `backend_start`, `backend_stop`, `backend_restart`) remain daemon/RPC-oriented. The daemon transport assembly injects backend lifecycle handlers into runtime-owned request dispatch, while stdio host request handling intentionally builds a runtime-local handler with backend lifecycle unavailable.

`525` closed primary-path ownership for `step`, `step --async`, `watch`, and `cancel`, but explicitly left backend lifecycle as a daemon/RPC exception.

## Desired Reality

Backend lifecycle ownership should be an explicit architecture decision rather than an exception hidden inside closed runtime-ownership work. If managed backend lifecycle is part of the operator's primary local runtime, its ownership should move to a runtime-owned boundary with daemon/RPC acting as transport or compatibility.

## Gap Analysis

The current split is coherent for closing `525`, but it leaves the highest-leverage remaining runtime ownership question unresolved:

- who owns managed backend process lifecycle?
- should stdio host/local runtime be able to start/stop/status backends?
- should daemon lifecycle handlers become adapters over runtime-owned process lifecycle?
- what are the ownership, teardown, health-check, and cross-session semantics?

## Known Facts

- `525` is closed and should not be reopened for broad backend lifecycle work.
- `toas backend ...` currently remains RPC/daemon-oriented.
- Runtime request dispatch and handler policy are now runtime-owned.
- Daemon assembly still injects backend lifecycle handlers.
- `400` can carry mechanical decomposition, but the backend lifecycle ownership decision is architectural.

## Unknowns

- Whether backend lifecycle should be session-owned, workspace-owned, or daemon/service-owned.
- Whether local stdio host should own managed backend lifecycle or only observe it.
- Whether backend start/stop should be available when daemon RPC mode is off.
- What compatibility surface is required for existing daemon-backed workflows.

## Risks

- Moving lifecycle ownership prematurely may create process leaks or cross-session interference.
- Leaving ownership daemon-only may keep the runtime architecture balanced on an exception in the highest-leverage remaining area.
- Treating this as mere decomposition could miss policy decisions around process ownership, health checks, and teardown.

## Decisions

- Track this as a new focused architecture task rather than unfinished `525` scope.
- Do not implement in this task until ownership semantics and transport compatibility requirements are explicit.
- Keep current daemon/RPC backend lifecycle behavior stable while evaluating the move.

## Next Actions

- [ ] Inventory current backend lifecycle call paths, state ownership, and tests.
- [ ] Decide intended ownership model: daemon/service-owned, workspace runtime-owned, or session-host-owned.
- [ ] Define compatibility requirements for `toas backend ...`, daemon RPC, and local-host/stdout users.
- [ ] Split implementation subtasks only after the ownership model is chosen.
