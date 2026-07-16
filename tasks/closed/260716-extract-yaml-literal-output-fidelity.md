Filed as: 260716-extract-yaml-literal-output-fidelity
FKA:
AKA: extract salvage whitespace preservation; yaml fence trailing bytes
Legacy index:

keywords: projection, hardening, active, correctness, transcript, tooling, yaml, salvage, whitespace

Parent: `260716-extract-yaml-literal-salvage`
Depends on: `260716-extract-yaml-literal-salvage`
Related: `260621-staged-replay-trailing-edge-newline-healing`

# YAML Literal Salvage Output Fidelity

## Current Reality

The explicit YAML literal salvage path performs the structural indentation
repair correctly, but trims the repaired projection with `rstrip()` before
placing it in a fenced YAML user message. That silently discards trailing
spaces, blank lines, and final-newline state which the parent task promised to
retain outside the added indentation.

## Desired Reality

Project the repaired YAML byte-for-byte after structural indentation. The
outer fence must supply its own delimiter newline, so extracting the projected
YAML later returns the repaired content exactly, including no-final-newline
state and YAML chomping-significant trailing blank lines.

## Contract

- do not trim, normalize, or otherwise rewrite the repaired literal before
  projection
- place one delimiter newline between the projected YAML and the closing fence;
  it belongs to the Markdown wrapper rather than the YAML payload
- preserve trailing spaces, trailing blank lines, and whether the repaired
  YAML ends with a newline when `extract_yaml_blocks()` reads the projection
- retain all existing source-handle selection, validation, and non-execution
  boundaries

## Allowed Write Surfaces

- `src/toas/runtime/operator_command_extract_replay.py`
- focused tests in `tests/test_step.py` and/or
  `tests/test_runtime_operator_command_handlers.py`
- this task file, its parent task file, and generated `tasks/WORKBOARD.md`

## Non-Goals

- changing the general fenced-YAML parser or transcript format
- broadening the kinds of malformed YAML that salvage can repair
- changing valid-candidate extraction or replay behavior
- coalescing adjacent callable plans

## Acceptance Criteria

- salvaged projection retains trailing spaces and blank lines exactly when
  read back through `extract_yaml_blocks()`
- a salvaged YAML source with no final newline reads back with no final newline
- existing ordinary literal salvage output remains unchanged
- focused tests, targeted coverage for the command module, and the full suite
  pass

## Completion Evidence

- exact round-trip tests cover whitespace, blank-line, and no-EOL payloads
- targeted command-module coverage is 100%
- the full suite passes

## Progress Notes

- 2026-07-16: Claimed for implementation. The repair itself is already
  structurally correct; this follow-on owns only the fenced projection boundary
  where `rstrip()` presently loses payload fidelity.
- 2026-07-16: Removed the trim and gave the outer fence its own delimiter
  newline. Round-trip coverage now proves trailing spaces, blank lines, and
  no-final-newline state survive salvage projection unchanged.

## Exit Evidence

- [x] `./.codex-local/bin/uvt run ruff check src/toas/runtime/operator_command_extract_replay.py tests/test_step.py`
- [x] focused tests: `237 passed`
- [x] targeted command-module coverage: `334 passed`, `100.00%`
- [x] full suite: `2701 passed, 9 deselected`, `100.00%`
