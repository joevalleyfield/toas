## Goal

Decompose `handle_prompt_workspace_commands` in `src/toas/runtime/operator_command_prompt_workspace.py` into focused helpers with explicit boundaries for parsing, selection, rendering, and workspace writes.

## Why Now

`code_survey` reports this handler at ~285 LOC, making it one of the highest-friction targets for incremental behavior changes and weaker-model execution.

## Scope

- split prompt/workspace command handling into cohesive helper functions
- isolate filesystem mutation paths from pure formatting/query logic
- add direct unit tests for edge-case branches (invalid args, missing targets, write paths)
- keep top-level handler as thin dispatch/orchestration

## Intended Behavior

- unchanged prompt/workspace command behavior and outputs
- reduced cognitive load and more surgical test targeting

## Constraints

- no behavior drift in prompt materialization or workspace file edits
- preserve current command entry points and payload shapes

## Done When

- function complexity and size are materially reduced
- new helper-level tests lock branch behavior
- full suite passes
