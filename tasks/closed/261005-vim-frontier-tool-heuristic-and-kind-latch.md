Filed as: 261005-vim-frontier-tool-heuristic-and-kind-latch
FKA:
AKA: vim frontier tool heuristic; run kind latch; tool str quirk; speculative tool pre-seed
Legacy index:

keywords: vim, runtime, transport, stream, tool, heuristics, status, latency, historical

Parent: `260811-activity-health-telemetry`
Depends on:
Blocks:
Blocked by:
Related: `261005-state-step-streaming-and-transient-preview`; `vim/plugin/toas.vim`

# Vim Frontier Tool Heuristic And Rigid Run-Kind Latch

## Intent

Prevent speculative frontier text heuristics from locking Vim's run mode into false
`tool` status and masking live LLM streaming output during generation.

## Problem Context & Observed Behavior

During operator interaction in Vim (observed during typed state-step runs), the run
region exhibited a 22-second stall displaying:

```text
## TOAS:RUN ea9a9308c4e7
status: running 0:22
tool: str,

## /TOAS:RUN ea9a9308c4e7
```

While the underlying process was actively generating inference tokens, the editor
displayed no streaming progress ("generating to nowhere"), remaining frozen on
`tool: str,` until the final result replacement occurred.

## Root Cause Analysis

Investigation traced this behavior through three coupled mechanisms in
`vim/plugin/toas.vim`:

1. **Unbounded Frontier Regex Match (`s:toas_extract_frontier_tool_name_from_lines`)**:
   Vim scanned backward through the frontier lines seeking tool operations:
   ```vim
   let l:operation = matchstr(l:line, '^\%(-\s*\)\?operation:\s*\zs[^#[:space:]]\+')
   ```
   This regex loosely matched any line containing `operation:`—including Python type
   annotations (`operation: str,`), docstrings, notes, or instructions in working
   transcripts or observation blocks—extracting `'str,'` as a tool name.

2. **Speculative Pre-seeding (`s:toas_seed_tool_meta_from_frontier`)**:
   Before a run was initiated with the host/backend, Vim guessed the run kind:
   ```vim
   let s:toas_run_kind[a:run_id] = 'tool'
   let s:toas_run_tool_meta[a:run_id].operation = l:tool_name
   ```
   This marked the run as a tool execution before any host confirmation or event.

3. **Rigid Kind Latch (`s:toas_note_run_kind`)**:
   When authoritative stream events arrived from the backend on `llm_reasoning`,
   `llm_answer`, or `llm_prompt_progress` lanes, Vim attempted to note the lane kind:
   ```vim
   let l:current = get(s:toas_run_kind, a:run_id, '')
   if l:current ==# 'tool' || l:current ==# 'llm'
     return 0
   endif
   ```
   Because `s:toas_run_kind` was pre-seeded to `'tool'`, it refused to transition
   to `'llm'`, permanently discarding the authoritative producer signals.

4. **Display Masking (`s:toas_run_display_text`)**:
   When rendering the run region:
   ```vim
   if get(s:toas_run_kind, a:run_id, '') ==# 'tool'
     return get(s:toas_run_tool_text, a:run_id, '')
   endif
   return get(s:toas_run_text, a:run_id, '')
   ```
   Because the kind remained `'tool'`, Vim rendered `s:toas_run_tool_text` (empty),
   while all streamed LLM tokens accumulating in `s:toas_run_text` were masked from
   view until terminal finalization replaced the entire run block with the settled
   projection.

## Desired Reality

1. Authoritative runtime stream events must take precedence over speculative frontier
   heuristics. When events arrive on an `llm_*` lane, Vim must transition `run_kind`
   to `'llm'`.
2. Frontier tool extraction must be structurally bounded (e.g. within genuine tool call
   blocks or directives) rather than matching arbitrary prose, types, or docstrings.
3. The kind latch should distinguish tentative pre-seeded heuristics from confirmed
   producer lane traffic.

## Acceptance Criteria

- Authoritative stream events from the runtime dynamically update `s:toas_run_kind`,
  overriding speculative pre-seeded values.
- Frontier tool extraction does not match arbitrary type annotations (e.g. `operation: str,`)
  or prose outside structural tool blocks.
- Real-time LLM streaming text is not hidden behind an empty tool text buffer when the
  underlying run is an LLM generation.
- Full Vim test coverage (Vader contract suites) and 100% repository coverage maintained.

## Progress

- 2026-10-05: Task opened following diagnosis of the `tool: str,` run stall quirk.
  Root cause isolated to `s:toas_extract_frontier_tool_name_from_lines` matching Python
  type annotations and `s:toas_note_run_kind` refusing to transition from speculative
  `tool` to authoritative `llm` lane.
- 2026-10-06: Resolved:
  - Hardened `s:toas_extract_frontier_tool_name_from_lines` to only match structural tool blocks
    (backtick `yaml` fences with valid identifier operations/tool_names, or unquoted `$` command lines),
    ignoring code blocks of other languages (e.g. `python`) and arbitrary prose annotations outside blocks.
  - Added `s:toas_run_kind_source` to distinguish speculative pre-seeded kinds from authoritative wire events.
    Authoritative wire events (`llm_*` or `tool`) dynamically update the kind latch, overriding speculative
    pre-seeds and clearing stale tool metadata.
  - Updated `s:toas_run_display_text` to fall through to `s:toas_run_text` when `s:toas_run_tool_text` is empty,
    ensuring streaming LLM tokens are never masked behind an empty tool text buffer.
  - Added automated test cases in `tests/vim/vim_plugin_local_host_projection_cases.py` and
    `tests/test_vim_plugin_local_host_projection_cases.py`:
    - `test_python_code_block_does_not_seed_tool_identity`
    - `test_prose_operation_does_not_seed_tool_identity`
    - `test_speculative_tool_overridden_by_authoritative_llm_stream`
  - Validated with full `./scripts/check.sh` suite passing with 100.00% statement coverage
    (3,446 unit + 17 acceptance tests, ruff, mypy).

Status: Complete.
