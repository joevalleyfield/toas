Filed as: 260628-graph-local-neighborhood-selector
FKA:
AKA: graph anchor window; graph node plus-minus selector; local graph neighborhood view
Legacy index:

keywords: surface, implementation, follow-on, usability, graph, history, projection, naming

Parent: `260627-history-surface-user-intent-alignment`
Related: `260628-graph-selected-history-topology-framing`

# Graph Local Neighborhood Selector

## Current Reality

`graph` now has a clearer topology-first contract, but there is still an
operator gap between:

- `history` as one root-to-head lineage
- `graph` as the whole currently visible logical history graph
- any future richer ref or node selection language

That gap is not well served by more framing alone. The missing affordance is a
small, explicit way to ask for a bounded local subset of the graph on purpose.

## Desired Reality

TOAS should offer a tiny graph-local selector shape that lets an operator anchor
on one node and expand a bounded amount backward and forward through the graph
without introducing a full shared ref language yet.

The motivating unified selector shape is:

- anchor node
- `-n` backward expansion
- `+n` forward expansion

For example, conceptually:

```text
toas graph n42
toas graph n42 -3
toas graph n42 +2
toas graph n42 -3 +2
```

The important property is not exact syntax yet. The important property is that
one coherent local-neighborhood model should replace a pile of unrelated
one-off subset flags.

## Focus

- define the smallest viable anchor-and-expansion contract for `graph`
- decide whether the first slice should accept only raw node ids or a slightly
  more abstract selector token
- define what "backward" and "forward" mean in graph terms
- define whether the rendered subset is the reachable induced subgraph within
  those bounds or a stricter path-biased view
- keep this command-local rather than turning it into the first hidden version
  of a shared global ref language
- preserve `graph` as topology-first rather than re-deriving `history`

## Questions To Settle

- Should bare `toas graph <node>` imply `-0 +0`, a small default neighborhood,
  or full local incident context?
- Is backward expansion ancestors-only, and forward expansion descendants-only,
  or should either side include immediate sibling context where the topology
  would otherwise read deceptively sparse?
- How should invalid node ids fail so the error remains surface-oriented?
- Does the first slice need to work only for zero-arg current logical history,
  or should it also compose with future projection/selection flags?

## Non-Goals

- a full shared ref language
- a generic history query DSL
- branch-selection heuristics that are not operator-addressable
- lineage-plus-siblings shorthand beyond what falls naturally out of the local
  neighborhood contract

## Exit Evidence

- one explicit bounded selector contract for local graph neighborhoods
- help/usage language that teaches the anchor and `-n` / `+n` model in user
  terms
- focused implementation plus tests for at least the first anchor-window slice
- explicit notes on what richer future ref-language work remains deferred
