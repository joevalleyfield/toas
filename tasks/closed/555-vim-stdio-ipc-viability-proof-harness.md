# 555 Vim Stdio IPC Viability Proof Harness

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
- `553`
- `docs/protocols/vim-host-stdio.md`

## Progress
- 2026-05-23: task opened; harness and tests to be added in this slice.
- 2026-05-24: closure audit confirms proof-harness outcomes are already landed across:
  - deterministic probe/harness artifacts: `tests/vim/phase3_stdio_push_probe.py`, `tests/vim/phase5_streaming_region_probe.py`, `tests/vim/phase6_stdio_contract_probe.py`, `tests/vim/stdio_contract_host_service.py`
  - contract tests and classifications: `tests/test_vim_driver_phase6_stdio_contract.py`, `tests/test_vim_driver_phase6_viability_report.py`, `tests/test_vim_driver_contract_plugin.py`, `tests/test_runtime_session_host_process.py`
  - protocol contract documentation: `docs/protocols/vim-host-stdio.md`, `docs/protocol-notes.md`
  - post-cutover incremental forwarding fix + lifecycle contract continuity tracked in closed contributing tasks (`542`, `543`, `552`, `553`, `554`).
- 2026-05-24: viability classification outcome:
  - viable now, with bounded mitigations already adopted (timer-sliced decode/render budgets, fallback polling lane, and immediate per-frame subscribe flush semantics).
- 2026-05-24: lessons-learned cross-reference:
  - before final subscribe/callback cutover, phase-7/phase-8 exploration found a "local maximum" polling shape that materially reduced pain via watch-pump decomposition/tuning and channel-read wakeups.
  - key commits to preserve as the pre-cutover polling peak:
    - `1df7b9ed` (`vim stdio: refine push/watch timing and burst render behavior`)
    - `c5903c4c` (`vim stdio: split watch pump into ingress/decode/adapt phases`)
    - `98fad306` (`vim local_host: trigger watch pump on channel read; add latency assertion and tighten vader waits`)
  - this path improved polling behavior but did not replace the architectural need for subscribe/receive callback semantics plus incremental host forwarding (`b4cc1f8a`).
