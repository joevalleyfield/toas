Filed as: 260930-state-step-transcript-supremacy
FKA:
AKA: state tool outcome transcript supremacy; truncated tool results in state mode
Legacy index:

keywords: runtime, bugfix, transcript, state-step, supremacy, tool_outcomes

Parent: `260926-state-step-requirements`
Depends on: `260928-state-user-control-turn-lifecycle`
Related: `260927-state-step-alpha-loop`; `260927-state-step-history-projections`

# Restore Transcript Supremacy For Tool Results In State-Mode Step Evaluation

Ensure operator edits or truncations to tool results in `session.md` are authoritative during state-mode step evaluation rather than being overridden by durable history records in `events.jsonl`.

## Current Reality
When batch tools execute in state mode, their results are appended to `session.md` as `## TOAS:USER\n\n## RESULT` turns and recorded to `events.jsonl` as `state_tool_result`. During subsequent state-step evaluation (`build_state_step_packet`), `_compound_observation` reads `state_tool_result` directly from `events.jsonl` history records and populates `tool_outcomes` with the raw untruncated result, ignoring any truncations or edits made by the operator in `session.md`. Furthermore, `extract_inert_blocks_by_id` seeds `blocks_by_id` from history records in `events.jsonl`, resurrecting original untruncated content.

## Desired Reality
The operator-controlled transcript `session.md` remains the supreme authority. If a tool result is truncated, modified, or removed by the operator in the transcript:
1. The inference packet observation reflects the operator's truncated result as authored in `session.md`.
2. History records in `events.jsonl` do not overwrite or supersede operator-edited transcript content.
3. Inert block extraction respects the transcript over history records when `session_text` is provided.

## Gap Analysis
- `observation_with_user_turns` must parse `## RESULT` blocks from `user` turns separately from user prompt prose, making transcript tool results available to observation assembly.
- `_compound_observation` must reconcile `tool_outcomes` against the transcript: if the operator truncated or removed `## RESULT` blocks, the transcript's content takes precedence over `records` in `events.jsonl`.
- `build_state_step_packet` must extract inert blocks from `session_text` as authoritative when `session_text` is available, falling back to `records` only when no session text is provided.

## Transformations
1. Update `src/toas/runtime/state_step.py`:
   - Parse `## RESULT` blocks out of `USER` turns in `observation_with_user_turns` into `user_results`, keeping only user prose in `user_inputs`.
   - Update `_compound_observation` to prioritize transcript `user_results` and `operator_observation["tool_outcomes"]` over history `records`.
   - Prioritize `session_text` over `records` for `extract_inert_blocks_by_id`.
2. Add comprehensive tests verifying truncated tool results in `session.md` are passed to inference rather than untruncated results from history.

## Progress
- 2026-09-30: Added `_user_result_observations` and `_user_input_observations` to split `USER` turns into prompt prose and tool result blocks.
- Added `_reconcile_tool_outcomes` to update tool outcome node contents with operator-authored transcript text and drop deleted outcomes.
- Updated `_compound_observation` and `build_state_step_packet` to respect `session_text` and transcript turns over history records, falling back to `records` only when running without a transcript.
- Updated `build_state_step_packet` so `extract_inert_blocks_by_id` uses `session_text` authoritatively when present without resurrecting from `records`.
- Added end-to-end and unit test coverage in `tests/test_cli_session_commands_state_step.py` and `tests/test_state_step.py`.

Status: Complete.
