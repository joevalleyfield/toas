## Goal

Expand RPC operation coverage and harden daemon/client recovery behavior for daily use.

## Scope

- add RPC parity for high-use operations (`jump`, `head`, `heads`, `prompt`, `prompts`)
- add protocol/version compatibility checks between client and daemon
- handle stale endpoints, daemon mismatch, and timeout/retry behaviors
- document operational recovery flow

## Intended Inputs

- daemon/CLI RPC path from `223`
- current non-step CLI command behavior
- transport adapter failure characteristics

## Intended Outputs

- expanded RPC operation set with parity to selected CLI commands
- robust client error handling and recovery strategy
- tests for mismatch/timeouts/stale endpoint scenarios

## Constraints

- parity operations must preserve existing command semantics
- recovery paths must fail clearly without silent data loss
- compatibility checks must be deterministic

## Non-Goals

- no new high-level product features
- no broad protocol redesign once 220 contract is established

## Done When

- selected non-step commands work over RPC with expected behavior
- failure/recovery behavior is predictable and tested
- version/protocol mismatch guidance is user-visible and documented
