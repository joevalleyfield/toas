Filed as: 260928-state-edit-and-user-tools
FKA:
AKA: user-authored state turn; state editing with user tool calls
Legacy index:

keywords: runtime, exploration, inception, state-step, user-intent, tools

Parent: `260926-state-step-requirements`
Related: `260927-state-step-alpha-loop`; `260927-state-step-history-projections`

# User-Authored State Editing And Tool Calls

## Proposal

Give state-step a user-authored editing affordance analogous to a user turn in
a conversation. The operator can edit state and author tool calls in the
state transcript. A `step` consolidates those edits into the next accepted
state, records the actual state delta, and executes any user-authored tool
calls in that same explicit step. Tool outcomes, including failures, become
observations on the consolidated state. A subsequent explicit `step` hands
that state and its observations to the model for inference.

The consolidation/execution step must not also call the model. This keeps the
user's authored intent and its observations inspectable before model handoff,
and avoids hidden execute-and-infer behavior.

## Intended Sequence

1. The operator authors state edits and optionally a batch of tool calls in a
   user-shaped state turn.
2. `step` consolidates the edits against the current accepted state, persists
   the resulting state and true delta, and executes the authored batch through
   user-intent capability handling.
3. Tool outcomes are materialized as observations on the consolidated state.
   The step ends without inference.
4. A later `step` sends the consolidated state and its compound observation to
   the model. Model-proposed calls retain their existing pending-call lifecycle
   and remain distinguishable from user-authored calls.

When the user turn has no calls, consolidation still ends without inference;
the next explicit step performs model handoff. This makes the phase boundary
consistent and gives the operator a chance to inspect the consolidated state.

## Confirmed Boundaries

- User-authored edits and calls are first-class state-step input, not
  conversation message events.
- The explicit step that consolidates user edits also executes that user's
  authored calls; it does not invoke the model.
- Tool results enter the state transcript as observations before inference.
- User-authored calls and model-proposed calls keep distinct provenance and
  execution timing.
- Earlier accepted state history and durable records are append-only; edits
  produce a new accepted state and delta.
- Tool failures are retained as outcomes/observations and do not roll back the
  accepted state edit.

## Implementation Scope

- Define a readable user-authored state-turn syntax for edits and optional tool
  calls, preserving YAML and Markdown state transcript formats where practical.
- Reconcile the authored edit against the latest accepted state and record the
  actual delta and resulting snapshot.
- Route authored calls through existing user-intent capability and permission
  semantics, not the model-addressable batch-call authority lane.
- Materialize each outcome into the current compound observation before the
  following model request.
- Make `step` report whether it consolidated/executed user intent or performed
  model inference, without combining those phases in one call.
- Preserve compatibility with existing state transcripts and model-proposed
  tool batches.

## Acceptance Criteria

- An operator can express state edits and zero or more tool calls in the
  state transcript without fabricating conversation message events.
- One explicit `step` accepts the edit, records its actual delta and resulting
  state, executes its authored calls, and records all outcomes as observations.
- That step never invokes the model, even when it executes calls.
- The following explicit `step` sends the consolidated state and resulting
  observations to the model.
- User-authored calls use user-intent authority and are durably distinguishable
  from model-proposed calls.
- Failed calls appear in observations and do not undo the consolidated state.
- Existing model-proposed calls still execute only on their later explicit
  step and remain identifiable as model-originated.
- Repeated steps, restart, and transcript editing do not duplicate already
  recorded user calls or rewrite prior accepted states.

## Decisions Deferred To Implementation

- Exact typed-turn marker and field names.
- Whether edits are expressed as a complete state or sparse patch; choose the
  form that best matches current editable state behavior while recording the
  actual delta durably.
- Whether one user turn may hold multiple tool calls; default to the existing
  batch shape unless a concrete constraint appears.
- Precise display shape for outcome blocks, provided they remain readable and
  import-safe in the session transcript.

## Elaboration Status

The phase sequence, provenance boundary, and failure behavior are sufficiently
clear to begin implementation. Exact transcript grammar and record schema are
delegated to the implementation task using existing TOAS state-step and
user-intent conventions.

Status: Ready.
