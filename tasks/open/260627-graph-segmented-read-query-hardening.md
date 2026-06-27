Filed as: 260627-graph-segmented-read-query-hardening
FKA:
AKA: segmented read_log; graph query stitching; logical history reads
Legacy index:

keywords: graph, implementation, inception, correctness, storage, boundaries, projection

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-segmented-event-journal-storage-contract`
Related: `260614-architecture-follow-through-coordination`

# Graph Segmented Read/Query Hardening

## Current Reality

Core graph/query code still assumes one physical event file:

- `read_log()` reads one path
- lineage/head/history helpers consume one in-memory event list
- operator query surfaces call those helpers directly

That makes segmented storage impossible without either hidden glue or broken
surface semantics.

## Desired Reality

Graph/query seams should be able to read many physical segments as one logical
durable history while preserving current append-only and message-tree
invariants.

## Scope

- define the segmented logical-history read seam
- make graph/query helpers work over stitched segment views
- preserve message and non-message record behavior across segments
- prove `heads`, `history`, `transcript`, and `llm-input` stay coherent

## Non-Goals

- index strategy
- provenance metadata design
- storage layout design itself

## Exit Evidence

- one graph/query seam that reads segmented logical history explicitly
- tests proving query parity across split storage
- no hidden dependence on one flat `events.jsonl` in the hardened graph/query
  path
