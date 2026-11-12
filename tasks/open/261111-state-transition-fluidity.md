Filed as: 261111-state-transition-fluidity
FKA:
AKA: fluid state in/out; conversation<->state transition
Legacy index:

keywords: state-step, transition, transcript, fluidity, conversation, operator-ergonomics, design
Depends on:
Related: `260926-state-step-requirements` (state runtime family); `261111-toas-new-edit-sessions` (out-of-scope note pointed here)

# Fluid in/out of the STATE flow

Status: OPEN; design/intent capture, deferred implementation

## Objective

Capture the operator's want to move between the conversation flow and the
STATE flow fluidly -- entering a state transcript and returning to
conversation without hand-editing `## TOAS:STATE/1` markers or manually
re-deriving state. This is a design/intent capture; implementation is
deferred until the underlying state runtime is in a shape the operator is
comfortable with.

## Context / Why deferred

- State mode is a SEPARATE runtime reached by transcript content (a
  `## TOAS:STATE/1` / `## TOAS:STATE-DIFF/1` turn routes to
  `_run_state_step` in `src/toas/cli_session_commands.py`), not by config.
  An empty session file cannot reach it without a hand-typed marker.
- The operator dislikes that state is a separate runtime and is "not in a
  position to fix it just yet." So the fluid-transition work is parked:
  building a transition surface on top of a runtime that is itself
  unsatisfactory would be premature.
- The "how do I start a state transcript" question is now documented
  knowledge (hand-type the first `## TOAS:STATE/1` turn); it is not the
  open problem. The open problem is the *fluidity* of moving in and out.

## The want (to be designed, not yet specified)

- Enter STATE from conversation: a deliberate, low-friction way to seed a
  state transcript from the current conversation context (not a blank
  marker the operator must hand-author).
- Exit STATE back to conversation: a way to return to the conversation
  flow with the state carried forward as context, rather than the state
  runtime terminating or the operator manually reconciling.
- Round-trip stability: moving in and out should not corrupt the durable
  transcript or the turn-namespace allocation (coordinate with
  `261111-result-turn-id-namespace-advance` if turn identity is affected).

## Out of Scope (this task)

- Rebuilding or unifying the separate state runtime itself. That is the
  `260926-state-step-requirements` family's concern and is explicitly
  deferred.
- Any seed-selection surface (`/prompt` covers message seeding; no
  `## TOAS:SEED`).

## Next step (when unblocked)

- Spike the state runtime's current enter/exit contract (what a state turn
  requires, what it emits on terminal) to define the minimal transition
  surface, THEN specify. Keep this task as the design owner; open narrow
  implementation follow-ons once the state runtime is stable enough to
  build on.
