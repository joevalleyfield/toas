Filed as: 260823-projection-discoverability
FKA:
AKA: prompt surface discoverability; projection progressive disclosure
Legacy index:

Parent: `260823-concept-graph-compaction`
Related: `260823-conversation-map-projection`

keywords: projection, surface, follow-on, usability, docs, contract

# Projection And Prompt Discoverability

Develop the discoverability and progressive-disclosure model for TOAS-owned
prompt and projection surfaces as the family grows beyond `concept-graph` and
`compact`.

## Motivation

TOAS now owns prompt-backed operations that have different purposes and
visibility semantics. Users need to discover the available surfaces and their
relationships without learning implementation names or being forced into a
second observer channel.

## Open Shape

- decide where the inventory belongs: help, prompt discovery, transcript
  affordances, or a combination;
- distinguish executable-context projections from conceptual and map-like
  projections;
- show defaults, optional visibility, provenance, and likely downstream use
  without making every operation verbose;
- keep the ordinary transcript as the primary surface until a concrete need
  justifies another projection surface.

## Exit Criteria

The surface model and user-facing inventory are documented, coherent across
CLI and transcript affordances, and validated against the existing prompt and
projection operations. The work should improve discovery without introducing a
new observer or scheduler as a prerequisite.
