Filed as: 260626-transcript-parallelism-design-pressures
FKA:
AKA: transcript parallelism; queue-shaped projections; coordinator and workers
Legacy index:

keywords: docs, exploration, inception, research, projection, transcript, orchestration, queue, boundaries

Parent: `260614-architecture-follow-through-coordination`
Related: `260509-multi-operator-orchestration`; `260524-exploratory-work-representation-model`

# Transcript Parallelism Design Pressures

## Current Reality

TOAS already has durable graph history, multiple heads, projection semantics,
async activity lanes, and earlier design work around multiple transcript
surfaces. But repeated real workflows still tend to accumulate inside one
growing authored transcript.

That is fine during exploration, but it becomes awkward once the operator has
identified a stable loop and wants bounded repeated execution, queue-shaped
supervision, or multiple child work surfaces.

## Desired Reality

One coordinating transcript should be able to manage many bounded projection
surfaces without making transcript materialization or watcher rendering the
source of durable truth.

The system should eventually be able to:

- discover a repeatable workflow
- extract a reusable seed
- represent remaining work as durable packets
- spawn or watch bounded child projections
- surface only attention-worthy events back to the coordinating transcript
- reconcile completed work back into durable state

## Why This Is Not Just "More Agents"

The pressure is architectural before it is implementation detail.

It touches:

- durable queue/claim facts
- projection identity versus transcript file identity
- parentage and reconciliation boundaries
- child activity lifecycle and terminality
- coordinator watcher rendering
- authority inheritance and narrowing

Treating this as generic "multi-agent" work would hide the more important TOAS
question: which parts are durable semantic truth, and which parts are only
projection or operator affordance?

## Evidence

- The design outline captured on 2026-06-26 describes a coherent shift from one
  looping transcript to one coordinating transcript plus bounded child
  projections.
- `docs/notes/2026-05-24-multi-active-transcript-surfaces-design.md` already
  establishes that one durable graph can support multiple authored surfaces when
  surface identity is explicit.
- `tasks/open/260509-multi-operator-orchestration.md` already records adjacent
  exploration around supervisor/worker transcript shapes.
- `docs/runtime-ownership.md` and `docs/runtime-direction.md` already separate
  durable state, transcript reconciliation, operator semantics, activity
  lifecycle, transport, and projection/rendering in a way this idea would need.

## Open Questions

- Does TOAS need durable projection identity before it needs durable queues?
- Should child work be modeled as projections first and activities second, or
  the reverse?
- What durable record family should own packet claims and reconciliation facts?
- How should a coordinating transcript step when children are live, blocked, or
  complete?
- Which parts of seed extraction are explicit operator action versus inferred
  helper behavior?

## Exit Evidence

This task can leave inception when at least one concrete seam is ready for a
focused child task with bounded scope and testable invariants.

Useful exit artifacts would be one or more of:

- a durable record proposal for queue/packet/claim semantics
- a projection-identity proposal that clearly distinguishes lineage from file
  materialization
- a watcher/rendering contract for coordinator visibility
- a child lifecycle sketch that names live versus durable facts

## Notes

This task is intentionally design-heavy and should resist collapsing into an
umbrella implementation bucket. The immediate value is sharper architectural
language and better task decomposition, not premature runtime expansion.
