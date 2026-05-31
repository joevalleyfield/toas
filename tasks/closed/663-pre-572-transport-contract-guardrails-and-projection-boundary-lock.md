# 663: Pre-572 Transport Contract Guardrails And Projection Boundary Lock

## Goal

Establish explicit guardrails that keep RPC and stdio semantics convergent by construction, with a single semantic producer contract and transport-specific projection only where intentional.

## Why

Compatibility glue can silently become permanent semantics. Without guardrails, RPC and stdio can drift again under local unit pressure even when durable/runtime truth is correct.

## Scope

- Define authoritative semantic event contract at producer boundary (lane/phase + payload keys + terminality authority).
- Define projection boundary rules for daemon wrapper, watch compatibility shape, and stdio push framing.
- Add contract tests that compare RPC/watch and stdio/subscribe outputs for the same run and assert semantic equivalence.
- Introduce explicit annotations/comments where compatibility shims remain temporary.
- Add sunset criteria for compatibility projections introduced pre-572.

## Non-Goals

- Terminology rename sweep (`572`).
- Replacing established compatibility fields that external consumers still require.

## Done When

- Producer semantics are documented and test-backed independent of transport.
- RPC and stdio parity tests enforce convergence on lane/phase/payload meaning and terminal status.
- Any compatibility projection is explicit, bounded, and justified.
- This task provides a safe behavioral floor for `572` rename/refactor work.

## Proposed Workplan

1. Write contract table for producer vs projection ownership.
2. Add cross-transport parity fixtures for identical run histories.
3. Add invariants for terminal authority and no duplicate semantic append paths.
4. Document and fence temporary compatibility shims with removal criteria.
5. Re-run focused transport/runtime suites and record parity evidence.

## Progress Log

- 2026-05-31: Task opened as guardrail precursor so `572` proceeds on stable semantic boundaries rather than test-accidental behavior.
- 2026-05-31: Began guardrail execution with explicit cross-transport parity assertion at host subscribe boundary: `push_event` lane/phase/payload semantics must preserve upstream `watch.events` meaning for the same run payload.
- 2026-05-31: Added terminal-authority parity guardrail ensuring subscribe completion is anchored to terminal run status (`push_complete.reason=terminal_status`) while allowing current compatibility terminal projection shape.
- 2026-05-31: Added duplication/cursor guardrails at host subscribe boundary: no `watch_chunk_projection` when tool-delta text already covers chunk content, and monotonic `since_seq` progression across multi-read loops even when upstream `next_seq` regresses.
- 2026-05-31: Ran broad pre-close parity sweep across host subscribe, daemon run-store, async runner, and daemon facade surfaces (`187 passed`, `--no-cov`) and confirmed guardrail behavior is stable.

## Outcome

- Producer-vs-projection ownership is now explicitly documented and test-backed.
- RPC/watch and stdio/subscribe parity guardrails cover:
  - semantic event preservation (`type/lane/phase/payload`)
  - terminal status authority for subscribe completion
  - chunk-projection dedup behavior
  - `since_seq` monotonic cursor progression
- Compatibility seams remain explicit and bounded with inline removal criteria.

Residual risk:
- Compatibility projections (`llm_delta` synthesis wrapper, `compat_terminal`) still exist and can be retired only after downstream consumers are fully parity-safe without them.
