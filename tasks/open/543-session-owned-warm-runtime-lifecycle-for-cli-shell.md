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
