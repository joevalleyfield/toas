# 569 Frontier Empty Transcript Block Normalization
keywords: projection, hardening, active, correctness, transcript, frontier, parser, normalization

## Summary

Intermittent frontier instability appears when consecutive transcript markers create empty parsed message nodes (for example an empty `## TOAS:USER` block after a projected `## RESULT`).

## Problem

`parse_transcript()` currently emits zero-content blocks when a role marker is followed immediately by another role marker. These empty nodes can become durable candidates in step lineage and perturb frontier role/parent selection.

## Desired Outcome

- Empty transcript role blocks are ignored during parsing.
- Frontier/runtime behavior remains stable across repeated `toas step` invocations after failed tool projections.
- Regression coverage exists for consecutive-marker empty block cases.
- Result projection lane semantics are explicit instead of hardcoded to `user`.
- Control-originated results remain in the control lane by default instead of surfacing into the user-visible lane.
- Result projection carries enough provenance to distinguish who initiated the consequence and what kind of operation produced it.

## Scope

- `src/toas/transcript.py`
- `tests/test_transcript.py`
- runtime/result projection seams that currently collapse all result nodes to `user`
- transcript rendering and step/runtime consequence assembly paths that can already see frontier role and execution kind

## Notes

Repro evidence: repeated `toas step` around assistant shell projection failures can introduce empty `## TOAS:USER` markers and duplicated result behavior at frontier.

Discovery questions now in scope before broader implementation:

- Is plain `{"role": "result"}` too lossy for projection semantics, and should transient result nodes carry explicit provenance metadata?
- Which provenance fields are already near-at-hand when result nodes are produced:
  - initiating role (`user`, `assistant`, `control`)
  - execution kind (`tool_call`, `slash_command`, `user_shell`, or another existing distinction)
- Should projection lane be derived from provenance at render time, or stamped onto result nodes earlier as explicit lane metadata?
- Which current result paths are semantically distinct:
  - assistant callable tool results
  - user callable tool results
  - control slash-command results
  - user `$ ...` shorthand results
- What existing durable or transient metadata can be reused so lane/provenance semantics do not require inventing a larger new record model?

## Progress

- runtime tool-result projection no longer injects an empty synthetic `user` prefix before `render_transcript_blocks()` adds the result-owned user-lane marker
- CLI and runtime seam regressions now assert the single-marker shape `## TOAS:USER\n\n## RESULT\n\n...` for callable tool results

## Discovery Notes

- Current collapse point:
  - `src/toas/runtime/rendering_edges.py` hardcodes every `{"role": "result"}` node into the `user` lane.
  - most upstream producers emit only `role/content` plus optional payload/update fields, so renderer-side inference has no provenance to work with.
- Provenance already near-at-hand in execution seams:
  - `src/toas/runtime/step_runtime.py`
    - `_run_user_intent_candidate()` knows candidate `kind` (`operator`, `plan`, `shell`) at append time.
    - `_handle_user_or_control_frontier()` already knows the frontier role and routes both `user` and `control` through the same mixed-intent execution path.
  - `src/toas/step.py`
    - `_execute_plan_for_frontier(..., frontier_role=...)` already receives the initiating frontier role.
    - `_execute_user_shell()` is a distinct path from callable tool plan execution.
  - `src/toas/runtime/operator_commands.py`
    - operator-command dispatch builds `OperatorCommandContext` with `working`, so handlers can inspect the active frontier role without new global lookup.
- Likely result provenance axes:
  - initiating role: `user`, `assistant`, `control`
  - execution kind: callable `tool_call`, slash/operator command, explicit user-shell shorthand
- Important special case already visible:
  - `_handle_prompt()` in `src/toas/runtime/operator_command_prompt_workspace.py` already branches on control frontier and manually shapes raw transcript output differently, which is evidence that control-lane result semantics are already straining against the current generic `result -> user` rule.
- Durable/transient mismatch to keep in view:
  - `src/toas/runtime/session_step_edges.py` currently decides durability side effects from the persisted frontier message (`tool_request`/`tool_result` vs `command_request`/`command_result`), but transient result projection itself does not carry equivalent provenance metadata yet.

## Outcome

- empty synthetic `user` result-prefix injection was removed for callable tool-result projection
- result projection lane semantics are no longer hardcoded solely by `role == "result"`
- mixed-intent frontier consequence paths now stamp transient result provenance with:
  - `origin_role`
  - `origin_kind`
  - `projection_lane`
- control-originated slash-command results now render in the control lane by default
- renderer fallback for legacy unstamped result nodes remains intentionally temporary and is tracked by follow-on `672`
