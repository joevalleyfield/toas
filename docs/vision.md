# Transcript-Oriented Agent System (TOAS)

## Core Idea

The system is not a loop.  
The system is not the agent.  

The system is:
→ a persistent message graph (.jsonl)  
→ a projected working transcript (markdown)  
→ a single step operator that advances state  

Everything else is implementation detail.

---

## Sources of Truth

### 1. Message Graph (`.jsonl`) — canonical

- Append-only
- Each entry is a message node
- Nodes reference a parent (forming a DAG)
- Supports branching, rewind, and replay

Minimal schema:

```json
{
  "id": "uuid",
  "parent": "uuid | null",
  "role": "user | assistant | tool",
  "content": "raw text",
  "metadata": {
    "kind": "chat | thought | plan | result",
    "tool_name": "optional",
    "status": "proposed | executed"
  }
}
```

This is the only durable state.

---

### 2. Transcript (`session.md`) — working proposal

- Linear, human-readable
- Represents a proposed path through the graph
- Authored and edited directly by the user
- Appended to by inserting `step` output
- Never rewritten by the system

The transcript is the authoritative working surface.

---

## The Operator

There is exactly one command:

→ `step`

No modes. No flags.

Each invocation:
1. Accepts transcript as proposal
2. Synchronizes it into history
3. Resolves exactly one layer of consequence

---

## Resolution Model

`step` is resolution-driven, not role-driven.

It advances only when something is unresolved.

> Step = advance the frontier of unresolved state

There is no loop to maintain. There is only pending state to resolve.

---

## Internal Phases

The operator has three distinct phases:

1. `transcript -> nodes`
2. `nodes vs log`
3. `tail state -> action`

This separates concerns cleanly:

- Projection parses transcript into message nodes
- Alignment finds where transcript diverges from history
- Advancement produces new consequences from the frontier

Reconcile is interpretation, not just delta.

---

## Frontier

The frontier is the last unresolved state in the transcript.

`step` operates only at the frontier.

Anything before that is already accepted history for the purposes of the invocation.

---

## Intent Model

Intent has two orthogonal axes.

### 1. Structural intent

- CALLABLE = an actionable tool/YAML block is present
- NOT CALLABLE = no actionable structure is present

### 2. Turn ownership

- last role = `user` -> assistant speaks next
- last role = `assistant` -> user speaks next

These axes determine behavior independently.

---

## Unified Step Behavior

| Tail condition | Action | Output |
| --- | --- | --- |
| NOT callable + user | generate | assistant |
| NOT callable + assistant | no-op | — |
| CALLABLE + assistant | execute | RESULT |
| CALLABLE + user | execute | RESULT |

Refinements:

- execution is role-agnostic
- generation is role-driven
- execution does not trigger generation
- after execution, control returns to the transcript author

Tools produce state, not dialogue.

---

## Structural Conventions (Transcript)

Loose everywhere except where it matters.

### Blocks

````
## USER
...

## ASSISTANT
Thought: ...
```yaml
- tool_name: ...
```

## RESULT
...
````

Rules:
- Only the **last YAML block** is actionable
- YAML must be parseable to trigger execution
- Everything else is advisory

---

## Stdout Contract

`stdout` contains only newly produced consequences.

Never:
- transcript echo
- historical nodes
- full append set

Format:

````
## ROLE
content
````

This enables:

```vim
:r !toas step
```

to insert only new material safely.

---

## Binding

The transcript is treated as corresponding to some lineage in the log.

Binding is explicit in two forms:

- automatic byte-level LCP alignment
- manual override via `jump N`

The system guesses alignment; the user can assert it.

Formatting changes are treated as discontinuity by default.

Sameness is declared, not inferred.

---

## Anchors

An anchor is:

`(transcript offset <-> node index)`

Anchors are non-causal log entries used to:

- avoid full replay
- resume projection locally

They are an emerging optimization, not yet part of the core model.

---

## Message-Event Space

