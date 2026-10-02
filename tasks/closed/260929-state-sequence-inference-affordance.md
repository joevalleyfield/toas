Filed as: 260929-state-sequence-inference-affordance
FKA:
AKA: multi-state inference; whole-sequence state review; state-chain inference
Legacy index:

keywords: runtime, investigation, inception, usability, state-step, transcript

Depends on: `260928-state-user-control-turn-lifecycle`; `261002-state-transcript-branching-and-modification`
Blocked by: `261002-state-transcript-branching-and-modification`
Related: `260927-state-step-alpha-loop`; `260928-state-user-control-turn-lifecycle`; `261002-state-transcript-branching-and-modification`

# Add An Affordance For Multi-State Inference

Status: CLOSED; implemented `/infer-from <state-label>` affordance in trailing USER turns and `--infer-from` CLI option for multi-state sequence inference with 100% test coverage and parity.

## Problem Context

In state-step operation, inference normally receives a single `{state, observation}`
packet derived from the latest state turn and trailing observations. When an operator
wants the model to reconsider its trajectory using accumulated context across multiple
states, an explicit affordance is needed so the model can inspect an ordered sequence of
state turns without requiring the operator to rewrite `STATE` markers as `ASSISTANT`.

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

## Acceptance Criteria

- [x] Command parsing: detect `/infer-from <state-label>` on any line of a trailing `USER` turn, extracting the target label and isolating remaining user text as redirection prose.
- [x] CLI option parity: support `--infer-from <state-label>` on `toas step` with identical resolution semantics.
- [x] Label resolution: resolve `<state-label>` matching `STATE/N`, `STATE-DIFF/N`, or integer `N` case-insensitively, raising a descriptive `ValueError` if the label is not found.
- [x] Sequence projection: construct a model-facing message sequence from the resolved starting state through the frontier, preserving explicit `STATE` identity in model-occupying turns and formatting intervening user/tool observations under standard visibility rules.
- [x] Response contract parity: state model output adheres to the existing `{state_patch, tool_calls, outcome}` JSON schema, applying the patch to advance state at the frontier without mutating prior turns or history.
- [x] One-inference lifetime: `/infer-from` directs only the active step; subsequent steps automatically return to ordinary single-state context.
- [x] Proposal overtake: pending tool proposals on earlier state turns are overtaken and not executed when `/infer-from` is invoked in a trailing user turn.
- [x] Preview parity: `toas step --preview-request` outputs the multi-state sequence projection when `/infer-from` or `--infer-from` is specified.
- [x] Verification: unit and integration tests covering all sequence projection, command parsing, and step execution scenarios; `./scripts/check.sh` passes 100% clean.

## Progress

- 2026-09-30: Refined span selection, transcript invocation, one-inference
  lifetime, model-facing projection, and pending-proposal behavior through
  operator discussion. The semantic direction is established; implementation
  encoding and recovery details remain deferred. No implementation changes
  were made in this refinement.
- 2026-10-02: Activated task implementation slice and defined acceptance criteria.
- 2026-10-02: Implemented `/infer-from <state-label>` parsing, state label resolution, sequence projection with explicit state identity (`build_multi_state_sequence_packet`), preview support, proposal overtake, and CLI `--infer-from` plumbing across CLI, operator API, and state-step runtime. Verified with comprehensive tests and `./scripts/check.sh` at 100% test pass and 100.00% statement coverage. Closed task.

## Evidence

- Verified `./scripts/check.sh` passing clean with 3418 tests passed, 17 acceptance tests passed, ruff clean, mypy clean, and 100.00% total statement coverage across 149 covered files.
- Unit and integration tests added in `tests/test_cli_session_commands_state_step.py`, `tests/test_cli_dispatch.py`, and `tests/test_state_step.py`.
