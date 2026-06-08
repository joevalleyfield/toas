# Config Sequencing Contract and Diagnostics Clarity

Filed as: 466-config-sequencing-contract-and-diagnostics-clarity
FKA: 466-config-sequencing-contract-and-diagnostics-clarity.md
AKA: config sequencing; config precedence; config overrides; config diagnostics
Legacy index: 466
keywords: config, governance, historical, contract, precedence, diagnostics, sequencing, clarity

## Goal

Clarify and stabilize the `/config` sequencing contract (timing, lane precedence, durability classes) with stronger operator diagnostics and documentation.

## Why

Current behavior is intentionally workable but cognitively ambiguous: some config operations are durable session overrides, some are ephemeral runtime-only, and precedence/timing expectations are not explicit enough in operator-facing surfaces.

## Scope

- document current `/config` operation classes (`durable override`, `ephemeral runtime`, `export/import side effect`)
- define and publish step-timing semantics (when updates apply relative to frontier consequence execution)
- define explicit precedence stack for effective config assembly
- improve `/config show --sources` and help copy to reflect sequencing/precedence model
- add tests for sequencing/precedence diagnostics and no-regression behavior

## Non-Goals

- no control-lane parser/projection work (handled by `465`)
- no broad config keyspace expansion
- no backend protocol redesign
- no mandatory behavior flips unless explicitly approved by follow-on slice

## Done When

- sequencing and precedence model is explicit in docs/help and reflected in diagnostics
- `/config` command responses align with the published contract language
- tests encode the contract and protect against ambiguous regressions
- any behavior-changing proposal is isolated to explicit follow-on subtasks

## Initial Slices

1. behavior inventory + contract draft (as-implemented truth table)
2. operator-surface copy pass (`/help`, `/config`, `/config show --sources`)
3. targeted diagnostic improvements for ambiguous cases
4. contract tests for timing/precedence invariants
5. optional behavior-change follow-on tasks if gaps remain after docs/diagnostics pass

## Closeout Rationale (2026-06-08)

This task has been resolved and closed:
1. **Formalized Precedence & Timing Contract**: Updated and promoted [docs/notes/2026-05-09-config-precedence-principles.md](file:///Users/tim/Documents/Projects/toas-gemini/docs/notes/2026-05-09-config-precedence-principles.md) to a formal contract, clearly documenting the durability classes (durable overrides, ephemeral secrets, side-effect exports), timing semantics (when updates apply during frontier execution and subsequent steps), and the precedence hierarchy: `ephemeral_secrets > session_override > config_file (local > global) > env > defaults`.
2. **Help Documentation**: Modified `render_help_config()` in `src/toas/step.py` to document the timing, durability classes, and precedence model explicitly in the `/help config` command view.
3. **Diagnostics & `/config show` Legend**: Updated `_config_show_result()` in `src/toas/runtime/operator_command_config_help.py` to append timing and precedence legends to the `/config show` and `/config show --sources` outputs.
4. **Contract and Regressions Tests**: Added `test_config_help_handler_config_show_sources` to `tests/test_runtime_operator_command_handlers.py` to ensure that `_build_config_sources` correctly resolves the sources hierarchy (`session_override`, `config_file`, `env`, `default`), that `--sources` prints them as expected, and that the legends are included in the view output. All tests pass successfully and coverage meets the 95% threshold.
