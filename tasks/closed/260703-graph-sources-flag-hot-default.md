Filed as: 260703-graph-sources-flag-hot-default
FKA:
AKA: graph --sources; graph hot default; selected-source graph plumbing
Legacy index:

keywords: graph, surface, projection, implementation, follow-on, correctness, contract

Parent: `260629-storage-scale-model-proof-contract`
Blocks: `260627-split-storage-rebuild-and-projection-parity`
Related: `260703-initial-source-selection-for-lcp-stitching`; `260630-selected-scope-lcp-stitch-contract`

# Graph Sources Flag Hot Default

## Current Reality

`toas graph` still reflects an earlier broad logical-history read path. That
path implicitly crosses sealed segments and hot history, even though the
current semantic contract says base/default behavior should stay hot/current
unless a broader source scope is selected.

## Desired Reality

`toas graph` is equivalent to `toas graph --sources hot` under base config.
Broader history must be requested with explicit source tokens.

The first CLI surface should wire source selection without making graph
rendering pretend it already understands stitched equivalence classes.

## Scope

- add `--sources` parsing for `toas graph`
- accept multiple source arguments after `--sources`
- default graph source selection to `hot`
- route graph rendering through selected source histories
- preserve existing `--projection temporal|consequence`
- leave stitched/pseudonym graph rendering for a later slice

## Non-Goals

- change `history`, `transcript`, `llm-input`, or `heads`
- add source selection to operator slash commands
- implement stitched graph labels or pseudonym display
- build source-selection aliases beyond `hot`, `segments`, and explicit paths

## Acceptance Shape

- `toas graph` equals `toas graph --sources hot`
- `toas graph --sources segments hot` opts into local sealed segments plus hot
- argparse accepts multiple `--sources` values
- reserved aliases refuse through the source-selection helper
- existing graph projections still render

## Outcome

Closed by wiring `toas graph --sources` through the CLI/session-view/operator
path. Default graph rendering now selects hot/current history, matching
`--sources hot`; explicit `segments hot` opts into local sealed segments plus
hot history. The graph surface now routes through selected source histories
without claiming stitched/pseudonym rendering.

Stitched graph labels, operator slash-command parity, and source selection for
other surfaces remain outside this slice.
