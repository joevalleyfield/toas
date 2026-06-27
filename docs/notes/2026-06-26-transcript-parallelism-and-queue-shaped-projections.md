# Transcript Parallelism And Queue-Shaped Projections

Status: DIRECTIONAL
Related tasks: `260626-transcript-parallelism-design-pressures`; `260509-multi-operator-orchestration`; `260614-architecture-follow-through-coordination`

## Purpose

Capture an emerging design pressure: some operator work stops being "one
transcript doing a loop" and starts wanting "one coordinating transcript
managing many bounded projection surfaces."

This note does not propose immediate implementation. It records the pressure,
names the architectural constraints, and identifies the task shapes that would
need to emerge if TOAS moves toward queue-driven transcript parallelism.

## Problem

Repeated workflow tasks currently tend to accumulate inside one growing working
transcript.

That shape is acceptable during exploration, but it degrades once the workflow
stabilizes:

- context keeps growing even when the work units are now repetitive
- setup instructions are repeated by hand
- reseeding new work costs operator attention
- the operator stays trapped in loop-shaped mechanics rather than queue-shaped
  supervision
- bounded parallel work is awkward because the main authored surface becomes
  both controller and worker

The pressure is not merely "more agents." It is a mismatch between:

- durable event-log semantics that already allow many lineages and projections
- a current working model that still centers one authored transcript as the
  practical place where repeated work happens

## Desired Shift

The desired operator posture is:

```text
one coordinating transcript manages many bounded projection surfaces
```

instead of:

```text
one transcript keeps doing the loop
```

The operator should be able to stay mostly in the coordinating transcript while
child projections absorb bounded execution, produce structured outcomes, and
surface only what needs human attention.

## Architectural Reading

This pressure aligns with several existing TOAS architectural commitments:

- the transcript file is a surface, not canonical truth
- durable truth lives in the append-only event log
- projections may be materialized, rebuilt, archived, or omitted without
  changing durable history
- activity and projection semantics should remain distinct from transport or UI
  adapters
- runtime hosts may coordinate warm bounded work without becoming the semantic
  owner of transcript meaning

This pressure also sharpens a boundary already visible in earlier notes about
multi-surface operation:

- a projection lineage is durable
- a transcript materialization is optional and replaceable

For transcript parallelism, that distinction becomes first-class rather than
incidental.

## Candidate Object Model

These objects appear necessary if TOAS wants queue-shaped transcript
parallelism.

### Event Log

The shared durable substrate remains `events.jsonl`.

Additional durable fact families would likely be required alongside message,
control, tool, and model-call records:

- queue records
- packet lifecycle records
- claim records
- worker/projection run records
- reconciliation records
- attention/blocked records

The event log would keep global append order without forcing one global
conversation head.

### Projection

A projection is a durable conversation-like identity with its own frontier and
lineage.

Examples:

- `main`
- `bugtriage-supervisor`
- `bugtriage-worker-017`
- `docs-keeper`

This should not be conflated with a particular markdown file path.

### Transcript Materialization

A transcript file is one possible materialization of a projection, not the
projection itself.

Examples:

- `.toas/main.md`
- `.toas/workers/bugtriage-017.md`
- an editor buffer
- no materialization at all until operator inspection is needed

### Seed

A seed is a reusable initializer extracted after exploratory iterations reveal a
stable loop.

Likely fields:

- purpose
- workflow instructions
- allowed context
- parameters
- output contract
- expected operator choices

### Queue

A queue is a durable set of work obligations.

It is not merely a rendering convenience. If queue-driven work is real, queue
state should be durable and auditable rather than inferred only from transcript
text.

### Packet

A packet is a bounded unit of work:

- one incoming bug
- one batch of STIGs
- one failing test cluster
- one reconciliation row

Packets need explicit shape limits so projections remain bounded.

### Claim

A claim is the concurrency primitive connecting a packet to a projection or run.

Without durable claims, "parallelism" degrades into hidden ambient coordination
or duplicate work risk.

### Run

