## Goal

Make multi-operation proposals execute as ordered queues with automatic handling of mixed authorization outcomes, minimizing manual extraction/re-run loops.

## Why Now

Strict all-or-nothing behavior is a show-stopper for real operator flows. Ordered sequences should remain sequences while exposing explicit controls at blocked boundaries.

## Scope

- introduce durable queue state for multi-op execution attempts
- per-op lifecycle states (e.g., pending, ran, blocked, failed, skipped, canceled)
- auto-run allowed ops in sequence
- pause on blocked op and support continuation controls:
  - approve (once)
  - skip
  - cancel remainder
  - resume
- continue queue automatically after decision

## Intended Behavior

- partial sequences do not require manual decomposition
- operator can resolve blocked boundaries in place
- execution order is preserved

## Constraints

- preserve deterministic order and durable audit trail
- avoid introducing hidden autonomous execution loops

## Done When

- mixed allow/deny sequences run with queue controls instead of manual reassembly
- queue decisions and outcomes are durably visible
- tests cover approve/skip/cancel/resume flows

## Progress

- 2026-04-24: First execution-queue slice landed for replay multi-op execution.
- Added durable `execution_queue` records in history with queue id/status payload snapshots.
- Added replay queue controls: `--resume`, `--approve`, `--skip`, `--cancel`.
- Replay multi-op execution now runs in-order until blocked/failure boundary, persists queue state, and surfaces continuation commands.
- Added coverage for queue parser/handler branches and durable queue side-effect writing.
- 2026-04-24: Completion coverage slice landed.
- Added explicit continuation-flow tests for `--skip`, `--cancel`, and terminal handling after cancellation.
- Verified blocked-boundary approval/skip/cancel/resume flows are queue-backed with durable `execution_queue` updates and status transitions.

## Status

Closed 2026-04-24.
