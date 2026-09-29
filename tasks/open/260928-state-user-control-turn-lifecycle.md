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

For the first slice, each `USER` turn's content becomes an observation on the
next editable state. `step` appends that state without calling the model. A
later explicit `step` sends the state and its compound observation through the
existing state-only request path. The raw user turn remains in the operator's
transcript history; it is represented to the model through the observation,
not replayed as a conversation message. Structured mappings from user text
directly into state fields can follow later.

`USER` and `CONTROL` may both contain slash commands and other user-authored
content. Their distinction is projection visibility: `USER` content becomes a
model-visible observation; `CONTROL` content is consumed by operator/runtime
resolution but omitted from both the LLM-facing transcript and state
projection. Consequences of a control, such as a tool result, may appear in
the next model-visible observation.

For the initial frontier rule, one explicit `step` resolves all contiguous
`USER` and `CONTROL` turns following the latest state, preserving their order
and provenance while producing one next state. Separate USER contents remain
separate observation components; control text itself is not projected.

Slash-command extraction and dispatch happen while resolving the USER or
CONTROL input turn that contains the command. A slash-looking line inside a
STATE turn is state content; it must not be extracted or executed as an
operator command.

The effective instructions remain the procedure boundary. The model may
propose changes to any mutable state field, including `goal`; accepting a goal
update through the existing state-patch path is an intentional extension from
the initial user-authored-goal setup, not a change to the instructions.

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
  and user-authored tool calls. Extract and dispatch slash commands only from
  USER/CONTROL input turns; never scan STATE content for executable commands.
  Slash commands and authored calls in either input role remain direct user
  intent; ordinary prose is not executable intent.
  Keep the operation explicit and user-stepped;
  inference and tool execution must not become a hidden loop.
- Preserve the original turns and append a resulting state turn with enough
  provenance to identify which input turn(s) it resolved.
- Project `USER` content as an observation in the next state-only model packet,
  not as a conversation message. Exclude `CONTROL` content from both
  transcript and state projections. Include eligible derived state and
  tool-result observations without leaking the control text that caused them.
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
- One step resolves the contiguous trailing USER/CONTROL group after the
  latest state into one next state, preserving input order and provenance.
- `/` commands and authored tool calls can occur in either role and follow the
  same direct-user-intent execution authority. Other user-authored content can
  occur in either role without becoming executable merely because of its role.
  A command-looking line in a STATE turn is never executed as a slash command.
  Command/tool consequences are recorded and correlated with the source turn.
- `USER` content is included in the next state-only model request through its
  compound observation; it is not also replayed as a conversation message.
  `CONTROL` content appears in neither the LLM-facing transcript nor the
  LLM-facing state projection, while derived results can be observed.
- The model can update `goal` through its ordinary validated state patch while
  the effective instructions remain unchanged and authoritative.
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

- How users may later request structured field mappings instead of recording
  their content as an observation.

Status: Active; initial projection and frontier behavior are ready for
implementation. Structured field mappings remain deferred.

## Progress

- Claimed for implementation on 2026-09-29; slash commands are being wired to
  USER/CONTROL input-turn resolution, with STATE content excluded from command
  extraction.
- State-step routing now recognizes typed states even when USER/CONTROL turns
  follow them. Trailing role turns are parsed and retained as transcript text.
- USER text is consolidated into separate `user_inputs` observation components
  before inference. CONTROL text is omitted from the model-facing observation.
- A later explicit inference step receives those observations through the
  state-only packet and may update `goal` through its ordinary state patch.
- Markdown state parsing now finds the outer YAML fence even when a serialized
  tool result contains its own fenced output.
- Focused state-step and CLI state-step coverage passes (33 tests). The
  elevated full suite improved from 14 to 11 failures: the state-step failures
  in the baseline are fixed; remaining failures are the existing CLI dispatch
  expectations and state-execution experiment assertions.
- Durable resolution of slash-command and other direct-action consequences
  remains to be implemented; this task is still active.
