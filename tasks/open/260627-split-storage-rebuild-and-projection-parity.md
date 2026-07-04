Filed as: 260627-split-storage-rebuild-and-projection-parity
FKA:
AKA: split storage parity; rebuild parity; projection parity across segments
Legacy index:

keywords: graph, hardening, inception, correctness, projection, transcript, storage

Parent: `260626-events-jsonl-multiplicity-and-merge-provenance`
Blocked by: `260627-graph-segmented-read-query-hardening`; `260629-storage-scale-model-proof-contract`
Related: `260614-architecture-follow-through-coordination`

# Split Storage Rebuild And Projection Parity

## Current Reality

If storage splits but projection and rebuild surfaces drift, TOAS will have
preserved bytes while losing user-trust semantics. The visible proof surfaces
still need to read as one coherent history.

## Desired Reality

Physical storage segmentation should change storage layout only. It should not
change the observable meaning of:

- `toas rebuild`
- `toas transcript`
- `toas llm-input`
- `toas heads`
- `toas graph`

That parity goal needs an important nuance:

- parity does not require every ordinary operation to traverse arbitrarily deep
  cold history
- warm-history continuation should remain fast and explicit
- operations that truly need deeper cold history should either opt into that
  cost or fail/refuse clearly rather than silently falling onto a pathological
  slow path

This task is therefore partly a contract-definition slice, not just a generic
"same output everywhere" proof.

## Scope

- projection/rebuild parity over segmented history
- anchor behavior across hot and cold segments
- user-visible proof that one logical history still projects coherently
- explicit contracts for warm-history continuation versus cold-history access
- bounded behavior for ordinary operations when requested history extends beyond
  warm material

### Contract Pressure

The key contract question is not only:

```text
does split storage preserve observable meaning?
```

It is also:

```text
when is TOAS allowed to stay on a warm path, and when must it cross into cold history?
```

Likely requirements:

- recent continuation should not require loading arbitrarily old compressed
  segments
- cold-history traversal should be explicit, bounded, or diagnostically visible
- "can continue from warm history" and "can fully reconstruct deep history"
  are related but not identical contracts
- projection parity may need tiered guarantees rather than one unqualified
  promise

### Current Clarification

As of 2026-06-27, this task should assume the conservative contract:

- stitched logical history is a durable-state capability, not an automatic
  default for every user-facing history surface
- default `rebuild` and default `graph` should not silently traverse sealed
  cold segments merely because they exist
- any cold-history traversal on operator-facing surfaces should be intentional,
  explicit in the affordance, or otherwise clearly surfaced as crossing beyond
  the warm active working set
- parity therefore means "split storage does not change semantics within a
  declared access mode," not "every surface always behaves as if deep cold
  history were in the hot path"

## Non-Goals

- storage-layout ownership
- index strategy
- provenance metadata design

## Exit Evidence

- deterministic tests or acceptance-style proofs for split-storage projection
  parity
- explicit confirmation that storage segmentation does not alter transcript or
  history semantics
- an explicit warm-vs-cold contract describing when ordinary operations may
  refuse, defer, or require deeper history loading instead of silently taking a
  crazy-slow path

## Outcome

Closed on 2026-06-29.

The current contract is now explicit in the surrounding closed segmented-storage
chain:

- ordinary append/reconciliation remains hot-file scoped
- operator query/projection surfaces that advertise current logical history read
  the stitched durable view
- invalid segment layout and fatal message-history corruption fail closed rather
  than silently degrading into partial hot-file projections
- full graph rendering remains bounded by the existing node-count refusal

The `rebuild` wording in this task is historical. `260628-transcript-writeback-
surface-unification` removed the standalone `toas rebuild` command; the
transcript projection surface is now the resume-from-lineage proof surface.

Implementation evidence:

- `heads`, `history`, `transcript`, and `llm-input` already routed through
  `read_logical_history()`
- `graph` now builds from `read_logical_history()` as well, instead of reading
  only the hot events file
- `tests/test_operator_api.py::test_graph_text_uses_segmented_logical_history`
  proves cold-plus-hot graph projection parity
- `tests/test_operator_api.py::test_query_surfaces_use_segmented_logical_history`
  continues to prove transcript and LLM-input parity across the same storage
  split

## Reopened: Logical Node Identity Correction

Reopened on 2026-06-29.

The 2026-06-29 implementation evidence above is still useful, but it is not the
final semantic contract. It proves that `graph` now matches the current stitched
read seam. It does **not** prove that the stitched read seam has the right
logical node-id model.

The corrected model:

- cold/hot storage should inherit event-log semantics rather than define a
  second graph semantic model
- `n1`, `n2`, and similar message ids are journal-local labels, not durable
  global node identities
- every independent `events.jsonl` may validly have an `n1` as a non-null root
- parent links are authoritative within the journal scope that wrote them
- adjacent user events remain distinct appended occurrences and are only
  concatenated at LLM-input projection time
