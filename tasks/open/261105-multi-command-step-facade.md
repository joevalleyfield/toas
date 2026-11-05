Filed as: 261105-multi-command-step-facade
FKA:
AKA: multi-command control turn; in-order operator commands; step facade operator commands export; control turn multi-command execution
Legacy index:

keywords: operator-command, control-turn, intent-arbitration, step-facade, frontier-resolution, execution-boundary

Parent: `260907-extraction-execution-boundary`
Related: `260803-tool-intent-ingress-separation`

# Multi-Command Operator Execution via Step Facade

## Intent

Export `extract_operator_commands` on `toas.step` so that turns containing
multiple slash commands (such as `## TOAS:CONTROL` or `## TOAS:USER`) execute
all authored operator commands sequentially when
`extraction.intent_arbitration = "in_order"`.

## Motivation

In `## TOAS:CONTROL` or `## TOAS:USER` turns, operators may author multiple
slash commands intended to execute within a single step cycle (for example:
`/config set telemetry compact` followed by `/clear-context`).

The multi-command parser [`extract_operator_commands`](src/toas/runtime/frontier_resolution.py)
and candidate expansion [`_expand_in_order_operator_candidates`](src/toas/runtime/step_runtime.py)
already support in-order multi-command sequencing. However, `step_runtime.py`
dynamically accesses the extractor via `getattr(step_mod, "extract_operator_commands", None)`,
where `step_mod` is `toas.step`.

Because `toas.step` only imports the single-tail extractor (`_extract_operator_command`),
the multi-command attribute check fails and falls back to only extracting the
single trailing command. Exposing `extract_operator_commands` on the `toas.step`
facade fixes this wiring gap.

## Acceptance Criteria

1. `toas.step` imports and exports `extract_operator_commands` from
   `toas.runtime.frontier_resolution`.
2. Turns with multiple slash commands (`## TOAS:CONTROL` and `## TOAS:USER`)
   execute all commands in authored order when `extraction.intent_arbitration = "in_order"`.
3. Add end-to-end regression tests verifying that a single step execution on a
   turn with multiple slash commands executes each command sequentially and
   records all corresponding consequences.
4. Maintain 100.00% statement coverage across all source files under
   `./scripts/check.sh`.
