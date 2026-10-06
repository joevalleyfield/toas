Filed as: 261005-state-step-streaming-and-transient-preview
FKA:
AKA: state-step streaming; transient state deltas; thinking streaming in state mode
Legacy index:

keywords: runtime, historical, state-step, streaming, thinking, preview

Parent: `260926-state-step-requirements`
Depends on: `260927-state-step-history-projections`; `261004-state-observation-reference-addressing`
Related: `260811-activity-health-telemetry`; `docs/state-step.md`; `src/toas/cli_streaming.py`; `src/toas/runtime/state_step.py`

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

This silence also accentuates the mode cutover latency observed in Vim across
`empty RUN-PENDING -> RUN -> [LLM generation or tool-call] -> streaming content -> final result`
(tracked in `260811-activity-health-telemetry`): entering `RUN` appears stalled even
after the model process is actively generating because no intermediate output reaches
the editor's run region until resolution finishes.

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
- 2026-10-05: Slice 1 completed:
  - Added streaming callback affordances (`on_delta`, `on_reasoning_delta`,
    `on_prompt_progress`) across `execute_state_step` / `step_state`,
    `step_state_once`, `GenerationRunner.generate_state_packet`, and
    `_run_state_step` / `run_step`.
  - Wired `generate_override` and generation flags (`stream_stdout_enabled`,
    `stream_thinking_enabled`, `stream_prompt_progress_enabled`, `llm_stream_mode`,
    `debug_prompt_progress_*`) through state-step dispatch.
  - Verified reasoning deltas, candidate delta chunks, and prompt progress stream in
    real time during generation while `on_projection_delta` delivers the final
    canonical state turn replacement upon completion.
  - All 3,443 unit tests and 17 acceptance tests pass at 100.00% statement coverage
    (22,148 statements) with clean Ruff and Mypy checks.
- 2026-10-06: Slice 2 completed:
  - Wrapped state-step execution in `_run_state_step` to catch malformed / invalid
    generation exceptions (`ValueError`), format structured validation diagnostics
    (`## TOAS:USER\n\n## RESULT\n\n[ERROR] ...`), and deliver them via
    `on_projection_delta` / stdout.
  - Verified transient streamed preview replacement upon generation validation
    failure in both CLI and Vim interface projection tests without corrupting
    durable state.
  - Added `on_llm_completion` callback dispatch to
    `GenerationRunner.generate_state_packet` for lifecycle symmetry.
  - All 3,456 unit tests and 17 acceptance tests pass at 100.00% statement coverage
    (22,225 statements) with clean Ruff and Mypy checks.

Status: Complete.
