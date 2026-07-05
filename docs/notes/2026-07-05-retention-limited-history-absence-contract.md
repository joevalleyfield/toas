# Retention-Limited History Absence Contract

Status: DIRECTIONAL
Task Link: `260705-retention-limited-history-absence-contract`
Related: `260629-storage-scale-model-proof-contract`; `260627-history-surface-user-intent-alignment`; `260627-history-recovery-tooling`

## Purpose

Pull the remaining retention-facing seam out of the broader storage scale-model
 work and state it compactly.

The core distinction:

```text
raw history can be unavailable by policy without the system being corrupt
```

This note is not a retention implementation plan. It is the contract for how
TOAS should name and surface that state.

## Primary Claim

Retention-limited absence is a first-class semantic state.

It means:

- raw source history once existed or may have existed within the declared scope
- that raw material is now unavailable because of retention, redaction,
  externalization, or a durable tombstone policy
- later surfaces must explain the limit instead of silently reconstructing,
  pretending the material never existed, or mislabeling the state as
  corruption

It does not mean:

- source-local corruption
- selector ambiguity
- missing alignment proof
- stale derived material by itself

Those are separate refusal classes, even if they can coexist.

## Vocabulary

Use these terms distinctly:

- `source-local corruption`: the source is internally invalid and cannot be
  trusted as history input
- `selector ambiguity`: the operator asked for a target or scope that does not
  resolve safely
- `missing alignment proof`: multiple valid source-local histories exist, but
  the requested semantic stitch is not proven
- `retention-limited absence`: raw history is unavailable by declared
  lifecycle policy
- `stale derived material`: an index, manifest, summary, or projection may no
  longer correspond to the currently retained raw source set

The key rule is:

```text
retention-limited absence is a visible truth boundary, not an integrity failure
```

## Durable Facts That Should Outlive Raw Loss

When raw material is expired or redacted, TOAS should prefer keeping compact
semantic facts that explain the gap:

- tombstones or redaction markers
- summary provenance
- decision records
- artifact provenance
- retention-scope metadata
- freshness/coverage metadata for derived material

These facts should not masquerade as raw lineage. Their job is to preserve
visible truth about absence and surviving meaning.

## Surface Contract

### `step`

- hot-local reconciliation remains authoritative
- absent cold raw history is not consulted as active continuation input
- retention-limited old scope should not block ordinary hot-local work unless
  the active operation explicitly depends on that missing raw scope

### `history`

- may acknowledge that a selected scope crosses expired or tombstoned history
- should refuse exact raw lineage reconstruction when that lineage is no longer
  retained
- may show summary or tombstone boundaries, but must label them as retained
  semantic facts rather than raw events

### `transcript`

- must refuse to recreate raw turns that no longer exist
- must not expand summary prose into transcript turns
- if a future summary-oriented view exists, it should be a separately declared
  mode or sibling surface rather than implicit transcript fallback

### `llm-input`

- must not fabricate provider input from summary-only memory
- may refuse with retention-limited language when exact raw prompt lineage is
  unavailable
- retained summaries may still inform a future explicit summary-for-context
  surface, but not ordinary exact lineage projection

### `graph`

- should not invent missing raw edges from summary prose
- may show declared gaps, tombstones, or retained-summary nodes in an explicit
  mode
- default graph truth should remain honest about where raw topology ends

### `fsck` and related diagnostics

- expired or tombstoned raw scope is not corruption when policy/provenance
  explains it
- diagnostics should distinguish invalid source files from expected
  retention-limited gaps

## Derived Material Rules

Indexes, manifests, and retained projections are accelerators or artifacts, not
ground truth.

When raw source disappears:

- rebuildable derived material may be discarded
- stale derived material must not silently answer as if it were fresh raw truth
- surfaces may refuse, invalidate, or clearly downgrade to retained-summary
  semantics
- derived artifacts that were intentionally published can remain visible, but
  they must carry scope/provenance/freshness meaning

The important split:

```text
summary retained after raw loss can still be truthful
stale derived material pretending raw coverage is truthful cannot be
```

## Recommendation On Surface Shape

Do not make summary/tombstone output an implicit fallback inside raw-history
surfaces.

Preferred direction:

- keep ordinary `history`, `transcript`, `llm-input`, and `graph` honest about
  raw-history limits
- allow those surfaces to emit retention-boundary diagnostics
- if summary-first browsing becomes worthwhile, expose it as an explicit mode
  or sibling surface

This keeps "exact retained lineage" and "surviving semantic memory" legible as
different operator questions.

## Minimal Fixture Pressure

The first proof layer does not need a full retention subsystem. One or two
small fixtures should be enough to pressure the contract:

- `raw_expired_summary_retained`: raw lineage gone, summary/tombstone remains,
  exact transcript/history reconstruction refuses, and boundary diagnostics stay
  distinct from corruption
- `stale_derived_after_raw_loss`: retained index/projection metadata exists
  after raw removal, and surfaces invalidate or downgrade instead of treating
  stale derivation as fresh lineage truth

## Open Questions

- whether retention facts should live as durable records, side manifests, or
  both
- how much tombstone detail is acceptable when the reason for redaction itself
  may be sensitive
- whether summary-oriented browsing is worth a dedicated public surface or only
  targeted diagnostics
- how search should behave when only retained summaries survive

## Working Conclusion

The remaining retention seam is narrower than the earlier storage-model parent.

The likely contract direction is:

```text
raw lineage absence should refuse exact reconstruction
retained semantic facts should explain the limit
diagnostics should name retention separately from corruption and ambiguity
summary views should be explicit, not silent fallbacks
```

That is enough to guide follow-on fixture or implementation work without
reopening the broader segmented-history identity debate.
