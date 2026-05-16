# 526 Primary-Path RPC Dependency Inventory and Exception Governance

## Objective
Produce a concrete inventory of RPC/daemon dependencies across `step`/`step --async`/`watch`/`cancel` (including Vim surfaces) and define what qualifies as a temporary RPC-only exception.

## Why
"Remove from primary paths unless no alternative exists" is directional but needs explicit inventory and governance to be enforceable.

## Scope
- map current path selection and fallback behavior for primary CLI and Vim surfaces
- identify where RPC/daemon dependency is still primary vs fallback
- define exception record shape for RPC-only cases (reason, evidence, removal intent)
- classify each dependency as removable now, removable later, or currently unavoidable

## Done When
- dependency matrix exists for all primary surfaces
- exception rule is concretely documented and testable
- follow-on implementation slices are opened from matrix findings

## Related
- `525` umbrella
- `470` operator API seam

## Inventory Matrix (Current State)

Legend:
- primary path = default path used in normal operation
- fallback path = backup path used on failure/unavailability
- classification = `removable_now` | `removable_later` | `currently_unavoidable`

### CLI surfaces

1. `toas step`
- primary path:
  - local when `TOAS_RPC_MODE=off`
  - RPC when mode is `auto|on` and endpoint is available (`_rpc_stdout("step")`)
- fallback path:
  - in `auto`, RPC request failure falls back to local
- dependency status:
  - RPC is not strictly required for correctness; local path is complete
- classification:
  - `removable_now` for primary-path policy (can force local-first without capability loss)

2. `toas step --async`
- primary path:
  - RPC-only (`run_step_async` requires rpc enabled and calls `step_async`)
- fallback path:
  - none
- dependency status:
  - async run-id/start semantics are daemon-backed in current CLI shape
- classification:
  - `removable_later`

3. `toas watch`
- primary path:
  - RPC-only (`run_watch` requires rpc enabled and calls `watch`)
- fallback path:
  - none
- dependency status:
  - watch stream contract currently served by daemon run-store
- classification:
  - `removable_later`

4. `toas cancel`
- primary path:
  - RPC-only (`run_cancel` requires rpc enabled and calls `cancel`)
- fallback path:
  - none
- dependency status:
  - cancel lifecycle state and process control currently daemon-run backed
- classification:
  - `removable_later`

### Vim surfaces (`vim/plugin/toas.vim`)

1. `ToasStep`
- primary path:
  - nonblocking RPC async lane (`step_async` + timer `watch`) by default
- fallback path:
  - warm lane (`step_async_warm`), then cold RPC collect, then synchronous RPC, then CLI `toas step`
- dependency status:
  - primary user experience is RPC/daemon-first
- classification:
  - `removable_later` (parity-critical; tied to 528 guardrails)

2. `ToasStepAsync`
- primary path:
  - RPC `step_async`
- fallback path:
  - CLI `toas step --async`
- dependency status:
  - both primary and fallback are daemon/RPC-dependent behaviorally
- classification:
  - `removable_later`

3. `ToasWatch` (`poll` / `--follow`)
- primary path:
  - RPC `watch`
- fallback path:
  - none
- dependency status:
  - fully daemon/RPC-backed today
- classification:
  - `removable_later`

4. `ToasCancel`
- primary path:
  - RPC `cancel`
- fallback path:
  - none
- dependency status:
  - fully daemon/RPC-backed today
- classification:
  - `removable_later`

5. `ToasStepHere`
- primary path:
  - nonblocking RPC async (`step_async` + watcher), fallback to RPC collect/sync, then CLI `toas step`
- dependency status:
  - Vim-only convenience flow remains RPC-first in normal operation
- classification:
  - `removable_later` (must preserve behavior under 528)

## RPC-Only Exception Governance

### Exception qualification rule
An RPC dependency qualifies as a temporary exception only when:
1. no non-RPC implementation exists that preserves required behavior, and
2. removing RPC immediately would cause loss of required primary-surface capability.

### Exception record schema
For each approved exception, record:
- `surface`: command/flow name
- `why_rpc_only`: concrete blocker description
- `evidence`: code-path and/or test evidence demonstrating no equivalent non-RPC path
- `user_impact_if_removed_now`: explicit regression statement
- `removal_target`: linked follow-on task id
- `review_checkpoint`: when to reevaluate (task milestone/date trigger)

### Testable policy checks
- every RPC-dependent primary surface must be either:
  - marked `removable_now`, or
  - listed as an exception record with `removal_target`
- no untracked RPC dependency in primary surface matrix

## Findings Summary

- CLI `step` already supports non-RPC primary operation; it is the first candidate for policy tightening.
- CLI async lifecycle (`step --async`/`watch`/`cancel`) is still hard RPC-dependent.
- Vim operational surfaces are currently RPC-first and require parity-protected migration sequencing.
- No surface is currently classified `currently_unavoidable`; all current RPC dependencies are treated as removable with staged follow-through.

## Follow-on Mapping

- `527` owns bounded cancel/interruption terminality enforcement and escalation semantics.
- `528` owns Vim parity guardrails while RPC-first surfaces are migrated.
- additional slices should target:
  - CLI async lifecycle non-RPC parity path introduction
  - Vim lane-order/policy update after non-RPC async lifecycle parity exists

## Progress

- completed first-pass primary-surface dependency inventory across CLI and Vim
- defined explicit RPC-only exception qualification and record schema
- classified each primary surface dependency as removable now/later
- linked findings to active follow-ons under `525` (`527`, `528`)
