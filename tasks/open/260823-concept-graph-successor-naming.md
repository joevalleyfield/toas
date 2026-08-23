Filed as: 260823-concept-graph-successor-naming
FKA:
AKA: graph-informed transcript naming; successor naming heuristic
Legacy index:

Parent: `260823-concept-graph-compaction`
Depends on: `260823-concept-graph-artifact-reuse`

keywords: projection, graph, follow-on, naming, usability, contract

# Concept-Graph-Informed Successor Naming

Explore and, if justified, implement a successor transcript naming heuristic
that can use concept-graph material rather than relying only on truncation of
the first sentence of the purpose.

## Motivation

Concept graphs may contain a better compact expression of the active thread,
especially after a transcript has accumulated several shifts of focus. Naming
should help users recognize trajectory without pretending that an inferred
label is authoritative.

## Open Shape

- determine whether naming reads a materialized graph artifact or a transcript
  projection directly;
- define fallback behavior when the graph is absent, stale, or ambiguous;
- decide whether the result is a suggestion, an accepted default, or a value
  requiring explicit confirmation;
- preserve stable and filesystem-safe names without overfitting to one prompt
  wording.

## Exit Criteria

The naming source, fallback rules, and acceptance behavior are explicit and
tested against representative focus shifts. Existing naming behavior remains
available as a predictable fallback, and inferred names are presented as
suggestions unless deliberately accepted.
