# 544 Session Host Serve Entrypoint And Parent-Coupled Lifecycle

## Goal
Implement a real spawned session host process (`toas host serve`) with parent-coupled lifecycle semantics, replacing current process-marker fallback behavior.

## Why
`543` established host-state scaffolding and attach-or-start semantics at the record layer, but true ownership-first runtime behavior requires an actual child host process with explicit spawn/attach/teardown contracts.

## Scope
In scope:
- add CLI surface: `toas host serve`
- add session-host process manager seam for spawn/attach/terminate
- wire `ensure_session_host_record` to prefer real spawned host attach/start behavior
- parent-coupled lifecycle behavior:
  - child tied to invoking owner process/session
  - stale host detection + reattach/restart
- focused unit/system tests for start/attach/stale-recover/teardown behavior

Out of scope:
- full Vim transport migration (`542` follow-ons)
- complete daemon retirement

## Done When
- `toas host serve` exists and is callable
- session-host record points at real host process identity (not current-process fallback in primary path)
- attach/start/recover/teardown semantics are test-backed
- CLI async local path uses real host manager seam by default

## Related
- `543`
- `525`
- `541`
- `542`

## Progress
- 2026-05-19: added initial `toas host serve` CLI surface:
  - dispatch route: `toas host ...`
  - host command module: `src/toas/cli_host_commands.py`
  - serve loop delegates to runtime host-process helper
- 2026-05-19: added runtime host-process helper seam:
  - `src/toas/runtime/session_host_process.py`
  - spawn helper for child host process
  - owner-pid watchdog serve loop for parent-coupled termination
- 2026-05-19: wired session-host ensure path to prefer real spawned-host pid:
  - `ensure_session_host_record(...)` now provisions pid from spawn helper on create/replace
  - attach path still reuses non-stale records
- 2026-05-19: added focused tests for host command dispatch and host-state spawn semantics.
