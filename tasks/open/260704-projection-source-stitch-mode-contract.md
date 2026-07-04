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
toas history --sources segments hot hot:n3
toas transcript --sources segments hot 000001:n2
toas llm-input --sources segments hot hot:n3
```

Initial syntax should minimize aliases. Do not spend future names such as
`all`, `local`, `cold`, `workspace`, or project/workspace globs in this slice.

## Anchor Rules To Settle

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
- Without an explicit anchor, selected-source lineage surfaces need a clear
  default: either refuse as ambiguous, choose the selected hot head when
  present in scope, or require an explicit anchor for all multi-source modes.

The last bullet is the main open design decision.

## Refusal Principles

- Source-local corruption remains fatal only for the affected source.
- Cross-source same local ids are expected; they are not fsck warnings.
- Missing selected sources are selector errors.
- Missing selected anchors are target errors.
- Ambiguous bare local ids are target errors.
- Lack of LCP/equivalence proof is a projection refusal, not storage
  corruption.
- Ordinary LCP divergence is not refusal by itself; it simply bounds how far
  stitched aliasing can enrich or align the projection.

## Exit Evidence

- compact contract note or task update settles source syntax, anchor syntax,
  default selected-source behavior, and refusal vocabulary
- scale-model scenarios identify at least:
  - single-source explicit anchor
  - multi-source qualified anchor
  - ambiguous bare local id
  - stitched equivalent anchor
  - divergence after common prefix
- implementation follow-ons are split by surface or shared projection helper,
  not hidden inside this requirements task
