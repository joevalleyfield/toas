## Goal

Execute the first `404` tools-side implementation slice by extracting tool-registry validation/dispatch helpers into a focused module.

## Why Now

`tools.py` still centralizes registry and dispatch mechanics; isolating these helpers creates a stable seam for later file/shell/capability operation module splits.

## Scope

- add a dedicated module (target: `src/toas/tools_registry.py`) for:
  - registry lookup
  - required-arg validation
  - single-call dispatch
- keep `tools.py` public compatibility surface unchanged (`get_tool`, `validate_call`, `execute_call`)
- avoid changing tool runner logic in this slice
- add direct tests for new module and achieve `100%` coverage

## Intended Behavior

- callable behavior and errors remain unchanged
- registry/validation/dispatch helpers are directly testable outside `tools.py`

## Constraints

- no change to `REGISTRY` content or tool required-arg contracts
- no change to `execute_plan` behavior in this slice
- extraction only; no policy/format changes

## Done When

- new helper module is introduced and used by `tools.py` wrappers
- full test suite passes
- new module has direct tests and `100%` coverage