A run is one execution attempt for a projection. Projection identity may outlive
any single run.

### Watcher

A watcher is the compact coordinating-transcript representation of a child
projection or packet state. It exists for operator attention management rather
than as canonical state.

## Lifecycle Sketch

### 1. Explore

The operator works manually in one normal transcript until the true workflow is
understood.

### 2. Extract

The system or operator extracts:

- seed
- packet shape
- output contract
- queue shape
- watcher rendering pattern

### 3. Queue

Remaining work is converted into durable packets.

### 4. Spawn Or Materialize

Child projections are created from the seed plus packets.

Some may get materialized as transcript files immediately; others may remain
durable-only until opened.

### 5. Work

Each child projection:

- claims a packet
- works in bounded context
- emits durable events
- requests attention if blocked
- produces structured output on completion

### 6. Watch

The coordinating transcript renders a compact watch group summarizing child
state.

### 7. Reconcile

Completed outputs are merged back into durable state through explicit
reconciliation records or adoption actions.

## Design Pressures

This idea creates real pressure on multiple architecture domains.

### Durable State

Questions:

- What durable record families represent queues, packets, claims, and
  reconciliation without overloading message-event space?
- Does projection identity need its own durable record type beyond current
  control records?
- What facts must survive process death versus remain live activity state?

### Transcript Reconciliation

Questions:

- How does edited transcript text align when many projections have separate
  authored surfaces?
- What is the handoff between surface identity, projection identity, and
  parent-selection rules?
- Can a coordinating transcript safely act on child outcomes without silently
  inheriting child lineage?

### Operator Semantics

Questions:

- What does "step the coordinator" mean when child projections are already
  running or waiting on attention?
- Which actions are transcript-frontier consequences versus queue-control
  commands?
- What is the semantic difference between spawning a new child, reopening a
  prior projection, and replaying within one projection?

### Activity Lifecycle

Questions:

- Is child work best modeled as current async activities, or is a new
  projection-run lifecycle needed?
- Which terminal facts are durable?
- How should cancellation, retries, and abandoned claims behave?

### Projection And Rendering

Questions:

- What is the watcher contract in a transcript or watch stream?
- How do links or affordances render without becoming canonical state?
- How compact can child summaries be while preserving auditable drill-down?

### Effective Policy And Authority

Questions:

- Which seeds are allowed to spawn what kinds of child work?
- How are authority, grants, or workspace restrictions inherited or narrowed?
- Does queue work need explicit policy inheritance records?

### Transport And Protocol

Questions:

- Do current stream lanes already support multiple child projections, or do they
  only support one activity with internal sub-lanes?
- Should coordinator-visible watcher updates be their own semantic stream shape
  or a projection-layer rendering over existing events?

## Invariants To Preserve

Any future design here should preserve at least these current TOAS invariants:

- prior durable history is never mutated
- transcript materialization is never canonical durable truth
- projection text or watcher rendering must not become the source of queue or
  claim truth
- direct user intent and model-addressable capability remain distinct
- child-lane or child-projection completion must not be mistaken for whole-run
  terminality
- model backend lifecycle must not quietly expand into generic worker
  supervision just because child projections exist

## Likely Task Split

If this direction becomes active, it likely wants several focused tasks rather
than one umbrella implementation:

1. projection identity and transcript-materialization terminology cleanup
2. queue/packet/claim durable-record design
3. coordinator watcher rendering contract
4. child projection activity/run lifecycle semantics
5. seed extraction and output-contract shape
6. reconciliation/adoption semantics for completed child work
7. CLI or host surfaces for listing/opening/spawning/inspecting projections

## Recommendation

Treat transcript parallelism as an architecture pressure and design program, not
as a near-term implementation commitment.

The near-term useful move is:

- keep this pressure visible in docs
- connect it to existing multi-surface and orchestration exploration
- open only narrow child tasks once one ownership seam becomes concrete enough
  to test

That is more aligned with TOAS than jumping directly from a promising operator
idea to a broad runtime refactor.
