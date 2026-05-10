# 498 Step Runtime Frontier Consequence Split Second Pass

## Objective
Decompose `src/toas/runtime/step_runtime.py` frontier consequence execution path into smaller, named seams that keep orchestration thin and branch behavior explicit.

## Why
`_execute_frontier_consequences` remains a top hotspot in AST/code-survey rankings. It still combines command dispatch outcomes, record writing, and projection-facing consequence stitching.

## Scope
- split `_execute_frontier_consequences` into focused helpers for:
  - operator-command handling path
  - assistant/tool-call path
  - consequence write/return shaping
- keep `run_step` orchestration contract unchanged
- add targeted tests for extracted helper branches

## Out Of Scope
- changing durable record semantics
- changing transcript projection format contracts

## Done When
- `_execute_frontier_consequences` is materially slimmer and delegates cohesive responsibilities
- new helper seams are directly covered by tests
- targeted parity tests and full suite pass

## Related
- `400` decomposition umbrella
- `495` first extraction slice for replay/runtime
- `470` operator-API seam alignment (behavior parity)

## Progress
- first extraction slice landed in `runtime/step_runtime.py` by splitting user/control frontier consequence handling into `_handle_user_or_control_frontier(...)`.
- `_execute_frontier_consequences(...)` now delegates the user/control arbitration/intent execution/generation-guard path to a focused helper, reducing mixed-role branching in the top-level consequence function.
- behavior parity validated with targeted runtime/step suites:
  - `uv run pytest tests/test_runtime_step_runtime.py -q --no-cov` (`13 passed`)
  - `uv run pytest tests/test_step.py tests/test_runtime_step_runtime.py tests/test_runtime_session_step_edges.py -q --no-cov` (`220 passed`)
- second extraction slice split assistant plan consequence handling from `_execute_frontier_consequences(...)` into:
  - `_handle_plan_frontier(...)` for plan execution + assistant auto-stage decisioning
  - `_build_assistant_auto_staged_plan(...)` for adopted user-plan projection shaping
- this keeps top-level frontier consequence flow role-dispatch focused while preserving existing plan/auto-stage behavior.
- parity validation rerun:
  - `uv run pytest tests/test_runtime_step_runtime.py tests/test_step.py tests/test_runtime_session_step_edges.py -q --no-cov` (`220 passed`).
- third extraction slice moved remaining assistant non-plan branch into `_handle_assistant_non_plan_frontier(...)`.
- `_execute_frontier_consequences(...)` now delegates all assistant consequence paths (single-shell precheck, plan path, non-plan path) through focused helpers.
- parity validation rerun:
  - `uv run pytest tests/test_runtime_step_runtime.py tests/test_step.py tests/test_runtime_session_step_edges.py -q --no-cov` (`220 passed`).
- closing pass extracted remaining frontier-dispatch residuals:
  - `_should_project_assistant_single_shell(...)` for assistant single-shell projection precheck.
  - `_should_return_after_user_or_control(...)` for explicit consequence return-policy shaping.
- added direct helper tests for extracted seams in `tests/test_runtime_step_runtime.py`:
  - `_should_project_assistant_single_shell`
  - `_should_return_after_user_or_control`
  - `_handle_assistant_non_plan_frontier`
  - `_build_assistant_auto_staged_plan`
  - `_handle_plan_frontier` auto-stage branch
- final validation:
  - targeted: `uv run pytest tests/test_runtime_step_runtime.py tests/test_step.py tests/test_runtime_session_step_edges.py -q --no-cov` (`225 passed`)
  - full suite: `uv run pytest` (`1362 passed`)

## Status
- [x] complete
