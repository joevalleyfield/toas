# Artifact Continuations And Polyglot Runtime State

Status: EXPLORATORY
Related task: `260614-shell-owned-backend-lifecycle`
Related notes: `2026-06-26-transcript-parallelism-and-queue-shaped-projections`

## Purpose

Capture an architectural alternative that emerged from the shell-attached warm
host spike and the surrounding discussion of persistent polyglot runtimes.

The initial picture was a TOAS host supervising warm workers, perhaps one per
language. That picture is mechanically plausible, but it may overvalue process
residency. For LLM-driven work, much of the useful continuity may instead be
expressed as a constructively cached tree of executable artifacts,
intermediates, and evidence.

This note does not select a product direction or propose immediate
implementation. It records the pressure, names a candidate object model, and
clarifies where persistent live runtimes still appear materially different.

## The Question

A persistent shell or language interpreter offers:

- low-latency repeated interaction
- continuous steering against live state
- preserved imports, objects, connections, jobs, and process handles
- a naturally conversational write, try, inspect, and adjust loop

The cost is the same accumulated state:

- later behavior depends on hidden mutations
- environment and language context become polluted
- reproduction and branching become difficult
- stale processes, objects, connections, and assumptions remain active
- the runtime can become an opaque source of truth

This resembles context accumulation in a long LLM conversation. Continuity is
valuable, but unbounded implicit continuity can eventually work against the
operator.

The design question is therefore not simply whether TOAS should keep runtimes
warm. It is which kinds of continuity deserve to persist, in what form, and
which of them must remain live.

## LLMs Change The Economics Of A REPL

Humans often use REPLs because entering and organizing a complete runnable
artifact is comparatively expensive. An LLM can commonly generate a larger
coherent script, test, fixture, or experiment in one write-and-try cycle than a
human would attempt interactively.

That makes this loop unusually natural:

```text
write artifact
    -> execute in a clean process
    -> retain useful outputs and evidence
    -> revise or derive the next artifact
```

Once model reasoning dominates elapsed time, reconstructing a process may be
cheap relative to reconstructing the thought that produced the next useful
experiment. The more important cache may be the executable continuation of the
reasoning rather than the interpreter heap.

This does not eliminate latency as a product concern. It narrows the claim:
interpreter residency should earn its complexity through important live state
or a measured interaction benefit, not through a general assumption that one
warm worker per language is inherently desirable.

## Conversational Build Tree

The candidate model resembles a Make-driven build tree whose intermediate
artifacts sometimes remain deliberately in place:

```text
intent
  \-- generated experiment
        |-- execution result
        |     |-- stdout / stderr
        |     |-- measurements
        |     |-- failure fixture
        |     \-- transformed data
        \-- revised experiment
              \-- next executable continuation
```

Each step materializes enough state for a later step to continue without
requiring the original process. If inputs remain valid, expensive construction
can be reused. If they change, execution can restart from the nearest valid
artifact.

Unlike a conventional static build graph, this graph is exploratory:

- its dependencies may only become clear after execution
- failed actions can produce valuable evidence and future inputs
- model-generated nodes may be nondeterministic
- an operator may retain stale artifacts intentionally for comparison
- a node may capture an unresolved question rather than a successful result
- intermediates may be promoted into durable project artifacts after proving
  useful

The graph is a way of making continuation inspectable, not a claim that all
interactive work can be reduced to a pure build system.

## Candidate State Classes

### Durable Conversational State

Intent, decisions, commands, results, and provenance belong in durable TOAS
history. This state explains why an artifact exists and what the operator was
trying to learn or achieve.

### Durable Source Artifacts

Code, tests, specifications, fixtures, and configuration that have become part
of the project remain ordinary inspectable project material.

### Materialized Intermediates

Generated scripts, normalized inputs, reproduction cases, compiled outputs,
captured datasets, and similar products may remain in place because the next
continuation consumes or edits them.

These are not necessarily permanent product artifacts. Their value may be
local to an active investigation.

### Evidence

Logs, traces, test reports, measurements, screenshots, and failure outputs are
first-class products of execution. A failed node can still be a successful
evidence-producing step.

### Disposable Derived Caches

Dependency downloads, indexes, bytecode, compiled products, and derived
summaries can be discarded when their inputs and construction procedure remain
available.

### Live Runtime State

Processes, interpreter heaps, stopped debuggers, open transactions, device
connections, and other non-serializable resources remain live only when their
continued identity matters materially.

The useful hierarchy is:

1. preserve reasoning continuity in durable history
2. preserve executable continuity in artifacts
3. cache expensive derived construction
4. retain a live runtime when its important state cannot be represented
   economically

## Artifact Continuation

An artifact continuation is a runnable description of how to resume useful
work without requiring the original live process.

A candidate continuation description might name:

- purpose or originating intent
- input artifacts and their identities
- executable procedure or command
- relevant environment and configuration identity
- expected and observed output artifacts
- result status and evidence
- durable history provenance
- cache validity assumptions
- the next known action or unresolved question, when one exists

The exact representation is intentionally open. It could range from an
ordinary script plus nearby files to an explicit manifest linked to durable
event records.

