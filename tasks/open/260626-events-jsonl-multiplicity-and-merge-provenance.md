Filed as: 260626-events-jsonl-multiplicity-and-merge-provenance
FKA:
AKA: events.jsonl multiplicity; lcp primacy; rebound provenance; mergeable journals
Legacy index:

keywords: docs, exploration, inception, research, graph, transcript, projection, boundaries, provenance

Parent: `260614-architecture-follow-through-coordination`
Related: `260626-transcript-parallelism-design-pressures`; `260509-multi-operator-orchestration`

# Events.jsonl Multiplicity And Merge Provenance

## Current Reality

TOAS already uses append-only `events.jsonl` durability plus LCP-based
transcript reconciliation. That gives strong local editing and branching
behavior without requiring durable transcript identity for ordinary work.

At the same time, broader transcript-parallelism and queue-shaped designs make
it more plausible that multiple journals, branch-local histories, or imported
worker histories will eventually need to combine into one coherent durable
history.

There is also a more direct storage pressure: one forever-growing hot
`events.jsonl` is an awkward long-term physical unit. Older history may want to
move into colder split segments and possibly compressed archival sets without
ceasing to be part of the durable record.

## Desired Reality

TOAS should remain LCP-first even if event histories multiply.

If additional merge provenance is needed, it should be introduced in the
smallest possible way, ideally by attaching limited ancestry-rebound metadata
only when new adopted message content is actually appended after an LCP
boundary.

## Pressure

This is a narrow but important architectural pressure:

- preserve mergeability across multiple journals or imported histories
- allow physical journal splitting for size and operational manageability
- allow older segments to be compressed or archived without semantic loss
- keep message-tree parentage simple and canonical
- avoid making transcript identity mandatory for ordinary stepping
- retain lightweight no-op transcript rebound behavior

The core question is not "how do we build merges now?" but:

```text
what extra durable provenance, if any, is justified without weakening LCP primacy?
```

## Evidence

- The 2026-06-26 design outline argues that transcript parallelism will create
  more situations where separate event histories later need to cohere.
- `docs/notes/2026-05-24-multi-active-transcript-surfaces-design.md` already
  shows that multi-surface stepping raises continuity and provenance questions
  once multiple authored surfaces share durable state.
- `docs/runtime-ownership.md` keeps durable state, transcript reconciliation,
  operator semantics, and projection/rendering distinct, which is exactly the
  split this design pressure needs.
- Operationally, split hot/cold journals and compressed archive sets are an
  attractive way to keep durable history manageable without discarding it.

### 2026-06-27 Graph/Storage Trace

Reading current storage and query seams makes the likely work split clearer:

- `src/toas/graph.py:68` `read_log()` is still a single-file reader.
- `src/toas/graph.py:989` `append_nodes()` still appends only to one physical
  file path.
- `src/toas/graph.py:945` `write_message_events()` computes ids/parents and
  index records against one current file and one current line count.
- `src/toas/graph_index_edges.py:77` `rebuild_index()` assumes one source file
  and one index file.
- `src/toas/operator_api.py` query surfaces such as `history`, `heads`,
  `transcript`, `llm-input`, and `rebuild` all call `read_log()` directly and
  therefore currently assume one flat event journal.

This points to a first wave that is more "durable-state and graph hardening"
than "merge UX":

- define segmented storage ownership and rollover rules
- harden graph read/query seams to span many segments as one logical history
- harden index and replay/projection behavior across split storage
- only then decide whether extra rebound provenance is still needed

## Open Questions

- Should rebound provenance live in message metadata, a parallel durable record,
  or remain absent until stronger evidence appears?
- Should segmented and compressed storage be transparent inside durable-state
  query APIs, or explicit at higher layers?
- What exact condition makes ancestry reachback meaningful rather than trivial?
- Should naked rebound with no new adopted message stay unrecorded by default?
- How should merged or imported histories preserve provenance without inventing
  durable transcript identity for normal single-surface use?

