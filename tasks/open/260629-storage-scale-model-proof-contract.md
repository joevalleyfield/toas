Filed as: 260629-storage-scale-model-proof-contract
FKA:
AKA: scale-model history proofs; storage consistency proof; segmented storage requirements parent
Legacy index:

keywords: graph, storage, projection, investigation, active, correctness, contract, parity

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocks: `260627-split-storage-rebuild-and-projection-parity`
Related: `260627-history-surface-user-intent-alignment`; `260627-history-surface-corruption-semantics`; `260628-graph-local-neighborhood-selector`

# Storage Scale-Model Proof Contract

## Current Reality

The segmented-storage work exposed a larger requirements gap: implementation
started proving local read/query behavior before TOAS had a small set of
user-facing history shapes that define what consistency means.

Current docs contain useful but partially cross-pressured claims:

- one logical durable history may span multiple physical journals
- hot reconciliation must stay hot-local
- message ids such as `n1` are journal-local labels
- stitched operator views must not pretend raw local ids are globally unique
- cold traversal should be explicit, bounded, or diagnostically visible
- transcript and LLM-input projection preserve different meanings

Those claims are individually plausible. They are not yet proven together
against scale-model histories that resemble the real shapes TOAS is trying to
support.

## Desired Reality

TOAS has a compact, named proof matrix that answers:

```text
For this use-case-shaped history layout, which surfaces must preserve which
meaning, which surfaces may refuse, and which contradictions are fatal?
```

The proof matrix should become the parent for narrower implementation slices,
instead of letting every graph/index/projection fix define its own local
version of the storage model.

## Brainstorming Inputs

The first brainstorming pass produced separate artifacts on purpose:

- `docs/notes/2026-06-29-operator-history-use-cases.md`
- `docs/notes/2026-06-29-runtime-history-use-cases.md`
- `docs/notes/2026-06-29-history-retention-and-lifecycle.md`
- `docs/notes/2026-06-29-history-storage-alternatives.md`
- `docs/notes/2026-06-29-scale-model-history-scenarios.md`
- `docs/notes/2026-06-29-segmented-storage-contradiction-inventory.md`
- `docs/notes/2026-06-29-history-use-pressure-contract.md`

Keep those notes separate while the model is still being refined. This task
should synthesize from them rather than turning into a catch-all design dump.

## Contract Shape

The parent contract should settle these dimensions before implementation
follow-ons claim closure:

- history jobs: what durable history is for beyond the current transcript
- authority modes: hot-local active reconciliation versus selected/cold
  inspection
- identity layers: journal-local id, physical occurrence, selected lineage,
  projection identity, provider projection
- surface obligations: what each operator/runtime surface must preserve,
  warn about, or refuse
- retention classes: raw facts, semantic facts, derived indexes/projections,
  summaries, tombstones
- refusal vocabulary: source-local corruption, missing alignment proof,
  ambiguous selector/scope, retention-limited absence, stale derived material
- scale-model fixtures: the small histories that prove consistency across
  surfaces

## Use-Case Scale Models

The initial proof set should cover these shapes before more implementation
work claims semantic closure:

1. **Hot-only active work**
   - one writable `events.jsonl`
   - ordinary LCP reconciliation, transcript projection, history, heads, and
     graph views should behave exactly as today's single-file model

2. **Rolled active history with redundant hot context**
   - older records sealed in a numbered segment
   - hot file retains enough overlapping context for active reconciliation
   - full-history inspection can cross cold storage, while ordinary step
     remains hot-local

3. **Independent hot root after rotation**
   - cold segment has one root and hot has a separate root with the same local
     ids allowed across sources
   - topology may show independent journal-local roots
   - selected-lineage projection must not stitch by raw id

4. **Aligned cold/hot continuation**
   - after rotation, the working transcript still contains visible old turns
     and the next step re-ingests them into the new hot journal
   - hot history therefore contains a transcript-derived prefix or boundary
     that can be LCP-aligned with a sealed segment
   - projection identity is derived from alignment, not local-id equality
   - graph/history surfaces can explain or qualify the stitch

