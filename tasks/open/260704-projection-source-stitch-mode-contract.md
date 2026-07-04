Filed as: 260704-projection-source-stitch-mode-contract
FKA:
AKA: projection source modes; qualified anchor projection; explicit stitch modes
Legacy index:

keywords: history, transcript, llm-input, sources, stitch, projection, selector

Parent: `260629-storage-scale-model-proof-contract`
Related: `260627-split-storage-rebuild-and-projection-parity`; `260627-history-surface-user-intent-alignment`; `260630-stitch-plan-contract`

# Projection Source/Stitch Mode Contract

## Current Reality

The main zero-arg history surfaces now default hot/current:

- `graph`
- `heads`
- `history`
- `transcript`
- `llm-input`

`graph` and `heads` already have explicit `--sources ...` modes for broader
physical source inspection. `history`, `transcript`, and `llm-input` still lack
explicit source/stitch modes, even though operators will need them to inspect
older segments, project selected cold/hot lineages, and use LCP proof when a
qualified anchor has equivalent occurrences across sources.

## Desired Reality

Define the common selector and stitch contract for lineage-shaped projection
surfaces before implementing more CLI behavior.

The contract should answer:

- how `--sources <hot|segments|path> ...` applies to `history`, `transcript`,
  and `llm-input`
- how anchors are spelled when local ids are source-local
- when a bare local id is allowed
- when a qualified id such as `hot:n3` or `000001:n3` is required
- when stitched aliases can select one equivalence class
- how surfaces refuse when selected sources lack sufficient proof

## Working Model

Defaults stay hot/current:

```text
toas history
toas transcript
toas llm-input
```

Broader projection should be explicit:

```text
toas history --sources segments hot
toas history --sources segments hot hot:n3
toas transcript --sources segments hot 000001:n2
toas llm-input --sources segments hot hot:n3
```

Initial syntax should minimize aliases. Do not spend future names such as
`all`, `local`, `cold`, `workspace`, or project/workspace globs in this slice.

## Anchor Rules To Settle

- Without an explicit anchor, selected-source lineage surfaces should choose
  the most recent available head in the selected source set.
- If `hot` is in the selected source set and has a head, that is the
  unambiguous default anchor.
- If `hot` is not selected, the default anchor may be the most recent head
  across the selected sources, using source order and source/record metadata
  as the tie-break contract to be settled before implementation.
- In a single-source scope, bare local ids may identify anchors.
- In a multi-source scope, bare local ids should refuse if more than one source
  contains the id.
- Qualified occurrence ids identify a physical occurrence.
- If selected LCP proof says multiple occurrences are equivalent, any
  pseudonym should select the stitched equivalence class for projection.
- Equivalence ends at divergence; no surface should guess beyond proven common
  prefix.
- Oldest qualified identity can remain the canonical identity for stitch
  evidence, but display should preserve pseudonyms where helpful.

## Surface Semantics To Settle

- `history --sources ... <anchor>` renders a bounded root-to-anchor lineage.
- `transcript --sources ... <anchor>` renders transcript projection for that
  lineage.
- `llm-input --sources ... <anchor>` renders provider/model-input projection
  for that lineage, preserving provider-specific transforms.
- `history --sources ...` without an anchor should be useful as a first query:
  it should let the operator discover an initial lineage question without
  having to run `heads` first.

The remaining design decision is the tie-break rule for selected-source scopes
that do not include `hot`, or include no usable hot head.

## Refusal Principles

- These are query tools. Source-local corruption should be reported as a
  diagnostic about why the requested result set could not be produced, not as
  a reason to treat unrelated selected sources as corrupt.
- Cross-source same local ids are expected; they are not fsck warnings.
- Missing selected sources are selector errors.
- Missing selected anchors are target errors.
- Ambiguous bare local ids are target errors.
- Lack of LCP/equivalence proof is a projection refusal, not storage
  corruption.
- Ordinary LCP divergence is not refusal by itself; it simply bounds how far
  stitched aliasing can enrich or align the projection.
- If a selected-source query cannot produce a result set, the surface should
  return actionable diagnostics naming which source, anchor, or proof condition
  blocked the result.

## Exit Evidence

- compact contract note or task update settles source syntax, anchor syntax,
  default selected-source behavior, and refusal vocabulary
- scale-model scenarios identify at least:
  - multi-source no-anchor default with `hot`
  - multi-source no-anchor default without `hot`
  - single-source explicit anchor
  - multi-source qualified anchor
  - ambiguous bare local id
  - stitched equivalent anchor
  - divergence after common prefix
- implementation follow-ons are split by surface or shared projection helper,
  not hidden inside this requirements task

## Progress

- Added the first `history --sources ...` implementation slice: when no anchor
  is supplied and `hot` is selected, history chooses the hot source's current
  head as the default anchor and renders that selected-source lineage with
  qualified ids. Explicit qualified anchors, stitched equivalent anchors, and
  no-hot default tie-breaks remain unsettled follow-ons.
- Extended `history` with explicit anchors using the unambiguous
  `history [limit] [anchor] --sources ...` shape. Multi-source history accepts
  qualified anchors, accepts bare anchors only when they resolve uniquely or to
  one stitched common-prefix equivalence class, and refuses missing or
  ambiguous anchors with targeted diagnostics. No-hot default tie-breaks remain
  unsettled.
- Settled the initial no-anchor/no-hot default for `history`: hot still wins
  when selected and non-empty; otherwise the last selected source with a head
  wins. This keeps `segments` naturally old-to-new while leaving explicit path
  order under operator control.
- Extended the same selected-source/anchor resolver to `transcript` and
  `llm-input`, including envelope mode. The CLI uses
  `transcript [anchor] --sources ...` and
  `llm-input [anchor] --sources ... [--envelope]`, matching the history
  constraint that anchors precede variadic source tokens.
- Extracted selected-source projection resolution into a shared
  projection-selection helper with surface-neutral diagnostics, then added a
  scale-model test that runs `history`, `transcript`, and `llm-input` against
  the same cold/hot fixture to prove their anchor behavior stays aligned.
