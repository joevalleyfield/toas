## Goal

Bootstrap decomposition of `step.py` and `tools.py` into runtime/operator/tool modules that reduce closure-heavy orchestration and improve coverage signal.

## Why Now

`step.py` and `tools.py` still concentrate diverse responsibilities; targeted decomposition will make behavior seams explicit and maintenance less error-prone.

## Scope

- extract first cohesive clusters aligned to `400` target shape:
  - step/runtime: frontier resolution, operator command routing, projection helpers
  - tools: registry/dispatch core, grouped file/shell/capability helper operations
- preserve callable tool contracts and step semantics
- add direct tests for extracted modules and adapt existing tests to import new boundaries where appropriate
- note follow-on smell tasks immediately when extraction reveals awkward seams

## Intended Behavior

- runtime and tool behavior are expressed in smaller, explicit callable units
- coverage reports identify real logic gaps instead of monolith residue

## Constraints

- no transcript/history contract changes
- keep direct user shell intent separate from model-addressable tool policy surfaces
- avoid big-bang migration; move one cohesive cluster per slice

## Done When

- at least one extraction slice lands for both step and tools target groups
- compatibility layer remains intact while callers migrate
- extracted-module tests cover edge and failure paths previously buried in monolith branches

## Progress

- first concrete extraction slice opened: `407` (step frontier helper cluster extraction into dedicated module)
- `407` completed and closed:
  - extracted frontier helper cluster into `src/toas/step_frontier.py`
  - kept compatibility aliases in `step.py` for existing import/test surfaces
  - added direct tests in `tests/test_step_frontier.py` and reached `100%` coverage for the new module
- performed post-extraction lint normalization pass (`ruff --fix`) across touched modules/tests to keep decomposition slices style-stable and CI-clean
- first tools-side extraction slice opened: `408` (tools registry/validation/dispatch helper extraction)
- `408` completed and closed:
  - extracted registry/validation/dispatch helpers into `src/toas/tools_registry.py`
  - kept `tools.py` compatibility wrappers for `get_tool` / `validate_call` / `execute_call`
  - added direct tests in `tests/test_tools_registry.py` and reached `100%` coverage for the new module
- next tools-side extraction slice opened: `409` (tools execute_plan orchestration extraction)
- `409` completed and closed:
  - extracted execute-plan orchestration into `src/toas/tools_execution.py`
  - kept `tools.py` compatibility wrapper for `execute_plan`
  - added direct tests in `tests/test_tools_execution.py` and reached `100%` coverage for the new module
- next tools-side extraction slice opened: `410` (tools result rendering extraction)
- `410` completed and closed:
  - extracted result-rendering helpers/dispatch into `src/toas/tools_rendering.py`
  - kept `tools.py` compatibility wrapper for `shape_result_content`
  - added direct tests in `tests/test_tools_rendering.py` and reached `100%` coverage for the new module
- package-shape migration slice opened: `411` (runtime subpackage migration with compatibility shims)
- `411` completed and closed:
  - introduced `src/toas/runtime/` package and moved runtime helper modules to:
    - `runtime/frontier_resolution.py`
    - `runtime/rpc_edges.py`
  - kept compatibility shims at legacy paths:
    - `step_frontier.py`
    - `runtime_edges.py`
  - updated core call sites to runtime package paths while preserving behavior
- tools package-shape migration slice opened: `412` (tools helper subpackage migration with compatibility shims)
- `412` completed and closed:
  - introduced `src/toas/tools_cluster/` package and moved tools helper modules to:
    - `tools_cluster/registry.py`
    - `tools_cluster/execution.py`
    - `tools_cluster/rendering.py`
  - kept compatibility shims at legacy helper paths:
    - `tools_registry.py`
    - `tools_execution.py`
    - `tools_rendering.py`
  - updated core tools imports to package paths while preserving behavior
