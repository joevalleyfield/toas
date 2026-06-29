Filed as: 260627-segmented-event-index-and-lookup-hardening
FKA:
AKA: segmented indexes; stitched lookups; multi-segment graph index
Legacy index:

keywords: graph, implementation, inception, performance, storage, index, provenance

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-graph-segmented-read-query-hardening`
Related: `260614-architecture-follow-through-coordination`

# Segmented Event Index And Lookup Hardening

## Current Reality

The current index layer is already a focused seam, but it assumes one source
file and one index artifact. Segmented storage will stress logical position,
byte offset meaning, rebuild behavior, and large-log lookup performance.

## Desired Reality

Index and lookup behavior should remain explicit and correct when one logical
durable history spans multiple physical segments.

## Scope

- decide per-segment vs stitched logical index strategy
- define logical position and physical offset expectations
- define rebuild behavior as segments roll or move to colder storage
- preserve lookup correctness for lineage and graph-oriented queries

## Non-Goals

- storage contract design
- user-visible rebuild/projection proof
- provenance metadata design

## Exit Evidence

- a concrete index strategy for segmented history
- direct tests proving rebuild and lookup correctness across segments
- explicit performance/correctness expectations for large histories

## Outcome

Closed on 2026-06-29.

Implemented an explicit stitched logical-index seam in
`src/toas/graph_index_edges.py`:

- hot-file index behavior remains compatible for existing single-source
  callers
- logical history indexing is per-source and stitched at read time
- `LogicalIndexRecord` carries logical position plus source path, source line,
  source-scoped offset, and message id
- sealed `.jsonl` segments, sealed `.jsonl.gz` segments, and the hot
  `.toas/events.jsonl` file each rebuild through their own disposable index
  artifact
- invalid segment layouts continue to fail closed for duplicate or missing
  sealed ordinals

`toas index rebuild` now rebuilds the logical-history source indexes rather
than only the hot file, while preserving the existing one-file message for
ordinary unsegmented history.

Verification:

- `./.codex-local/bin/uvt run python scripts/targeted_coverage.py --cov toas.graph_index_edges --fail-under 100 --max-missing-files 0 -- tests/test_graph_index_edges.py -q`
- `./.codex-local/bin/uvt run pytest tests/test_operator_api.py -q --no-cov`
