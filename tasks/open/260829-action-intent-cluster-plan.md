Filed as: 260829-action-intent-cluster-plan
FKA:
AKA: action-intent cluster; tool-calling cluster; action-path plan
Legacy index:

Related: `260803-tool-intent-ingress-separation`; `260829-user-authority-profile-propagation`; `260829-declared-objective-lane`

# Action-Intent Cluster Plan

Coordinate the classification, sequencing, and rationalization of open work
around action ingress, tool calling, authority, execution, durable evidence,
resolution, and consequence projection.

## Intent

Define a provenance-bearing path from recognized action requests to canonical
history and explicit TOAS step outcomes.

This task coordinates the design and dependency decisions needed to move the
existing system toward that path. It does not impose a universal goal/plan/
action ontology on TOAS and does not absorb implementation ownership from its
children.

## Scope

- classify existing open issues as core, enabling, validation, adjacent, or
  orthogonal;
- identify dependencies and implementation gates across those issues;
- preserve confirmed status-quo semantics while naming architectural pressure;
- open bounded follow-ons only when an owner, seam, and test story are clear;
- close, merge, supersede, or defer tasks when the classification establishes
  that their current framing is no longer useful;
- keep design notes and the workboard aligned with the resulting task graph.

## Confirmed Boundaries

- direct-user action intent is intentionally unbounded;
- assistant action intent follows a user-configurable assistant execution
  policy, normally bounded but not an immutable ceiling;
- both paths retain ordinary validation, operating-system permissions, durable
  request/result evidence, and explicit user-mediated `step` boundaries;
- declared objectives are explicit operator context, not callable action
  intent or execution authority;
- shared taxonomy does not require one record kind, one parser, or one
  universal runtime hierarchy;
- existing normalized plans and durable record families remain the starting
  point until a concrete invariant requires more structure.

## Current Sequence

1. Implement user authority-profile propagation.
2. Close execution drift in shell spawning and platform launcher behavior.
3. Refine the ingress boundary and incumbent normalized action shape.
4. Add executable-fence and conditional JSON ingress lanes.
5. Add native provider calling as a later adapter.
6. Certify cross-lane equivalence and strengthen durable-history evidence.
7. Advance projections, restaging, and broader orchestration only when a
   concrete consumer or recurring operator job justifies them.

The detailed classification and gates are maintained in
[`docs/notes/2026-08-29-action-intent-cluster-sequencing.md`](../../docs/notes/2026-08-29-action-intent-cluster-sequencing.md).

## Non-Goals

- implementing every issue in the cluster;
- replacing working behavior for symmetry alone;
- renaming `shell` before a concrete migration decision;
- making native provider calling mandatory;
- introducing hidden execution loops;
- treating inferred focus, summaries, or projections as execution authority;
- making direct-user authority configurable without a demonstrated use case.

## Exit Criteria

- the cluster has a reviewed classification and dependency sequence;
- each active implementation slice has one primary owner and bounded write
  surfaces;
- obsolete or duplicated issue framing is explicitly closed, merged, or
  superseded rather than silently ignored;
- the parent and child tasks point to the same confirmed authority and
  roundtrip semantics;
- the first implementation slice can proceed without reopening the cluster's
  core intent statement.

## Current Next Step

Implement and verify
[`260829-user-authority-profile-propagation.md`](260829-user-authority-profile-propagation.md),
then use its observed seam to refine the ingress follow-on split.
