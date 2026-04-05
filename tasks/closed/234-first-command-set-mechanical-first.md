## Goal

Ship an initial high-value command set focused on mechanical workflows before broader LLM-assisted extensions.

## Scope

- implement at least one mechanical command end-to-end (`extract --dry-run`, `outline`, or `compact`)
- include command-context controls (`/workspace...`, `/cd`, `/pwd`) in the first command set
- define command-specific inputs/outputs with explicit failure modes
- provide deterministic behavior for non-tail targeting where applicable
- gate any LLM-assisted path behind explicit opt-in mode

## Intended Inputs

- command record model from `231`
- command execution path from `232`
- projection/adoption semantics from `233`

## Intended Outputs

- at least one production-ready command with tests and docs
- clear command help/usage surface
- follow-on backlog for additional commands

## Constraints

- default behavior should be mechanical and inspectable
- no hidden command invocation from `step`
- command side effects must be durable and attributable

## Non-Goals

- no full command catalog in first pass
- no broad autonomous repair system

## Done When

- one command is stable enough for routine operator use
- command outcomes are durable, projected, and adoption-safe
- tests cover normal path, ambiguity path, and failure path
