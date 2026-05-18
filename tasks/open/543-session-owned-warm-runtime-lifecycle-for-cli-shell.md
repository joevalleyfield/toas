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

## Progress
- 2026-05-18: captured concrete shell/session-owned runtime lifecycle model and compatibility boundaries.
- 2026-05-18: decomposed implementation into executable slices for follow-through under `525`.
