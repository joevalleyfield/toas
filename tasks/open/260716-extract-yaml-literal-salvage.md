Filed as: 260716-extract-yaml-literal-salvage
FKA:
AKA: extract salvage indent; malformed YAML literal repair; fenced YAML source selection
Legacy index:

keywords: projection, implementation, active, usability, transcript, frontier, tooling, yaml, salvage

Parent: `260621-yaml-block-indent-salvage`
Depends on: `573-callable-near-miss-yaml-diagnostics-for-step-and-extract`
Related: `260621-assistant-callable-plan-coalescing`; `260621-staged-replay-trailing-edge-newline-healing`

# Explicit YAML Literal Salvage Through Extract

## Current Reality

`/extract` safely previews or adopts only valid callable candidates from the
latest assistant message. Invalid callable-looking YAML is intentionally kept
out of those candidate handles and reported only as a skipped diagnostic. That
preserves the strict execution boundary, but leaves no explicit selection path
for a user who wants to repair a known malformed fenced YAML block.

## Desired Reality

Add an explicit two-step salvage path for one fenced YAML block from the
latest assistant message:

1. `/extract --salvage-indent` lists malformed callable-looking YAML source
   fences as discoverable `#sN` handles, with a compact diagnostic preview.
2. `/extract --salvage-indent #sN` projects that selected block with
   mechanical literal indentation repair as a user message, ready for
   inspection and later transcript editing.

`N` is the one-based ordinal among fenced YAML blocks in the latest assistant
message. The `s` namespace keeps source-fence handles distinct from normal
valid-candidate `#dN` extract handles. Neither form executes, replays, or
mutates durable history.

## Contract

- the no-index form lists only the available source-fence handles; it does not
  repair or adopt any content
- require an explicit `#sN` source-fence handle to project a repair; no
  implicit selection and no automatic malformed-YAML repair
- accept only a fenced YAML source block from the latest assistant message
- repair only a literal block introduced by a supported argument key
  (`search_block`, `replacement_block`, or `patch`) whose content is visibly
  unindented beneath a `|`, `|-`, `|+`, `>`, `>-`, or `>+` indicator
- retain operation order, scalar values, chomping indicator, and literal body
  bytes except for structural leading indentation added to that body
- reject mixed prose, multiple possible literal owners, unsupported indicators,
  or a source block that is already parseable/has no needed repair
- return the projected YAML as a `role=user` adopted message; do not invoke
  tool execution or replay helpers

## Allowed Write Surfaces

- `src/toas/runtime/operator_command_extract_replay.py`
- narrowly owned extraction/helper code under `src/toas/runtime/`
- `src/toas/step.py` only for the existing transitional command/help facade
- focused tests in `tests/test_step.py` and/or
  `tests/test_runtime_operator_command_handlers.py`
- this task file and generated `tasks/WORKBOARD.md`

## Non-Goals

- relaxing normal callable parsing or executing malformed YAML
- salvaging multiple fenced blocks in one invocation
- reusing valid-candidate `#dN` handles for invalid source fences
- coalescing adjacent single-operation plans
- repairing arbitrary YAML indentation, comments, or prose outside the
  supported literal argument shape

## Acceptance Criteria

- `/extract --salvage-indent` lists discoverable `#sN` source-fence handles
  with enough diagnostic context to choose one
- `/extract --salvage-indent #sN` has documented parsing and rejects malformed,
  non-positive, or out-of-range source-fence handles
- fixtures cover unindented `search_block` and `replacement_block` literal
  bodies, including chomping indicators
- projected YAML parses as a callable plan and preserves its literal body
  except for added structural indentation
- ambiguous, already-valid, and unsupported source blocks refuse explicitly
- tests prove the command projects a user message without executing tools,
  adding tool records, or rewriting prior messages

## Completion Evidence

- focused command-handler and transcript-level tests pass
- a targeted coverage run covers the new extraction/salvage helper(s)
- the full suite passes
