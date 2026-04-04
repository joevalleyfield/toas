## Goal

Add command-native prompt browsing that emits only follow-up command lines.

## Scope

- implement `/prompts` and `/prompts <prefix>` as browse commands
- implement `/prompt <ref>` as prompt materialization command
- output format is whitespace-only command lines (no headers, bullets, or prose)
- leaf prompt entries are emitted as `/prompt <ref>` lines
- non-leaf entries are emitted as `/prompts <prefix>` lines

## Intended Inputs

- operator-command arc (`230`)
- command entry and projection path (`232`, `233`)
- existing prompt asset listing/loading behavior in CLI

## Intended Outputs

- command-native prompt discovery flow
- zero-friction follow-up execution (`dd` + run next suggested command)
- tests covering top-level browse, prefix browse, and leaf prompt output

## Constraints

- output must contain nothing but whitespace-separated command lines
- no narrative wrappers in command output
- behavior must be deterministic across local and RPC paths

## Non-Goals

- no new prompt content in this task
- no auto-insertion into transcript; adoption stays explicit

## Done When

- `/prompts` produces only runnable next-step command lines
- `/prompts <prefix>` produces only runnable next-step command lines
- `/prompt <ref>` returns the selected prompt content for explicit user adoption
