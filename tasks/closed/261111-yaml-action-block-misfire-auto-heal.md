Filed as: 261111-yaml-action-block-misfire-auto-heal
FKA:
AKA: yaml misfire auto-heal; structured action block parser robustness
Legacy index:

keywords: yaml, extraction, parser, action-block, auto-heal, robustness, defect
Depends on:
Related: `261111-result-turn-id-namespace-advance` (flagged as sibling defect there)

# Structured action block YAML misfires need auto-heal

Status: CLOSED 2026-11-13; normalize misplaced shell argv and nested operation intent

## Contract

- `shell` takes a string sequence at `arguments.argv`. Flow and block
  sequences both work in single-operation and multi-operation plans.
- `shell_script` takes shell text at `arguments.script`, as specified by
  the registry and capability help. Its optional `runtime` is a separate
  argument.
- `intent` and `intention` describe an operation. Required tool inputs
  still come from the arguments mapping.

## Reproduction and repair

The canonical block and flow forms ran successfully before the fix. A valid
YAML near-miss with `argv` beside an empty arguments mapping lost its
sequence during normalization and produced a missing-argv error. A
`read_file` operation with `intent` under `arguments` failed with
`unknown argument(s): intent`, then projected the same failure into its
retry block.

Shared plan normalization now recovers an explicit local `shell` call's
misplaced string sequence when its arguments are empty and the operation
has no competing payload. It routes nested intent to operation metadata
and rejects conflicting intent values. This applies to model output and
edited retries through the same extraction path. Malformed YAML with
`argv` now shows where to put the sequence and describes both list forms.

## Verification

The public extractor tests cover flow and block sequences, misplaced
indentation, aliases, edited retry blocks, invalid or conflicting intent,
and provider-native syntax. Local `toas step` runs executed both operations
for each canonical argv form and the sibling-argv repair, ran the repaired
`read_file` retry, and promoted its staged remainder to the next executable
turn. A separate `shell_script` probe ran its documented `script` argument.
Malformed argv displayed the corrected guidance, and a provider-native
tool call produced no tool result.
