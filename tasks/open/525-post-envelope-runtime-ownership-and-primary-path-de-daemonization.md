# 525 Post-Envelope Runtime Ownership and Primary-Path De-Daemonization
keywords: runtime, implementation, active, compatibility, async, transport, watch, cancel

## Objective
Define and execute the next runtime architecture arc after envelope adoption so primary operator flows are ownership-coupled and user-surface-first, with daemon/listener behavior secondary.

## Why
Envelope compatibility landed (`515`-`524`), but primary-path behavior still carries daemon/RPC-era assumptions. We need a master plan that re-centers execution on explicit lifecycle ownership while preserving current Vim streaming surfaces and improving cancel/interruption reliability.

## Scope
In scope:
- primary-path surfaces: `step`, `step --async`, `watch`, `cancel`
- Vim must-preserve surfaces:
  - `ToasStep`
  - `ToasStepAsync`
  - `ToasWatch` (poll + `--follow`)
  - `ToasCancel`
  - `ToasStepHere`
- bounded cancellation/interruption completion semantics for primary paths
- explicit RPC exception governance for cases where no non-RPC path is feasible
- decomposition into focused implementation slices and roadmap stitching

Out of scope:
- complete removal of all daemon/listener capabilities in one pass
- full frontend strategy resolution (`490` remains separate)
- broad prompt/protocol model-alignment work outside runtime ownership/cancel semantics

## Requirements Baseline
- Direction: hierarchical lifecycle and user-owned surfaces are primary.
- RPC policy: remove RPC from primary execution paths unless a flow cannot be accomplished another way.
- sequencing policy (capability-first):
  - implement end-to-end happy-path capability first
  - add restrictions/guardrails only when backed by reproduced failure, cross-platform incompatibility, or data-loss/corruption risk
  - prefer minimum defensive branching necessary to keep primary surfaces reliable
- Cancellation reliability baseline:
  - terminal status must be reached within 10 seconds of cancel request
  - if graceful cancellation does not complete, escalation path is required
  - threshold may be revised if implementation evidence proves mismatch
- Verification posture:
  - favor fast/minimal automated behavior assertions
  - use heavier runtime probe/log workflows selectively for gap closure and debugability proof

## Done When
- umbrella decomposition slices are opened and sequenced
- each primary surface has explicit compliance checks for ownership-first and cancellation bounds
- Vim listed surfaces retain functional streaming behavior (no regression)
- RPC-only exceptions (if any) are explicitly documented with rationale and follow-on removal path
- roadmap and related umbrella links (`470`, `400`, `466`) reflect new architecture lane cleanly

## Related
- `470` operator API seam and CLI-thin migration
- `400` decomposition umbrella
- `466` config sequencing/diagnostics clarity
- `483`, `485`, `509`, `517`-`524` runtime/protocol predecessor work
