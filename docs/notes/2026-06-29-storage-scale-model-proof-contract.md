# Storage Scale-Model Proof Contract

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260627-split-storage-rebuild-and-projection-parity`; `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`

## Purpose

Name the use-case-shaped histories TOAS must prove before segmented storage can
claim semantic consistency.

The immediate risk is that local implementation fixes make one surface green
while leaving the product model contradictory. The proof target should be a
small set of scale models: artificial enough to test cheaply, but shaped like
the real operating pressures of transcript-controlled durable history.

This note is the proof-contract layer. It should be read with the broader
brainstorming set:

- `2026-06-29-operator-history-use-cases`
- `2026-06-29-runtime-history-use-cases`
- `2026-06-29-history-retention-and-lifecycle`
- `2026-06-29-history-storage-alternatives`
- `2026-06-29-scale-model-history-scenarios`
- `2026-06-29-segmented-storage-contradiction-inventory`
- `2026-06-29-history-use-pressure-contract`

## Product Frame

TOAS is trying to preserve three operator experiences at once:

1. active work stays cheap, local, and transcript-driven
2. old durable history remains recoverable and inspectable
3. projection surfaces do not lie about identity, parentage, or scope

The system therefore cannot use one undifferentiated "read all history" rule.
It needs declared access scopes and identity semantics per surface.

TOAS history should also be understood as local operator harness memory over
repository work. Repository artifacts remain primary project truth; event
history records the working process, provenance, recovery context, and
projection material around those artifacts.

## Identity Layers

Use these terms when evaluating storage/projection behavior:

- **journal-local id**: the `id` string written inside one event journal, such
  as `n1`; unique only inside that source
- **physical occurrence**: one record at one source and line/position
- **message lineage identity**: parentage within one journal source unless a
  stitcher has proven cross-source alignment
- **projection identity**: the identity a selected surface presents after
  alignment, qualification, or refusal
- **provider identity**: the LLM-input message sequence after projection rules
  such as adjacent-user concatenation

Do not collapse these layers merely because a test fixture is small.

## Proof Questions

Every scale-model assertion should answer:

- which source scope is being read
- which identity layer is being asserted
- whether the surface is lineage-shaped, topology-shaped, provider-shaped, or
  diagnostic
- whether missing proof is a warning, refusal, fatal corruption, or
  retention-limited absence
- whether retained material is raw history, derived summary, index/manifest, or
  projected artifact

## Scale Models

### Hot-Only Active Work

One writable hot journal contains the active message graph and operational
facts.

Expected: all current single-file semantics hold. This is the regression
baseline.

### Rolled Active History With Redundant Hot Context

Older records are sealed in cold storage, and hot storage carries enough
overlapping context to keep active reconciliation hot-local.

Expected: `step` uses hot only; explicit full-history inspection can include
cold storage; duplicate physical facts introduced by restaging must not create
phantom transcript messages.

### Independent Hot Root After Rotation

Cold storage has one root and hot storage starts a new independent root. Both
sources may validly contain local ids such as `n1`.

Expected: fsck accepts same local ids across sources; topology may show
separate source-local roots; transcript/LLM-input selected-lineage projection
must not stitch by raw id.

### Aligned Cold/Hot Continuation

Hot storage can restage enough content or boundary material to align with a cold
segment because the working transcript remains visible after rotation and the
next step re-ingests transcript turns into the new hot journal.

Expected: any cross-source stitch is derived from LCP/alignment evidence, not
id equality. The rendered surface should either qualify local ids or present a
derived equivalence class.

### Ambiguous Same Local Id Across Sources

Two or more sources contain the same local ids and insufficient alignment
evidence.

Expected: storage integrity is not fatal solely because ids repeat across
sources. Semantic stitched surfaces may refuse and should say that alignment is
missing.

### Source-Local Corruption

One journal source contains duplicate local ids, malformed message records, or
missing parents inside that same source.

Expected: integrity fails closed for that source. Recovery can reason about the
source and avoid treating the whole storage layout as inherently corrupt.

### Non-Message Durable Facts Across Scopes

Tool records, model calls, heads, binds, anchors, and projection artifacts live
near message events but are not message events.

Expected: message projection keeps durable facts distinct. Rendered `RESULT`
blocks remain projection output, not durable message history.

### Raw Expired, Summary Retained

Raw operational history has expired, been redacted, or been tombstoned, while a
derived summary or decision record remains.

Expected: retention-limited absence is not corruption. Raw transcript
reconstruction refuses when source history is unavailable. Summary or decision
views may explain what remains, but they must not masquerade as raw lineage.

## Test Direction

High-level tests should build these scale models from fixtures rather than from
incidental one-off JSON strings scattered across unit tests.

The tests should assert three things:

- behavior: what the surface returns, refuses, or warns about
- scope: which sources were allowed to participate
- identity: whether ids are source-qualified, aligned, or deliberately absent

Unit tests can still cover parser and helper details, but consistency proof
belongs to the scale-model layer.

The first fixture layer should prefer readable, hand-sized histories over broad
property testing. Later property or matrix tests can grow out of these examples
once the expected semantics stop moving.

Bounded hot-log size should become an explicit soft trigger and test knob. The
trigger should ask for or schedule rotation at safe boundaries; it should not
stop durable writes mid-turn. Production may choose a larger configurable
rotation threshold, but scale fixtures should be able to turn that threshold
down to a few message events so rotation, transcript rehydration, and cold/hot
stitching pressure appear in tiny reproducible histories.

The soft trigger should have an explicit operator sibling: a command such as
`/rotate` should let the user request hot/cold rotation at the next safe
boundary even before size pressure requires it. That keeps lifecycle management
visible and intentional. Additional `/compact` options or assisted compaction
modes belong in the same family for transcript/context ergonomics: visible
operator actions rather than hidden automatic rewrites.

## Why Hot-Size Pressure Exists

Hot history is the active working set, not the whole durable archive. Very large
hot logs make ordinary work unpleasant because active operations risk paying for
old context: reads, index refresh, fsck, projection, debug surfaces, editor
tooling, backup, and recovery all become heavier than the current task warrants.

The pressure is not that old history became unimportant. It is that old history
changed lifecycle. It should become cold, stable, indexed, and explicitly
traversed, while hot remains cheap, writable, and operator-near. The soft
trigger protects active work ergonomics without deleting or hiding durable
history.

## Stitching Lemma To Preserve

For transcript-rehydrated continuation, the useful first stitch proof is
root-prefix shaped:

```text
cold was once hot
hot now contains a full transcript-derived lineage from the root forward
therefore any overlap between the two complete lineages is a common prefix
```

If the prefix is present, nothing inside that prefix is missing. Matching should
be based on ordered message role/content and homomorphic parent topology, not
source-local id equality. Partial single-source lineage views do not need a
stitch merely to operate; stitching becomes necessary when a cold-inclusive
surface wants to treat the hot prefix and cold prefix as the same semantic
lineage, especially to recover non-message facts that did not rehydrate from
the transcript.
