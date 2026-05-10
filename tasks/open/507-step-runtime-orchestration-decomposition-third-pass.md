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
