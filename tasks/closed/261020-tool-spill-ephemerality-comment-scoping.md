# Tool Spill Ephemerality Comment Scoping

Filed as: 261020-tool-spill-ephemerality-comment-scoping
FKA:
AKA: tool spill ephemerality comment; single turn ephemerality conditions; spill trailer scoping
Legacy index:

keywords: tools, rendering, spill, ephemerality, state-step, transcript

Parent: `260926-state-step-requirements`
Related: `261008-state-spill-ingestion-and-artifact-references`

Status: CLOSED; scoped the single-turn ephemerality comment in spilled tool trailers to appear only under single-turn ephemerality conditions.

## Context and Motivation

In task `261008-state-spill-ingestion-and-artifact-references`, `spill_inert_block` in `src/toas/tools_cluster/rendering.py` was updated to warn models:
`[... lines remaining. Read full output (up to 500 lines without spilling) or inspect with read_file, grep, or script via path="..."; under single-turn ephemerality, sipping only the tail drops the previewed head unless persisted into state]`

However, `spill_inert_block` is also invoked during standard conversation transcript sessions (`toas step`), where prior tool outputs persist indefinitely across turns in the transcript and state persistence semantics (`state.notes`, `state.artifacts`) do not apply. In these non-ephemeral conversation conditions, the tail-sipping ephemerality warning is confusing, irrelevant, and counter-factual.

## Intent

Scope the comment about single-turn ephemerality in tool overflow spillage so that it only appears under single-turn ephemerality conditions (e.g. state-step execution/packet generation or explicit ephemerality overrides), while omitting the comment in standard conversation transcript sessions.

## Outcome

- Added `is_single_turn_ephemeral()` and `active_single_turn_ephemeral(enabled)` context management in `src/toas/tools_cluster/rendering.py` using `ContextVar` with fallback to `TOAS_SINGLE_TURN_EPHEMERAL` environment variable.
- Updated `spill_inert_block`, `render_fenced_output`, `render_import_block`, and `shape_result_content` to accept optional `single_turn_ephemeral` (and alias `ephemeral`) parameters or read it from result dictionary payloads, falling back to the active context.
- Scoped trailer generation in `spill_inert_block` so that `; under single-turn ephemerality, sipping only the tail drops the previewed head unless persisted into state` only appends when single-turn ephemerality conditions hold.
- Activated `active_single_turn_ephemeral(True)` in state-step lifecycles (`step_state`, `build_state_step_packet`, `build_multi_state_sequence_packet`, `preview_state_request`, and CLI `_run_state_step`).
- Added comprehensive unit tests in `tests/test_tools_rendering.py` asserting trailer appearance under ephemerality conditions and omission in standard non-ephemeral contexts.
- Verified all 3,512 tests pass and 100.00% statement coverage is maintained across all 22,831 statements in `./scripts/check.sh`.
