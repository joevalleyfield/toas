# Scope Pending State Transitions To Frontier Lineage And Invalidate Stale Proposals

Filed as: 261008-scope-pending-state-transitions
FKA:
AKA: stale pending transition cancellation; scope pending tools to transcript frontier; prevent ghost tool execution
Legacy index:

Parent: `260926-state-step-requirements`
Depends on: `261007-state-protocol-tool-argument-definitions`
Related: `261002-state-transcript-branching-and-modification`; `260928-state-user-control-turn-lifecycle`

## Context

In state-step execution, when model inference proposes tool calls, a `state_transition` record is appended with `status: "pending"`, and the turn is emitted to the transcript with `pending_tools: [...]`.

In `state_step.py`, `_latest_pending(records)` previously looked up the latest `state_transition` with `status in {"pending", "running"}` globally across all records in `events.jsonl`.
However:
1. **Unscoped historical search**: `_latest_pending` did not verify whether the pending transition belonged to the active transcript frontier turn or lineage. If an operator ran conversational/slash commands, branched, edited the transcript to remove `pending_tools`, or seeded a new state turn (`n25`), the dangling pending transition from an earlier turn (e.g. `n17`) remained in history as `"pending"`.
2. **Missing cancellation on intervening input or omitted pending_tools**: In `cli_session_commands.py`, if the user supplied input (`cleaned_input_turns`, e.g. `List open tasks.`), `pending_tool_calls` was passed as `None`. In `step_state()`, cancellation only checked `pending_tool_calls == []`. Because `pending_tool_calls` was `None`, cancellation did not trigger, and `step_state()` proceeded to execute the ancient pending tool calls from `n17`, projecting unexpected result blocks into the new turn.
3. **Preview inconsistency**: `preview_state_request()` also blindly checked `_latest_pending(records)` without checking if the active frontier actually requested pending tool execution.

## Objectives

1. **Scope Pending Tool Execution to Active Frontier**:
   - In `step_state()`, when `session_text` is present, the transcript frontier is authoritative.
   - If the active frontier state turn has no pending tool calls (`not pending_tool_calls`, including `None` and `[]`, or when user input has intervened), any dangling historical `pending` transition must be marked `cancelled` and NOT executed.
   - If `pending_tool_calls` is provided, verify that the pending transition matches the active turn's `state_message_id` and tool calls. If it does not match (stale proposal from a prior/branched turn or edited by operator), cancel the stale proposal and create a fresh operator transition for the active tools.
2. **Update Preview Request Inspection**:
   - Pass `pending_tool_calls` and `state_message_id` to `preview_state_request()`.
   - Ensure preview only reports `execute_batch` if the active frontier actually requests tool execution, and otherwise previews `infer`.
3. **Verify Dogfood & Regressions**:
   - Add targeted tests reproducing the dogfood sequence:
     a) model generates pending transition on turn A;
     b) user runs intervening commands and seeds turn B;
     c) user inputs text on turn B;
     d) verify the stale transition is marked `cancelled` and inference proceeds without ghost tool execution.
   - Verify historical proposal cancellation when user deletes `pending_tools` entirely without typing explicit `[]`.
   - Verify full test suite passes with 100.00% statement coverage.

## Outcome

- Added `_is_stale_pending` in `src/toas/runtime/state_step.py` to identify stale pending proposals when overridden by explicit inference (`infer_from`), empty pending tools (`pending_tool_calls == []`), intervening seed snapshots in history, session frontier discrepancy, or active transcript state turns omitting `pending_tools`.
- Updated `step_state` to explicitly mark stale historical transitions as `cancelled` in `events.jsonl` and avoid executing ghost tool calls.
- Updated `preview_state_request` to accept `pending_tool_calls` and `state_message_id` and use `_is_stale_pending`, ensuring `execute_batch` is previewed only when the frontier actively requests it.
- Updated `cli_session_commands._run_state_step` to pass `pending_tool_calls=[]` when user input turns intervene at the frontier, guaranteeing immediate cancellation of unexecuted proposals from previous turns.
- Verified end-to-end artifact and transcript output reproducing the dogfood sequence: verified stale proposals are cancelled, user input is passed as observation, and no ghost tool calls execute.
- Added comprehensive unit and CLI regression tests and verified `./scripts/check.sh` passes with 100.00% statement test coverage across all 151 source files.
