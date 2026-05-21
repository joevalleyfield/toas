# 543 Session-Owned Warm Runtime Lifecycle For CLI Shell

## Goal
Define and implement shell-owned warm runtime lifecycle behavior for plain CLI usage, aligned with ownership-tree semantics.

## Why
Primary-path de-daemonization requires runtime lifetime to track operator ownership. For plain CLI usage, coupling to shell/session lifetime provides the intended warm path without ambient daemon assumptions.

## Scope
In scope:
- lifecycle model for runtime ownership in plain CLI shell usage
- start/attach/teardown behavior and cancellation interaction
- compatibility boundaries with existing daemon and Vim paths
- tests and documentation for lifecycle expectations

Out of scope:
- complete frontend unification
- unrelated orchestration work (`488`)

## Done When
- shell/session-owned warm lifecycle is implemented for CLI-owned path
- cancellation and teardown semantics are explicit and test-backed
- compatibility boundaries are documented
- capability-first sequencing is preserved:
  - lifecycle capability/reuse works end-to-end before incremental restriction tightening

## Related
- `525`
- `470`
- `489`
- `509`

## Lifecycle Model (2026-05-18)

### Ownership
- A CLI shell session owns a persistent TOAS runtime host instance.
- Operator commands attach to that owned host by default for async/local lifecycle surfaces.
- Ownership is explicit and bounded to user/session context (no ambient machine-global assumption).

### Start / Attach
- First qualifying command starts host if absent.
- Subsequent commands in same shell/session attach to existing host.
- Host identity is surfaced in diagnostics (session/host identifier) for observability.

### Teardown
- Graceful teardown on explicit stop/exit path.
- Crash/abandon recovery on next attach with stale-host detection.
- No requirement for daemon-global lifecycle for primary CLI ownership path.

### Cancellation Interaction
- `cancel` targets activities owned by the same runtime host/session.
- Cancellation follows bounded terminality policy (graceful then escalation).
- Watch consumers converge on terminal status deterministically.

## Compatibility Boundaries
- Vim and external clients may continue using compatibility transport while this lands.
- RPC remains explicit opt-back where required, but not primary lifecycle model.
- Daemon/listener paths remain secondary compatibility surfaces.

## Implementation Slices Spawned From 543
1. Host identity/state seam:
   - define host identity record + attach/start resolution logic for CLI-owned sessions.
2. CLI attach/start integration:
   - wire primary async commands to resolve/use session-owned host lifecycle.
3. Teardown/recovery semantics:
   - explicit stale-host detection, cleanup, and reattach behavior.
4. Lifecycle diagnostics + docs:
   - expose host/session ownership status and boundaries in operator-facing output/docs.
5. Tests:
   - unit/system assertions for start/attach/teardown/recovery/cancel interactions.

## Protocol Alignment Note (2026-05-21)
- Lifecycle ownership work under `543` now explicitly aligns with a stream-first async protocol direction:
  - host/runtime should expose one canonical async event stream contract for run progress/terminality
  - compatibility watch `poll`/`follow` surfaces should be adapters over that stream core, not parallel independently-evolved semantics
  - this reduces lifecycle + transport divergence across CLI/Vim and simplifies ownership-coupled host behavior

## Progress
- 2026-05-18: captured concrete shell/session-owned runtime lifecycle model and compatibility boundaries.
- 2026-05-18: decomposed implementation into executable slices for follow-through under `525`.
- 2026-05-18: implemented slice 1 foundation seam:
  - added `src/toas/runtime/session_host_state.py` for host identity/state persistence
  - record path: `.toas/session-host.json`
  - added stale-host detection helpers (host/owner pid liveness + time-regression guard)
  - added focused seam tests in `tests/test_runtime_session_host_state.py`
- 2026-05-18: implemented slice 2 attach/start integration seam in async CLI path:
  - extended async deps with `resolve_session_host_record`
  - `run_step_async`/`run_cancel` now resolve active non-stale session host records
  - host identity is included in diagnostics (`host=<host_id>`) when active host state exists
  - payload includes `session_host_id` hint when host state is present
  - covered with focused CLI async tests
- 2026-05-18: implemented slice 3 stale-host cleanup semantics:
  - stale resolved host records now trigger cleanup via `clear_session_host_record`
  - cleanup occurs before falling back to hostless lifecycle path
  - added focused stale-record cleanup test coverage in async CLI tests
- 2026-05-19: implemented slice 4 diagnostics/docs alignment:
  - updated README and capabilities docs to reflect local-first async lifecycle defaults
  - documented explicit RPC opt-back (`TOAS_ASYNC_BACKEND_MODE=rpc`)
  - documented backend/host diagnostics (`backend=<mode>`, optional `host=<host_id>`)
- 2026-05-19: started host start/attach orchestration seam:
  - added `ensure_session_host_record` async dependency hook
  - local backend path now resolves active host, otherwise attempts ensure (attach-or-start seam)
  - ensured host id is threaded into payload/diagnostics when provisioned through ensure path
  - added focused tests for ensure-path behavior and dependency wiring
- 2026-05-19: implemented baseline attach-or-start host state provisioning:
  - added `ensure_session_host_record(...)` in `runtime/session_host_state.py`
  - behavior:
    - reuse existing non-stale host record (attach)
    - replace stale/missing host record with generated host identity (start baseline)
  - wired `build_deps()` to use provisioning path by default (pid/owner_pid = current process baseline)
  - added focused tests for create/reuse/replace host-record paths
- 2026-05-21: implemented host stdio JSON command surface seam for compatibility transport:
  - `toas host serve` now accepts `--stdio-json` and sets `TOAS_HOST_STDIO_JSON=1`
  - `runtime/session_host_process.py` now supports stdio JSON request/response serving mode
  - stdio handler reuses RPC request validation/response shaping and daemon dispatch path (`step_async/watch/cancel`)
  - added focused tests for CLI serve option parsing/env behavior and stdio JSON request handler success/error mapping
  - validation:
    - focused: `./.codex-local/bin/uvt run pytest -q tests/test_cli_host_commands.py tests/test_runtime_session_host_state.py tests/test_runtime_session_host_process.py --no-cov` (pass)
    - full suite: `./.codex-local/bin/uvt run pytest` (sandbox AF_UNIX bind permission failures in `tests/test_rpc_unix.py`, unrelated to this slice)
