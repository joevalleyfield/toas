# Execution Model

## Executive Summary

The transcript is operational. The graph is observational.

The transcript participates in execution. The graph records execution.

The transcript gets a vote. The graph gets an audit trail.

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

The graph does not participate in ordinary forward execution.

During normal operation, information flows from the transcript into the graph, not from the graph into the transcript.

```text
transcript -> execution
transcript -> graph
```

The reverse direction exists only through explicit history-oriented operations.

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

### The graph is observational

The graph is an audit record, provenance store, branching history, and reuse artifact.

It exists to remember.

It does not exist to decide.

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

The graph is observational.

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

---

## Common Misconceptions

### "The graph is the source of runtime state."

No.

The transcript is the source of runtime state.

The graph is a provenance artifact.

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

No.

History affects execution only through explicit history-oriented operations.

---

## Mental Model

If you remember only one thing, remember this:

The transcript is operational.

The graph is observational.

The transcript participates in execution.

The graph records execution.

The transcript gets a vote.

The graph gets an audit trail.
