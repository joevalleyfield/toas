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

## Acceptance Criteria
- A new assembly seam exists and is exercised in at least one inference path.
- Lens artifacts are provenance-linked and recoverable from durable history.
- Packet assembly order and content are deterministic under fixed inputs.
- Weak packet conditions produce explicit actionable output.
- Tests cover assembly determinism and at least one quality-gate failure path.
