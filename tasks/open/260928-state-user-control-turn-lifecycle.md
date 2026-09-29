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

## Current Direction (Revised)

Keep normal USER/CONTROL turn resolution regardless of whether the transcript
also has a state horizon. Executable USER turns execute through the existing
user-intent path and return as USER turns with their results embedded;
executable CONTROL turns behave correspondingly as CONTROL turns. Slash
commands are resolved from USER/CONTROL input turns, never from STATE content.
Adjacent user/control turns keep their ordinary transcript consolidation
behavior instead of acquiring a separate state-only intent-resolution phase.

The state-specific difference is the inference projection: when a state
horizon is present, consolidated user/control material and eligible embedded
results are represented as additional observations on the state object sent
for inference, instead of sending a conversation transcript. Existing
USER/CONTROL projection visibility rules still apply. This removes the
state-specific `consolidate_user` phase and its parallel user-action lifecycle.

Inference is eligible only after the frontier has no unresolved executable
intent. Once eligible, the operator may either preview the consolidated state
in one step and infer on a later step, or consolidate and infer in one step
without the intermediate preview.

The working progression may still be described as `STATE/n → USER or CONTROL
→ STATE/n+1`; `n` names a progression position, not a change to the current
`## TOAS:STATE/1` format-version marker. Effective instructions remain
authoritative, while the model may patch other mutable state fields, including
`goal`.

## Scope

- Route a transcript containing typed state markers through state-step parsing
  even when its frontier is `USER` or `CONTROL`; do not fall through to the
  message-only parser and reject `STATE/n` as an invalid role marker.
- Keep ordinary USER/CONTROL command and tool execution, result embedding,
  adjacent-turn consolidation, and replay semantics shared by conversation
  and state modes. Do not create a state-specific user-intent lifecycle.
- When a state horizon is present and no executable intent remains unresolved,
  project consolidated eligible user material and embedded results as
  additional state observations for inference, instead of constructing a
  conversation-transcript request.
- Support both an intermediate consolidated-state preview followed by a later
  inference step and direct consolidation plus inference without the preview.
- Preserve the original turn/result transcript and its existing provenance.
- Resolve executable intent only from USER/CONTROL turns; STATE content is
  never scanned as a slash-command source.
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
- USER/CONTROL actions retain ordinary execution and embedded-result behavior
  in state transcripts as well as conversation transcripts.
- One step follows ordinary USER/CONTROL turn consolidation semantics. When a
  state horizon is present, inference occurs only after executable intents are
  resolved and receives consolidated eligible turn content and results as
  state observations rather than conversation messages.
- `/` commands and authored tool calls can occur in either role and follow the
  same direct-user-intent execution authority. Other user-authored content can
  occur in either role without becoming executable merely because of its role.
  A command-looking line in a STATE turn is never executed as a slash command.
- USER/CONTROL text and embedded results follow their normal transcript
  behavior; state inference consumes their eligible content through state
  observations rather than replaying a conversation transcript.
- The model can update `goal` through its ordinary validated state patch while
  the effective instructions remain unchanged and authoritative.
- User-tool outcomes become model-visible observations at the agreed state
  boundary before inference.
- Existing conversation transcripts and ordinary `USER`/`CONTROL` parsing
  retain their current behavior.
- The closed predecessor and active connecting task files describe the
  superseding turn model consistently, with links and completion evidence.
- Focused coverage exercises parsing, frontier choice, role-specific model
  projection, state advancement, command/tool provenance, replay recovery, and
  conversation compatibility.

## Open Contract Details

- How users may later request structured field mappings instead of recording
  their content as an observation.
- Deferred choice of structured mappings; the initial surface uses existing
  `step --preview` for the intermediate consolidated-state view and plain
  `step` for direct consolidation and inference.

Status: Active; shared USER/CONTROL frontier routing and state observation
projection are implemented for the initial slice. Broader execution recovery
and hostio/RPC parity coverage remain in progress. Structured field mappings
remain deferred.

## Progress

- Preserved the local `toas step` call contract by omitting inactive preview
  options from local/operator dispatch. The no-argument default and RPC
  preference/fallback tests pass; the CLI and dispatch modules pass together
  (263 tests).
- Claimed for implementation on 2026-09-29 under the revised shared-turn
  contract. The existing preview switch selects the intermediate state view;
  plain step proceeds to inference after executable intent is resolved.
- 2026-09-29: The initial state-specific user-intent consolidation direction
  was revised. Keep ordinary turn execution/result embedding shared; use the
  state horizon only to change the inference projection. Previous
  `consolidate_user` implementation is exploratory and must be reconciled
  against this direction before implementation continues.
- 2026-09-29: State input turns now use the ordinary USER/CONTROL frontier
  runtime only when the turn contains executable intent. Results are embedded
  back into their source role turn; ordinary text proceeds directly to state
  inference as observation input, without invoking conversation inference.
  CONTROL text is omitted from the state packet while embedded CONTROL results
  are retained as observations.
- 2026-09-29: Focused state-step and CLI coverage passes (299 tests). The full
  suite passes 3346 tests and retains two failures in
  `tests/test_state_execution_experiment.py`, outside this implementation
  slice: expected experiment wording for failed actions and empty continuation
  observations.
- Inference is eligible only after no executable intent remains unresolved.
  The operator may preview the consolidated state before a later inference
  step, or proceed directly to inference; selection mechanics remain open.
- State-step routing now recognizes typed states even when USER/CONTROL turns
  follow them. Trailing role turns are parsed and retained as transcript text.
- The current implementation puts USER text in `user_inputs`, omits CONTROL
  text, and handles inference on a later explicit step. This projection and
  phase boundary need to be reconciled with the revised shared-turn model.
- Markdown state parsing now finds the outer YAML fence even when a serialized
  tool result contains its own fenced output.
- Focused state-step and CLI state-step coverage passes (33 tests). The
  elevated full suite improved from 14 to 11 failures: the state-step failures
  in the baseline are fixed; remaining failures are the existing CLI dispatch
  expectations and state-execution experiment assertions.
- Durable resolution of slash-command and other direct-action consequences
  remains to be implemented; this task is still active.
