# Events.jsonl Multiplicity, LCP Primacy, And Merge Provenance

Status: DIRECTIONAL
Related tasks: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260626-transcript-parallelism-design-pressures`; `260614-architecture-follow-through-coordination`

## Purpose

Capture a conservative design direction for `events.jsonl` multiplicity:
multiple event journals, transcript branches, or projection surfaces may need
to merge into one durable history without weakening TOAS's current LCP-based
reconciliation model.

An important motivation is storage manageability:

- one ever-growing hot journal becomes awkward to keep as the only physical
  durable unit
- older durable history may want colder storage and compression semantics
- archival should preserve recoverability rather than acting like semantic
  deletion

The key stance is:

```text
LCP remains the master reconciliation primitive.
```

If TOAS needs more provenance for merge-heavy workflows, the likely addition is
small:

```text
record ancestry-rebound provenance only when new adopted message nodes are created.
```

## Problem

TOAS already gets useful flexibility from two current facts:

- transcript text is a materialized surface
- `events.jsonl` is durable append-only history

That means:

- transcript suffixes can be deleted
- branches can be created by changing the surface
- prior durable message nodes are not mutated
- LCP reconciliation decides whether anything new exists

Transcript parallelism and queue-shaped work increase the number of situations
where several event journals or event streams may later need to combine.

Storage pressure adds another reason to split journals even without
parallelism:

- keep the active append target small enough to stay operationally cheap
- roll older history into colder segments
- compress archival segments without losing them entirely
- preserve one logical durable history across many physical journal files or
  blobs

Examples:

- a worker transcript produces its own event log
- a side branch is explored separately and later merged
- repeated workflow batches produce separate durable journals
- one hot journal is rolled into older compressed archive segments
- a transcript suffix is deleted and the surface is stepped again from an older
  point
- assistant-authored text is adopted later through an assistant-frontier step

The desired operation is not text concatenation. It is:

```text
combine many append-only journals into one coherent message tree plus operational history.
```

## Core Model

`events.jsonl` is the append-only journal.

The message tree is a privileged subgraph inside that journal.

This note intentionally separates:

- logical durable history
- physical journal layout

One logical durable history may eventually span:

- one current hot append target
- several older cold segments
- compressed archival shards
- imported or merged side journals

Useful invariant:

```text
Every line in events.jsonl is a durable event record.
Only message records participate in the transcript/message tree.
```

This matters because a merged journal may include many durable non-message
facts:

- tool records
- model-call records
- run records
- queue or claim records
- watcher or projection records
- reconciliation records

The message tree remains special because it represents adopted transcript
content, not because it is the only durable thing in the log.

## LCP Primacy

Current LCP-based reconciliation should remain the main primitive.

Given a materialized transcript surface and a durable message tree, TOAS
computes the longest common prefix and appends new message records only for
content after that boundary.

This preserves important current properties:

- no durable transcript registration is required for ordinary use
- copied or hand-edited transcript files remain useful
- branch creation stays text-native
- durable history is not mutated
- assistant-frontier adoption remains compatible with the same basic model
- storage segmentation does not require different reconciliation semantics

Guiding rule:

```text
If no new adopted transcript content appears after LCP, no new message-tree node is required.
```

## What Pure LCP Does Not Capture

Pure LCP preserves message order and parentage, but it may lose one kind of
provenance:

```text
an old ancestry path became active context again when a later branch was authored.
```

That is not a parentage problem. Parentage already answers:

```text
what message did this new node directly descend from?
```

The missing question is:

```text
what older ancestry was operationally rebound into active context when this new node was created?
```

That distinction becomes more relevant when many journals or projection-local
histories later merge into one durable forest.

## Rejected Larger Move

One way to preserve rebound provenance would be to give every transcript or
projection durable identity and emit explicit bind/rebind events whenever its
effective LCP context changes.

That would add provenance, but it also adds weight:

- ordinary hand-edited transcripts become lifecycle entities
- file paths risk becoming semantic identity
- process or host identity may leak into durable meaning
- no-op rebind steps would want records even when no adopted content changes
- ordinary LCP-only freedom becomes less lightweight

This note does not choose that as the default for base transcript
reconciliation.

Projection identity may still be useful for explicit worker or queue semantics,
but ordinary transcript stepping should not require durable transcript identity
just to preserve mergeability.

## Conservative Addition

The smaller idea is:

```text
record rebound provenance only on the first new message node after an LCP boundary.
```

That metadata would say, in effect:

```text
this new node descends from this LCP tip,
and at creation time the active rebound context reached this far back into ancestry.
```

This keeps provenance attached to actual adopted content instead of creating
standalone bind records for every no-op rebound.

## Candidate Shape

Illustrative shape:

```yaml
id: n900
parent: n123
role: user
content: ...
metadata:
  rebound:
    lcp_message_id: n123
    ancestry_split_distance: 17
    rebound_at: 2026-06-26T15:42:00-04:00
