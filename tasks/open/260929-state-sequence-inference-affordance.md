Filed as: 260929-state-sequence-inference-affordance
FKA:
AKA: multi-state inference; whole-sequence state review; state-chain inference
Legacy index:

keywords: runtime, investigation, inception, usability, state-step, transcript

Related: `260927-state-step-alpha-loop`; `260928-state-user-control-turn-lifecycle`

# Add An Affordance For Multi-State Inference

Explore and add an explicit affordance that lets state inference consider a
selected transcript stretch containing an ordered sequence of state turns. This should
let the model reconsider its trajectory using the accumulated context without
requiring the operator to change `STATE` markers to `ASSISTANT` markers.

## Intended Behavior

- Inference receives a model-facing transcript projection from a labeled
  starting state through the current transcript frontier.
- The model produces one forward state advancement from that context; prior
  state turns and durable history remain immutable.
- The affordance is explicit and leaves ordinary single-state stepping
  available.

## Refined Direction (2026-09-30)

- A USER turn can contain custom redirection prose followed by
  `/infer-from <state-label>`. A CLI option may expose the same capability, but
  the affordance must be accessible through transcript operation rather than
  only through the CLI.
- Use existing state labels to address the first included state. Label
  formatting may evolve without removing the addressing contract. Richer
  git-revision-like addressing is deferred.
- The selected stretch ends at the current transcript frontier. Existing
  transcript truncation and Vim leader-S fork controls already let the
  operator choose an earlier endpoint while preserving the tail; this
  affordance does not need a separate endpoint selector. Selecting the first
  state covers the whole-transcript use case, while selecting a later label
  bounds context consumption.
- The selector applies to one inference only. Subsequent ordinary steps return
  to the normal single-state inference context.
- Build a model-facing transcript shaped much like ordinary transcript-mode
  input, with STATE turns in the positions otherwise occupied by assistant
  turns. Preserve explicit STATE identity so the model answers in state
  terms; do not convert those turns to ASSISTANT or introduce a separate
  states-plus-associated-observations packet. Apply normal model-visibility
  rules to intervening user input and tool interactions.
- The USER turn's custom prose supplies the operator's redirection. No special
  superseded-request observation is required.
- Creating this USER frontier lets the operator move past an unwanted pending
  tool proposal, as in ordinary transcript operation. The proposal is
  overtaken by the new frontier: it must not execute or block the requested
  inference. Preserve its durable history without making it govern the new
  frontier.
- Carry over the existing state response contract: one validated state patch
  and optional tool batch advancing the frontier. Prior states and durable
  history remain immutable.

## Deferred Implementation Details

- Exact provider-message encoding of the transcript projection while retaining
  explicit STATE identity.
- Label resolution diagnostics and command parsing details.
- Durable selector/proposal disposition and replay mechanics that preserve the
  one-inference selection and prevent an overtaken proposal from executing.

## Progress

- 2026-09-30: Refined span selection, transcript invocation, one-inference
  lifetime, model-facing projection, and pending-proposal behavior through
  operator discussion. The semantic direction is established; implementation
  encoding and recovery details remain deferred. No implementation changes
  were made in this refinement.
