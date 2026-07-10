Filed as: 260710-step-generation-runtime-boundary-cleanup
FKA:
AKA: step generation boundary cleanup; generation runtime cli glue split; generation deps split
Legacy index:

keywords: runtime, hardening, historical, maintainability, boundaries, generation, cli, projection

Parent: `260615-runtime-package-growth-boundary-audit`
Related: `260614-architecture-follow-through-coordination`

# Step Generation Runtime Boundary Cleanup

## Current Reality

`src/toas/runtime/step_generation_runtime.py` currently owns a coherent
runtime-domain `GenerationRunner`, but it also assembles CLI/session dependency
bindings and presentation helpers through `build_step_cli_deps()`.

That means one file reads as both:

- model-invocation / step-generation runtime ownership
- CLI-facing orchestration and output-shaping glue

The audit task `260615-runtime-package-growth-boundary-audit` identified this
as the highest-leverage narrow seam for reducing future context cost.

## Desired Reality

`step_generation_runtime.py` should read primarily as runtime-owned generation
semantics.

CLI/session dependency assembly and presentation glue should sit in an
explicit edge module so future readers do not have to parse one file to answer
both:

- how generation works
- how the CLI/session surface wires generation into transcript/session flows

## Scope

- move `build_step_cli_deps()` and directly related presentation/dependency
  assembly out of `step_generation_runtime.py`
- keep `GenerationRunner` and `StepCliDeps` behavior stable
- preserve current callers and targeted test coverage with minimal churn

## Non-Goals

- redesign of generation policy or model invocation semantics
- broad runtime package reshuffle
- refactoring unrelated large runtime files in the same pass

## Done When

- `step_generation_runtime.py` no longer owns the CLI/session dependency
  assembly implementation
- the new edge-owned home is explicit in naming and imports
- targeted tests covering generation runner and CLI session flow stay green

## Progress

`build_step_cli_deps()` and its presentation/dependency wiring now live in
`src/toas/runtime/step_generation_cli_edges.py`, while
`step_generation_runtime.py` keeps a thin compatibility facade so existing
callers and tests can continue to import the helper during the transition.

Focused verification:

- `./.codex-local/bin/uvt run pytest tests/test_cli_session_commands.py -q --no-cov`
