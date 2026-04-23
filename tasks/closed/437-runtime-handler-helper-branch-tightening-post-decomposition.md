## Goal

Tighten branch coverage for newly extracted runtime handler helpers after tasks `431`-`433`, prioritizing edge/error paths that are now unit-testable.

## Why Now

The decomposition landed cleanly, but helper modules remain below desired confidence levels (`operator_command_config_help`, `operator_command_prompt_workspace`, `operator_command_extract_replay`).

## Scope

- add focused tests for helper-level edge/error paths in:
  - `src/toas/runtime/operator_command_config_help.py`
  - `src/toas/runtime/operator_command_prompt_workspace.py`
  - `src/toas/runtime/operator_command_extract_replay.py`
  - bounded seams in `src/toas/runtime/step_runtime.py`
- prefer explicit helper coverage over end-to-end-only tests where practical

## Intended Behavior

- no behavior changes; confidence and branch lock-in increase
- helper modules become safer to evolve in future slices

## Constraints

- avoid architecture churn in this task; test tightening first
- preserve existing command/output contracts

## Done When

- targeted helper branches are covered with deterministic tests
- module coverage improves in the identified runtime handler files
- full suite passes
