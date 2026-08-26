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

If the graph already contains a useful LLM-generated or graph-derived label,
the handoff and successor naming paths should reuse that material rather than
performing a second naming exercise. When the graph exposes a clear node under
an active `next action`, that node is a candidate source for the successor
transcript name.

A small versioned prompt-contract change is an acceptable way to make these
 cues reliable. The graph may explicitly identify one dominant active front
 with a concise readable label and, when justified, a nested `next action`
 node. The visible output can remain the existing nested Markdown graph; the
 added structure should improve both human reading and deterministic naming.

## Open Shape

- determine whether naming reads a materialized graph artifact or a transcript
  projection directly;
- define fallback behavior when the graph is absent, stale, or ambiguous;
- decide how a graph-provided label is identified, including whether the
  current Markdown graph shape needs an explicit title or next-action field;
- use prompt engineering and a new prompt version where needed to make the
  dominant active-front label and optional `next action` node explicit without
  adding a second naming model call;
- define when a clear node under `next action` is specific enough to name the
  successor and when the existing handoff objective remains the fallback;
- avoid a second model naming call when an accepted graph label is already
  available;
- decide whether the result is a suggestion, an accepted default, or a value
  requiring explicit confirmation;
- preserve stable and filesystem-safe names without overfitting to one prompt
  wording.

## Exit Criteria

The naming source, fallback rules, and acceptance behavior are explicit and
tested against representative focus shifts. Existing naming behavior remains
available as a predictable fallback, and inferred names are presented as
suggestions unless deliberately accepted.
