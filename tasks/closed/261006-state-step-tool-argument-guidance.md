# State-Step Tool Argument Guidance

Filed as: 261006-state-step-tool-argument-guidance
FKA:
AKA: state step tool schemas; state tool args; state step argument guidance
Legacy index:
Parent: `260926-state-step-requirements`
Related: `261005-state-step-streaming-and-transient-preview`

## Context

State-step advertises available tools in the state packet and prompt (`build_state_step_packet` and `build_multi_state_sequence_packet`), but only provides a flat list of tool names (`"available": sorted(REGISTRY)`). When the model is expected to formulate batch tool calls in `tool_calls` (each with `tool_name` and `args`), it has no guidance or schemas specifying what argument keys are required, optional, or accepted.

This leads to unguided guessing of parameter names (e.g., guessing `file` vs `path` for `read_file`, `cmd` vs `argv` for `shell`), causing validation errors when the model attempts to invoke tools during state advancement.

## Objectives

1. Define a structured representation of tool specifications (definitions) including required arguments, optional arguments, default arguments, and human-readable descriptions based on TOAS tool registry and capability definitions.
2. Provide tool argument definitions in the state-step packet (`packet["tools"]["definitions"]`) alongside `tools["available"]`.
3. Provide tool argument definitions in multi-state sequence prompts (`build_multi_state_sequence_packet`).
4. Ensure instructions and schemas explicitly guide the model on argument structure when proposing tool calls.
5. Maintain 100.00% statement test coverage across all test suites.

## Outcome

- Implemented `tool_definitions()` in `src/toas/tools_cluster/capability_help_ops.py` and exposed it via `src/toas/tools.py`. It returns structured tool summaries, required arguments, optional arguments, and default argument specifications.
- Expanded `tool_summary()` to cover task and script execution tools (`capture_task_thread`, `python_script`, `powershell_script`, `interpreter_script`).
- Enhanced `build_state_step_packet()` to supply `"definitions"` alongside `"available"` in `packet["tools"]`.
- Enhanced `build_multi_state_sequence_packet()` to include full tool argument definitions in both the returned packet's `tools["definitions"]` and the system instructions prompt block.
- Updated `STATE_INSTRUCTIONS` to direct the model to formulate tool calls matching the supplied argument definitions.
- Verified 100.00% statement coverage across all test suites via `./scripts/check.sh`.