5. **Ambiguous cross-source local ids**
   - the same local ids exist across journals without enough alignment evidence
   - storage fsck remains clean because ids are source-local
   - stitched semantic surfaces refuse until a selector or stitcher can prove
     intent

6. **Corrupt source-local history**
   - duplicate message ids or missing parents occur inside one journal source
   - integrity checks fail closed
   - recovery affordances can reason about the specific source

7. **Non-message durable facts across storage scopes**
   - tool results, model calls, anchors, heads, and binds appear in cold/hot
     scopes
   - message-event projection stays distinct from durable operational facts
   - rendered `RESULT` blocks remain projection output, not durable messages

8. **Raw expired, summary retained**
   - raw operational history is absent by retention/redaction policy
   - a summary, decision record, or tombstone remains
   - exact raw reconstruction refuses while summary/tombstone views explain the
     limit

## Surface Contract Questions

For each scale model, explicitly classify:

- `step`: hot-local reconciliation authority only
- `history`: selected lineage over a declared access scope
- `transcript`: transcript-shaped projection of a selected lineage
- `llm-input`: provider projection, including adjacent-user concatenation
- `heads`: compact leaf-set/topology summary over its declared scope
- `graph`: topology view with qualified occurrence identity or explicit refusal
- index lookup: source-qualified lookup unless a stitcher has produced an
  equivalence class
- fsck: source-local fatality only; cross-source local-id ambiguity belongs to
  lookups and projection surfaces

## Current Output

The compact contract note now lives at:

- `docs/notes/2026-06-29-history-use-pressure-contract.md`

The fixture-facing scenario note now lives at:

- `docs/notes/2026-06-29-scale-model-history-scenarios.md`

The contradiction inventory now lives at:

- `docs/notes/2026-06-29-segmented-storage-contradiction-inventory.md`

The first mismatch matrix now lives at:

- `docs/notes/2026-06-30-history-contract-mismatch-matrix.md`

These are directional, not final. The next step is to turn them into a
mismatch matrix against current code/tests before opening more implementation
follow-ons.

The first opened follow-on is:

- `260630-source-qualified-logical-index-lookup`

## Progress: Cross-Source Local-Id Vocabulary Correction

On 2026-06-30, tightened terminology after clarifying that same local ids across
multiple journal sources are not duplicates in the integrity sense. Duplicate
message ids remain source-local corruption only when repeated inside one source.

The integrity/refusal concept should be read as:

```text
same local message id across sources => ambiguous bare lookup or stitching
duplicate message id inside one source => source-local corruption
```

Follow-up correction: the first case is not an fsck warning. It is expected
journal-local behavior; only an unqualified lookup or stitched surface has to
refuse or request proof.

## Progress: Transcript-Rehydrated Cold/Hot Continuation Fixture

On 2026-06-30, added a current-behavior scale fixture for the cold/hot
continuation use case. The fixture models the real bridge:

```text
sealed cold segment exists
working transcript still contains visible cold turns plus a new turn
step re-ingests those turns into the empty hot journal
```

The current expected behavior is intentionally conservative: storage integrity
stays clean, hot-local projection works, source-qualified index candidates are
visible, and stitched semantic surfaces refuse until TOAS has explicit
alignment proof.

## Exit Evidence

- a compact use-pressure contract naming history jobs, non-goals, storage
  pressures, surface obligations, retention classes, refusal principles,
  scale-model matrix, and unresolved decisions
- a contradiction inventory that names likely semantic mismatches and the
  scenario that should expose each one
- a fixture-facing scenario note naming per-surface expected behavior for each
  scale model
- a mismatch matrix for current code paths/tests that still assume globally
  unique message ids, raw concatenation, or undeclared cold traversal
- high-level tests or acceptance-style fixtures for at least the first five
  scale models, once the matrix identifies the first implementation seam
- follow-on tasks opened only after a concrete owner, acceptance shape, and
  test seam are known
