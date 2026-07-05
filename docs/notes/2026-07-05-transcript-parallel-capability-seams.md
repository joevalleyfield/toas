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

The first design question is not merge provenance. It is:

```text
what is a child surface, and what durable facts make it distinct from a
transcript file path?
```

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

## Coordinator/Child Invariants

The capability currently wants these invariants:

- transcript materialization is projection, not durable truth
- one durable graph can support many authored surfaces when surface identity is
  explicit
- continuity inference remains surface-local unless explicit rebind intent
  exists
- the coordinating transcript sees selected attention-worthy child state, not
  every child transcript as primary durable truth

## Queue And Claim Facts

Durable queue/claim facts still matter, but they do not look like the first
required seam.

They should come after surface identity is clear enough to answer:

- what exactly is being claimed
- whether a claim belongs to a child projection, an activity, or both
- how coordinator-visible progress differs from child-authored transcript state

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
- demote merge provenance to a conditional follow-on pressure
- point the next concrete work at `260428-session-identity-orchestration`

That is enough to move from broad architectural pressure toward one real new
capability without pretending the whole parallel system is already designed.
