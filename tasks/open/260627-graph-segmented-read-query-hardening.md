Filed as: 260627-graph-segmented-read-query-hardening
FKA:
AKA: segmented read_log; graph query stitching; logical history reads
Legacy index:

keywords: graph, implementation, inception, correctness, storage, boundaries, projection

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Related: `260614-architecture-follow-through-coordination`

# Graph Segmented Read/Query Hardening

## Current Reality

Core graph/query code still assumes one physical event file:

- `read_log()` reads one path
- lineage/head/history helpers consume one in-memory event list
- operator query surfaces call those helpers directly

That makes segmented storage impossible without either hidden glue or broken
surface semantics.

The selected storage contract also makes one boundary explicit: transcript LCP
reconciliation remains hot-only and must not reach into sealed segments.

That same contract also keeps segmentation decoupled from live lineage
selection: rotation must not depend on whichever root or parent chain happens
to be active during a step.

## Desired Reality

Graph/query seams should be able to read many physical segments as one logical
durable history while preserving current append-only and message-tree
invariants, while leaving ordinary reconciliation authority entirely with hot
`.toas/events.jsonl`.

## Scope

- define the segmented logical-history read seam
- make graph/query helpers work over stitched segment views
- preserve message and non-message record behavior across segments
- preserve the separation between hot-only reconciliation and segmented history
  queries
- preserve the independence of segmentation/rotation from step-time lineage
  selection
- prove `heads`, `history`, `transcript`, and `llm-input` stay coherent

## Non-Goals

- index strategy
- provenance metadata design
- storage layout design itself
- changing reconciliation to depend on sealed segment reads

## Exit Evidence

- one graph/query seam that reads segmented logical history explicitly
- tests proving query parity across split storage
- explicit proof that the hardened query path does not become a hidden
  dependency of LCP reconciliation
- no hidden dependence on one flat `events.jsonl` in the hardened graph/query
  path
