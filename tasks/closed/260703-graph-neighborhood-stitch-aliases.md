Filed as: 260703-graph-neighborhood-stitch-aliases
FKA:
AKA: graph neighborhood stitched aliases; selected-source graph anchor aliases
Legacy index:

keywords: graph, surface, stitching, aliases, history

Parent: `260627-history-surface-user-intent-alignment`
Related: `260628-graph-local-neighborhood-selector`; `260629-storage-scale-model-proof-contract`

# Graph Neighborhood Stitch Aliases

## Current Reality

`toas graph --sources ...` qualifies physical occurrence ids, and
`toas graph <anchor> -N +N` can render a bounded neighborhood. Those two pieces
do not yet meet at the stitched identity layer: anchoring on one occurrence does
not bring along its selected-scope stitched aliases.

## Desired Reality

When a selected-source graph neighborhood anchor resolves to a selected-scope
LCP stitch node, the local graph view should include the equivalent occurrence
anchors and name them as aliases.

## Scope

- resolve unqualified and qualified graph neighborhood anchors through the
  selected-scope LCP stitch proof when sources are selected
- include all matched alias occurrences in the bounded neighborhood
- print compact neighborhood-local alias context
- keep full stitch proof behind `--stitch-diagnostics`

## Non-Goals

- a shared ref language
- transcript or LLM-input stitching
- automatic stitching outside explicit selected-source graph inspection

## Exit Evidence

- `toas graph n2 -0 +0 --sources segments hot` can show `hot:n2` and its
  selected stitched aliases
- missing or ambiguous anchors still fail clearly

## Outcome

Closed on 2026-07-03.

Selected-source graph neighborhoods now resolve anchors through selected-scope
LCP stitch nodes when proof is available:

- unqualified anchors such as `n2` can select the stitched aliases for the same
  common-prefix occurrence across selected sources
- qualified anchors such as `hot:h2` can still expand to their stitched
  pseudonyms
- the neighborhood output prints a compact `aliases:` line, while full stitch
  proof remains behind `--stitch-diagnostics`
- `-0 +0` includes only the matched alias occurrence nodes, not their parents or
  children
