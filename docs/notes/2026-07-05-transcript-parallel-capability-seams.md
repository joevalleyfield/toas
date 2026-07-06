# Transcript Parallel Capability Seams

Status: DIRECTIONAL
Task Link: `260626-transcript-parallelism-design-pressures`
Related: `260428-session-identity-orchestration`; `260626-events-jsonl-multiplicity-and-merge-provenance`

## Purpose

Turn the broad transcript-parallelism pressure into a smaller set of first
seams that can drive real capability work.

## Main Conclusion

The parallel-task capability should be treated as:

```text
one coordinating transcript
plus bounded child projections
over shared durable history
```

For the strongest use-case, this is not merely flat parallel delegation.
The process steps themselves may be hierarchical:

- one broad scripted pass can apply across many packets
- that pass can produce smaller cohorts that still rhyme
- narrower shared follow-up steps can then apply per cohort
- only the true stragglers need bespoke exception handling

The first design question is not merge provenance. It is:

```text
what explicit handles and visibility affordances let one transcript coordinate
another transcript surface without becoming a hidden loop?
```

One useful correction:

- a transcript is already a surface
- a path is already a handle to a surface
- "child" may be a coordination relation among ordinary surfaces rather than a
  fundamentally different surface type

## Meaning-First Order

The current best order is:

1. `260626-transcript-parallelism-design-pressures`
2. `260428-session-identity-orchestration`
3. `260626-events-jsonl-multiplicity-and-merge-provenance`

Reason:

- first define the coordinator/child model
- then make explicit surface identity concrete
- only then pay merge/provenance complexity if the first two seams prove it is
  necessary

## First Capability Seam

The first concrete seam is durable projection identity, not queue records and
not multi-journal merge semantics.

The nearby multi-surface design note already gives a credible first model:

- one stable `surface_id` per authored control surface
- explicit `surface_bind` / `surface_select` / `surface_rebind` /
  `surface_guardrail` control records
- fail-closed protection against accidental cross-surface inheritance

That means the likely first real implementation child is session/surface
identity rather than packet claims or journal multiplicity.

## Existing Mechanical Baseline

Cross-surface stepping is already mechanically possible today. A coordinating
transcript can shell out to a child transcript surface through commands shaped
like:

```text
toas step .toas/child.md >> .toas/child.md
tail -20 .toas/child.md
```

So the first capability gap is not raw possibility.

It is the lack of:

- explicit targeting instead of shell-ceremony
- enough frontier visibility to know what the child surface is about to do
- enough result visibility to know what was added
- bounded feedback into the coordinating transcript without flooding it

This is context-management pressure magnified more than a raw execution gap.

## Coordinator/Child Invariants

The capability currently wants these invariants:

- transcript materialization is projection, not durable truth
- no hidden semantic loop is introduced just to make many surfaces move
- one durable graph can support many authored surfaces when surface identity is
  explicit
- continuity inference remains surface-local unless explicit rebind intent
  exists
- the coordinating transcript sees selected attention-worthy child state, not
  every child transcript as primary durable truth

At least in the first useful version, "parallel" should therefore read more
like explicit interleaving and observation across many surfaces than like an
autonomous scheduler.

It should also read more like hierarchical process narrowing than like one
flat swarm of unrelated workers.

## Immediate Operator Question

The next concrete question is:

```text
what must appear in a coordinating transcript so it can target and operate on
another transcript surface explicitly, while seeing enough frontier/result
context to be useful and not so much that it floods itself?
```

That should be answered before queue/claim semantics become the center of the
design.

## Queue And Claim Facts

Durable queue/claim facts still matter, but they do not look like the first
required seam.

They should come after surface identity is clear enough to answer:

- what exactly is being claimed
- whether a claim belongs to a child projection, an activity, or both
- how coordinator-visible progress differs from child-authored transcript state

Packets now read as more than optional decoration for the coherent
delegated-work use-case.

Their value is that they remove degrees of freedom:

