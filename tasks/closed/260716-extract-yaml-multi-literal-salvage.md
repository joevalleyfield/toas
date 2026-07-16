Filed as: 260716-extract-yaml-multi-literal-salvage
FKA:
AKA: extract salvage multiple yaml literals; multi-owner literal reindentation
Legacy index:

keywords: projection, implementation, active, correctness, transcript, tooling, yaml, salvage

Parent: `260621-yaml-block-indent-salvage`
Depends on: `260716-extract-yaml-literal-salvage`; `260716-extract-yaml-literal-output-fidelity`
Related: `260621-assistant-callable-plan-coalescing`

# Multi-Literal YAML Salvage Through Extract

## Current Reality

`/extract --salvage-indent #sN` repairs exactly one malformed supported YAML
literal in a source fence. It intentionally refuses a block with multiple
repair candidates, even when their boundaries are independently clear. That
leaves the parent task's multiple-literal constraint unmet.

## Desired Reality

For one explicitly selected fenced YAML source block, mechanically indent all
unambiguous supported malformed literal bodies (`search_block`,
`replacement_block`, and `patch`) and project the resulting callable YAML as a
user message. The operation must retain the existing explicit selection,
validation, byte-fidelity, and non-execution boundaries.

## Contract

- repair every and only supported literal owner whose body visibly needs
  indentation in the selected source block
- preserve owner order, scalar arguments, indicators, and literal payload
  bytes except for each required structural leading indentation
- reject sources with no repair, an ambiguous boundary, unsupported owner, or
  a repaired result that is not a callable plan
- continue to list the source fence once as `#sN`; no new handle namespace or
  automatic selection
- preserve the output-fidelity delimiter behavior, including trailing spaces,
  blank lines, and no-final-newline state

## Allowed Write Surfaces

- `src/toas/runtime/operator_command_extract_replay.py`
- focused tests in `tests/test_step.py` and/or
  `tests/test_runtime_operator_command_handlers.py`
- this task file, its parent task file, and generated `tasks/WORKBOARD.md`

## Non-Goals

- repairing arbitrary YAML indentation or unrelated prose
- combining adjacent YAML fences into one plan
- executing or replaying the projected plan
- changing the general fenced-YAML parser

## Acceptance Criteria

- one malformed callable fence with both `search_block` and `replacement_block`
  bodies projects a valid plan with both bodies repaired
- an ambiguous or unsupported multi-owner source still refuses without partial
  projection
- one-owner salvage and output-fidelity coverage remain green
- focused tests, targeted command-module coverage, and the full suite pass

## Completion Evidence

- focused multi-owner fixtures cover literal/chomping forms and refusal shape
- targeted command-module coverage is 100%
- the full suite passes

## Progress Notes

- 2026-07-16: Claimed for implementation as the bounded remaining contract
  slice under YAML block indent salvage.
- 2026-07-16: Implemented collection-before-application for all unambiguous
  supported literal owners. Source-fence listing now names multiple owners and
  the selected projection retains existing output-fidelity behavior.

## Exit Evidence

- [x] focused command-handler and transcript tests: `335 passed`
- [x] targeted command-module coverage: `335 passed`, `100.00%`
- [x] full suite: `2702 passed, 9 deselected`, `100.00%`