- selected-scope stitching should remain LCP/alignment based over event
  occurrences, not a raw concatenation that treats local ids as globally unique

Useful distinction for future design:

```text
physical occurrence identity: (source journal or segment, local message id)
projection identity: derived by LCP/content alignment over selected scopes
provider identity: LLM-input projection, including adjacent-user concatenation
```

Hashing may be useful as derivative/index material for LCP alignment and
integrity, especially if it separates stable content identity from volatile
occurrence/event identity in the git-shaped sense:

- content object-ish hash: role plus normalized content/payload
- occurrence/event object-ish hash: content hash plus parent/local metadata,
  provenance, timestamp, source scope, and other volatile fields
- segment/index hash: derivative manifest/check aid, not canonical storage
  replacement yet

The current fail-closed duplicate-id behavior is therefore too broad if it
treats same local ids across stitched scopes as corruption. Same local ids
across independent journals should be expected; duplicate ids inside one
journal scope remain suspicious or fatal.

Open questions now owned by this task:

- What is the declared access scope for each operator surface (`hot`,
  selected-window, selected-lineage, full stitched history)?
- Which surfaces may cross into cold storage by default, and which require an
  explicit selector/mode?
- What concrete LCP/alignment inputs are sufficient to stitch selected
  event-log histories without scanning unrelated sources?
- How should `graph` display qualified local ids or stitched equivalence classes
  without overstating uniqueness?
- Should per-segment manifests carry content/occurrence hashes before any
  canonical storage migration is considered?

Current status: the graph-specific questions above have now been answered under
`260629-storage-scale-model-proof-contract`. `graph` defaults hot/current,
`--sources` makes physical source scope explicit, multi-source graph output
qualifies occurrence ids, full stitch proof is diagnostic-only, and local
neighborhood aliases are shown only when selected-source LCP proof supports
them. `heads` also defaults hot/current and has an explicit `--sources` mode
for selected physical leaf-set inspection. `history`, `transcript`, and
`llm-input` now default hot/current for their respective lineage projections.
The remaining parity questions are no longer primarily default-scope questions.

## Progress: Source-Scoped Integrity Slice

Landed a first corrective implementation slice after reopening:

- `fsck_logical_history()` now treats duplicate message ids as fatal only within
  the same journal source
- same local ids across segment/hot sources are normal journal-local identity,
  not durable corruption or fsck warnings
- missing-parent checks are source-scoped, so a hot event cannot silently depend
  on a cold event's local id as its parent
- current operator projection surfaces still refuse same local ids across
  sources, but the refusal now says stitched history needs LCP alignment
  rather than calling the underlying history corrupt
- independent hot/cold roots can appear in topology, while selected-lineage
  transcript/LLM-input projection remains local until a real LCP stitcher
  exists
- explicit multi-source graph rendering now source-qualifies occurrence ids and
  avoids collapsing equal local ids or claiming one globally concatenated graph
  identity
- selected-scope LCP stitch evidence is proof/diagnostic material for an
  explicit diagnostic surface (`toas graph --stitch-diagnostics`), not default
  graph output
- graph local neighborhoods can use selected-scope LCP proof as local alias
  context without turning the full graph into a stitched projection
- `heads --sources` can inspect selected physical source leaf sets with
  source-qualified ids, so same local ids across sources do not collapse into
  one branch tip
- default `history` reads hot/current history and no longer refuses merely
  because cold and hot sources share journal-local ids
- default `transcript` and `llm-input` read hot/current history and preserve
  their distinct projection semantics without implicit stitched traversal

This narrows the remaining task: decide whether explicit source/stitch modes
need to be spun out now, or whether this parity lane can close with the
remaining surface-affordance questions owned by
`260627-history-surface-user-intent-alignment`.

`260704-projection-source-stitch-mode-contract` now owns that source/stitch
mode question for `history`, `transcript`, and `llm-input`. This task should
not absorb selector-design implementation directly; it should either close once
the hot-default correction and follow-on routing are accepted, or stay open
only for a final parity-summary update.

## Pivot: Scale-Model Proof Before More Closure Claims

On 2026-06-29, this task was threaded through
`260629-storage-scale-model-proof-contract` because the remaining gap is now
requirements-shaped before it is implementation-shaped.

Do not close this task by adding another local read/projection fix alone. First
prove the intended behavior against use-case-shaped storage configurations:

- hot-only active work
- rolled history with redundant hot context
- independent hot roots after rotation
- aligned cold/hot continuation
- ambiguous cross-source local ids
- source-local corruption
- non-message durable facts across scopes
- raw expired, summary retained

Those scale models should say which surfaces preserve meaning, which surfaces
may refuse, and which identity layer each assertion is using.

The related brainstorm and synthesis notes now make this task narrower, not
broader: this task should not absorb all history/storage design work itself.
After the recent graph slices, the next useful action is a close-or-dispatch
decision against `260629-storage-scale-model-proof-contract`, not another local
graph patch.
