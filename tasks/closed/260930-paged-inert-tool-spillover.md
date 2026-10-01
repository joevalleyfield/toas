Filed as: 260930-paged-inert-tool-spillover
FKA:
AKA: inert block pagination; tool output spillover; sip tool results; scratch addressable blocks
Legacy index:

keywords: runtime, tooling, projection, inert, pagination, affordance, scratch

Parent: `260926-state-step-requirements`
Depends on: `260930-strip-payload-from-state-packet`
Related: `260930-state-step-transcript-supremacy`

# Paged Inert Tool Result Spillover And Scratch-Addressable Sipping

Bound oversized tool outputs in transcripts and state observations by spilling to addressable scratch buffers with compact previews, enabling models and operators to sip, search, sample, and script results through standard file primitives.

## Context
When models invoke broad tools (e.g. `get_structure`, `code_survey`, recursive searches, or shell commands), they often request more data than can fit comfortably in context. Currently, large outputs are either dumped completely into the transcript/prompt or manually truncated by the operator.
Rather than inventing bespoke query tools (`search_block`, `sample_block`), oversized outputs can be backed by standard addressable files in `.toas/scratch/`. This grants models and operators bounded reads (`read_file`), searching (`grep`), sampling (`shuf`), and arbitrary pipeline processing (`jq`, `python`) for free using established Unix tools.

## Desired Reality
1. **Render-Time Spillover**:
   When a tool produces output exceeding a threshold (e.g. >40 lines or >4 KB):
   - The full output is written to `.toas/scratch/<block_id>.txt` (where `block_id = ib_<sha256[:16]>`).
   - The transcript receives a compact outcome line, a bounded preview (e.g. lines 1..30), and an explicit hint with the scratch path and remaining line count:
     ```text
     ## RESULT

     [OK] get_structure: found 1856 symbols across src/toas
     Output exceeded threshold (42 KB, 1856 lines); spilled to `.toas/scratch/ib_8f2a1c.txt`.

     ```text toas-output kind=result block_id=ib_8f2a1c path=".toas/scratch/ib_8f2a1c.txt" lines=1..30 of 1856
     class.AcceptanceBackendConfig (12-16) src/toas/acceptance_harness.py
     ...
     ```
     [1826 lines remaining. Inspect with `read_file`, `grep`, or script via path=".toas/scratch/ib_8f2a1c.txt"]
     ```
2. **Durable Indexing**:
   The full content remains durably preserved in `events.jsonl` under `state_tool_result` and in `.toas/scratch/<block_id>.txt`.
3. **Sipping via Existing Primitives**:
   No new bespoke tools are needed. Models and operators interact with spilled content using existing primitives:
   - Bounded slices: `read_file(path=".toas/scratch/ib_8f2a1c.txt", line_start=31, line_end=60)`
   - Search: `grep -n ...` or `rg` via `shell`
   - Sampling & Scripting: standard shell/python pipes against the scratch file
4. **Controlled Observation Projection**:
   State-step packet generation does not unconditionally re-expand spilled blocks into the LLM prompt. The model observes the compact preview and path, keeping inference packets lightweight.
5. **Transcript Supremacy**:
   If the operator edits or truncates the preview in `session.md`, the operator's authored text remains supreme during subsequent step evaluation.

## Acceptance Criteria
- Tools producing output over threshold automatically spill to `.toas/scratch/<block_id>.txt`.
- Rendered transcript blocks display a bounded preview (e.g. 30 lines) with path and remaining line annotations.
- `read_file` successfully reads slices from `.toas/scratch/` paths.
- `build_state_step_packet` preserves bounded previews in the LLM packet without re-expanding spilled contents.
- Operator edits to spilled previews in `session.md` are authoritative.
- All existing tests pass without regressions.

## Completion Log
- **2026-10-01**: Implemented paged inert tool result spillover:
  - Added `spill_inert_block` and auto-spillover logic to `src/toas/tools_cluster/rendering.py` for tool result, stdout, and stderr blocks when exceeding line (>40) or byte (>4000) thresholds.
  - Spilled outputs write the raw full output to `.toas/scratch/<block_id>.txt` and render a bounded 30-line preview with banner, header annotations (`block_id`, `path`, `lines=1..30 of N`), and remaining-line trailer hints.
  - Supported `line_start` and `line_end` as parameter aliases in `run_read_file` (`src/toas/tools_cluster/basic_ops.py`), enabling standard bounded slice reads against `.toas/scratch/` paths.
  - Protected spilled preview blocks in `condense_inert_blocks` and `expand_inert_blocks` (`src/toas/runtime/state_step.py`) to prevent premature condensation into references and unspilled re-expansion in state packets.
  - Verified full test suite passes (3382 tests). Closed task.