- they give the child a bounded work unit
- they give the coordinator a clearer handoff target
- they reduce how much intent must be reconstructed from a whole transcript
- they make delegation tractable before work diverges

That does not mean packets solve the whole problem.

Important caveat:

- packets constrain divergence; they do not eliminate it
- once packet-bounded work forks, expands, or mutates beyond its original
  shape, the broader coordination problem returns

So the current best split is:

- ordinary surfaces plus handles define the base cross-surface coordination
  model
- packets become first-class when the use-case is coherent delegated work
- claims come later if concurrency/accountability across packets actually needs
  a stronger primitive

The next packet-shaped design question is therefore:

```text
what is the minimum packet shape that usefully constrains delegated work
without pretending divergence will not happen?
```

## Hierarchical Script And Cohort Model

The real power in the capability may be that process steps themselves can be
shared hierarchically.

That means:

- one script can run across many packets at once
- outcomes from that script can form cohorts
- each cohort can then take a narrower shared script
- one user can do forced-serial QA at the cohort barrier because the outputs
  still rhyme

This is stronger than generic parallelism because it changes the economics of
divergence:

- divergence does not immediately imply one-off bespoke handling
- many packets can still cluster into small groups with comparable next steps
- only the real outliers need exception handling

Useful working terms:

- `script`: the shared procedure many worker surfaces follow
- `packet`: one bounded work unit
- `cohort`: a subset of packets/workers that land in the same outcome class
  after a script step
- `barrier`: the resync point where the coordinator reviews many results in a
  comparable shape
- `exception lane`: the place where non-rhyming results go when they no longer
  fit a useful cohort

## Divergence Policy

The current likely policy is:

- keep workers in the shared scripted path as long as their results still rhyme
- when a worker stops rhyming, move it into a problem-child / exception lane
- from there, either:
  - get it back onto the current cohort's path
  - couple it to a later batch/cohort where it rhymes again
  - or handle it as a true exception

That means divergence is not denied. It is triaged.

Packets and cohorts therefore do not eliminate divergence; they localize and
route it.

## Scouting Before Procedure

Not every broad pass begins with a coherent packet or procedure model.

Sometimes the operator has to scout first to learn whether enough work units
actually rhyme to justify one.

Example shape:

- find every `events.jsonl`
- run `salvage_root_divergence` across them
- observe whether the outcomes cluster into a meaningful shared next step

At the start of that pass, coherence is only suspected.

So the capability likely needs a distinction between:

- `scouting`: a loose broad pass used to discover whether shared structure
  exists
- `procedure`: a declared packet/cohort/barrier model used once enough shared
  structure has been found

This creates a new affordance pressure:

```text
scouting work should be convertible into structured coordination without
throwing away what the scout pass learned
```

The conversion target is not clear yet, but the need is:

- preserve enough observed state from the scouting pass
- make later cohort formation cheaper
- avoid forcing the operator to either overdesign up front or rediscover the
  same structure twice

Because scouting may meander, preserving "everything" is probably the wrong
goal for context management.

The more useful target may be condensed waypoints:

- enough to show the path that was tried
- enough to explain why the path looked promising at the time
- enough to judge later whether a waypoint was actually critical to the
  discovered path or only incidental exploration

So the bridge may need to preserve not just outcomes, but selected path
discovery summaries that are compact enough to carry forward and evaluable
enough to revisit in hindsight.

Working principle:

```text
coherency is often sampled before it is formalized
```

So the system may eventually want some bridge artifact or declaration family
that lets an exploratory multi-surface pass harden into packet/cohort
structure once the work proves it is worth batching.

## Procedure Barriers Versus TOAS Steps

One useful clarification is that procedure steps and TOAS steps are not the
same thing.

- a **procedure step** is a barrier in the larger scripted process
- a **TOAS step** is one local turn that may or may not move a worker closer to
  that barrier

Workers can therefore take different numbers of TOAS steps while still being
on the same procedure step.

