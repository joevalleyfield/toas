## Goal

Extract shared runtime edges used across `cli.py`, `daemon.py`, `step.py`, and `tools.py` so decomposition removes duplication before module splits.

## Why Now

Cross-cutting helper duplication inflates coupling and obscures ownership; extracting shared edges first lowers risk for later phase movement.

## Scope

- identify and extract shared helpers for:
  - RPC mode gating/request wrapping
  - result rendering/formatting adapters used by command and daemon surfaces
  - shell/workspace/config policy resolution helpers
- place extracted helpers in stable modules with clear ownership
- migrate first call sites in small slices while preserving behavior
- add direct unit tests for extracted helpers independent of command handlers

## Intended Behavior

- command/runtime modules depend on shared helpers instead of re-implementing edge logic
- later command-handler extraction becomes mostly movement and wiring

## Constraints

- no behavioral change at CLI/RPC transcript output boundaries
- no broad call-site rewrite in one pass; migrate incrementally
- maintain compatibility imports while call sites transition

## Done When

- at least one helper cluster from each edge category is extracted and adopted
- duplicate implementations are reduced in existing monolith modules
- helper-focused tests lock fallback/error contracts

## Progress

- extracted first shared helper cluster to new module `src/toas/runtime_edges.py`:
  - `require_rpc_enabled`
  - `rpc_request_or_exit`
- migrated CLI async/rpc lifecycle call sites to shared helpers (`run_step_async`, `run_watch`, `run_cancel`, `run_backend`)
- added direct unit coverage for the new shared module in `tests/test_runtime_edges.py`
- extracted shared runtime policy helper cluster to new module `src/toas/runtime/policy_edges.py`:
  - `load_operator_config_for_workdir`
  - `stream_flags_for_workdir`
- migrated call sites to shared policy helpers:
  - `cli._load_operator_config_for_cwd` now delegates to `load_operator_config_for_workdir`
  - daemon streaming toggles (`_thinking_stream_enabled`, `_prompt_progress_stream_enabled`) now delegate to `stream_flags_for_workdir`
- added direct unit coverage for policy helpers in `tests/test_runtime_policy_edges.py`
- extracted shared rendering/format edge helper cluster to new module `src/toas/runtime/rendering_edges.py`:
  - `detect_newline_style`
  - `apply_newline_style`
  - `render_transcript_blocks`
- migrated first CLI rendering call sites to shared helpers while preserving compatibility wrappers:
  - `cli._detect_newline_style` delegates to `detect_newline_style`
  - `cli._apply_newline_style` delegates to `apply_newline_style`
  - `cli._render_blocks` delegates to `render_transcript_blocks`
- added direct unit coverage for rendering helpers in `tests/test_runtime_rendering_edges.py`
- extracted shared content-preview formatter to `src/toas/runtime/rendering_edges.py`:
  - `format_content_preview`
- migrated first diff/ancestry preview call sites in `cli.py` to shared formatter:
  - `_format_content` now delegates to `format_content_preview`
  - `run_ancestry_local` now uses `format_content_preview` instead of duplicated inline truncation logic
- expanded direct unit coverage in `tests/test_runtime_rendering_edges.py` for preview truncation/full modes
- extracted shared lineage edge helpers to new module `src/toas/runtime/lineage_edges.py`:
  - `find_common_ancestor`
  - `first_after`
  - lineage row formatters for common-ancestor/branch/diverging/ancestry output lines
- migrated CLI diff/ancestry local handlers to delegate to lineage helpers:
  - `_find_common_ancestor` and `_first_after` now delegate to runtime helpers
  - diff/ancestry output row construction now delegates to runtime formatter helpers
- added direct unit coverage in `tests/test_runtime_lineage_edges.py`
- extracted shared presentation/output edge helpers to new module `src/toas/runtime/presentation_edges.py`:
  - `render_output_with_newline_style`
  - `extract_response_stdout`
  - row/line formatters for heads/history/status output
- migrated narrow CLI call sites to shared presentation helpers:
  - `_print_blocks_with_newline` now delegates newline-style emission shaping
  - `_rpc_stdout` now delegates stdout extraction from RPC response
  - `run_heads_local` and `run_history_local` row/line formatting now delegates to presentation helpers
- added direct unit coverage in `tests/test_runtime_presentation_edges.py`
- extracted shared RPC payload helpers to new module `src/toas/runtime/rpc_payload_edges.py`:
  - `with_workdir`
  - `drop_none_fields`
- migrated CLI RPC call paths to use shared payload helpers:
  - `_rpc_stdout` now delegates default `workdir` payload shaping
  - optional-arg RPC wrappers (`transcript`, `rebuild`, `llm_input`, `prompts`, `ancestry`) now prune `None` fields via shared helper
- added direct unit coverage in `tests/test_runtime_rpc_payload_edges.py`