```

Field naming is still open. The currently attractive semantic payload is:

- LCP tip identity
- ancestry split distance
- rebound timestamp

The parent pointer still owns direct lineage. Rebound metadata would not replace
parentage.

## Meaning Of Ancestry Split Distance

`ancestry_split_distance` should mean:

```text
when this node was created, the rebound context reached back N message ancestors from the LCP tip.
```

This gives useful merge provenance without storing an entire ancestry list on
every new message.

It should not be treated as an alternate parent pointer, branch identifier, or
projection identity.

## Emission Rule

Rebound metadata should only be emitted when all are true:

1. a new message node is created
2. it is the first new message node after the LCP boundary for that step
3. a meaningful ancestry reachback can be identified
4. that reachback is not already trivial from direct parentage alone

Do not emit it on every later descendant in the same newly appended suffix
unless there is a distinct semantic reason.

## Naked Rebound

A naked rebound is a step where a surface effectively rebinds to older history
but no new adopted message node is created.

This note leans conservative:

- naked rebound should remain acceptable as a no-new-message condition
- it does not automatically require a durable provenance record

That choice keeps ordinary transcript editing lightweight, though it means some
rebind moments remain intentionally unrecorded unless they lead to new adopted
content.

## Merge Reading

Under this model, merging journals remains fundamentally a durable-state and
message-tree integration problem, not a transcript-surface identity problem.

Desired outcome:

- the combined journal still preserves append-only facts
- physically split or compressed segments still participate in one logical
  durable history
- the message tree remains reconstructable from message records
- operational records stay outside message-tree semantics
- later readers can infer important rebound context for newly created branches
  without requiring every historical surface binding to have been recorded

Compression should be understood as storage policy, not semantic loss.

Cold segments may be slower to read, lazily opened, or physically compacted,
but they should remain part of the recoverable durable record set.

## Architecture Pressures

This note mainly pressures these domains:

### Durable State

- how merged journals preserve stable ids, ordering, and fact families
- whether segmented hot/cold storage is transparent inside `graph.py` or
  explicit in higher-level storage/query seams
- how compression/archive formats preserve replayability and append-only audit
  meaning
- whether rebound provenance belongs in message metadata or a related durable
  record family
- how much merge evidence should exist without promoting transcript identity to
  first-class durable truth

### Transcript Reconciliation

- how LCP remains primary even when input histories are merged or imported
- when rebound context is meaningful enough to stamp on first-new-node
- how assistant-frontier adoption or branch reuse should appear in the same law

### Projection And Rendering

- how rebound provenance is shown without turning render text into truth
- whether merge diagnostics should highlight rebound metadata explicitly

### Operator Semantics

- whether any explicit merge or import action is needed beyond ordinary stepping
- whether some future replay/import surfaces should stamp provenance more
  explicitly

## Invariants To Preserve

Any future work here should preserve:

- prior durable history is never mutated
- LCP remains the primary reconciliation primitive
- transcript files remain materialized surfaces, not required durable identities
- message-tree parentage remains distinct from operational merge provenance
- physical storage segmentation or compression never implies semantic deletion
- render/projection output must not become canonical merge truth

## Recommendation

Treat this as a design note and follow-on task seed, not an implementation
commitment.

If work advances, the first useful slice is likely a narrow provenance-design
task:

- define whether rebound metadata belongs on message records
- specify exact emission conditions
- prove that the design preserves ordinary LCP-first transcript stepping

Closely related follow-on slices may be needed for storage layout:

- define segmented hot/cold journal ownership in Durable State
- decide whether compressed archival segments are stitched transparently by
  graph/query code
- prove that rebuild/projection semantics remain correct across split storage

That is a better first step than broadening transcript identity or inventing a
full merge subsystem prematurely.
