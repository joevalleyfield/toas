## Goal

Decompose `src/toas/runtime/operator_commands.py` so `execute_operator_command` is no longer a single ~790-line function and command families can be edited/tested independently.

## Why Now

`code_survey` shows `execute_operator_command` as the largest function in the repo (790 lines). This undermines the decomposition objective of `400` by relocating, not reducing, monolithic command logic.

## Scope

- split operator command handling into focused modules by family, e.g.:
  - prompt/history/navigation handlers
  - shell/env/policy handlers
  - extraction/replay/projection handlers
- keep a single public entrypoint `execute_operator_command(...)` in `runtime/operator_commands.py` as a compatibility facade
- preserve command semantics and output contracts
- add focused module tests for each extracted family

## Intended Behavior

- targeted changes to one command family should not require scanning a 700+ line dispatcher
- failure behavior and projection output remain parity-safe

## Constraints

- no semantic drift in operator command contracts
- keep import surface stable while callers migrate

## Done When

- `execute_operator_command` becomes a thin dispatcher/facade
- extracted family modules are directly unit tested
- full suite passes with parity behavior

## Result

- extracted command-family handlers:
  - `src/toas/runtime/operator_command_prompt_workspace.py`
  - `src/toas/runtime/operator_command_extract_replay.py`
  - `src/toas/runtime/operator_command_config_help.py`
- added shared dispatch context:
  - `src/toas/runtime/operator_command_context.py`
- reduced `src/toas/runtime/operator_commands.py` to thin facade/dispatcher over extracted handlers
- added direct handler tests:
  - `tests/test_runtime_operator_command_handlers.py`
- verification:
  - focused: `uv run pytest tests/test_runtime_operator_commands.py tests/test_runtime_operator_command_handlers.py`
  - full: `uv run pytest` (passes except known sandbox-unavailable unix socket tests in `tests/test_rpc_unix.py`)
