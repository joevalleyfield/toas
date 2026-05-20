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
