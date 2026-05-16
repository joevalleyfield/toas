# 523 Envelope Adoption For Daemon Dispatch Contract Docs And Tests

## Objective
Consolidate daemon op response contract expectations (legacy + envelope) in docs/tests so future protocol shifts are deliberate and auditable.

## Scope
- codify per-op response expectations in docs/protocol notes
- add/adjust dispatch-level tests to assert dual-shape compatibility
- avoid behavior changes; documentation and contract coverage only

## Done When
- protocol docs include daemon op response dual-shape contract
- dispatch tests assert envelope-compatible additions without legacy regression

## Related
- `515`, `517`, `518`, `519`, `520`

## Progress
- documented daemon op dual-shape response contract in:
  - `docs/protocol-notes.md`
- added/updated dispatch-adjacent tests asserting legacy+envelope compatibility for:
  - `status`
  - `backend_status`
  - backend lifecycle mutation handlers
- validated with full suite:
  - `uv run pytest -q -n 14`
