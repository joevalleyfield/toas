# History Use-Pressure Contract

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-split-storage-rebuild-and-projection-parity`; `260627-history-surface-user-intent-alignment`

## Purpose

Synthesize the history/event-log brainstorming into a compact contract for what
TOAS history is trying to do. This is not an implementation plan.

The core framing:

```text
TOAS history is local operator harness memory over repository work. It
supplements project artifacts; it does not replace them as project truth.
```

## History Jobs

TOAS history should support these jobs:

- preserve adopted transcript lineage separately from current rendering
- recover from interruption, bad edits, failed tools, and mistaken branches
- prove what tools ran, what models produced, and what consequences resolved
- explain task pivots, decisions, artifacts, and validation evidence
- let operators navigate heads, branches, attempts, tasks, epochs, and projects
- provide durable semantic memory while allowing raw operational detail to age
  or be redacted under explicit policy
- support selected/aligned views over scoped journals instead of assuming one
  forever-global namespace

## Non-Goals

TOAS history should not promise:

- one raw forever log as the only valid model
- globally unique message ids inside every physical journal
- ordinary `step` traversal over arbitrary cold/archive history
- transcript projection and LLM-input projection having identical shape
- summaries, previews, or indexes as canonical replacement truth
- silent best-effort stitching when scope or identity is ambiguous
- raw retention of all secrets, tool output, model payloads, and exploratory
  noise forever

## Storage Pressures

The use-cases imply these pressures:

- active work must remain hot-local, cheap, and self-sufficient
- cold history should be inspectable, stable, and failure-isolatable
- journals need source/scope identity because local ids are not global
- selected history may cross physical storage only through proof, selection, or
  explicit scope
- indexes and manifests are accelerators and proof aids, not the root semantic
  truth
- repository artifacts remain primary project outputs; history links work
  process, provenance, and recovery to those artifacts
- content-addressed ideas are attractive for identity/equivalence later, but do
  not need to replace journals up front
- summaries are derived memory with provenance, not invisible compaction of
  truth

## Surface Obligations

Each surface should declare or imply its scope and identity layer.

- `step`: hot-local reconciliation authority; should not require cold traversal
  for ordinary continuation
- `history`: selected lineage over a declared scope; should not pretend topology
  is one lineage
- `transcript`: editable projection of a selected lineage; projection is not
  canonical durable truth
- `llm-input`: provider-facing projection from selected durable messages; may
  transform shape without mutating history
- `heads`: compact leaf/head view over a declared graph scope
- `graph`: topology view; must qualify source-local ids or refuse unified
  identity when alignment is missing
- fsck/integrity: source-local fatality only; cross-source local-id reuse is
  normal and distinct from projection safety
- indexes/lookups: valid only within declared scope, source qualification, or a
  proven equivalence class

## Retention Classes

History retention should distinguish:

- raw message events: lineage and projection truth; long-lived when meaningful,
  but redaction/expiration must be explicit
- tool calls/results: accountability and recovery evidence; raw payloads may
  summarize or expire separately from terminal facts
- model calls/results: prompt/protocol/debug evidence; often summarizable after
  active use
- task state changes: long-lived semantic project memory
- decisions: durable rationale; usually superseded rather than deleted
- artifacts: repository/output lifecycle plus provenance links
- indexes: rebuildable scoped accelerators with freshness checks
- projections: surfaces or published artifacts, not canonical truth unless
  explicitly retained as artifacts
- summaries: derived semantic memory with provenance and freshness markers
- redactions/tombstones: durable explanation of absence when absence would
  otherwise mislead

## Refusal Principles

Refusal is part of the semantic contract, not just an error fallback.

TOAS should refuse or warn when:

- a requested surface would merge source-local ids without alignment proof
- a selected lineage cannot be distinguished from topology
- a raw id lookup has multiple possible occurrences
- cold/full traversal is requested without sufficient scope, index, or cost
  bounds
- retained summaries cannot reconstruct raw transcript lineage
- a source has source-local corruption
- projection safety is missing even though storage integrity is acceptable

Refusal language should distinguish:

- source-local corruption
- missing alignment proof
- ambiguous selector/scope
- retention-limited absence
- stale or untrusted derived material

## Scale-Model Proof Matrix

The first consistency proof layer should cover:

| Scenario | Primary pressure | Expected safe behavior |
| --- | --- | --- |
| hot-only active lineage | single-file baseline | all current semantics hold |
| rolled history with redundant hot context | hot-local continuation plus cold inspection | `step` remains hot-local; cold-inclusive surfaces align or refuse |
| independent hot root after rotation | same local ids across sources | hot transcript/history select hot lineage; topology qualifies roots |
| aligned cold/hot continuation | selected lineage across sources | stitch is proof-derived, not raw-id-derived |
| ambiguous same local id across sources | valid storage but unsafe projection | fsck stays clean; stitched surfaces refuse |
| source-local corruption | invalid one-source history | affected scopes fail closed; unrelated hot-local work may proceed |
| non-message facts across scopes | message history versus operational facts | projections keep records distinct |
| raw expired, summary retained | retention and visible truth | raw reconstruction refuses; summary/tombstone surfaces explain limits |

## Unresolved Decisions

Open decisions before implementation closure:

- exact vocabulary for source-qualified message references and physical
  occurrences
- whether alignment proof is represented as durable records, derived indexes,
  manifests, or surface-local computation first
- which operator surfaces default to hot, selected lineage, topology, or full
  stitched scope
- how much cold/archive traversal is allowed by default for `graph`, `history`,
  search, and recovery
- how retained summaries participate in search and navigation without becoming
  fake raw lineage
- what deletion/redaction policy is acceptable for private local harness
  history
- when content-addressed identity becomes worth promoting from derived proof
  aid to storage substrate
- how cross-project, task-bound, transcript-bound, and epoch-bound views select
  and align history

## Likely Destination Pressure

The current pressure points toward:

```text
events are durable observations
journals are scoped append-only containers
segments are lifecycle/storage units
local ids are source-local affordances
logical history is selected/aligned, not globally concatenated
projections are user/runtime surfaces over declared scopes
stitching is a proof-producing operation
indexes are scoped accelerators
summaries are derived events with provenance
retention is a policy layer, not a storage accident
```

This is a direction of pressure, not a final design.
