Filed as: 260716-extract-adjacent-plan-coalescing
FKA:
AKA: extract coalesce yaml plans; adjacent callable fence projection
Legacy index:

keywords: projection, implementation, active, correctness, transcript, frontier, tooling, yaml

Parent: `260621-assistant-callable-plan-coalescing`
Depends on: `260716-extract-yaml-multi-literal-salvage`
Related: `260621-yaml-block-indent-salvage`

# Adjacent Callable Plan Coalescing Through Extract

## Current Reality

`/extract` lists each valid YAML tool plan from the latest assistant message as
an independent `#dN` candidate. When a model emits several adjacent
single-operation fenced plans, the operator must manually compose them into
one multi-operation plan before adoption.

## Desired Reality

`/extract --coalesce` explicitly lists contiguous, whitespace-separated runs
of two or more single-operation YAML tool-plan fences as `#cN` candidates.
`/extract --coalesce #cN` projects the selected run as one canonical YAML plan
in a user message, without execution, replay, or history mutation.

## Contract

- a coalescible run contains at least two immediately adjacent YAML fences,
  separated only by whitespace
- every fence in the run must parse to exactly one valid callable operation;
  malformed blocks, loose commands, multi-operation plans, and prose between
  fences make that run ineligible
- retain ordered callable semantics and canonical argument values using the
  existing normalized-plan projection; source comments remain in immutable
  assistant history and are not copied into the canonical adopted plan
- require explicit `#cN` selection to project; the no-selection form only
  lists candidates
- use a distinct `c` handle namespace; normal `#dN` extraction remains
  unchanged

## Allowed Write Surfaces

- `src/toas/runtime/operator_command_extract_replay.py`
- narrowly owned extraction helpers under `src/toas/runtime/` if needed
- focused tests in `tests/test_step.py` and/or
  `tests/test_runtime_operator_command_handlers.py`
- this task file, its parent task file, and generated `tasks/WORKBOARD.md`

## Non-Goals

- automatic coalescing or executing the result
- spanning prose, non-YAML fences, or separate assistant messages
- preserving YAML comments/formatting in the canonical projected replacement
- merging multi-operation source plans or loose shell-command blocks

## Acceptance Criteria

- two whitespace-adjacent single-operation plans list as `#c1` and adopt as
  one ordered YAML plan
- selection syntax rejects malformed, non-positive, and out-of-range handles
- prose-separated, malformed, loose-command, or multi-operation sources do
  not yield a coalescing candidate
- normal `/extract` behavior and existing YAML salvage remain unchanged
- focused tests, targeted coverage, and full-suite verification pass

## Completion Evidence

- list/adopt/refusal fixtures prove the explicit non-executing projection path
- targeted command-module coverage is 100%
- the full suite passes

## Progress Notes

- 2026-07-16: Claimed for implementation. The selected surface is an explicit
  `/extract --coalesce [#cN]` mode because it reuses the established latest-
  assistant and user-message projection boundary without overloading `#dN`.
- 2026-07-16: Implemented contiguous source-run discovery and canonical ordered
  projection. The mode refuses prose-separated, invalid, loose-command, and
  multi-operation fences instead of partially coalescing them.

## Exit Evidence

- [x] focused list/adopt/refusal tests: `338 passed`
- [x] targeted command-module coverage: `338 passed`, `100.00%`
- [x] full suite: `2705 passed, 9 deselected`, `100.00%`
