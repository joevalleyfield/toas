# State Tool Argument Type Signatures

Filed as: 261008-state-tool-argument-type-signatures
FKA:
AKA: state tool argument types; type signatures in state protocol tools; shell argv list typing
Legacy index:

keywords: tooling, contract, active, correctness, usability, schema

Parent: `260926-state-step-requirements`
Depends on: `261007-state-protocol-tool-argument-definitions`
Related: `261008-state-step-terminal-reporting-channel`

Status: CLOSED; advertised explicit type signatures for tool arguments in state-step protocol definitions across all registry tools.

## Context

In `261007-state-protocol-tool-argument-definitions`, tool argument definitions were expanded into Turn 1 protocols, providing `required_args`, `optional_args`, and `default_args`.
However, arguments were listed as bare parameter names without type signatures (e.g., `required_args: [argv]`).

In dogfood (`session-20261007-1946-state-seed.md` Turn 4), the model proposed:
```yaml
pending_tools:
- tool_name: shell
  args:
    argv: ls -1 tasks/open
```
Because `argv` lacked a type signature, the model assumed `argv` accepted a shell command string, failing with:
`[FAILED] tool 0 (shell): invalid arguments for tool shell: argv must be a non-empty list[str]`
While the model recovered in Turn 5, this was a preventable failure and wasted step caused by an incomplete argument contract.

## Objectives

1. **Advertise Argument Type Signatures**:
   - Enrich `tool_definitions` and `expand_state_turn_protocol` to advertise concrete argument types (e.g., `argv: list[str]`, `path: str`, `start_line: int`, `append: bool`).
   - Symmetrically support type metadata across all registry tools (`shell`, `read_file`, `replace_block`, `write_file`, etc.).
2. **Harmonize Schema & Guidance**:
   - Ensure protocol YAML rendering clearly differentiates list and scalar argument requirements.
3. **Validation and Testing**:
   - Test that `toas prompt state/swe_v1` and `expand_state_turn_protocol` output explicit type signatures.
   - Verify parsing and schema compatibility with 100.00% test coverage.

## Outcome

- Added `arg_types: dict[str, str]` to `ToolSpec` (`tools_cluster/registry.py`) and `Tool` (`tools.py`).
- Populated concrete `arg_types` for all 18 tools in `REGISTRY`, clearly indicating `list[str]` for `argv` on shell and script tools, and scalar types (`str`, `int`, `bool`, `float`) for file and search operations.
- Updated `tool_definitions` in `tools_cluster/capability_help_ops.py` to include `arg_types` in tool definitions dictionaries when present.
- Updated `instructions_v1.txt` and packet builder in `state_step.py` to instruct models that tool call arguments must match tool argument definitions and type signatures.
- Verified concrete end-to-end output (`toas prompt state/swe_v1`) rendering `arg_types` for all tools.
- Added comprehensive assertions in `tests/test_tools_capability_help_ops.py`, `tests/test_tools.py`, and `tests/test_state_step.py`.
- Verified full test suite passes with 100.00% statement coverage via `./scripts/check.sh`.
