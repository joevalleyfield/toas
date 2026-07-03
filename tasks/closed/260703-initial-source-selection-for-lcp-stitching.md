Filed as: 260703-initial-source-selection-for-lcp-stitching
FKA:
AKA: --sources; selected event-log histories; stitch source enumeration
Legacy index:

keywords: graph, storage, projection, implementation, follow-on, correctness, contract

Parent: `260629-storage-scale-model-proof-contract`
Blocks: `260627-split-storage-rebuild-and-projection-parity`
Related: `260630-selected-scope-lcp-stitch-contract`

# Initial Source Selection For LCP Stitching

## Current Reality

TOAS has a selected-scope LCP stitch result over already-selected event-log
histories, but no small contract for turning operator source selection into
those histories.

The next seam is selection, not rendering. TOAS needs an argparse-friendly
intermediate form before it grows a richer project/workspace/task/epoch
selection language.

## Desired Reality

Source selection starts with a minimal literal vocabulary:

- `hot`: this project's current `.toas/events.jsonl`
- `segments`: this project's sealed `.toas/segments/*-events.jsonl[.gz]`,
  expanded in ordinal order
- explicit event-log paths, used in the order provided

Default behavior remains hot/current when no source selection is provided.
Cross-project stitching remains possible through explicit paths, not through
new aliases or glob language.

## Scope

- add a helper that expands source tokens into selected event-log histories
- default empty selection to hot/current
- keep `segments` concrete and local to the provided hot events path
- allow explicit source paths for cross-project experiments
- reject future-loaded aliases such as `all`, `local`, `cold`, and `workspace`
- preserve selected source order so stitch canonical identity is not decided by
  path-string sorting
- prove the selected histories feed directly into the selected-scope LCP stitch
  helper

## Non-Goals

- add CLI flags to operator commands
- render stitched `history`, `graph`, `transcript`, or `llm-input`
- build a source-selection DSL
- expand globs inside TOAS
- define project/workspace/task/epoch source names

## Acceptance Shape

- no source tokens selects hot/current history
- `segments` selects sealed local segments in ordinal order
- `hot` selects the current hot event log
- explicit paths select those files in the order provided
- reserved aliases refuse clearly instead of becoming early syntax sugar
- duplicate expanded paths refuse clearly
- selected histories can be passed to `selected_scope_lcp_stitch`

## Outcome

Closed by adding a source-token expansion helper for selected event-log
histories. The helper defaults to hot/current history, expands `segments` in
sealed ordinal order, accepts explicit event-log paths in the order provided,
rejects reserved future aliases, rejects duplicate expanded paths, and returns
histories that can feed directly into `selected_scope_lcp_stitch`.

This intentionally does not add CLI flags or surface rendering yet.
