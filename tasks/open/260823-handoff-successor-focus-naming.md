Filed as: 260823-concept-graph-successor-naming
FKA: 260823-concept-graph-successor-naming
AKA: handoff-derived successor naming; successor focus; graph-informed transcript naming; successor naming heuristic
Legacy index:

Parent: `260823-concept-graph-compaction`
Depends on: `260823-concept-graph-artifact-reuse`

keywords: projection, graph, follow-on, naming, usability, contract

# Handoff-Derived Successor Focus Naming

Explore and, if justified, implement a successor transcript naming heuristic
that derives a concise continuation focus from the required compaction handoff.

## Motivation

The compaction handoff already sees the complete transcript, including any
preceding concept-graph projection. It is therefore the better ownership
boundary for carrying forward a concise expression of the active thread after
several shifts of focus. Naming should help users recognize trajectory without
pretending that an inferred label is authoritative.

The handoff prompt should ask for one short successor-focus phrase as part of
its normal compaction output. The model may derive that phrase from a concept
graph when one is present, but successor construction should consume the
handoff field rather than inspect a graph artifact or perform a second naming
exercise.

A small versioned handoff prompt-contract change is an acceptable way to make
this cue reliable. The visible handoff remains human-readable Markdown; the
added section should provide a concise, non-authoritative label for deterministic
filesystem-safe slugging.

## Decision

Successor naming is handoff-derived, not graph-artifact-derived. Add an
explicit `## Successor Focus` field to a new handoff prompt version. It should
contain one short human-readable phrase naming the work the successor should
continue, preferring the active next action or dominant active front. The
phrase must not include dates, punctuation, certainty claims, or filesystem
syntax.

The existing successor naming path will parse and slug `## Successor Focus`
when present, then fall back to `## Current Objective`, then to
`session-handoff`. The result remains a suggestion until the user accepts it.
Concept-graph material can inform the handoff's choice when available, but no
graph lookup and no second model naming call are required during continuation.

## Open Shape

- define and version the handoff `Successor Focus` field;
- define parsing and fallback behavior when the field is absent, stale, or
  ambiguous;
- ensure the handoff prompt can use preceding concept-graph material without
  making the graph a runtime naming dependency;
- decide whether the result is a suggestion, an accepted default, or a value
  requiring explicit confirmation;
- preserve stable and filesystem-safe names without overfitting to one prompt
  wording.

## Exit Criteria

The handoff naming source, fallback rules, and acceptance behavior are explicit
and tested against representative focus shifts, including handoffs produced
with and without a preceding concept graph. Existing naming behavior remains
available as a predictable fallback, and inferred names are presented as
suggestions unless deliberately accepted.
