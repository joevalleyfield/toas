# 344: Context Assembly Engine prototype from lens artifacts

## Summary
Prototype a deterministic context-assembly layer that builds inference packets from provenance-linked lens artifacts rather than ad hoc flat transcript slices.

## Why Now
The project has a clear hierarchical context/lensing direction but no implementation seam yet. This prototype creates a concrete path from design intent to operational behavior.

## Source Notes
- `docs/notes/2026-04-11-hierarchical-context-lifecycle-and-lensing.md`
- `docs/notes/2026-04-08-context-without-prefix-caching.md`

## Problem
Current context supply is still primarily transcript-shaped. That underuses derived structure, increases operator bottlenecks, and makes quality/coverage of model input hard to reason about.

## Goals
- Introduce a first-class Context Assembly Engine seam.
- Assemble step-time inference packets from derived lens artifacts with explicit provenance pointers.
- Keep durable truth immutable and derivations reversible.
- Add minimal quality gates to detect weak packets before inference.

## Proposed Scope (Prototype)
- Define lens artifact shape and storage surface for prototype use:
  - `title`
  - `distillation` (3-6 lines)
  - `source_pointers` (event ids/ranges)
  - `use_when`
- Implement deterministic packet assembly for inference using:
  - current task/goal cue
  - active lens artifacts
  - relevant constraints/policy context
  - minimal evidence snippets
- Add packet quality checks (initial set):
  - coverage (goal has supporting sources)
  - conflict (obvious contradictory lenses)
  - staleness (artifact recency/lineage mismatch)
- On failed quality gate, emit explicit continuation guidance rather than silently proceeding.

## Non-goals (Initial Pass)
- Full automatic lifecycle state machine.
- Sophisticated ranking/learning policies.
- Rich UI around lens authoring.

## Subtasks

- `444`: lens command ergonomics and multiline authoring
- `445`: lens validation and diagnostics at write time
- `446`: context packet observability and inspection surface
- `447`: lens quality-gate remediation workflow
- `448`: context packet shaping expansion in generation path

## Acceptance Criteria
- A new assembly seam exists and is exercised in at least one inference path.
- Lens artifacts are provenance-linked and recoverable from durable history.
- Packet assembly order and content are deterministic under fixed inputs.
- Weak packet conditions produce explicit actionable output.
- Tests cover assembly determinism and at least one quality-gate failure path.

## Progress

- 2026-04-26: Landed first context-assembly seam slice:
  - Added `runtime/context_assembly.py` with deterministic packet construction (`build_context_packet`) and lens artifact collection from durable message metadata (`metadata.lens_artifact` with `title/distillation/source_pointers/use_when`).
  - Integrated the seam into a live inference path by routing `GenerationRunner.prepare_request` through context-packet assembly before model request planning.
  - Added initial packet quality gates (`coverage`, `staleness`, `conflict`) and wired generation-time guard output through `_generation_guard_result` so weak packets produce explicit continuation guidance instead of silent fallback.
  - Added tests for deterministic packet assembly and quality-gate failure behavior.
- 2026-04-26: Landed operator-facing durable lens authoring slice:
  - Added `/lens` command surface with `list|set|remove|reset` in the prompt/workspace operator-command lane.
  - Added durable `lens_artifact` non-message records in `events.jsonl` and side-effect persistence wiring from slash-command results.
  - Extended context assembly to consume durable lens artifact records from event history, with deterministic title-key override behavior between message metadata and durable event lane.
  - Added handler/session-edge/context-assembly regressions covering lens command behavior, durable write path, and event-lane packet inclusion.
- 2026-04-26: Completed subtask chain `444`-`448` and met prototype acceptance:
  - Landed lens authoring ergonomics (`/lens set` flag form + multiline distillation), write-time source-pointer validation, packet inspection (`/lens packet`), and remediation workflow (`/lens doctor` + quality-gate guidance).
  - Expanded generation shaping from a simple summary prepend to deterministic sectioned packet rendering with bounded artifact/distillation/evidence limits and truncation signaling.
  - Verified no-artifact parity and deterministic shaping behavior under fixed inputs with focused regressions and full-suite coverage gate.
