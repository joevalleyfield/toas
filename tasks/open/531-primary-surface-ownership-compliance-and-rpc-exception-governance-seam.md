# 531 Primary-Surface Ownership Compliance and RPC-Exception Governance Seam

## Goal
Define and implement explicit compliance checks for primary operator surfaces so ownership-first behavior is testable and any RPC-only exceptions are deliberate, documented, and removable.

## Why
`525` needs concrete guardrails after `526` inventory and `530` lifecycle hardening. Without explicit checks, RPC-era drift can re-enter primary paths (`step`, `step --async`, `watch`, `cancel`) silently.

## Scope
In scope:
- codify ownership-first expectations for primary surfaces
- add/adjust tests that assert local/operator-API-first execution behavior where available
- document any unavoidable RPC exceptions with rationale and removal path
- keep Vim-facing behavior parity (no regression in streaming/cancel surfaces)

Out of scope:
- daemon removal in one pass
- transport/protocol redesign
- broad frontend strategy changes (`490`)

## Done When
- primary-surface compliance checks exist and pass
- RPC-only exceptions are explicitly documented and justified
- roadmap reflects the new active `525` slice
- full suite passes

## Related
- `525` post-envelope runtime ownership and primary-path de-daemonization
- `526` RPC dependency inventory and exception governance
- `530` shared terminality policy seam
