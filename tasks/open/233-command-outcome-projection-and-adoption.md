## Goal

Define and implement projection behavior for command outcomes so results are visible without mutating conversation lineage.

## Scope

- render command outcomes in result-style projected output
- define adoption semantics when users choose to fold projected output into conversation
- ensure history/transcript views keep command records and message events distinct
- add inspection affordances for command provenance

## Intended Inputs

- record model from `231`
- command execution path from `232`
- current transcript/result projection behavior

## Intended Outputs

- clear projection rules for command outcomes
- explicit adoption behavior documentation
- tests for projection and lineage boundaries

## Constraints

- projected output must not imply message parentage
- adoption must be explicit user action
- ambiguity must be surfaced, not guessed

## Non-Goals

- no attempt to solve all transcript repair scenarios
- no hidden auto-adoption policies

## Done When

- command outcomes are visible, inspectable, and replay-safe
- conversation lineage remains untouched unless users explicitly adopt output
- projection behavior is consistent across CLI and daemon execution paths
