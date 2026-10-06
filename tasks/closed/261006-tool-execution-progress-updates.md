Filed as: 261006-tool-execution-progress-updates
FKA:
AKA: tool progress updates; tool execution telemetry; multi-tool progress; silent tool visibility
Legacy index:

keywords: runtime, transport, stream, tool, progress, vim, surface, historical, usability

Parent: `260811-activity-health-telemetry`
Depends on: `261005-vim-frontier-tool-heuristic-and-kind-latch`
Blocks:
Blocked by:
Related: `261005-state-step-streaming-and-transient-preview`; `src/toas/tools_cluster/execution.py`; `vim/plugin/toas.vim`

# Tool Execution Progress Updates During Plan And State Execution

## Intent

Provide live progress updates in the operator UI (Vim) as TOAS works through tool
executions—including silent tools with no stdout/stderr output and multi-tool batches—preserving
strong typed event semantics across the stream bridge.

## Problem Context

Currently, tool execution observability in Vim is reactive and sparse:
1. When a step begins executing tools, Vim only displays the initially seeded or first-detected
   tool name (e.g. `tool: read_file`).
2. Tools that produce no streaming stdout/stderr (e.g. `read_file`, `write_file`, `search`,
   `sleep`, API operations) emit no intermediate output chunks while running. The editor remains
   static (`status: running 0:14`) with no indication of whether the current tool is still
   executing or has stalled.
3. In multi-tool plans or state-step tool batches, subsequent tools do not update the display
   when they start. The header only updates if/when terminal `[OK]` status lines arrive or when
   the run concludes.

## Semantic Integrity & Event Typing

When streaming progress through the runtime and daemon bridge, we must preserve strict event
typing and avoid blurring stream semantics:
- Tool execution lifecycle events on `lane="tool"`:
  - `tool_start` / `tool_progress`: indicates active tool transition or progress, carrying
    `operation`, optional batch `index` and `total`, and lifecycle stage.
  - `tool_progress` with `text`: carries actual streamed stdout/stderr chunks from tools that
    produce live output.
  - `tool_done`: indicates individual tool completion, carrying `operation`, `ok`, and `status`.
- Ephemeral metadata vs renderable text:
  - Start and progress metadata updates the editor's status line (e.g. `tool: read_file (1/3)`)
    without polluting the raw output buffer with non-text artifacts.

## Acceptance Criteria

- Runtime plan execution (`execute_plan_calls`) and state batch execution (`step_state`) emit
  typed tool progress/start events as each tool begins execution, including `operation`,
  `index`, and `total`.
- The stream bridge (`async_step_runtime_worker.py` and activity store) forwards typed tool
  lifecycle events across the watch/subscribe channel without losing payload semantics.
- Vim (`vim/plugin/toas.vim`) captures tool progress metadata and updates the run header
  dynamically:
  - Single tool: `tool: <operation>`
  - Multi-tool: `tool: <operation> (i/n)`
- Silent tools with zero output visibly advance the run header as each tool starts and finishes.
- Full test coverage and 100% repository coverage maintained.

## Progress

- 2026-10-06: Task opened to provide live progress updates across tool execution batches and
  silent tools while preserving typed stream event semantics.
- 2026-10-06: Implemented full typed tool lifecycle and live Vim header telemetry:
  - Added `tool_start` event policy in `src/toas/runtime/event_classification.py`.
  - Added `emit_tool_start` and updated `emit_tool_done` with `index` and `total` in
    `src/toas/runtime/tool_stream_context.py`, with clean ContextVar emitter isolation.
  - Extended runtime worker (`src/toas/runtime/async_step_runtime_worker.py`) and activity store
    (`src/toas/runtime/async_activity_store_impl.py`) to bridge `tool_start` without losing
    payload semantics.
  - Instrumented plan execution (`src/toas/tools_cluster/execution.py`) and state execution
    (`src/toas/runtime/state_step.py`) to emit batch `index` and `total` around each call.
  - Enhanced Vim plugin (`vim/plugin/toas.vim`):
    - Formats multi-tool label as `tool: <operation> (i/n)`.
    - Detects metadata changes and flags redraw even when no chunk text is produced.
  - Added comprehensive test coverage in unit and Vader suites; verified 100.00% statement
    coverage with `./scripts/check.sh` (3,452 unit tests, 17 acceptance tests, mypy, ruff).

Status: Complete.
