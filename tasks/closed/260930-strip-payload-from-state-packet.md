Filed as: 260930-strip-payload-from-state-packet
FKA:
AKA: strip tool result payload from state packet; state observation payload sanitization
Legacy index:

keywords: runtime, state-step, projection, payload, sanitization, correctness

Parent: `260926-state-step-requirements`
Depends on: `260930-state-step-transcript-supremacy`
Related: `260930-paged-inert-tool-spillover`

# Strip Tool Result Payloads From State-Step Inference Projection

Ensure internal tool execution payloads stored in `state_tool_result` records in durable history are not serialized into model inference packets during state-step projection.

## Current Reality
When tools execute, result nodes carry both `content` (rendered text for transcript display) and `payload` (internal Python execution data, e.g. `get_structure`'s 1,856 raw AST symbol dictionaries totaling >300 KB).
In conversational mode, `project_llm_input_from_messages` projects message events strictly to `{"role": ..., "content": ...}`, never forwarding `payload`.
In state mode, however, `_reconcile_tool_outcomes` and `build_state_step_packet` serialize raw result node dicts into `tool_outcomes[i]["result"]`, passing `payload` directly to the model. This silently leaks hundreds of kilobytes of internal tool data into LLM prompts and undermines operator transcript edits.

## Desired Reality
1. Result nodes in `tool_outcomes` projected into the state-step LLM inference packet only include model-facing observation fields (`content`, `role`, `projection_lane`, `origin_role`, etc.) and strip `payload`.
2. When `_reconcile_tool_outcomes` updates result nodes from operator-authored transcript text, `payload` is stripped so internal state never shadows or accompanies operator-edited text.
3. Durable history in `events.jsonl` continues to retain `payload` on `state_tool_result` records for auditability and tool-level checks.

## Gap Analysis
- `_reconcile_tool_outcomes` preserves `node.get("payload")` when copying result nodes.
- `build_state_step_packet` (or a helper sanitizing tool outcomes for projection) forwards `node["payload"]` into the model's observation packet.

## Acceptance Criteria
- Result nodes in `packet["observation"]["tool_outcomes"][...]["result"]` do not contain `payload`.
- Truncated or untouched tool outcomes project clean, minimal result nodes with `content`, `role`, and `projection_lane`.
- Durable `state_tool_result` records in `events.jsonl` still retain `payload`.
- State-step preview of sessions with heavy tools (e.g. `get_structure`) shrinks by >95% to model-relevant text.
- All existing tests pass without regressions.

## Progress
- 2026-09-30: Added `_sanitize_projected_tool_outcomes` in `toas.runtime.state_step` to strip `payload` from all result nodes in `tool_outcomes` during `build_state_step_packet`.
- Updated `_reconcile_tool_outcomes` to strip `payload` when reconciling result nodes with operator-authored transcript text.
- Verified on live user session `.toas/session-20260930-1803-commit-state-sequence-task-refinements`: `request_messages[0]` shrank from 314,630 chars (345 KB) to 6,516 chars (6.8 KB), a 98% reduction.
- Added unit tests in `tests/test_state_step.py` verifying `payload` is absent from projected packet result nodes while retained in `events.jsonl`.
- Verified test suite passes without regressions.

Status: Complete.
