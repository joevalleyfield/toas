Filed as: 261005-state-step-streaming-and-transient-preview
FKA:
AKA: state-step streaming; transient state deltas; thinking streaming in state mode
Legacy index:

keywords: runtime, active, state-step, streaming, thinking, preview

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-history-projections`; `261004-state-observation-reference-addressing`
Related: `docs/state-step.md`; `src/toas/cli_streaming.py`; `src/toas/runtime/state_step.py`

# State-Step Streaming And Transient Delta Preview

## Intent

Support live streaming feedback (prompt progress, thinking deltas, and candidate
state delta text) during state-step model generation, replacing the transient
streamed preview with the canonical resolved state turn once generation and
validation complete.

## Problem Context

In state-transition mode, model invocation currently executes as an unstreamed
call. When the model engages in extended reasoning or generates a large state
patch with tool calls, the user observes no live feedback until the full
response is returned, decoded, and merged into durable state.

TOAS has an established precedent in conversation mode where:
1. Thinking deltas stream in real time into the active turn or result region.
2. Prompt construction progress streams live.
3. Content deltas stream progressively.
4. When the step concludes, the transient representation is replaced by the
   settled, canonical projection.

Applying this pattern to state-step provides immediate liveness and early
visibility into the model's draft trajectory while keeping durable history and
settled working transcripts clean and projection-grounded.

## Scope And Boundaries

- Wire streaming callback affordances (`on_delta`, `on_reasoning_delta`,
  `on_prompt_progress`) into `execute_state_step` and the state generation runner.
- Stream reasoning deltas and candidate state delta text into transient preview
  surfaces during generation.
- On successful completion, replace the transient preview with the canonical
  projected state turn (`## TOAS:STATE [[handle]]` or diff vector) and pending tool
  blocks.
- On malformed or invalid generation output, replace the transient preview with
  the validation diagnostic and record the invalid response event without
  corrupting durable state.
- Maintain 100.00% statement coverage across all test suites.

## Acceptance Criteria

- `execute_state_step` accepts streaming callbacks (`on_delta`,
  `on_reasoning_delta`, `on_prompt_progress`) and forwards them to the underlying
  model generator.
- Thinking deltas are emitted to `on_reasoning_delta` when thinking is enabled.
- Content deltas are emitted to `on_delta` progressively during state-step
  generation.
- Settled transcript output materializes the canonical state turn and replaces or
  supersedes transient candidate text.
- Full unit test coverage and clean type checks.

## Progress

- 2026-10-05: Task opened following discussion on applying the thinking-streaming
  transient-to-canonical replacement precedent to state-step generation.

Status: Active.
