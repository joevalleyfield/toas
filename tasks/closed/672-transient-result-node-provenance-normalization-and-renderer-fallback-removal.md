# 672 Transient Result-Node Provenance Normalization And Renderer Fallback Removal
keywords: projection, result, provenance, normalization, control-lane, renderer, active, architecture

## Summary

Transient result projection semantics now depend on explicit provenance (`origin_role`, `origin_kind`) and resolved `projection_lane`, but active code paths still construct bare result nodes and rely on downstream repair or renderer fallback to recover missing semantics.

## Problem

Hand-rolled `{"role": "result"}` nodes remain possible in active code paths. As long as provenance-complete result shaping is optional, hidden downstream repair remains possible, renderer fallback remains semantic policy in disguise, and the architecture can drift back toward ambiguous lane behavior.

## Desired Outcome

- Every active transient result producer constructs result nodes through shared provenance-stamping helper(s).
- Bare `{"role": "result"}` construction is not allowed in active runtime code.
- Append-time and render-time code may validate stamped result nodes, but must not supply missing provenance.
- `render_transcript_blocks()` no longer needs a semantic fallback for unstamped result nodes.
- Control/user/assistant result projection remains deterministic because provenance is complete at creation time.

## Scope

- runtime/result-producing seams across:
  - `src/toas/runtime/step_runtime.py`
  - `src/toas/step.py`
  - `src/toas/runtime/operator_command_prompt_workspace.py`
  - `src/toas/runtime/operator_command_config_help.py`
  - `src/toas/runtime/operator_config_backend_ops.py`
  - `src/toas/runtime/operator_command_extract_replay.py`
- shared transient result-node helper(s) used by active producers
- removal of append-time/render-time semantic repair for missing provenance
- renderer fallback removal once active producers are normalized
- regression coverage for provenance-complete result creation and lane rendering

## Notes

Working architectural invariant:

- transient result projection must be provenance-complete at the producer boundary, before append-time or render-time handling

Expected provenance axes:

- `origin_role`: `user` | `assistant` | `control`
- `origin_kind`: `tool_call` | `slash_command` | `user_shell`

Current tuple-to-lane policy established by `569`:

- `("user", "tool_call") -> "user"`
- `("user", "user_shell") -> "user"`
- `("assistant", "tool_call") -> "user"`
- `("control", "slash_command") -> "control"`
- `("control", "tool_call") -> "control"`

Explicit anti-goal:

- do not solve this task by adding another downstream normalization pass; producer-side construction is the required mechanism

## Done When

- active result producers no longer hand-roll bare `{"role": "result"}` nodes without provenance
- shared helper coverage exists for producer-side result-node creation/stamping
- append-time and render-time code do not repair missing provenance
- renderer fallback to implicit `user` lane is removed
- regression coverage proves control-lane result privacy and user-lane result visibility under the normalized helper path

## Resolution

- landed shared producer-side helpers in `src/toas/step.py` for result-node creation and validation
- migrated active result producers in step/runtime and slash-command handlers to construct provenance-complete result nodes at creation time
- removed append-time and render-time provenance repair; unstamped result nodes now fail validation instead of silently defaulting lanes
- added regression coverage across step, runtime, CLI, and operator-command seams for stamped result creation and rendering behavior
