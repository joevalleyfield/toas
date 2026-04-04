## Goal

Add an explicit command-entry path that persists command requests/results through the new operator record model.

## Scope

- define command-entry syntax and dispatch point (`/commands` and/or `toas op ...`)
- parse and validate command invocation arguments
- append command request, execute command handler, append command result
- preserve current `step` behavior as-is

## Intended Inputs

- record model from `231`
- existing CLI dispatch and durable append flow
- existing tool execution error/reporting patterns

## Intended Outputs

- user-invokable command entrypoint
- deterministic request/result append flow
- tests covering happy path and error path

## Constraints

- command execution must be explicit, never implicit during ordinary `step`
- failures must be visible and durable
- no conversation-message writes unless explicitly adopted by user action

## Non-Goals

- no broad command catalog yet
- no automatic transcript rewrite behavior

## Done When

- a user can invoke a command and observe durable request/result records
- command execution is replayable from event history
- CLI behavior remains parity-safe with existing core operations
