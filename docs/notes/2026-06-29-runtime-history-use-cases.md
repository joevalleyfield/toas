# Runtime History Use-Cases

Status: DIRECTIONAL
Task Link: `260629-storage-scale-model-proof-contract`
Related: `260626-events-jsonl-multiplicity-and-merge-provenance`; `260627-history-surface-user-intent-alignment`; `260627-history-surface-corruption-semantics`

## Purpose

Brainstorm runtime and agent-facing reasons TOAS needs event history while
staying at the semantic-requirements layer. This note intentionally avoids code
design.

The focus here is not what the operator wants to see directly. It is what
semantic work event history must do so runtime behavior remains trustworthy.

## LCP Reconciliation

Semantic requirement:

```text
Runtime needs durable message history so the current transcript can be
interpreted as a proposal against prior adopted content.
```

History must preserve:

- adopted message events
- role and content order
- parentage within the active authority scope
- enough lineage to find the longest common prefix
- distinction between message events and projected/result text

History may ignore:

- cold segments during ordinary active reconciliation
- non-message operational records except where they affect active binding
- derived summaries unless explicitly selected as semantic input

Failure modes:

- LCP scans too broadly, and old or cold history unexpectedly influences active
  work
- LCP scans too narrowly, and valid continuation looks like a new branch
- projected `RESULT` text is treated as message history, causing runtime to
  adopt fake transcript content
- adjacent user messages are collapsed too early, losing durable parentage

## Frontier Selection

Semantic requirement:

```text
Runtime needs to identify the unresolved frontier from the selected
transcript/history relationship, not merely from last visible text.
```

History must preserve:

- selected head or bind state
- current lineage parentage
- unresolved tail state
- whether the tail is user-authored, assistant-authored, callable, or no-op
- prior consequences already resolved for that frontier

History may omit:

- unrelated heads
- old abandoned branches
- full cold ancestry when hot-local selection is self-contained

Failure modes:

- runtime generates from the wrong parent
- a resolved callable block executes again
- assistant text is mistaken for pending user intent
- transcript projection redirects future `step` accidentally because
  projection target and active frontier are conflated

## Tool Consequence Tracking

Semantic requirement:

```text
Tool execution needs durable consequence records separate from assistant prose,
so runtime can tell what was requested, what ran, what returned, and what
remains unresolved.
```

History must preserve:

- tool request identity
- request parent/frontier
- arguments or redacted argument shape
- result status
- result payload or retained diagnostic
- distinction between model-addressable tool calls and direct user shell intent

History may omit:

- bulky raw stdout once summarized or retained elsewhere
- transient progress events after terminal facts are durable
- denied or malformed details beyond what is needed for repair and audit

Failure modes:

- duplicate execution after restart
- assistant claims are treated as actual tool results
- tool results are projected into transcript without durable backing
- user shell shorthand is subjected to model-addressable tool policy, or vice
  versa
- failure diagnostics needed to decide the next consequence are lost

## Transcript Projection

Semantic requirement:

```text
Runtime needs to project durable selected history back into editable transcript
form without making the projection itself canonical truth.
```

History must preserve:

- enough message lineage to render role blocks
- escaping and marker semantics
- projected tool/result relationship
- selected lineage or head
- provenance markers where needed to avoid misleading the user

History may omit:

- unrelated branches
- cold history outside the requested projection scope
- derived previews unless the projection explicitly asks for them

Failure modes:

- projected transcript becomes confused with active authority
- rendering drops role boundaries and changes future parse meaning
- projected `RESULT` blocks are re-adopted as message content
- restoring from a projected lineage silently changes active head without
  explicit operator action

## LLM-Input Projection

Semantic requirement:

```text
Runtime needs a provider-facing projection that may differ from transcript
projection while remaining derived from durable message events.
```

History must preserve:

- selected message lineage
- system, user, and assistant roles
- exact adopted content before provider shaping
- projection rules such as adjacent-user concatenation
- prompt or policy material selected for this invocation

History may omit:

- tool-result raw payloads not intended for model context
- graph branches not selected for this invocation
- cold history outside the chosen context window
- operational records irrelevant to provider input

Failure modes:

- provider input includes stale or unrelated branches
- adjacent user concatenation mutates durable history instead of projection only
- prompt or policy material becomes hidden runtime state rather than visible or
  selectable input
- cold traversal silently expands context, cost, latency, or meaning

## Hot-Local Authority

Semantic requirement:

```text
Ordinary step should treat the hot journal as the active authority surface.
Cold history may exist, but it should not be required for every active
consequence.
```

History must preserve:

- hot-local self-sufficient active context
- active parentage or independent root
- current frontier
- enough recent tool/model facts to avoid duplicate consequence

History may omit:

- ancient cold ancestry
- archived details irrelevant to current reconciliation
- unrelated independent journals

Failure modes:

- active step becomes slow or fragile because it depends on deep cold traversal
- cold corruption blocks unrelated current work
- rotation policy accidentally changes runtime semantics
- hot file that is not self-sufficient causes ambiguous parentage

## Cold/Hot Stitching

Semantic requirement:

```text
When runtime or a surface crosses hot/cold boundaries, stitching must be
proof-producing: derived from alignment, provenance, or explicit selection, not
raw id equality.
```

History must preserve:

- source identity
- source-local ids
- physical occurrence identity
- content and parentage needed for alignment
- enough provenance to explain a stitch or refusal

History may omit:

- unrelated cold segments
- raw duplicate records once an equivalence class is proven
- derived indexes when stale or untrusted

Failure modes:

- duplicate local ids across sources are treated as one node
- independent roots are falsely stitched
- restaged hot context appears as duplicate transcript history
- graph/history surfaces overstate uniqueness
- index lookup returns the wrong physical occurrence for a local id

## Refusal When Scope Is Ambiguous

Semantic requirement:

```text
Runtime must sometimes refuse instead of guessing. Ambiguity should be semantic
information, not an exception accidentally leaking from a helper.
```

History must preserve:

- reason for ambiguity
- involved sources or scopes
- whether the ambiguity is fatal corruption, missing alignment, or insufficient
  selector information
- enough context for recovery or explicit selection

History may omit:

- full deep scan if the refusal is about an undeclared scope
- speculative best-effort stitched projections
- unrelated warning noise

Failure modes:

- runtime silently chooses the wrong branch or source
- refusal text calls valid journal-local ids corruption
- valid current work is blocked by unrelated cold ambiguity
- user cannot tell what selector or recovery action would make the request safe

## Cross-Cutting Semantic Requirements

- Message events, tool records, model-call records, and control records remain
  distinct.
- Journal-local ids are not global identities.
- Parentage is authoritative only within its declared source unless a stitcher
  proves more.
- Projection can transform shape, but it must not mutate durable meaning.
- Active reconciliation and historical inspection are different authority
  modes.
- Runtime must track whether it is using hot, selected-lineage,
  selected-window, or full stitched scope.
- Refusal is valid behavior when the requested scope exceeds available proof.

## Failure Modes To Test Later

- duplicate `n1` across hot/cold incorrectly treated as one node
- cold segment corruption blocks hot-local `step`
- projected transcript changes active frontier without explicit selection
- tool result rendered without durable tool result fact
- LLM input includes unrelated branch content
- adjacent user turns are merged durably instead of only in provider projection
- ambiguous stitched history produces partial output instead of refusal
- index lookup by raw local id returns a cross-source false match