That means the useful synchronization state is not:

```text
everyone took one more TOAS step
```

It is:

```text
who is still working toward procedure step N
who has reached the barrier for procedure step N+1
who has fallen out of the scripted path
```

## Procedure-State Cohorts

The simplest useful state model now looks like:

- `in_progress`
- `reached_barrier`
- `blocked`
- `off_track`

These states are effectively mini-cohorts.

Workers can be grouped by:

```text
procedure_step + status + cohort_key
```

where `cohort_key` is an optional narrower grouping when many workers are still
on the same step but already rhyme in a more specific way.

Operationally:

- `reached_barrier` workers mostly wait
- `in_progress` workers keep stepping
- `blocked` and `off_track` workers move into exception/remediation handling or
  a later cohort

## Procedure-State Declarations

TOAS is unlikely to infer these states reliably from transcript evolution
alone. The executing intelligence will usually need to declare them.

That declaration may be supported by multiple evidence sources:

- explicit commands / structured declarations
- milestone events such as commits or key-file writes
- evaluators tied to the current procedure step

So the real design problem is not "prove progress in the abstract."

It is:

```text
define a procedure-step taxonomy that makes state declarations concrete enough
to group, wait, or reroute workers safely
```

## Next Design Seam: Procedure-Step Taxonomy

The next closure-shaped question is therefore:

- what kinds of procedure steps exist?
- what declared facts can each kind emit?
- what milestone hooks or evaluators can each kind use?

A plausible first outline is:

1. **Step kind**
   - review
   - transform
   - verify
   - classify
   - extract
   - reconcile
   - dispatch
   - escalate

2. **Declared facts**
   - `procedure_step`
   - `status`
   - `subject`
   - `artifact`
   - `summary`
   - `needs`
   - `blocked_by`
   - `cohort_key`
   - `exception_reason`

3. **Evidence / evaluators**
   - explicit declaration
   - command completion
   - file write / key artifact update
   - commit created
   - test/check pass
   - step-kind-specific evaluator

The main value of this taxonomy is not perfection. It is making barrier
recognition concrete enough that one user can do serial QA over groups that
still rhyme.

The same taxonomy may also need to support promotion from scouting into
procedure:

- which observed facts from a scout pass are durable enough to keep?
- which become packet seeds, cohort keys, or declared barrier outcomes later?
- which scouting waypoints were critical to path discovery, and which can be
  safely collapsed away once the procedure is known?

## `events.jsonl` Multiplicity

Multiplicity/merge provenance remains a real pressure, but it currently reads
as secondary for this capability.

Why it still matters:

- it may soften resource pressure on very large event histories depending on
  where coordination lives
- it may become necessary if child histories later need to cohere across
  journals or imported worker state

Why it is not first:

- the capability can likely get meaningful shape before multiple journals or
  merge provenance are required
- paying that complexity too early risks solving storage questions before the
  coordinator/child model is explicit

Working stance:

```text
keep LCP-first single-journal truth unless coordinator/child semantics force
stronger multiplicity or merge provenance sooner
```

## Immediate Follow-Through

The first useful closure shape for the design-pressure task is:

- state the coordinator/child model explicitly
- name durable projection identity as the first implementation seam
- name the explicit non-loop baseline: ordinary surfaces plus handles,
  explicit targeting, and bounded visibility
- keep packetization in scope for the coherent delegated-work use-case, but as
  the structure that constrains coordination rather than as a claim that
  divergence disappears
- add the scouting-to-procedure bridge as a first-class pressure, because some
  broad passes must discover coherence before they can safely declare it
- add hierarchical scripted passes, cohort formation, and exception-lane
  routing to the core model rather than treating them as later embellishments
- demote merge provenance to a conditional follow-on pressure
- point the next concrete work at `260428-session-identity-orchestration`

That is enough to move from broad architectural pressure toward one real new
capability without pretending the whole parallel system is already designed.
