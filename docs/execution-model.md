# Execution Model

## Executive Summary

The transcript is operational. The graph is durable evidence and control-state
storage.

The transcript participates in execution. The graph records execution and, for
selected control domains, stores facts that are resolved into runtime policy.

The transcript gets a vote. The graph gets an audit trail and durable control
facts; neither is a substitute for the other.

TOAS maintains two histories:

* an operational transcript (`session.md`)
* an observational event graph (`events.jsonl`)

Both contain multi-turn history. They serve different purposes.

The transcript determines what happens next.

The graph records what happened.

---

## Runtime Authority

The transcript is the active work surface.

Normal execution proceeds from the transcript frontier, which is always the last turn in the transcript.

The graph does not determine the frontier.

The graph does not redirect execution.

The graph does not rewrite the transcript.

The graph does not choose the ordinary transcript frontier. Resolved control
records may still participate in ordinary execution as runtime inputs.

During normal operation, information flows from the transcript into the graph,
while runtime context may resolve applicable control records from durable
history. This does not let history redirect the transcript frontier.

```text
transcript -> execution
transcript -> graph
control records -> policy resolution -> execution
```

The graph-to-transcript direction exists only through explicit history-oriented
operations. Graph control facts may still flow through policy resolution into
ordinary execution without rewriting the transcript.

---

## Consequences

Several design decisions follow directly from the authority model.

### Transcript-first execution

Execution always proceeds from the transcript.

The current frontier is the transcript tail.

There is no separate runtime frontier stored in the graph.

### Graph divergence is not corrective

If transcript history diverges from graph history, the graph does not attempt to repair or replace the transcript.

Divergence results in additional graph nodes.

Execution continues from the transcript frontier.

### The graph is observational for frontier selection

The graph is an audit record, provenance store, branching history, reuse
artifact, and durable store for selected control facts.

It exists to remember.

It does not choose the transcript frontier. Owning policy resolvers may consult
applicable control records when constructing runtime context.

### History access is explicit

Graph information only influences execution when the frontier explicitly requests a history-oriented operation.

Examples include:

* replay
* reconstruction
* inspection
* reuse
* graph navigation
* future graph-derived operations

Absent such a request, execution ignores graph contents.

---

## Normal Execution

Normal execution consists of stepping the transcript.

Conceptually:

```text
session.md
    ↓
step
    ↓
new consequences
```

The operator reads the transcript, identifies the frontier, performs the required action, and appends new consequences.

The graph may receive additional records during this process, but those records do not influence the current step.

The graph is accumulated.

The transcript is consulted.

---

## Reconciliation

Reconciliation exists to preserve provenance.

It does not determine runtime state.

Given:

```text
previous transcript
current transcript
event graph
```

reconciliation determines what transcript content has already been represented in the graph and what content has not.

New transcript content may result in new graph nodes.

Conceptually:

```text
transcript delta
      ↓
reconciliation
      ↓
graph append
```

The purpose of reconciliation is to extend provenance.

The purpose of reconciliation is not to recover runtime state.

### LCP-based reconciliation

Reconciliation begins by finding the longest common prefix between previously reconciled transcript content and current transcript content.

The reconciliation boundary identifies where transcript history diverges from previously recorded provenance.

Everything beyond that boundary is evaluated for graph representation.

The result is additional graph records where necessary.

Execution continues from the transcript frontier.

---

## The Event Graph

The event graph serves several purposes.

### Auditing

The graph preserves what occurred.

### Provenance

The graph preserves causal relationships and lineage.

### Branching

The graph can represent alternate possibilities and divergent histories.

### Reuse

Future operations may reuse prior graph material.

### Reconstruction

The graph can be used to reconstruct transcripts and historical states when explicitly requested.

None of these purposes grant authority over ordinary execution.

The graph is observational with respect to frontier selection, not an inert
sidecar for every runtime policy.

---

## Explicit History Operations

Some operations intentionally consult the graph.

Examples include:

* replaying prior history
* reconstructing a transcript
* inspecting lineage
* exploring branches
* reusing prior results
* future graph-oriented tooling

These operations create a deliberate flow from graph to transcript.

Conceptually:

```text
graph
  ↓
history operation
  ↓
transcript
  ↓
execution
```

This flow is explicit.

It never occurs implicitly during ordinary stepping.

## Control state and resolution

Not every setting that affects a future step is an ordinary project or global
configuration value. Transcript control deltas include config overrides,
shell-scope grants, command/workspace context, target selection, surface
bindings, and child-process environment modifiers. They remain individual
durable records so that operator intent, ordering, provenance, and branching
are preserved.

The resolution order is domain-specific. Ordinary `OperatorConfig` values use
the [config precedence contract](notes/2026-05-09-config-precedence-principles.md).
Child-process environment is a separate consumer with its own layering, and
TOAS control-plane environment variables are compatibility inputs rather than
transcript state. The complete distinction is maintained in the [transcript
control-state contract](notes/2026-09-20-transcript-control-state-contract.md).

The intended history rule is branch-forward: a delta inserted at a frontier
applies to that branch and its descendants until overridden. The current
implementation is mixed. Message-derived controls use working lineage in
several paths, but some record reducers currently scan the supplied journal
without a head and therefore behave history-forward when normal stepping gives
them the whole journal. A requested head or branch must not be silently reduced
to the storage tip as this work is completed.

---

## Common Misconceptions

### "The graph is the source of all runtime state."

No.

The transcript is the source of the operational frontier. Runtime policy may
also include resolved durable control records, file configuration, and explicit
environment inputs.

The graph is a provenance artifact and a durable store for those control facts;
it is not a universal settings object.

### "Execution proceeds from a graph frontier."

No.

Execution proceeds from the transcript frontier.

The frontier is the transcript tail.

### "Reconciliation restores the graph version."

No.

Reconciliation records transcript consequences in the graph.

It does not replace transcript state.

### "Divergence causes the graph to correct the transcript."

No.

Divergence causes additional graph records.

The transcript remains authoritative.

### "The graph is required for ordinary execution."

No.

The graph is required for provenance.

Ordinary forward execution proceeds from the transcript.

### "History automatically affects future execution."

Not in the undifferentiated sense.

Not message history merely because it exists. Control records do affect future
execution when the owning resolver includes them, and the resolver must select
the applicable lineage rather than blindly using all history. History does not
automatically choose the frontier or replace the working transcript.

---

## Mental Model

If you remember only one thing, remember this:

The transcript is operational.

The graph is observational for frontier selection and durable for control-state
facts.

The transcript participates in execution.

The graph records execution.

The transcript gets a vote.

The graph gets an audit trail.
