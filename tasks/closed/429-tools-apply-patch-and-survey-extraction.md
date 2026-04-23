## Goal

Further decompose `src/toas/tools.py` by extracting `apply_patch` and `code_survey` clusters into `tools_cluster` modules with compatibility wrappers.

## Why Now

`code_survey` still reports `tools.py` at 1367 lines, with large cohesive helpers (`_run_apply_patch`, patch parsing, survey visitor/formatting) still co-located in the monolith.

## Scope

- extract `apply_patch` parsing/execution helpers into a focused `tools_cluster` module
- extract `code_survey` visitor/collection/formatting/run helpers into a focused `tools_cluster` module
- keep `tools.py` as registry/wrapper facade for compatibility
- add focused tests for new modules plus parity coverage in tool dispatch paths

## Intended Behavior

- patch and survey operations can evolve independently from registry plumbing
- tool behavior and error messages remain parity-safe

## Constraints

- no contract drift for tool arguments/result shape
- preserve existing operation names and policy boundaries

## Done When

- extracted modules own patch/survey internals
- `tools.py` delegates via thin wrappers
- full suite passes

## Result

- extracted apply-patch internals to:
  - `src/toas/tools_cluster/apply_patch_ops.py`
- extracted code-survey internals to:
  - `src/toas/tools_cluster/survey_ops.py`
- updated `src/toas/tools.py` wrappers:
  - `_run_apply_patch(...)` delegates to `tools_cluster.apply_patch_ops.run_apply_patch(...)`
  - `_run_code_survey(...)` delegates to `tools_cluster.survey_ops.run_code_survey(...)`
- removed in-module duplicated apply-patch/code-survey helper internals from `tools.py`
- added direct module tests:
  - `tests/test_tools_apply_patch_ops.py`
  - `tests/test_tools_survey_ops.py`
- verification:
  - full suite: `uv run pytest` -> `949 passed`, coverage `89.46%`