## Exit Evidence

This task can leave inception when one focused design slice becomes concrete
enough to specify and test.

Useful exit artifacts would be one or more of:

- a proposed rebound provenance schema with exact emission rules
- examples proving the schema helps merged-history interpretation without
  changing ordinary LCP-first stepping
- a storage-layout proposal for hot/cold segments and compressed archive sets
  that preserves one logical durable history
- a decision that message metadata is sufficient, or a justified reason it is
  not

## Proposed Child Tasks

### 1. Segmented Event Journal Storage Contract

Why first:

- before hardening reads or indexes, TOAS needs one owning contract for hot
  append target, cold segments, rollover, and compressed archive semantics

Focus:

- file/layout contract for one logical history across many physical segments
- rollover rules
- compression/archive semantics as storage policy, not semantic deletion
- what metadata, if any, identifies segment order and recoverability

Likely owner:

- Durable State

Useful exit evidence:

- design note or task slice that names the physical layout and append/rollover
  invariants clearly enough for graph/query code to target

### 2. Graph Segmented Read/Query Hardening

Why early:

- current graph/query callers assume one flat file
- the query surface should be able to treat many segments as one logical
  history before higher-level UX grows around it

Focus:

- `read_log()` replacement or wrapper for segmented logical history
- message-event and non-message-event query parity across segments
- lineage/head/history semantics over split storage
- preserving append-only audit meaning while reading merged segments

Likely owner:

- Durable State with graph/query seams

Useful exit evidence:

- graph/query API contract plus tests showing `heads`, `history`, `transcript`,
  and `llm-input` remain coherent across segmented storage

### 3. Segmented Index And Lookup Hardening

Why distinct:

- current index work is already a focused seam
- segmented storage risks hidden regressions in direct lookup, position
  tracking, and large-log performance

Focus:

- whether indexes remain one-per-segment or gain a stitched logical layer
- lookup by logical position vs physical segment offset
- rebuild behavior for index artifacts when segments roll or are compressed
- correctness/performance expectations for lineage and graph views

Likely owner:

- Durable State / `graph_index_edges.py`

Useful exit evidence:

- explicit index strategy and tests proving lookup/rebuild behavior across
  multi-segment history

### 4. Rebuild/Projection Parity Across Split Storage

Why separate:

- rebuild/projection correctness is the user-visible proof that segmented
  storage did not quietly change semantics

Focus:

- `rebuild`, `transcript`, `llm-input`, `graph`, and `heads` parity
- anchor behavior when durable history spans hot and cold segments
- acceptance-style proof that split physical storage still projects one
  coherent transcript/message tree

Likely owner:

- Durable State plus Projection And Rendering boundary tests

Useful exit evidence:

- deterministic proofs that split storage changes storage layout only, not
  observable transcript/history meaning

### 5. Rebound Provenance Contract

Why later:

- extra provenance should come only after storage and graph semantics are clear
- otherwise TOAS risks adding metadata before knowing what gap actually remains

Focus:

- first-new-node rebound metadata vs no additional provenance
- exact emission rules
- whether merged-history interpretation truly needs more than parentage plus
  segmented durable records

Likely owner:

- Transcript Reconciliation plus Durable State

Useful exit evidence:

- a narrow schema decision with examples and tests, or an explicit decision not
  to add it yet

## Recommended Sequencing

Recommended order:

1. segmented storage contract
2. graph segmented read/query hardening
3. segmented index and lookup hardening
4. rebuild/projection parity proof
5. rebound provenance decision

This order keeps TOAS honest about the likely first problem. The system
probably needs graph/storage hardening before it needs richer provenance
metadata.

## Notes

This task should stay deliberately conservative. The value is preserving TOAS's
lightweight transcript-first model while making room for richer merged-history
provenance only if real evidence demands it.

The storage-layout angle is part of the same pressure, but it should still be
framed as durable-state ownership and recoverability work rather than as an
excuse to loosen transcript or message-tree invariants.
