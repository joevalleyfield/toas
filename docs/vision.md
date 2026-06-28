# Transcript-Oriented Agent System (TOAS)

## Core Idea

TOAS is not a hidden loop and not the agent itself.

For current shipped operator behavior, see `docs/capabilities.md`.

It is:
- a durable append-only event log
- a user-edited working transcript
- a small operator surface that advances one layer of consequence at a time

Everything else sits on top of that substrate.

---

## Sources Of Truth

### 1. Event Log (`.toas/events.jsonl` default)

This is the canonical durable state.

It is append-only and contains:
- message events
- control records
- tool records
- model-call records

Message event shape:

```json
{
  "id": "n7",
  "parent": "n6",
  "role": "user",
  "content": "raw text",
  "metadata": {}
}
```

Non-message record kinds currently include:
- `anchor`
- `tool_request`
- `tool_result`
- `llm_call`

### 2. Working Transcript (`.toas/session.md` default)

This is the user-controlled working surface.

It is:
- linear and human-readable
- directly editable
- treated as the current proposal against history
- never rewritten by the system during ordinary `step`

The user may rewrite it freely. Rewriting previously aligned content means branching, not mutation of history.

---

## The Operator

The core command is `step`.

Each invocation:
1. accepts transcript state as proposal
2. aligns that proposal against history
3. resolves exactly one layer of consequence from transcript frontier

The supporting CLI surface exists to inspect, select, and project around that core behavior.

Current commands:
- `toas step`
- `toas heads`
- `toas transcript [head_id]`
- `toas llm-input [head_id]`
- `toas prompt <kind>/<version>`
- `toas prompts [prefix]`
- `toas history [limit]`
- `toas daemon [start|stop|status]`

Execution contract:
- `step` execution is transcript-frontier authoritative.
- Only current frontier content (user/assistant/control) can select what executes next.
- `/replay` is the explicit non-frontier callable selection mechanism.
- Projection targeting (`transcript [head_id]`, `llm-input [head_id]`) is read-only and does not redirect subsequent `step`.
- Resuming from a lineage is projection plus an explicit operator redirect
  (`toas transcript <head_id> > <session_path>`), not a separate writeback
  surface.
- `history [limit]` is the current root-to-head lineage view over the shared implicit anchor slice, not a mixed head-listing/event-summary surface.
- Projection targeting should remain explicit. Split or
  archived storage must not silently widen a surface from warm-history
  inspection into automatic deep cold-history traversal.

---

## Resolution Model

`step` is resolution-driven, not role-driven.

It advances only when something at the frontier is unresolved.

> Step = advance the frontier of unresolved state

There is no loop to maintain. There is only pending state to resolve.

---

## Internal Phases

The operator separates three concerns:

1. `transcript -> nodes`
2. `nodes vs history`
3. `tail state -> action`

That maps to:
- projection
- alignment
- advancement

This separation is one of the main points of the system.

---

## Frontier And Intent

The frontier is the last unresolved transcript state.

Intent is split along two axes:

### Structural Intent

- CALLABLE = the tail contains a parseable actionable YAML block
- NOT CALLABLE = it does not

### Turn Ownership

- tail role `user` means generation is possible
- tail role `assistant` means generation is not

Unified behavior:

| Tail condition | Action | Output |
| --- | --- | --- |
| NOT callable + user | generate | assistant |
| NOT callable + assistant | no-op | — |
| CALLABLE + user | execute | RESULT |
| CALLABLE + assistant | execute | RESULT |

Refinements:
- execution is role-agnostic
- generation is role-driven
- execution does not automatically continue generation

---

## Transcript Structure

Transcript blocks are loose except where callable structure matters.

Example:

````markdown
## TOAS:USER
...

## TOAS:ASSISTANT
...
```yaml
- tool_name: echo
  args:
    text: hi
```

## RESULT
...
````

Rules:
- transcript role markers are strict ASCII level-2 headings:
  - `## TOAS:SYSTEM` (optional; only once at top)
  - `## TOAS:USER`
  - `## TOAS:ASSISTANT`
- only the last YAML block is actionable
- YAML must parse to become callable
- everything else is working text
- line-start marker collisions inside message content are escaped on render (`\## TOAS:...`) and unescaped at parse boundary
- `## RESULT` is content inside a turn, not a transcript role marker or structural boundary

### Why The Action Syntax Is Flexible

TOAS should not assume the backend model is a neutral blank slate.

Some backends impose:
- hidden system prompting
- built-in personas
- provider-owned tool-use protocols
- partial or inconsistent respect for system instructions

That means TOAS may need to establish an operator protocol that does not collide with the backend's own protocol.

Current actionable YAML is one example of this strategy:
- it provides a structured lane inside ordinary message content
- it avoids direct dependence on provider-native tool calling
- it can be changed if another action syntax proves less collision-prone

