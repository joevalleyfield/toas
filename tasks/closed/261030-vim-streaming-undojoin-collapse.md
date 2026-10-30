Filed as: 261030-vim-streaming-undojoin-collapse
FKA:
AKA: vim streaming undojoin; collapse streaming undo points; atomic streaming undo block
Legacy index:

keywords: vim, transcript, streaming, undo, undojoin, usability

Parent:
Depends on:
Blocks:
Blocked by:
Related: 261030-yaml-replace-block-indent-healing

# Collapse Vim Streaming Undo Points Via undojoin

Prevent intermediate undo fragmentation during streaming generation in `toas.vim`
by joining incremental chunk updates into a single undo block.

## Current Reality

1. When a model generation streams into a buffer in `vim/plugin/toas.vim`, chunks are
   appended and run regions are replaced across multiple async timer and job callbacks
   via `s:toas_replace_buffer_region(...)`.
2. Each event loop cycle modifying the buffer creates a separate undo entry in Vim.
3. If an assistant completion streams over several seconds across 30-50 chunks,
   pressing `u` in normal mode steps backwards through every intermediate chunk fragment
   rather than undoing the generated turn in a single step.

## Desired Reality

1. Incremental streaming buffer modifications (`s:toas_append_run_region_chunk` and
   intermediate `s:toas_replace_run_region` calls while a run is active) invoke Vim's
   `undojoin` before modifying buffer lines.
2. The `undojoin` calls are safely wrapped (e.g. `silent! undojoin` or `try | undojoin | catch /^Vim\%((\a\+)\)\=:E790:/ | endtry`)
   so that edge cases (such as running immediately after an undo or in an empty undo state)
   fail silently and safely without breaking buffer updates.
3. After a streaming run completes, pressing `u` once reverts the entire streamed turn
   back to the pre-generation state, and `<C-r>` restores the complete streamed turn.
4. Passes `./scripts/check.sh` and dedicated Vim integration/vader tests.

## Acceptance Criteria

- [x] Incremental streaming chunk replacements invoke `undojoin` in the target buffer before modifying lines.
- [x] Any E790 / undojoin exceptions are caught and handled safely.
- [x] A multi-chunk streaming run produces a single unified undo block in Vim that reverts completely with one `u`.
- [x] Existing Vim driver and plugin tests continue to pass cleanly.

## Verification Evidence

1. Vader integration suite:
   - `vim -Nu NONE -n -es -c "set rtp^=tests/vendor/vader.vim" -c "runtime! plugin/vader.vim" -c "source vim/plugin/toas.vim" -c "Vader! tests/vim/streaming_undojoin_collapse.vader"`: 7/7 assertions passed (streaming chunks, single undo to pre-run buffer, single redo).
2. Existing Vim driver tests:
   - `uv run pytest tests/test_vim_driver_baseline.py tests/test_vim_driver_contract_plugin.py`: all tests passed cleanly.
3. Full mechanical suite check:
   - `./scripts/check.sh`: 3,630 tests passed, 100.00% statement coverage across 157 source files, ruff lint/format clean, mypy clean.
