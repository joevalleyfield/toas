Filed as: 260626-transcript-parallelism-design-pressures
FKA:
AKA: transcript parallelism; queue-shaped projections; coordinator and workers
Legacy index:

keywords: docs, exploration, inception, research, projection, transcript, orchestration, queue, boundaries

Parent: `260614-architecture-follow-through-coordination`
Related: `561`; `260509-multi-operator-orchestration`; `260524-exploratory-work-representation-model`; `260626-events-jsonl-multiplicity-and-merge-provenance`

# Transcript Parallelism Design Pressures

## Current Reality

TOAS already has durable graph history, multiple heads, projection semantics,
async activity lanes, and earlier design work around multiple transcript
surfaces. But repeated real workflows still tend to accumulate inside one
growing authored transcript.

That is fine during exploration, but it becomes awkward once the operator has
identified a stable loop and wants bounded repeated execution, queue-shaped
supervision, or multiple child work surfaces.

Cross-surface stepping is already mechanically possible today through shell
indirection, for example by stepping a child transcript path and then tailing
it from the coordinating transcript. The first problem is therefore not raw
possibility; it is ergonomics and bounded visibility.

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

For the strongest use-case, those repeated steps may themselves be
hierarchical:

- one broad scripted pass applies across many work units
- that pass produces smaller cohorts whose results still rhyme
- narrower shared follow-up steps then apply per cohort
- only true outliers fall into bespoke exception handling

## Why This Is Not Just "More Agents"

The pressure is architectural before it is implementation detail.

It touches:

- durable queue/claim facts
- projection identity versus transcript file identity
- parentage and reconciliation boundaries
- child activity lifecycle and terminality
- coordinator watcher rendering
- authority inheritance and narrowing

It also raises an anti-goal that has to stay explicit:

- TOAS should not solve this by introducing a hidden semantic loop

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
- What must a coordinating transcript contain so it can target another
  transcript surface explicitly while seeing enough frontier/result context to
  be useful without flooding itself?

## Working Conclusions

The current best cut is:

- this capability is better understood as one coordinating transcript plus
  bounded child projections than as generic "more agents"
- a transcript is already a surface, and a path is already a handle to it, so
  the first coordination model can be built on ordinary surfaces plus handles
  rather than on a special child-surface ontology
- the first implementation seam is durable projection identity / surface
  identity, not queue records and not merge provenance
- durable surface identity was the first concrete seam, and it is already
  implemented by closed task `561`; the older placeholder
  `260428-session-identity-orchestration` is now closed as its duplicate
- packets are likely first-class for the coherent delegated-work use-case
  because they remove degrees of freedom and make handoff/coordination more
  tractable, even though they do not eliminate later divergence
- the real power is not only flat worker parallelism; it is hierarchical
  scripted work where broad passes produce cohorts, and one user can do
  forced-serial QA over outputs that still rhyme
- `260626-events-jsonl-multiplicity-and-merge-provenance` remains real, but it
  should be treated as secondary unless coordinator/child semantics prove that
  multiple journals or extra merge provenance are required sooner

Resource/storage pressure is still a valid reason to keep multiplicity warm:

- coordination location may change the resource pressure on event journals
- split/archival history may still matter operationally

But that currently reads as a later pressure softener, not the first capability
seam.

The first capability gap is better described as:

- explicit targeting instead of shell ceremony
- enough child-frontier visibility to decide whether to step
- enough child-result visibility to understand what changed
- bounded feedback into the coordinating transcript so context management does
  not collapse under its own weight

For the coherent delegated-work case, a second gap is now explicit:

- what is the minimum packet shape that usefully constrains delegated work
  without pretending divergence will not happen later?

And a third gap now matters:

- what durable facts let broad scripted passes produce stable cohorts and
  explicit exception lanes instead of degenerating immediately into one-off
  worker handling?

And a fourth pressure is becoming visible:

- some broad passes begin as scouting rather than as already-coherent packet
  work, so the system may need affordances that let exploratory multi-surface
  work become structured packet/cohort coordination later without discarding
  what the scout pass learned

The compact note for this narrowed read now lives at:

- `docs/notes/2026-07-05-transcript-parallel-capability-seams.md`

## Exit Evidence

This task can leave inception when at least one concrete seam is ready for a
focused child task with bounded scope and testable invariants.

Useful exit artifacts would be one or more of:

- a durable record proposal for queue/packet/claim semantics
- a projection-identity proposal that clearly distinguishes lineage from file
  materialization
- a watcher/rendering contract for coordinator visibility
- a child lifecycle sketch that names live versus durable facts
- a cohort/barrier/exception-lane sketch that explains how one user can review
  many worker results serially while they still share the same QA shape
- a scouting-to-procedure bridge sketch that explains how loose broad passes
  can harden into reusable packet/cohort structure once coherence is observed

## Notes

This task is intentionally design-heavy and should resist collapsing into an
umbrella implementation bucket. The immediate value is sharper architectural
language and better task decomposition, not premature runtime expansion.

At the current stage, "better task decomposition" now means:

1. keep the coordinator/child model and its non-loop baseline here
2. use the landed `561` surface model as the base, rather than reopening
   session identity
3. name the first cohort/barrier/exception-lane model for hierarchical scripted
   passes
4. name the scouting-to-procedure bridge for exploratory broad passes that only
   later prove coherent enough to batch
5. keep `260626-events-jsonl-multiplicity-and-merge-provenance` behind that
   unless the model forces provenance work forward

The first new child is `260716-procedure-step-taxonomy`: it will turn the
cohort/barrier language into an explicit declaration contract before any queue
or scheduler semantics are proposed.

That research now resolves to the narrow implementation child
`260716-coordination-state-records-projection`. Queue/claim and
merge-provenance work remain conditional follow-ons rather than prerequisites.
