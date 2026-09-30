Filed as: 260929-vim-state-turn-projection-header
FKA:
AKA: vim post-inference state turn; vim state turn assistant prefix fix
Legacy index:

keywords: surface, vim, projection, runtime, state, correctness

Parent: `260926-state-step-requirements`
Depends on: `260929-state-transcript-parsing-alignment`
Related: `260929-transcript-turn-decorations`

# Vim Plugin Preserves State Turn Headers Post-Inference

Prevent Vim plugin from inserting `## TOAS:ASSISTANT` when finalizing state turns post-inference.

## Context

When running inference in a session containing a state turn (or producing a new `## TOAS:STATE/n` turn), Vim's post-inference finalization logic in `s:toas_ensure_projection_for_lane` and `s:toas_extract_final_projection` in `vim/plugin/toas.vim` only recognizes `^## TOAS:(SYSTEM|USER|ASSISTANT)$`.

As a result:
1. `s:toas_extract_final_projection` fails to match `## TOAS:STATE/...` or decorated turn markers.
2. `s:toas_ensure_projection_for_lane` falls back to prepending `## TOAS:ASSISTANT\n`.
3. In the working transcript, the turn ends up prefixed with `## TOAS:ASSISTANT` immediately before `## TOAS:STATE/n`.

## Principles

1. **State Turn Identity**: State turns (`STATE` and `STATE-DIFF`), as well as all first-class TOAS turn types (`SYSTEM`, `USER`, `ASSISTANT`, `CONTROL`, `STATE`, `STATE-DIFF`), must be preserved as their own turn headers.
2. **Turn Marker Decorations**: Turn markers carrying versions (`/1`, `/2`) or presentation decorations must be matched consistently across all Vim regex anchors.
3. **No Spurious Assistant Framing**: Vim must never insert `## TOAS:ASSISTANT` above a turn that is already marked as a valid TOAS role (specifically including `STATE` and `STATE-DIFF`).

## Acceptance Criteria

- `s:toas_ensure_projection_for_lane` recognizes all canonical TOAS turn markers (`SYSTEM`, `USER`, `ASSISTANT`, `CONTROL`, `STATE`, `STATE-DIFF`) including version suffixes and decorations, and does not prepend `## TOAS:ASSISTANT`.
- `s:toas_extract_final_projection` and `s:toas_trim_*` helper functions in `vim/plugin/toas.vim` recognize `STATE` and `STATE-DIFF` markers with version/decorations.
- Vim syntax (`vim/syntax/toas_transcript.vim`) recognizes `STATE` and `STATE-DIFF` turn markers with version/decorations.
- Test coverage in `tests/test_vim_plugin_local_host_projection_cases.py` verifies that post-inference state turn projection preserves `## TOAS:STATE/n` without inserting `## TOAS:ASSISTANT`.
- Full test suite passes.

## Implementation Progress (2026-09-29)

- Updated `vim/plugin/toas.vim`:
  - `s:toas_ensure_projection_for_lane` now scans past leading whitespace/newlines, matches all canonical turn headers (`SYSTEM`, `USER`, `ASSISTANT`, `CONTROL`, `STATE`, `STATE-DIFF`) with arbitrary suffixes/decorations, and returns the stripped text without prepending `## TOAS:ASSISTANT`.
  - `s:toas_extract_final_projection`, `s:toas_trim_streamed_tool_prefix`, `s:toas_trim_hallucinated_follow_on_turns`, `s:toas_render_run_body_lines`, and `s:toas_extract_frontier_tool_name_from_lines` now match all turn headers including `STATE` and `STATE-DIFF`.
  - Unified `s:toas_finalize_terminal_run_region` so that `projection_text` also routes through `s:toas_finalize_success_text`.
- Updated `vim/syntax/toas_transcript.vim`:
  - Added syntax matches for `toasRoleState` and `toasRoleStateDiff`.
  - Allowed turn headers with version suffixes (`/1`, `/2`) and presentation decorations.
  - Linked `toasRoleState` and `toasRoleStateDiff` to `Title`.
  - Updated fence region end markers and sync line anchors to recognize `STATE` and `STATE-DIFF`.
- Tests and verification:
  - Updated `tests/vim/transcript_syntax_probe.vader` with syntax assertions for state and state-diff roles and highlight links.
  - Added `state_projection_lane` scenario and `test_local_host_state_projection_lane_preserves_state_header_without_assistant` in `tests/test_vim_plugin_local_host_projection_cases.py`.
  - Verified all 23 Vim tests pass cleanly.

