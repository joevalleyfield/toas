Filed as: 261106-multi-turn-run-region-envelopes
FKA:
AKA: multi-turn run streaming; TOAS:RUN envelopes; stream invariant turn scoping
Legacy index:

keywords: runtime, daemon, vim, streaming, multi-step, envelopes, boundaries, transcript

Related: `261106-bounded-step-quiescence`; `261106-vim-step-count-prefix`

# Multi-Turn Run Region Envelopes and Stream State Scoping

## Intent

Resolve multi-step streaming failures across the daemon runner and Vim watcher:
1. Scope and reset LLM stream accumulator state per turn in `async_step_runtime_worker.py`
   to prevent false `stream invariant violated: typed final answer diverges from streamed answer content`
   assertions on multi-turn bounded runs.
2. Indicate frontier action (tool vs. LLM generation) immediately in `TOAS:RUN` status headers upon
   action decision rather than delaying until stream deltas arrive, and support dynamic run kind
   transitions across consecutive turns.
3. Use canonical transcript markers (`## TOAS:USER` / `## RESULT` and `## TOAS:ASSISTANT`) as
   dedicated envelopes inside `## TOAS:RUN` so resolved tool projections and active assistant
   streams coexist without self-overwriting or flicker.

## Context & Motivation

During dogfooding of bounded multi-step (`\s` with count prefix) in
`.toas/session-20261106-1823-visible-transcript-turn-ids.md` (run `45857b3fb1ff`),
two issues broke the operator experience:

1. **Backend Runner Crash**:
   `async_step_runtime_worker.py` accumulated `run.meta["answer_text_parts"]` across the lifetime
   of the run without resetting between turns. When Turn 4 finished generation,
   `_reconcile_typed_completion` compared Turn 4's single-turn completion against the concatenation
   of Turn 2 + Turn 4 streamed tokens, crashing the run with:
   `[run failed] stream invariant violated: typed final answer diverges from streamed answer content`.

2. **Vim Watcher Overwrite & Status Lock**:
   In `vim/plugin/toas.vim`:
   - `s:toas_note_run_kind` locked `s:toas_run_kind` to `'tool'` as soon as the first tool executed,
     permanently rejecting transitions to `'llm'` for subsequent turns. The status header stayed frozen
     on `tool: read_file (2/2)`.
   - `s:toas_run_display_text` returned only `s:toas_run_projection_text` whenever projection was non-empty,
     discarding `s:toas_run_text` on every timer tick.
   - Streaming assistant tokens lacked a dedicated `## TOAS:ASSISTANT` envelope inside `TOAS:RUN`,
     causing active tokens to stream directly against resolved tool blocks and overwrite themselves.

## In Scope

- **Backend Stream State Scoping**:
  - Scope `run.meta["answer_text_parts"]` and `run.meta["reasoning_text_parts"]` per turn in
    `src/toas/runtime/async_step_runtime_worker.py`.
  - Reset accumulators when an LLM stream opens or when starting generation for a turn so
    `_reconcile_typed_completion` validates only the active turn's completion against that turn's deltas.
- **Vim Frontier Action Indication**:
  - Seed run kind from frontier: if no frontier tool is detected, seed as `'llm'` with stream policy
    indicated immediately.
  - Allow run kind transitions between `'tool'` and `'llm'` across turn boundaries as events arrive.
  - Update status header dynamically (clearing `tool_meta` when transitioning to `'llm'`).
- **Run Region Envelopes & Coexistence**:
  - Frame streaming assistant content under `## TOAS:ASSISTANT` as soon as the active turn is LLM.
  - Update `s:toas_run_display_text` to combine resolved projection and active stream:
    `projection . "\n\n" . active_stream`.
  - Prevent buffer replacement ticks from wiping active streamed tokens.

## Out of Scope

- Changes to durable event schema in `events.jsonl`.
- Changes to single-step execution contracts.
- Altering the wire format of daemon RPC events.

## Acceptance Criteria

1. [x] Multi-turn bounded runs with interleaved tool calls and assistant generations complete without
   raising `stream invariant violated` assertions.
2. [x] In Vim, `TOAS:RUN` immediately indicates `'tool'` or `'stream: ...'` depending on frontier action.
3. [x] Multi-turn runs transition status headers dynamically between tools and LLM streaming.
4. [x] Resolved tool projections and active assistant streams coexist inside `TOAS:RUN` with proper
   `## TOAS:USER` and `## TOAS:ASSISTANT` boundaries.
5. [x] All Python unit tests pass with 100% statement coverage on modified modules; `./scripts/check.sh` passes clean.
6. [x] All Vader tests and Vim plugin python test drivers in `tests/` pass.

## Resolution & Verification

- **Backend Stream Reset**:
  - In `src/toas/runtime/async_step_runtime_worker.py`: reset `run.meta["answer_text_parts"] = []` on successful completion in `_reconcile_typed_completion`; reset `run.meta["reasoning_text_parts"] = []` in `_reconcile_typed_projection_nodes`; reset both in `_on_llm_stream_open` upon opening stream generation for a turn. Emitted `llm_start` event (`lane="llm_answer", phase="start"`).
  - Added `llm_start` to `_EVENT_POLICIES` in `src/toas/runtime/event_classification.py` and registered it as active LLM activity in `src/toas/runtime/async_activity_store_impl.py`.
- **Vim Frontier Action & Dynamic Kind Transitions**:
  - Updated `s:toas_note_run_kind` in `vim/plugin/toas.vim` to allow dynamic transitions between `'tool'` and `'llm'` across turn boundaries.
  - On transition to `'llm'`, cleared `s:toas_run_tool_meta` so status header reflects streaming assistant rather than stale tool metadata.
  - On transitions, reset turn text accumulators so subsequent turns stream into clean buffers.
- **Run Region Envelopes & Multi-Turn Coexistence**:
  - In `s:toas_run_display_text`, combined resolved `s:toas_run_projection_text` and active `s:toas_run_text`, framing active streaming content under `## TOAS:ASSISTANT` boundary when kind is `'llm'`.
  - In `s:toas_append_run_region_chunk`, synchronized with `s:toas_run_display_text` to eliminate drift between append and replace paths.
  - In `s:toas_finalize_terminal_run_region`, preserved enveloped multi-turn output with both tool results and assistant responses intact.
- **Verification**:
  - Full `./scripts/check.sh` passed cleanly with 3,857 unit tests, 17 acceptance tests, and 100.00% statement coverage across all 25,823 statements (162 source files).
  - All 28 Vim plugin test suites in `tests/test_vim_plugin_*.py` passed cleanly.