Lineage defaults are defined in message-event space only.

- Message events participate in conversational identity and parentage
- Control records and tool records do not participate in default message numbering
- Default `parent` means "continue the previous message event"
- Branching requires explicit parent declaration when continuation is not the previous message event
- Default `id` sequencing, when elided in serialization, is also defined over message events only

This keeps conversational lineage stable even when non-message records are appended to the log.

---

## Operational Layers

The transcript/history model is the substrate, not the whole system.

It enables three operational layers that must remain explicit.

### 1. LLM Integration

LLMs are pluggable reasoning and generation backends.

They consume projected context, not raw storage.

Responsibilities:
- generation from user-owned transcript state
- extraction from loosely structured transcript content
- continuation over selected lineage context
- failure handling when model output is partial, malformed, or wrong

The graph/transcript split exists partly to make model interaction inspectable and controllable.

### 2. Tool Library

Tools are reusable operator capabilities, not ad hoc one-off calls.

Responsibilities:
- define callable interfaces
- execute against structured arguments
- record durable request/result facts
- expose consequences back to the transcript author in canonical form

Tools produce state. They do not own the dialogue surface.

### 3. Prompt Library

Prompts are reusable assets, not invisible inline accidents.

Responsibilities:
- shape generation behavior
- shape extraction behavior
- frame execution and repair behavior
- allow prompt changes to be deliberate and reviewable

The system should be able to evolve its prompting strategy without changing the underlying history model.

---

## Enabled Capabilities

This substrate is intended to enable:

- editable human-in-the-loop transcript authoring
- inspectable graph-native conversational history
- branch-aware continuation and replay
- durable operator facts alongside message lineage
- LLM-backed generation and extraction over projected context
- reusable tool execution with recorded consequences
- reusable prompt assets that shape operator behavior

The point is not only to store messages differently.

The point is to make agent behavior legible, branchable, replayable, and operable without hidden state.

---

## Design Principles

### 1. Transcript authority with append-only history

- Treat transcript as the authoritative working proposal
- Treat `.jsonl` as append-only durable history
- Never restate existing transcript content
- Only append new consequences

---

### 2. Resolution over looping

- Advance only unresolved state
- Do not model the system as a conversational loop
- Extract callable structure when present
- Leave control with the transcript author

---

### 3. One step, always

- Every invocation advances exactly one step
- No batching
- No hidden loops

---

### 4. Identity enables control

- Byte identity is the default notion of sameness
- `jump` provides explicit semantic override
- Branching = choosing a different parent
- Rewind = selecting an earlier node as head

---

### 5. Human-in-the-loop by default

- User may edit transcript before step
- User may inject PLAN directly
- System does not require permission cycles

---

## Branching Model

- Graph supports multiple children per node
- Transcript selects a single head
- Forking = selecting a different node as parent for next step

Analogy:
- `.jsonl` = commit graph
- transcript = working copy

---

## Failure Philosophy

The model is not trusted.

- Output may be chatty
- YAML may be malformed
- Plans may be wrong

System response:
- extract what is usable
- retry narrowly if needed
- never require perfect compliance

---

## Minimal Responsibilities

### LLM
- Produce reasoning
- Optionally propose actions

### System
- Decide what matters
- Execute safely
- Maintain state integrity

---

## Non-Goals

- Perfect prompt compliance
- Rigid agent personas
- Hidden automation loops
- Opaque internal state

---

## Future Extensions (Optional)

- Partial replay / diff of branches
- Plan validation before execution
- Lightweight state injection (recent context summary)
- Secondary model for plan extraction

---

## Guiding Constraint

If a feature:
- cannot be expressed as a transformation of the message graph, or
- requires hidden state outside `.jsonl`

→ it is likely the wrong abstraction.

---

## Summary

- The graph is real
- The transcript is authoritative
- The operator resolves one frontier layer
- Execution ignores roles
- Generation follows roles
- Stdout is frontier only

Everything else is negotiable.
