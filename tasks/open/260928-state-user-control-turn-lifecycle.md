Filed as: 260928-state-user-control-turn-lifecycle
FKA:
AKA: state-step user/control turns; state transcript frontier lifecycle
Legacy index:

keywords: runtime, implementation, active, transcript, frontier, projection, provenance

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-alpha-loop`
Related: `260927-state-step-history-projections`; `260928-state-edit-and-user-tools`

# Resolve User And Control Turns Between State Snapshots

Implement the state-step transcript lifecycle around ordinary `TOAS:USER` and
`TOAS:CONTROL` turns, preserving the normal TOAS turn markers and defining how
those turns advance one state frontier.

## Agreed Direction

The working transcript can progress as `STATE/n → USER or CONTROL → STATE/n+1`.
Here `n` names a position in the progression; it is not a proposal to change
the current `## TOAS:STATE/1` format-version marker.
`USER` and `CONTROL` may both contain slash commands and other user-authored
content. Their distinction is projection visibility: `USER` content appears in
the LLM-facing transcript; `CONTROL` content is consumed by operator/runtime
resolution but is omitted from both the LLM-facing transcript and any
LLM-facing state projection. Consequences of a control, such as a tool result,
may appear in the next model-visible observation.

The turns remain durable transcript history. Resolving a turn appends its
resulting state and records an explicit relationship to the input; it does not
erase or silently replay the input. User-originated commands retain direct
user-intent authority regardless of whether they appear in `USER` or
`CONTROL`.

## Scope

- Route a transcript containing typed state markers through state-step parsing
  even when its frontier is `USER` or `CONTROL`; do not fall through to the
  message-only parser and reject `STATE/n` as an invalid role marker.
- Define and implement how the frontier resolver handles a state followed by
  one or more user/control turns, including state edits, prose, slash commands,
  and user-authored tool calls. Slash commands and authored calls in either
  role remain direct user intent; ordinary prose is not executable intent.
  Keep the operation explicit and user-stepped;
  inference and tool execution must not become a hidden loop.
- Preserve the original turns and append a resulting state turn with enough
  provenance to identify which input turn(s) it resolved.
- Include `USER` content in the model-facing transcript projection and exclude
  `CONTROL` content from both transcript and state projections. Include
  eligible derived state and tool-result observations without leaking the
  control text that caused them.
- Make frontier selection, consumption, and interruption/re-step behavior
  explicit so resolved user actions are not replayed and unresolved ones are
  not skipped.
- Preserve ordinary conversation parsing and message-event numbering; typed
  state turns remain outside message-event space.
- Reconcile task documentation: mark the closed
  `260928-state-edit-and-user-tools` transcript-shape decision as superseded,
  and amend active state-step tasks that otherwise imply edits belong inside a
  `STATE` turn.

## Acceptance Criteria

- A transcript with `STATE/n` followed by `USER` or `CONTROL` is recognized as
  a state-step transcript and reaches state frontier resolution without the
  invalid-marker error.
- A resolved input produces an appended `STATE/n+1`; original state and input
  turns remain intact and the resolved input is not acted on again after a
  restart or repeated `step`.
- `/` commands and authored tool calls can occur in either role and follow the
  same direct-user-intent execution authority. Other user-authored content can
  occur in either role without becoming executable merely because of its role.
  Command/tool consequences are recorded and correlated with the source turn.
- `USER` content appears in the LLM-facing transcript projection. `CONTROL`
  content appears in neither the LLM-facing transcript nor the LLM-facing
  state projection, while resulting accepted state and observations can be
  projected according to the state request contract.
- User-tool outcomes become model-visible observations at the agreed state
  boundary; execution and inference remain separate explicit steps.
- Existing conversation transcripts and ordinary `USER`/`CONTROL` parsing
  retain their current behavior.
- The closed predecessor and active connecting task files describe the
  superseding turn model consistently, with links and completion evidence.
- Focused coverage exercises parsing, frontier choice, role-specific model
  projection, state advancement, command/tool provenance, replay recovery, and
  conversation compatibility.

## Open Contract Details To Set Before The Implementation Slice

- The supported syntax for expressing an explicit state edit in a `USER` turn
  versus prose that should be provided to the model.
- Whether several adjacent `USER`/`CONTROL` turns resolve as one frontier
  group or as distinct explicit steps, and how role order affects projection.
- The exact state/request boundary for exposing resolved `USER` content while
  keeping the default state packet concise.

Status: Active; contract details are bounded to this transcript/frontier seam.
