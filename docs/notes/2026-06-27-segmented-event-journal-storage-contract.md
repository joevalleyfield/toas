# Segmented Event Journal Storage Contract

Status: DIRECTIONAL
Related tasks: `260627-segmented-event-journal-storage-contract`; `260627-graph-segmented-read-query-hardening`; `260627-segmented-event-index-and-lookup-hardening`; `260627-split-storage-rebuild-and-projection-parity`

## Purpose

Define the first durable-state contract for splitting one logical TOAS history
across multiple physical event-journal files without changing append-only
semantics.

This note is intentionally about storage layout and recoverability, not graph
query implementation, index stitching, or merge UX.

This contract also fixes an expediency rule for `n1` work:

```text
LCP reconciliation reads hot storage only.
```

Sealed segments exist for broader history, rebuild, and query surfaces. They do
not participate in ordinary active transcript reconciliation.

## Core Stance

```text
One logical durable history may span many physical segments,
but exactly one segment is writable at a time.
```

Segmenting storage does not create separate histories by itself. It only
changes how one append-only history is physically laid out.

Operationally, the hot file is not just a tail shard. It is the active
continuation working set and must remain self-sufficient for reconciliation.

## Layout

Given an active events path such as `.toas/events.jsonl`, the physical layout is:

```text
.toas/
  events.jsonl                  # hot writable segment
  segments/
    000001-events.jsonl         # cold immutable segment
    000002-events.jsonl         # cold immutable segment
    000003-events.jsonl.gz      # archived immutable compressed segment
```

Rules:

- `.toas/events.jsonl` remains the canonical hot append target.
- Older segments live under `.toas/segments/`.
- Segment filenames carry a zero-padded monotonic ordinal prefix.
- Segment suffix determines encoding:
  - `.jsonl` = plain UTF-8 JSONL
  - `.jsonl.gz` = gzip-compressed UTF-8 JSONL archive
- Segment ordinals define physical read order from oldest to newest.
- The hot file is logically after every numbered segment, regardless of its
  filename.

## Segment Classes

### Hot Segment

The hot segment is the only file that append operations may write to.

Properties:

- path is fixed at `.toas/events.jsonl`
- writable
- may be absent and treated as empty
- may grow until a rollover policy seals older records into a cold segment
- must contain a self-contained reconciliable history for active transcript
  stepping
- must preserve the reachable active lineage back to the first non-null root
  `n1`

### Cold Segment

A cold segment is a sealed immutable part of the same logical history.

Properties:

- stored as numbered `.jsonl`
- never appended to after sealing
- remains directly readable without decompression
- may be used as rollover input for later archival compression

### Archived Segment

An archived segment is a sealed immutable part of the same logical history
stored in compressed form.

Properties:

- stored as numbered `.jsonl.gz`
- never appended to after sealing
- recoverable by ordinary gzip decompression
- semantically identical to its uncompressed JSONL contents

Compression is storage compaction, not semantic deletion.

## Ordering Invariants

The storage contract relies on simple explicit ordering:

1. segment ordinal order is the logical order for numbered segments
2. the hot segment always comes after the highest numbered sealed segment
3. record order inside a segment remains file order

This means logical history order is:

```text
all records from segment 000001
then all records from segment 000002
...
then all records from the current hot events.jsonl
```

No per-record cross-segment sequence number is required for the base storage
contract. If later work needs stronger corruption detection or merge imports,
that should be additive rather than implicit here.

## Reconciliation Boundary

For `n1`, the active reconciliation contract is intentionally asymmetric:

- LCP reconciliation reads `.toas/events.jsonl` only.
- Sealed segments are not consulted during ordinary transcript reconciliation.
- If reconciliation would require reading a sealed segment, the storage layout
  is wrong for the active hot set.

This means hot storage must preserve enough history to keep the active graph
well-formed and rooted locally at `n1`.

## Rollover Contract

Rollover is the act of sealing older hot history into a numbered segment while
leaving behind a new hot file that is still self-sufficient for active
continuation.

Required behavior:

1. choose the next unused segment ordinal
2. seal some older prefix of hot history into
   `.toas/segments/<ordinal>-events.jsonl`
3. retain or restage in `.toas/events.jsonl` every record needed so active
   transcript reconciliation still has a complete hot-local rooted history back
   to `n1`
4. never interleave new appends into the sealed segment afterward

The base contract does not yet standardize when rollover happens. Size-based,
manual, or maintenance-triggered rollover are all compatible as long as the
sealed-file invariant holds.

Important expediency rule:

- rollover may leave redundant history in hot storage
- redundancy removal is optional and bounded
- preserving hot-local reconciliation context is required

Put differently, rotation is storage management, not a semantic repartitioning
pass.

## Recoverability

The minimum recoverability promise is:

```text
If every present segment can be read in logical order,
the full logical history can be reconstructed by concatenating records in that order.
```

Implications:

- no segment-local metadata file is required to interpret ordinary history
- rollover may restage redundant records in hot when that is the cheapest way
  to preserve reconciliation context
- compressed archival segments must decode to byte-equivalent JSONL lines for
  the records they contain
- deletion of a segment is semantic data loss, not a routine maintenance step

## Failure And Partial-State Rules

The storage contract should bias toward readable older history plus a clearly
bounded hot-write failure, rather than silently ambiguous ordering.

Required rules:

- A numbered segment is not considered sealed unless its full file is present.
- Gaps in numbered ordinals are invalid for automatic stitched reads.
- Mixed duplicate ordinals are invalid.
- If both `000003-events.jsonl` and `000003-events.jsonl.gz` exist, that is an
  invalid state until a repair tool resolves it.
- Query surfaces should fail explicitly on invalid segment layout rather than
  guessing.

This keeps recoverability auditable and pushes repair semantics into explicit
tools rather than hidden read heuristics.

## Why Filename Order Is Enough For Now

This task is deliberately conservative.

Filename ordinal order is sufficient today because:

- TOAS currently owns the local rollover story
- split storage is first about hot/cold/archive management, not imported merge
  batches
- existing durable semantics already depend on append-only record order
- the active reconciliation path is intentionally hot-only rather than
  multi-segment

Future work may add manifests or stronger provenance for imported side journals,
but that should be justified by those workflows rather than smuggled into the
base hot/cold contract.

## Query And Index Consequences

This note does not implement graph or index behavior, but it fixes the target:

- graph/query code must treat numbered sealed segments plus hot `events.jsonl`
  as one logical record stream
- transcript LCP reconciliation must continue to treat hot `events.jsonl` as
  its entire authority surface
- index strategy may be per-segment, stitched, or hybrid, but must respect
  segment ordinal order
- rebuild/projection parity must be tested against this logical stream, not
  against assumptions that only one file exists

## Non-Goals

This storage contract does not yet define:

- merged/imported side-journal provenance
- per-segment manifests
- automatic repair tooling
- rollover policy thresholds
- cache/index invalidation details
- warm-vs-cold performance heuristics

## Exit Value

The concrete contract from this slice is:

- one writable hot file at `.toas/events.jsonl`
- zero or more immutable ordered segments under `.toas/segments/`
- optional gzip compression for sealed archival segments
- filename ordinal order as the durable logical ordering primitive
- active transcript reconciliation is hot-only
- hot storage remains self-contained and rooted back to `n1`
- explicit invalid-state failure for gaps, duplicates, or ambiguous sealed forms

That is enough for the next graph/query task to harden a stitched read seam
without also inventing storage policy.
