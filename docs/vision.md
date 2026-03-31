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

### 2. Transcript (`session.md`) — projection

- Linear, human-readable
- Represents a single path through the graph
- Regenerable at any time from `.jsonl`
- May be edited, but edits are **proposals**, not truth

The transcript is a working surface, not a database.

---

## The Operator

There is exactly one command:

→ `step`

No modes. No flags.

Each invocation:
1. Reads transcript
2. Resolves the next incomplete step
3. Appends new node(s) to `.jsonl`
4. Reprojects transcript

---

## Step Resolution

The system inspects the tail of the transcript.

### Cases

#### 1. Needs reasoning

Tail is:
- USER input
- ASSISTANT without a PLAN

Action:
→ call LLM  
→ append ASSISTANT node (may include PLAN)

---

#### 2. Needs execution

Tail contains:
- PLAN without RESULT

Action:
→ parse YAML  
→ execute tools  
→ append TOOL/RESULT nodes

---

#### 3. Needs continuation

Tail is:
- RESULT

Action:
→ call LLM for next step  
→ append ASSISTANT node

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

## Design Principles

### 1. Projection over mutation

- Never treat markdown as canonical
- Always derive from `.jsonl`
- Edits become new nodes, not in-place changes

---

### 2. Behavior emerges from loop pressure

- Do not over-specify agent behavior
- Allow conversational drift
- Extract structure when present
- Ignore what does not matter

---

### 3. One step, always

- Every invocation advances exactly one step
- No batching
- No hidden loops

---

### 4. Identity enables control

- Every message has an ID
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
- The transcript is a view
- The operator advances one step
- Structure is extracted, not enforced

Everything else is negotiable.