The important property is constructive caching: each useful execution should
leave behind enough inspectable material to make the next execution cheaper in
thought, setup, or computation.

## Branching And Reconstruction

Live runtime state is difficult to branch. Arbitrary heaps, jobs, file
descriptors, and external sessions cannot generally be cloned safely or
explained completely.

Artifact continuations branch naturally:

```text
continuation A
    |-- derive and execute hypothesis B
    \-- derive and execute hypothesis C
```

Each branch can run in a clean process while sharing immutable or validated
intermediates. This aligns with TOAS's append-only history and explicit
lineages: prior reasoning remains fixed, while new attempts carry explicit
parentage.

Reconstruction need not mean replaying every historical command. It means
finding the nearest valid continuation whose declared artifacts and cached
derivations still exist, then proceeding from there.

## Validity And Retention Pressures

Constructive caching moves complexity from hidden process state into artifact
identity and validity.

Questions include:

- which inputs determine whether an intermediate is reusable
- how environment, dependency, tool, model, and prompt identity participate
- when nondeterministic outputs may be reused as evidence rather than rebuilt
- how external mutable systems affect validity
- which artifacts should be pinned, promoted, archived, or collected
- how secrets and sensitive outputs are excluded from retained state
- how a missing cache is distinguished from missing durable truth

A useful retention vocabulary may eventually distinguish:

- **promote**: make an exploratory artifact part of the project
- **pin**: retain an intermediate because active reasoning still depends on it
- **cache**: retain a rebuildable derived artifact opportunistically
- **collect**: remove an unreferenced or expired intermediate
- **reconstruct**: recreate a continuation from declared inputs and procedure

These are observations, not proposed commands or settled record types.

## Where Live Runtimes Still Win

Artifact continuation is not equivalent to every kind of live state. Process
residency remains compelling when work depends on:

- a debugger stopped at a valuable execution point
- a server being probed and steered
- an open database transaction or external session
- device or hardware connections
- very large, costly, or non-serializable in-memory state
- interactive control loops where subsecond latency materially changes use
- background jobs whose identities are themselves the subject of work

Even in these cases, the conversation can periodically distill the live
investigation into artifacts: a reproduction script, fixture, checkpoint,
captured request, state summary, or next-action note. Losing the runtime should
ideally become inconvenient rather than destructive to the investigation.

Conversational continuity and runtime-state continuity should remain
separable. An operator should be able to keep the durable conversation while
resetting the live runtime explicitly.

## Polyglot Implication

The earlier infrastructure-shaped picture was:

```text
TOAS host
    |-- warm Python worker
    |-- warm Node worker
    |-- warm Julia worker
    \-- warm shell worker
```

The artifact-continuation picture is more demand-shaped:

```text
TOAS host or operator surface
    |-- clean polyglot executions
    |-- constructively cached artifact continuations
    \-- zero or more intentional live contexts
```

A live context should be identified by purpose rather than language alone:

- `debugging-server-failure`
- `loaded-data-exploration`
- `scratch-python`

Language is an implementation property of the context, not necessarily its
operator-facing identity or reason to exist.

This reframes a possible polyglot runtime capability. TOAS may need a common
execution and evidence contract more than it needs a permanent collection of
language kernels. Language-specific executors can remain disposable unless a
particular activity deliberately promotes one into a live context.

## Relationship To TOAS

The idea is consonant with existing TOAS boundaries:

- durable event history explains intent, provenance, and lineage
- files and other artifacts make parts of that history executable
- rendered or transported representations do not become canonical truth
- live runtime state remains ephemeral unless explicit facts are recorded
- host supervision does not become the semantic owner of language behavior
- clean and persistent execution can share an outer activity/event contract

One possible conceptual relationship is:

```text
durable event graph
        <->
materialized artifact graph
        ->
next executable continuation
```

The durable event graph answers why. The artifact graph answers with what and
how. Neither requires an old interpreter process to remain the only source of
continuity.

This does not establish that TOAS should implement a build system, artifact
store, notebook kernel manager, or polyglot runtime service. Those ownership
and product questions remain open.

## Open Questions

- Is an artifact continuation merely a convention around ordinary files, or a
  named domain object?
- Which continuation facts, if any, belong in durable event history?
- Can useful dependency edges be observed after execution without requiring a
  fully declared build graph first?
- How should cache identity account for model and prompt inputs without making
  nondeterministic generation look reproducible?
- What is the smallest useful distinction between project artifacts,
  investigation intermediates, evidence, and disposable cache?
- When should an activity be promoted from clean execution to a live context?
- How should a live context emit a reconstructable artifact continuation?
- Could an external build, workflow, or kernel system provide this capability
  behind a TOAS-facing contract?
- How much latency and operator friction does process reconstruction actually
  add once model reasoning dominates elapsed time?

## Non-Decisions

This note does not decide:

- that persistent interpreters are unnecessary
- that TOAS should implement artifact caching
- that Make or any particular build system is the target substrate
- that every intermediate should be retained
- that live runtime state should become durable
- that one polyglot execution protocol should replace native language tooling
- that the shell-attached warm host should become a supported product surface

