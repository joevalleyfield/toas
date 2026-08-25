Filed as: 260823-concept-graph-artifact-reuse
FKA:
AKA: materialized concept graph; concept graph artifact; successor graph reuse
Legacy index:

Parent: `260823-concept-graph-compaction`
Related: `260823-concept-graph-successor-naming`; `260823-projection-discoverability`

keywords: projection, graph, follow-on, contract, usability, transcript

# Materialize And Reuse Concept Graphs

Define and implement the next projection boundary for `concept-graph`: retain
the generated graph as a named `.toas/` artifact that can be inspected and
optionally reused when constructing a successor transcript.

## Motivation

The current first slice durably records the graph projection and appends it to
the transcript, but using it across a session boundary still requires manual
copying or reconstruction. A materialized artifact could preserve the useful
conceptual framing without conflating it with compact's executable handoff.

## Open Shape

- decide whether the artifact is a latest projection, an append-only history of
  projections, or both;
- preserve source message/head identity and prompt provenance;
- define whether successor construction opts in explicitly or follows a visible
  operator choice;
- specify how missing, stale, or incompatible artifacts are reported without
  blocking ordinary continuation.

## Exit Criteria

An artifact lifecycle and reuse contract are documented, source-linked, and
covered by focused tests. Ordinary compact continuation remains valid when no
graph artifact exists, and reuse is observable in the successor transcript or
its durable history.
