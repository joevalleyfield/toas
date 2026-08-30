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

1. Reconcile the canonical ingress contract with the implemented seams and
   incumbent normalized shapes.
2. Close execution drift in shell spawning and platform launcher behavior when
   a concrete host or failure case warrants it.
3. Decide whether the remaining ingress vocabulary, especially
   `yaml_position`, needs a bounded compatibility follow-on.
4. Add native provider calling as a later adapter only after step-state and
   result identity are stable.
5. Apply shared-path guardrails and strengthen durable-history evidence when a
   second independently implemented adapter makes that useful.
6. Advance projections, restaging, and broader orchestration only when a
   concrete consumer or recurring operator job justifies them.

The detailed classification and gates are maintained in
[`docs/notes/2026-08-29-action-intent-cluster-sequencing.md`](../../docs/notes/2026-08-29-action-intent-cluster-sequencing.md).

The next design follow-on is
[`260829-canonical-action-ingress-contract.md`](260829-canonical-action-ingress-contract.md),
which now has implementation evidence from the authority, candidate,
envelope, compound-record, toolset, and executable-language slices. No new
runtime object or ingress lane should be opened until that evidence pass
settles the remaining boundary questions.

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

## Current Status

The first implementation wave is complete and closed: user authority
propagation, ordered frontier arbitration, assistant candidate convergence,
the narrow `ActionPlan` envelope, compound request records, structured
toolset provenance, executable fence activation, Bash, and Python execution.
The cluster is at the canonical-ingress design checkpoint. Its next output is
documented contract clarification, not another implementation lane.

## Current Next Step

Refresh the canonical ingress contract and sequencing note from the completed
implementation evidence, then identify one bounded follow-on only if a
remaining invariant has a clear owner and focused test story.
