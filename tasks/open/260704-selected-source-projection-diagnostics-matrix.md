Filed as: 260704-selected-source-projection-diagnostics-matrix
FKA:
AKA: projection diagnostics matrix; selected-source failure fixtures
Legacy index:

keywords: projection, testing, active, correctness, diagnostics, scale-model

Parent: `260629-storage-scale-model-proof-contract`
Related: `260704-projection-source-stitch-mode-contract`; `260627-split-storage-rebuild-and-projection-parity`

# Selected Source Projection Diagnostics Matrix

Pressure selected-source projection failures through use-shaped fixtures.

## Goal

Add scale-model pressure for selected-source projection diagnostics across
`history`, `transcript`, and `llm-input` now that those surfaces share explicit
source and anchor selection.

## Why

The first selected-source projection slice proved the happy path and basic
anchor behavior. The next proof should cover the ways an operator query can
fail or omit material without treating ordinary journal-local identity,
divergence, or non-message facts as corruption.

## Matrix

- missing selected source/path reports a selector diagnostic
- missing selected anchor reports a target diagnostic
- source-local corruption names the selected source that blocked projection
- divergent same local ids without LCP proof refuse bare anchors as ambiguous
- non-message enrichment can exist in selected sources without leaking into
  transcript or LLM-input projection

## Non-Goals

- no new source-selection DSL
- no retention/tombstone semantics yet
- no stitched transcript enrichment display
- no recovery-only corrupt-history surface

## Exit Evidence

- scale-model tests exercise the matrix through operator-facing projection
  surfaces, not only helper functions
- diagnostics are actionable enough to distinguish selector, target, and
  source-local integrity failures
- task and parent notes identify any diagnostics left for follow-on work

## Progress

- Added the first scale-model matrix across `history`, `transcript`, and
  `llm-input` selected-source projection. The fixture coverage now includes
  missing source/path selector diagnostics, missing anchor target diagnostics,
  selected-source corruption diagnostics naming the blocking source, divergent
  same-local-id bare-anchor refusal, and non-message enrichment remaining out
  of transcript/LLM-input projection.
- Normalized lineage projection selector errors in
  `src/toas/projection_selection.py` so missing selected paths report as
  `projection source selector failed: ...`.
- Normalized selected-source projection integrity failures so source-local
  corruption names the selected source that blocked projection without treating
  other selected sources as corrupt.
- Added CLI boundary tests through `toas transcript --sources ...`,
  `toas history --sources ...`, and `toas llm-input <anchor> --sources ...`
  so selector, source-integrity, and target-ambiguity diagnostics are proven
  through command parsing and local command dispatch, not just operator API
  calls.
