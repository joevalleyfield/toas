# Operational State vs Conversational Projection

TOAS now treats shell authorization/grant state as authoritative operational state, not transcript-derived conversational projection.

## Boundary

- Conversational projection: compactable, rewrite-friendly transcript material (`TOAS:USER`, `TOAS:ASSISTANT`, projected `RESULT` text).
- Operational state: durable non-message records and config-backed policy layers that must remain authoritative across compaction/reprojection.

## Shell grant policy (v1 layering)

Effective scope precedence (highest to lowest):

1. transient
2. session
3. head
4. workspace
5. user
6. global
7. defaults

## Practical implication

`/shell` mutations no longer rely on parsing prior transcript text to reconstruct policy. Effective grants are resolved from operational records and config baseline, so transcript compaction or rewriting cannot silently change authorization behavior.
