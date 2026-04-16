## Goal

Execute the next `404` tools-side decomposition slice by extracting `execute_plan` orchestration into a focused module.

## Why Now

After `408` split registry/validation/dispatch, `execute_plan` is the largest cohesive orchestration cluster remaining in `tools.py` and is a strong next seam.

## Scope

- add dedicated module (target: `src/toas/tools_execution.py`) for:
  - per-call cwd/path/env adaptation logic
  - plan execution loop and error/result shaping for call outcomes
- keep `tools.py` public compatibility surface unchanged (`execute_plan` remains available)
- preserve existing behavior for shell cwd/env defaults, path resolution, intention projection, and error shaping
- add direct tests for new module and achieve `100%` coverage

## Intended Behavior

- no semantic drift in plan execution outcomes
- orchestration logic is directly testable outside monolithic `tools.py`

## Constraints

- no changes to tool runner semantics
- no policy changes in shell/workspace context handling
- extraction-only slice

## Done When

- `tools_execution.py` is introduced and used by `tools.py` wrapper
- full suite passes and lint is clean
- new module has direct tests and `100%` coverage
