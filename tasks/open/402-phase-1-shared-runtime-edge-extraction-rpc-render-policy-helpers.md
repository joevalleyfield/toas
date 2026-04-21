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
