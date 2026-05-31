## Goal
keywords: config, governance, active, contract, precedence, diagnostics, sequencing, clarity

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
