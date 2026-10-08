# State Tool Argument Type Signatures

Filed as: 261008-state-tool-argument-type-signatures
FKA:
AKA: state tool argument types; type signatures in state protocol tools; shell argv list typing
Legacy index:

keywords: tooling, contract, active, correctness, usability, schema

Parent: `260926-state-step-requirements`
Depends on: `261007-state-protocol-tool-argument-definitions`
Related: `261008-state-step-terminal-reporting-channel`

Status: ACTIVE implementation slice; advertises explicit type signatures for tool arguments in state-step protocol definitions to prevent model guessing and argument schema failures.

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
   - Symmetrically support type metadata across all registry tools (`shell`, `read_file`, `replace_block`, `write_file`).
2. **Harmonize Schema & Guidance**:
   - Ensure protocol YAML rendering clearly differentiates list and scalar argument requirements.
3. **Validation and Testing**:
   - Test that `toas prompt state/swe_v1` and `expand_state_turn_protocol` output explicit type signatures.
   - Verify parsing and schema compatibility with 100.00% test coverage.
