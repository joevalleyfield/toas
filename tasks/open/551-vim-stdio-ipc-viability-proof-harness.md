# 551 Vim Stdio IPC Viability Proof Harness

## Goal
Prove, with deterministic evidence, whether Vim<->child-process stdio can satisfy TOAS protocol invariants at acceptable interactive latency.

## Why
Current failures are ambiguous between transport, framing, extraction/projection, and render scheduling. We need a contract-first benchmark path that isolates IPC mechanics from full TOAS semantics.

## Scope
In scope:
- deterministic stdio fixture producer/consumer path
- contract assertions for:
  - newline-delimited JSON frame boundaries
  - UTF-8 decode with partial-frame carryover
  - ordering/sequence monotonicity
  - completion-frame terminality semantics
  - bounded per-tick decode/render budget behavior
  - backpressure counters and thresholds
  - end-to-end latency measurement (emit->render)
- replayable trace artifacts for failed runs

Out of scope:
- broad plugin UX redesign
- model quality/content semantics

## Done When
- a dedicated harness can reproduce healthy and pathological transport cases deterministically
- tests produce clear pass/fail against protocol contract
- we can classify stdio viability as:
  - viable now
  - viable with bounded mitigations
  - not viable for current UX/latency targets

## Related
- `542`
- `docs/protocols/vim-host-stdio.md`

## Progress
- 2026-05-23: task opened; harness and tests to be added in this slice.
