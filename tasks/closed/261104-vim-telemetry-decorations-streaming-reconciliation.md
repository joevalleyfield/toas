Filed as: 261104-vim-telemetry-decorations-streaming-reconciliation
FKA:
AKA: vim telemetry decorations; async step projection streaming reconciliation; vim canonical assistant turn header
Legacy index:

keywords: vim, runtime, streaming, telemetry, turn-id, canonicalization, projection, reconciliation

Parent: `260825-visible-transcript-turn-ids`
Related: `261104-visible-turn-ids-and-compact-headers`; `261104-transcript-turn-telemetry-decorations`; `261030-post-generation-yaml-canonicalization`

# Vim Telemetry Decorations and Streaming Reconciliation

## Status

Closed on 2026-11-04. The async step worker now emits canonical assistant
projection onto the `projection` lane upon generation completion, allowing
Vim's canonical reconciliation path (`s:toas_replace_run_region_with_canonical`)
to swap the streamed region with the canonical decorated heading while retaining
isolated undo history.

## Intent

Wire up Vim plugin and async step runtime so that canonical transcript
projections (including telemetry decorations, visible turn IDs, and YAML healing)
are emitted on the projection lane and reconciled into the buffer upon successful
turn completion when streaming in Vim.

## Problem

In Vim, during interactive `:ToasStep`, answers stream live into the buffer
wrapped by transient run markers. When streaming succeeds:
1. `src/toas/runtime/async_step_runtime_worker.py` suppressed emitting
   `projection_delta` when `run.llm_answer_bytes > 0`. As a result,
   `s:toas_run_projection_text` in Vim remained empty.
2. Because `s:toas_run_projection_text` was empty, `toas.vim` fell back to
   reconstructing the final turn heading via `s:toas_ensure_projection_for_lane`,
   which hardcoded `return '## TOAS:ASSISTANT' . "\n" . l:text`.
3. Consequently, telemetry decorations (such as `[bravo claude-3-7-sonnet 11:42:00 1.2s]`),
   visible turn IDs, and YAML healing did not appear in the Vim buffer, and saving
   the buffer stripped them from `session.md`.

## Solution

1. Updated `async_step_runtime_worker.py` so that canonical assistant projection
   is emitted on `lane="projection"` even when answer streaming occurred
   (`run.llm_answer_bytes > 0`), unless explicitly suppressed by reasoning
   fallback (`suppress_next_assistant_projection`).
2. Added `tests/vim/post_generation_telemetry_decorations_undo.vader` verifying
   that Vim's `s:toas_replace_run_region_with_canonical` swaps the buffer region
   with the canonical decorated heading, and that undo (`u`) cleanly reverts to
   the raw streamed output and then the pre-run state.
3. Updated `tests/test_daemon_async_runner.py` to assert emission of canonical
   projection on `lane="projection"`.
4. Verified `./scripts/check.sh` passes with 100.00% statement coverage across
   all 161 source files.
