Filed as: 260823-intent-tail-focus-trace
FKA:
AKA: focus tracing; intent-tail extraction; change-of-focus history; intent trajectory
Legacy index:

keywords: projection, exploration, inception, inference, transcript, provenance, trajectory, intent

Related: `260823-concept-graph-compaction`; `260823-conversation-map-projection`

# Intent-Tail Extraction And Focus Trace

Explore how TOAS can derive a durable or inspectable trace of changing focus
from intent-tracking tails and surrounding transcript evidence.

## Current Reality

The intent-tree tail currently helps keep the model and user grounded under
limited prose. Its language can drift, so successive tails cannot always be
compared mechanically as strings.

In nearly every case where an intent tail is available, extraction should be
mechanical. The tail should be treated as observed evidence rather than
reconstructed unnecessarily.

The tail may not always be available. Missing evidence must remain visible as
unavailable; inference may supplement, normalize, or bridge gaps, but should
not silently impersonate direct extraction.

## Desired Direction

Explore an inferred focus trace that can identify:

- the foregrounded intent or concept;
- what has receded;
- whether a change is refinement, branching, return, abandonment, or
  replacement;
- the evidence and confidence supporting the interpretation.

The trace should tolerate linguistic drift while retaining links to the raw
tail and source events.

Queries for this purpose may be short and often out-of-cache. They need not be
synchronous, but this task does not imply a scheduler, push channel, or second
conversation. Results may remain available for an existing surface to inspect
when useful.

## Epistemic States

- `observed`: mechanically extracted from an available intent-tracking event;
- `inferred`: reconstructed or normalized from evidence;
- `tentative`: plausible but unresolved interpretation;
- `unavailable`: no usable tail or sufficient evidence exists.

## Exit From Inception

Promote a bounded follow-on when one focus-transition class and one existing
consumer have a clear representation, provenance shape, and testable evidence
set.
