Filed as: 261109-vim-terminal-projection-stream-dedup
FKA:
AKA: vim terminal projection stream deduplication; vim projection tail hunk leak; vim duplicate TOAS:ASSISTANT after projection; vim raw streamed tail leak
Legacy index:

keywords: active, bugfix, vim, streaming, projection, terminality, ux

Related: `261109-leading-assistant-turn-normalization`

# Vim Plugin Terminal Projection Stream Deduplication

## Intent

Prevent `s:toas_run_display_text` and `s:toas_finalize_terminal_run_region` in `vim/plugin/toas.vim` from concatenating canonical projection text with leftover streamed `s:toas_run_text` chunks upon terminal success, which causes a duplicate `## TOAS:ASSISTANT` marker and the trailing prenormalized hunk to land after the normalized content.

## Context & Motivation

In `vim/plugin/toas.vim`:

1. `s:toas_apply_watch_events` sets `s:toas_run_text[a:run_id] = ''` when `projection_chunk != ''`. However, if the same watch event batch or subsequent poll events contain trailing `llm_delta` chunks (`l:event_chunk`), the caller immediately re-populates `s:toas_run_text[a:run_id]` with that trailing hunk.
2. In `s:toas_run_display_text`, if both `s:toas_run_projection_text` and `s:toas_run_text` are non-empty:
   ```vim
   if l:projection !=# '' && l:formatted_active !=# ''
     let l:proj_trimmed = substitute(l:projection, '\_s\+$', '', '')
     return l:proj_trimmed . "\n\n" . l:formatted_active
   ```
   where `l:formatted_active` wraps `l:active` with `## TOAS:ASSISTANT\n\n`.
3. In `s:toas_finalize_terminal_run_region`:
   ```vim
   if l:projection_text !=# '' && get(s:toas_run_text, a:run_id, '') !=# ''
     let l:canonical_final_text = s:toas_finalize_success_text(s:toas_run_display_text(a:run_id), 'projection')
   ```
   This passes the concatenated text to finalization, leaving the user with the complete normalized content followed by `## TOAS:ASSISTANT` and the final chunk of the raw prenormalized streamed response.
4. When a terminal projection arrives (or during success finalization), `projection_text` is canonical and authoritative; it must wholly supersede intermediate streamed text (`s:toas_run_text`) rather than append to it.

## In Scope

- [ ] Ensure that once canonical projection is received or finalized, `s:toas_run_display_text` and `s:toas_finalize_terminal_run_region` use `l:projection_text` exclusively, rather than concatenating trailing `s:toas_run_text`.
- [ ] Ensure `s:toas_apply_watch_events` ignores/drops stale `llm_delta` chunks once `projection` events start arriving or have already populated `s:toas_run_projection_text`.
- [ ] Add/update Vader or python-vim tests (e.g. `tests/vim/streaming_*.vader` or `tests/vim/vim_plugin_local_host_projection_cases.py`) verifying no trailing hunk or duplicate `## TOAS:ASSISTANT` header is appended after canonical projection.

## Out of Scope

- Modifying backend daemon event emission or graph persistence.

## Acceptance Criteria

1. On terminal success with canonical projection, only canonical projection text replaces the run region in the Vim buffer.
2. No duplicate `## TOAS:ASSISTANT` header or trailing raw hunk remains after the normalized projection.
3. Existing and updated Vader/Vim integration tests pass cleanly.