The important invariant is not YAML itself. The invariant is:

> TOAS needs a controllable action protocol even when the backend already has its own agenda.

Prompt assets, flags, extraction, repair, and runtime policy all exist partly to maintain that controllable protocol under backend-specific pressure.

The intended default posture is:
- prompt content should be visible in the transcript or explicitly selected
- extraction should be primarily mechanical
- repair should be primarily manual
- LLM-backed extraction or repair is an optional later layer, not the baseline assumption

---

## Stdout Contract

`stdout` contains only newly produced consequences.

Never:
- transcript echo
- historical nodes
- the full append set

This is what makes:

```vim
:r !toas step
```

safe for forward insertion.

---

## Message-Event Space

Lineage defaults are defined in message-event space only.

- Message events carry conversational identity and parentage.
- Control, tool, and model-call records do not participate in message numbering.
- Default `parent` means continue the previous message event.
- Branching requires explicit parentage when continuation is not from the previous message event.
- Default `id` sequencing, when elided, is also over message events only.

This keeps conversational lineage stable even as other durable operator facts are appended.

---

## Operator Command Surface

TOAS can expose explicit operator commands beyond `step` for mechanical and assisted workflows (for example: extraction, compaction, outlining, replay helpers).

When those commands are introduced, they should be represented as durable non-message records rather than conversation messages.

Design intent:
- command execution is durable and auditable in the event log
- command records may reference message-space targets (head, node, range)
- command records do not become parents in message-event lineage
- user-visible command outcomes can be projected as result-style output and adopted into conversation explicitly when desired

Current projection/adoption semantics:
- command outcomes are projected as `## RESULT` blocks
- projected `## RESULT` text is non-authoritative for durable frontier selection
- durable `tool_result` records are side-car operational facts, not dialogue-turn lineage nodes
- if a user edits prior turn content (including `## RESULT` text) and steps again, the edited turn is adopted as a sibling branch and becomes the active stepped frontier
- command durability is carried by `command_request` -> `command_result` records
- result projection never implies message-event parentage
- adoption is explicit: users copy or reformulate result content into subsequent `## TOAS:USER` turns when they want it to become conversational input
- history views keep message events and command records distinct

This preserves the core split:
- message events carry conversation identity
- operator records carry operator activity

---

## Binding, Selection, And Anchors

Transcript alignment is influenced by three distinct mechanisms.

### Binding

- automatic byte-level LCP alignment
- manual override via durable `jump` records

Formatting changes are treated as discontinuity by default.

### Head Selection

- durable `head` records select the current lineage
- selected head compatibility state must not determine what `step` executes; step is frontier-authoritative

### Anchors

Anchors are non-causal records of:

`(transcript offset <-> node id)`

They are used for:
- alignment shortcuts
- transcript-reprojection checkpoints
- replay locality

They are helpers, not sources of truth.

---

## Operational Layers

The transcript/history model is the substrate. Three operational layers sit on top of it.

### 1. LLM Integration

LLMs consume projected lineage context, not raw storage.

Current implementation:
- local OpenAI-compatible chat backend
- defaults suitable for `llama-cpp`
- durable `llm_call` records for success and failure
- transcript-first model input with no implicit default generation prompt

This layer is not only about transport. It is also where TOAS adapts to backend quirks such as:
- hidden system instructions
- response-side reasoning fields
- provider-specific request flags
- protocol-collision risks around tool use and structured output

### 2. Tool Library

Tools are reusable operator capabilities, not ad hoc callback accidents.

Current implementation:
- in-process registry
- explicit lookup by `tool_name`
- required-argument validation
- execution adapters
- canonical result shaping
- durable `tool_request` / `tool_result` records

### 3. Prompt Library

Prompts are versioned assets, not scattered strings.

Current implementation:
- generation, extraction, repair, and protocol prompt families
- on-disk prompt assets
- shared prompt loading conventions
- explicit prompt retrieval via `toas prompt <kind>/<version>`

---

## Enabled Capabilities

This substrate enables:
- editable human-in-the-loop transcript authoring
- inspectable graph-native history
- branch-aware continuation and replay
- durable operator facts alongside message lineage
- LLM-backed generation over projected context
- reusable tool execution with recorded consequences
- prompt evolution without storage-model churn

The point is not only to store messages differently.

The point is to make agent behavior legible, branchable, replayable, and operable without hidden mutable state.

---

## Design Principles

- Treat `session.md` as the working proposal.
- Treat `.toas/events.jsonl` (or legacy root `events.jsonl` when present) as canonical durable history.
- Never mutate prior history entries.
- Prefer new durable records over sidecar state.
- Keep message events, control records, tool records, and model-call records distinct.
- Put projection and serialization rules at the boundary, not in storage.
