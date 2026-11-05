Filed as: 261105-multi-command-step-facade
FKA:
AKA: multi-command control turn; in-order operator commands; step facade operator commands export; control turn multi-command execution
Legacy index:

keywords: operator-command, control-turn, intent-arbitration, step-facade, frontier-resolution, execution-boundary

Parent: `260907-extraction-execution-boundary`
Related: `260803-tool-intent-ingress-separation`

# Multi-Command Operator Execution via Step Facade

## Status

Closed on 2026-11-05. `extract_operator_commands` is imported and re-exported
on the `toas.step` facade (and declared in `__all__`), allowing `step_runtime.py`
to resolve the multi-command extractor and expand all slash commands in a turn
sequentially when `extraction.intent_arbitration = "in_order"`.

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

Because `toas.step` only imported the single-tail extractor (`_extract_operator_command`),
the multi-command attribute check failed and fell back to only extracting the
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

## Verification

1. Added `test_step_control_multi_slash_command_runs_in_source_order_by_default`,
   `test_step_user_multi_slash_command_runs_in_source_order_by_default`, and
   `test_step_exports_extract_operator_commands` in `tests/test_step.py`.
2. Updated acceptance scenario assertions in
   `tests/acceptance/steps/test_control_lane_multi_command_frontier_steps.py` to
   assert all slash commands execute with durable outcomes and rendered output.
3. Added missing branch coverage for `resolve_selected_model` in `tests/test_step.py`.
4. Performed manual end-to-end execution of a multi-command `## TOAS:CONTROL` turn
   and verified sequential order, origin metadata, and consequence projection.
5. All 3,772 tests passed with 100.00% statement coverage (24,633 statements across
   161 files) and clean static checks under `./scripts/check.sh`.
