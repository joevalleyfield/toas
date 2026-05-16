# 507 Step Runtime Orchestration Decomposition Third Pass

## Objective
Continue decomposition of `src/toas/runtime/step_runtime.py` by extracting a bounded orchestration slice around consequence assembly/projection handoff.

## Why
`step_runtime.py` remains a top runtime hotspot after earlier passes, and further seam extraction improves behavior auditability and reduces coupling in consequence flow.

## Scope
- extract one bounded orchestration cluster from `step_runtime.py`
- keep runtime semantics unchanged (frontier handling, projection boundaries, durable writes)
- add focused tests for new seam helpers
- avoid broad cross-module reshaping in this slice

## Done When
- chosen orchestration cluster is materially slimmer via helper delegation
- targeted runtime tests and full suite pass
- task progress records extracted seam names and parity checks

## Related
- `400` decomposition umbrella
- `498` step runtime frontier consequence split second pass

## Progress
- extracted bootstrap-seed orchestration from `run_step` into focused helpers:
  - `_build_bootstrap_node`
  - `_bootstrap_seed_consequences`
- kept bootstrap semantics unchanged (seeded user prompt + trailing empty user slot with `bootstrap_seed` provenance)
- added direct helper tests for bootstrap node build and consequence shaping
- extracted user/control frontier arbitration and fallback orchestration seams from `_handle_user_or_control_frontier` into focused helpers:
  - `_expand_in_order_operator_candidates`
  - `_append_strict_mixed_intent_error_if_needed`
  - `_handle_user_generation_fallback`
- preserved runtime behavior for mixed-intent strict-mode errors, multi-operator in-order expansion, and user-generation guard/generate fallback paths
- added direct helper tests covering new arbitration/fallback helpers alongside existing `_execute_frontier_consequences` parity tests
- extracted plan-frontier consequence assembly from `_handle_plan_frontier` into focused phase helpers:
  - `_execute_plan_frontier_results`
  - `_append_plan_frontier_results`
  - `_should_auto_stage_assistant_shell_block`
- preserved assistant auto-stage behavior and plan execution/result-append semantics while reducing mixed responsibility in `_handle_plan_frontier`
- added direct helper tests for plan-frontier phase execution/append/auto-stage decision paths
- extracted frontier consequence dispatch routing from `_execute_frontier_consequences` into `_route_frontier_consequence_path`, separating assistant-shell projection, user/control intent execution, plan-frontier handling, and assistant fallback routing from top-level consequence orchestration
- preserved existing early-return behavior and consequence ordering semantics while reducing branch fan-out in `_execute_frontier_consequences`
- added direct helper test for assistant single-shell projection routing path in `_route_frontier_consequence_path`
