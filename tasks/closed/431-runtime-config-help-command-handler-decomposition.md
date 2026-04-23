## Goal

Decompose `handle_config_help_commands` in `src/toas/runtime/operator_command_config_help.py` into smaller focused helpers so targeted changes do not require editing a ~300-line function.

## Why Now

`code_survey` identifies this as the largest remaining function (~294 LOC) in the extracted operator-command family. It is now a primary maintenance hotspot.

## Scope

- split config/help command routing into small helper units (parse, dispatch, render, write)
- keep the external command behavior and output contracts stable
- add direct helper-level tests for previously implicit branches
- keep `handle_config_help_commands` as a thin orchestrator

## Intended Behavior

- same CLI/operator behavior for `/config` and help-related commands
- smaller internal functions with explicit responsibilities

## Constraints

- no semantic drift in config mutation, persistence, or help text contracts
- preserve existing public call signatures during transition

## Done When

- largest handler function size is materially reduced
- direct tests cover branch logic previously buried in the monolith handler
- full suite passes
