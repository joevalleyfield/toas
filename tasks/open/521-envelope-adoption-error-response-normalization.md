# 521 Envelope Adoption For Error Response Normalization

## Objective
Normalize envelope-compatible projection for operation error responses so op-level failures have consistent envelope/legacy dual-shape semantics where applicable.

## Scope
- inventory daemon op error payload shapes
- add adapter seam for eligible error responses without breaking protocol wrapper (`ok=false/error`)
- keep legacy error contract intact

## Done When
- selected error paths have deterministic envelope-compatible payload additions
- no RPC protocol regressions
- tests assert compatibility for both success/error flows

## Related
- `515` envelope semantics
- `517` transport seam
- `520` backend mutation response adoption
