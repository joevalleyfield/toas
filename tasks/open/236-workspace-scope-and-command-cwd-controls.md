## Goal

Add explicit operator commands to control execution scope and command working directory without moving TOAS transcript/history state.

## Scope

- add `/workspace` commands for allow-root inspection and mutation
- add `/cd`, `/pwd`, and `/cd -` for command execution context
- keep `session.md` and `events.jsonl` location fixed
- make command context and allow-root changes durable and replayable
- default to protecting TOAS state files from ordinary command/tool access

## Intended Inputs

- operator-command record model (`231`)
- command entry/projection path (`232`, `233`)
- current shell/tool guardrail behavior

## Intended Outputs

- command surface:
  - `/workspace`
  - `/workspace add <path>`
  - `/workspace remove <path>`
  - `/workspace reset`
  - `/workspace mode strict|unbounded` (optional profile switch)
  - `/cd <path>`
  - `/cd -`
  - `/pwd`
- durable records for scope/context changes and related outcomes
- tests for path handling, replay behavior, and guardrail enforcement

## Constraints

- `/cd` affects only command execution context, never transcript/history storage paths
- scope changes must be explicit operator actions, never hidden side effects
- default posture remains least-privilege
- failures must be visible and recoverable

## Non-Goals

- no implicit auto-expansion outside declared allow roots
- no removal of guardrails as a default behavior

## Done When

- users can explicitly widen/narrow command scope during a session
- users can route command execution to alternate directories safely
- TOAS control-plane files remain isolated from ordinary command operations by default
