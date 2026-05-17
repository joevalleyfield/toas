# 537 Local-First Cancellation And Interruption Hardening

## Goal
Harden bounded cancellation/interrupt completion under local-first async behavior and preserve Vim/watch UX parity.

## Why
Defaulting to local async ownership shifts cancellation pressure to local paths; bounded terminality and recovery guarantees must remain explicit and reliable.

## Scope
In scope:
- local-first cancel timeout/escalation behavior checks
- interrupt/recovery behavior assertions for local mode
- Vim/watch parity safeguards for local-first execution

Out of scope:
- frontend UX redesign
- non-async session semantics changes

## Done When
- local-first cancel/interrupt behavior is bounded and test-backed
- no Vim/watch regression in lifecycle UX contracts
- full suite passes

## Related
- `525` umbrella
- `530`, `534`
