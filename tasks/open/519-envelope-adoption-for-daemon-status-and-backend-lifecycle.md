# 519 Envelope Adoption For Daemon Status And Backend Lifecycle

## Objective
Extend envelope-aware adapterization to daemon status/back-end lifecycle response flows so non-watch operational responses share envelope-first compatibility semantics.

## Why
`518` covered async step/cancel lifecycle. Remaining daemon operational responses (`status`, `backend_*`) still rely on legacy-only payload semantics.

## Scope
- add envelope adapterization for `status` and one backend lifecycle response family
- keep existing legacy fields and CLI output unchanged
- add focused parity tests for envelope + legacy dual-shape behavior

## Out of Scope
- protocol big-bang replacement
- frontend UX changes
- daemon removal

## Done When
- `status` and at least one `backend_*` response include envelope-compatible payload
- consumers preserve output parity while tolerating envelope-first data
- tests cover both legacy and envelope paths

## Initial Slices
1. Inventory daemon status and backend lifecycle payload shapes.
2. Reuse/extend lifecycle envelope adapter for selected ops.
3. Wire daemon handlers and one consumer path with legacy parity retained.
4. Add targeted tests + full-suite validation.

## Related
- `515` protocol envelope v0 + durability map (closed)
- `517` transport abstraction (closed)
- `518` envelope adoption beyond watch for step/cancel (closed)
- `470` operator API seam migration
