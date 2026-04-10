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
