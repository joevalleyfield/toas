Filed as: 260829-declared-objective-lane
FKA:
AKA: declared objective; operator objective; objective query surface
Legacy index: 462

Related: `462`; `456`

# Declared Objective Lane

Replace the dormant `/intent` affordance with a clearly named declared-
objective surface for explicit operator-maintained task context.

## Historical Origin

This task reworks the affordance implemented by [462: Intent Lane Durability
And Query Surfaces](../closed/462-intent-lane-durability-and-query-surfaces.md),
which was spawned from [456: Configurable Session Transcript Path And
Naming](../closed/456-configurable-session-transcript-path-and-naming.md).
The former name is retained here only to explain the historical relationship;
it is not a compatibility commitment.

## Why Rename

The existing affordance is an explicit user operation for declaring session-
level task context. It is not an action request, an inferred goal, a callable
tool intention, or an execution candidate.

The name `intent` collides with those other concepts and makes the durable
history taxonomy harder to understand. The affordance has not been used in
the wild, so there is no user-facing compatibility surface that requires
retaining the old command, record kind, or field names.

## Desired Semantics

An operator may explicitly declare, inspect, annotate, pause, complete, or
cancel an objective. Objective records remain append-only, non-message
records and do not alter message numbering or lineage.

An objective is optional context. It does not authorize execution, imply a
callable action, or require a relationship to any particular tool request.

## Scope

- replace the preferred `/intent` command family with an objective-named
  command family;
- rename the CLI inspection surface from `toas intents` to an objective-named
  surface;
- rename the durable record and helper vocabulary to objective terminology;
- preserve append-only updates, current-objective resolution, query behavior,
  and existing projection invariants;
- update tests, prompt/help material, documentation, and task references;
- remove the old product vocabulary rather than adding a compatibility alias.

## Non-Goals

- inferring objectives from transcript content;
- representing callable action intent;
- introducing goal/plan/action records as a universal TOAS ontology;
- linking every objective to a tool request or execution;
- changing message-event lineage or durable-history numbering semantics;
- changing unrelated uses of `intent` that describe action arbitration,
  execution metadata, or focus inference.

## Exit Criteria

- the affordance is consistently named around declared objectives;
- no product, CLI, prompt, or code compatibility path preserves `/intent`;
- the old name appears only in historical task material;
- tests prove objective append, query, status, note, and projection behavior;
- the resulting vocabulary does not collide with action-intent terminology;
- the parent historical task contains a non-destructive erratum linking here.

