# 672 Transient Result-Node Provenance Normalization And Renderer Fallback Removal
keywords: projection, result, provenance, normalization, control-lane, renderer, active, architecture

## Summary

Transient result projection semantics now depend on explicit provenance (`origin_role`, `origin_kind`) and resolved `projection_lane`, but result creation is still uneven across the codebase and the renderer still carries a compatibility fallback for bare result nodes.

## Problem

Hand-rolled `{"role": "result"}` nodes remain possible in active code paths. As long as provenance-complete result shaping is optional, renderer fallback remains hidden semantic policy and the architecture can drift back toward ambiguous lane behavior.

## Desired Outcome

- Every active transient result producer stamps explicit provenance before rendering.
- Result creation converges on shared helper seams instead of ad hoc leaf-node construction.
- `render_transcript_blocks()` no longer needs a semantic fallback for unstamped result nodes.
- Control/user/assistant result projection remains deterministic because provenance is complete before render time.

## Scope

- runtime/result-producing seams across:
  - `src/toas/runtime/step_runtime.py`
  - `src/toas/step.py`
  - `src/toas/runtime/operator_command_prompt_workspace.py`
  - `src/toas/runtime/operator_command_config_help.py`
  - `src/toas/runtime/operator_command_extract_replay.py`
- shared transient result-node helper(s)
- renderer fallback removal once active producers are normalized
- regression coverage for provenance-complete result creation and lane rendering

## Notes

Working architectural invariant:

- transient result projection must be provenance-complete before rendering

Expected provenance axes:

- `origin_role`: `user` | `assistant` | `control`
- `origin_kind`: `tool_call` | `slash_command` | `user_shell`

Current tuple-to-lane policy established by `569`:

- `("user", "tool_call") -> "user"`
- `("user", "user_shell") -> "user"`
- `("assistant", "tool_call") -> "user"`
- `("control", "slash_command") -> "control"`
- `("control", "tool_call") -> "control"`

## Done When

- active result producers no longer hand-roll bare `{"role": "result"}` nodes without provenance
- shared helper coverage exists for result-node annotation/creation
- renderer fallback to implicit `user` lane is removed
- regression coverage proves control-lane result privacy and user-lane result visibility under the normalized helper path
