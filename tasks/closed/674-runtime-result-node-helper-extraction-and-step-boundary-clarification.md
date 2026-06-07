# 674 Runtime result-node helper extraction and step boundary clarification
keywords: runtime, decomposition, step, projection, provenance, result-node, ownership, architecture

## Goal

Follow through on `672` by moving shared transient result-node provenance/lane helpers out of `src/toas/step.py` into a runtime-owned boundary that matches the decomposition plan.

## Why

`672` correctly made producer-side result provenance mandatory, but the shared helper landed in `src/toas/step.py` as an expedient compatibility-safe home. That keeps behavior correct, yet it blurs the ownership line between step orchestration and shared runtime projection semantics.

The current decomposition plan in `400` explicitly aims to reduce cross-cutting helper sprawl in monolithic files and move shared runtime edges into focused modules. Result-node stamping/validation is a shared runtime projection concern, not uniquely `step` logic.

## Scope

- extract shared result-node helper logic from `src/toas/step.py` into a runtime-owned module
  - likely candidates:
    - `src/toas/runtime/result_nodes.py`
    - or `src/toas/runtime/projection.py` if that boundary is judged more coherent
- migrate active callers to the new module boundary
  - `src/toas/step.py`
  - `src/toas/runtime/step_runtime.py`
  - slash-command/result-producing runtime handlers
  - tests importing the helper directly
- keep compatibility-safe imports/wrappers only if needed for staged migration
- document the ownership rule in task notes or module comments if the extraction would otherwise look arbitrary

## Non-Goals

- changing result-lane semantics established by `569`/`672`
- reopening renderer fallback behavior
- broader `step.py` decomposition beyond this focused seam

## Intended Behavior

- `step.py` remains an operator-facing orchestration surface
- shared transient result-node shaping/validation lives under `src/toas/runtime/`
- callers use one canonical helper boundary for provenance-complete result construction

## Done When

- `make_result_node()` / validation / lane-resolution helper logic no longer lives primarily in `src/toas/step.py`
- runtime-owned module boundary is the canonical import path for shared result-node semantics
- active callers and tests are migrated with parity retained
- any compatibility alias left behind has explicit sunset intent rather than becoming a new permanent resting place

## Progress

- Created `src/toas/runtime/result_nodes.py` with the canonical result-node helper logic:
  - `RESULT_ORIGIN_KINDS`, `RESULT_ORIGIN_ROLES` (constants)
  - `projection_lane_for_result_origin()` (lane resolution)
  - `make_result_node()` (provenance-complete construction)
  - `validate_result_node()` (validation)
- `step.py` now imports from `runtime.result_nodes` and re-exports for backward compat (compatibility alias with sunset intent)
- `runtime/step_runtime.py` imports directly from `result_nodes` (removed `_result_helpers` indirection)
- `runtime/rendering_edges.py` imports directly from `result_nodes`
- Operator command handler modules (`operator_command_config_help.py`, `operator_command_extract_replay.py`, `operator_command_prompt_workspace.py`, `operator_config_backend_ops.py`) import directly from `result_nodes`; `_result_node` helpers now use `make_result_node` directly (kept `step_mod` parameter for test injection compatibility)
- Test imports updated: `test_cli.py`, `test_runtime_rendering_edges.py`, `test_runtime_operator_commands.py` now import from `toas.runtime.result_nodes`
- Follow-up added `tests/test_runtime_result_nodes.py` to cover the extracted helper boundary and remove `runtime/result_nodes.py` from the below-100 coverage list
- Full suite: 1953 passed, parity retained

## Notes

- This is a decomposition/ownership follow-on to `672`, not a semantic correction to `672`.
- Prefer a small, explicit module over re-expanding `step.py` with more projection-shaping responsibilities.
- Stitch outcome back to `400` so the decomposition plan reflects the seam extraction.
