Filed as: 260920-effective-policy-provenance-inspection
FKA:
AKA: branch policy sources; effective settings inspection; transcript overlay provenance
Legacy index:

keywords: runtime, implementation, active, correctness, usability, transcript, policy, provenance, config

Parent: `260920-branch-projected-policy-program`
Depends on: `260920-lcp-direct-policy-deltas`; `260920-config-load-result-reconstitution`
Related: `260920-transcript-control-documentation-contract`; `260825-visible-transcript-turn-ids`

# Inspect Effective Branch Policy Provenance

Give an operator a compact inspection surface that explains the effective
branch-visible policy for a selected step without claiming a universal settings
ladder or exposing secrets.

## Current Reality

The branch reducers now establish direct config, grants, target selection,
command context, workspace scope, and immutable config-load results. Their
provenance is durable but scattered across message and record types. Existing
`/config --sources` describes ordinary configuration sources, not the active
transcript overlay or its compatibility fallbacks.

## Desired Reality

An operator can inspect the applicable policy for the selected branch/frontier
and see, per domain, the resolved value or state, contributing source message
IDs or immutable result identity, and any legacy fallback. The surface remains
an inspection projection: it does not serialize a settings checkpoint or make
ephemeral child environment/secrets durable.

## Acceptance Criteria

- Select an explicit transcript head or the active frontier without reading
  unrelated sibling records as policy.
- Show provenance for the currently implemented branch reducers: ordinary
  config overrides (including reconstituted config loads), shell grants,
  selected target, command context, and workspace scope.
- Clearly distinguish transcript-overlay sources from ordinary config
  baseline sources and label any compatibility fallback.
- Avoid exposing secret values or representing child-process environment as a
  TOAS bootstrap environment setting.
- Add focused projection/CLI tests plus transcript examples where they clarify
  branch isolation, and retain 100% coverage.
- Update the control-state contract only if the implemented inspection surface
  makes an existing statement inaccurate; do not introduce a checkpoint.

## Allowed Write Surfaces

- policy/graph projection helpers and their narrow CLI or operator-command
  presentation adapter
- focused runtime, graph, CLI, and transcript-policy tests
- the control-state contract only for an implementation-proven correction
- this task, its parent task, and generated workboard

## Exclusions

- Settings checkpoint creation or replay.
- A single cross-domain precedence resolver.
- New branch reducers or source-reference syntax.
- Secret disclosure and durable capture of host/bootstrap environment.

## Progress

- Added a head-aware graph projection that partitions supported policy records
  into source-linked selected-lineage evidence and explicitly labeled unlinked
  compatibility fallback. Rendering and domain reduction remain next.

## Completion Evidence

- Compact inspection output demonstrates a branch-local source, an immutable
  config-load reconstitution source, and an explicitly labeled fallback.
- `ruff check .` and the full test suite pass at 100% coverage.

Status: Active.
