# Segmented Storage Contradiction Inventory

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260627-split-storage-rebuild-and-projection-parity`; `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`

## Purpose

Identify likely contradictions in the current segmented-storage direction before
more implementation work hardens the wrong model.

This note assumes these claims are all desirable, but not yet fully reconciled:

- one logical history may span multiple physical journals
- message ids are journal-local
- hot reconciliation is hot-local
- graph/history may cross cold storage
- transcript projection selects a lineage
- LLM-input projection has provider-specific semantics
- stitched surfaces require LCP/alignment evidence
- duplicate local ids across sources are warnings, not source corruption

The point is not to reject the claims. The point is to name where they can pull
against each other and what scenario would expose the pressure.

## Contradiction 1: "One Logical History" Sounds Like One Namespace

Contradiction:

```text
One logical history may span multiple journals, but message ids are
journal-local.
```

Why it matters:

- code and users may treat `n1` as a durable global node identity
- graph, lookup, and projection surfaces can accidentally merge unrelated
  occurrences
- "logical history" can be misread as raw concatenation rather than selected or
  aligned history

Affected surfaces:

- `graph`
- `history`
- `heads`
- index lookup
- transcript projection by head id
- diagnostics and fsck output

Possible resolution:

- reserve raw `id` for journal-local labels
- introduce source-qualified occurrence identity in proof/test language
- define "logical history" as a selected/aligned view over sources, not a
  global-id namespace
- require any unqualified display to be scoped to one source or to a proven
  equivalence class

Test scenario that would expose it:

- `independent_hot_root_after_rotation`
- cold has `n1` root, hot has `n1` root, and graph/history must not merge them

## Contradiction 2: Hot-Local Reconciliation Versus Full-History Projection

Contradiction:

```text
Hot reconciliation is hot-local, but graph/history may cross cold storage.
```

Why it matters:

- users may assume a projection that sees cold history also changes what the
  next `step` will reconcile against
- runtime may accidentally depend on cold state if helper APIs hide access scope
- cold corruption or ambiguity could block active work that should remain safe

Affected surfaces:

- `step`
- `history`
- `transcript`
- `llm-input`
- `graph`
- recovery commands

Possible resolution:

- treat active reconciliation and historical inspection as different authority
  modes
- label surfaces by declared scope: hot, selected lineage, selected window, full
  stitched, or topology
- make projection targeting read-only unless an explicit operator action
  retargets active authority

Test scenario that would expose it:

- `source_local_corruption`
- corrupt cold source exists, hot source is valid; hot-local `step` should
  proceed while cold-inclusive graph/history refuses

## Contradiction 3: Transcript Projection Selects A Lineage, But Graph Is Topology

Contradiction:

```text
Transcript projection selects one lineage, while graph/history surfaces may
cross cold storage and expose multiple roots or branches.
```

Why it matters:

- a graph/topology view can show facts that should not appear in the selected
  transcript
- "current history" can ambiguously mean selected lineage or whole visible
  topology
- resume-from-projection may accidentally pull in unrelated roots

Affected surfaces:

- `transcript`
- `history`
- `heads`
- `graph`
- branch/head selectors
- help text

Possible resolution:

- keep transcript projection lineage-shaped
- keep graph topology-shaped
- make `history` explicitly root-to-selected-head or explicitly modeful
- avoid using "current logical history" without naming whether it is selected
  lineage or topology scope

Test scenario that would expose it:

- `independent_hot_root_after_rotation`
- graph may show hot and cold roots; transcript should render only selected hot
  lineage

## Contradiction 4: LLM-Input Projection Is Not Transcript Projection

Contradiction:

```text
Transcript projection selects a lineage, but LLM-input projection has
provider-specific semantics such as adjacent-user concatenation and prompt
material shaping.
```

Why it matters:

- provider input can differ from editable transcript text without changing
  durable history
- tests can mistakenly assert transcript text equals provider messages
- adjacent-user concatenation may be implemented as durable mutation instead of
  projection behavior

Affected surfaces:

- `llm-input`
- `transcript`
- model-call records
- prompt/protocol debugging
- acceptance tests that inspect model input

Possible resolution:

- define provider input as a derived projection from selected durable messages
- assert projection-specific transformations without mutating message events
- persist model-call request shape as evidence when needed, but not as canonical
  message history

Test scenario that would expose it:

- `non_message_facts_across_scopes`
- two adjacent durable user message events should remain distinct in history but
  may be joined in LLM-input projection

## Contradiction 5: Duplicate IDs Are Warnings, But Stitched Surfaces Must Refuse

Contradiction:

```text
Duplicate local ids across sources are warnings, not source corruption, but
stitched semantic surfaces require alignment evidence and may need to refuse.
```

Why it matters:

- warning/fatal/refusal categories can blur
- valid storage may be called corrupt
- unsafe stitched projections may proceed because fsck says the storage is ok

Affected surfaces:

- fsck
- `history`
- `transcript`
- `llm-input`
- `graph`
- CLI error wording
- recovery affordances

Possible resolution:

- separate integrity status from projection safety
- fsck says whether sources are valid and whether cross-source warnings exist
- projection surfaces decide whether their requested scope has enough proof
- refusal language should say "alignment required," not "history corrupt"

Test scenario that would expose it:

- `ambiguous_duplicate_local_ids`
- fsck reports warning; stitched transcript/history refuses; hot-local step may
  proceed

## Contradiction 6: Concatenation Is Recoverable, But Not Semantically Stitched

Contradiction:

```text
Segment ordering can recover records by physical concatenation, but semantic
history cannot be stitched by raw concatenation when local ids repeat.
```

Why it matters:

- storage recoverability and graph/projection meaning are different contracts
- a read helper that returns one list of records can hide source boundaries
- ordered records may still not form one valid message tree

Affected surfaces:

- `read_logical_history`-style helpers
- index rebuild
- graph rendering
- history projection
- fsck

Possible resolution:

- distinguish physical record stream from semantic message graph
- preserve source identity alongside records when crossing journals
- make raw concatenation acceptable for recovery/audit, not sufficient for
  selected-lineage projection

Test scenario that would expose it:

- `rolled_history_redundant_hot_context`
- concatenating cold plus hot overlap would duplicate or corrupt lineage unless
  alignment/source identity is honored

## Contradiction 7: Source-Local Parentage Versus Cross-Source Continuation

Contradiction:

```text
Parent links are authoritative within a journal source, but cold/hot
continuation may need to present one selected lineage across sources.
```

Why it matters:

- a hot event with `parent: n3` may not be allowed to silently refer to cold
  `n3`
- a real continuation across cold/hot needs a proof mechanism other than raw
  parent id matching
- missing-parent checks can be either too strict or too permissive

Affected surfaces:

- fsck
- `history`
- `transcript`
- `llm-input`
- graph topology
- stitcher/alignment diagnostics

Possible resolution:

- treat source-local parent links as local only
- cross-source lineage requires LCP/alignment evidence, rebound provenance, or
  an explicit stitch record/equivalence class
- report hot-local cross-source parent assumptions as unsafe until proven

Test scenario that would expose it:

- `aligned_cold_hot_continuation`
- hot starts from restaged boundary and continues; stitch can be shown only if
  alignment proof exists

## Contradiction 8: Retention Can Remove Raw History, But Visible Truth Wants Evidence

Contradiction:

```text
History may be expired, summarized, or redacted, but visible truth and recovery
depend on knowing what happened.
```

Why it matters:

- missing raw records can be mistaken for never-existing records
- summaries can be over-trusted as raw evidence
- graph/history surfaces may invent continuity from derived prose

Affected surfaces:

- history
- graph
- transcript projection
- search
- audit/review views
- retention diagnostics

Possible resolution:

- keep redactions, tombstones, and summary provenance as durable semantic facts
- make "raw unavailable" different from corruption
- allow summary projections, but do not use summary prose as raw lineage unless
  the surface explicitly declares that mode

Test scenario that would expose it:

- `raw_expired_summary_retained`
- old raw messages are gone, summary remains; transcript reconstruction refuses
  while summary/history view explains the retention boundary

## Contradiction 9: Index Lookup Wants Convenience, Identity Wants Qualification

Contradiction:

```text
Users and helpers want lookup by `n1`, but journal-local ids require source
qualification or alignment-derived equivalence.
```

Why it matters:

- raw id lookup can return the wrong physical occurrence
- index layers can quietly reintroduce global-id assumptions after graph/fsck
  have been corrected
- operator surfaces may display a convenient id that cannot safely be resolved

Affected surfaces:

- index lookup
- `head <id>`-style selectors
- graph node selection
- transcript/history targeting
- recovery tooling

Possible resolution:

- make unqualified id lookup valid only in a single-source or selected-scope
  context
- require source-qualified refs or a declared equivalence class for
  cross-source lookup
- diagnostics should offer candidate occurrences when unqualified lookup is
  ambiguous

Test scenario that would expose it:

- `ambiguous_duplicate_local_ids`
- lookup for `n1` across full scope should refuse or return candidates, not
  choose one

## Contradiction 10: "Full History" Is Useful, But It Can Be Too Expensive Or Unsafe

Contradiction:

```text
Operators want full graph/history inspection, but active performance and
storage lifecycle require bounded scopes.
```

Why it matters:

- a surface may silently traverse deep cold archives and become slow or brittle
- deleted/redacted/archived sources may make full views partial
- "full" without scope can become a false promise

Affected surfaces:

- `graph`
- `history`
- search
- previews
- recovery tooling
- future cross-project/epoch views

Possible resolution:

- define full history as a requested mode with declared cost and scope
- support bounded windows and previews
- make cold/archive traversal explicit or diagnostically visible
- allow refusal when scope is too broad for available indexes/proof

Test scenario that would expose it:

- `rolled_history_redundant_hot_context`
- default active surfaces stay hot/selected; explicit cold-inclusive graph may
  use indexes or refuse if proof/cost bounds are absent

## Inventory Pressure

The central contradiction is not "segmented storage is wrong." The central
contradiction is that several words currently carry too much:

- logical
- history
- current
- selected
- stitched
- full
- id
- corruption

The likely resolution is a stricter vocabulary:

- physical record stream
- journal source
- source-local message id
- physical occurrence
- selected lineage
- topology scope
- projection identity
- provider projection
- alignment/equivalence proof
- source-local corruption
- semantic refusal
- retention-limited absence

The scale-model fixture layer should force every surface assertion to name its
scope and identity layer.

