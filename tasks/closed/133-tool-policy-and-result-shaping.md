## Goal

Make tool execution policy explicit and shape tool results consistently.

## Scope

- Define a minimal execution policy boundary for registered tools
- Normalize tool outputs into canonical result content
- Keep tool request/result records aligned with the new execution subsystem

## Behavior

- Disallowed or failing tool calls surface clearly
- Successful tool executions produce canonical result content
- Durable tool request/result records remain explicit and stable

## Rules

- Policy decisions must not be hidden in prompt text
- Result shaping should be deterministic enough to test
- Tool records remain distinct from message events and model-call records

## Non-Goals

- No full sandbox or permission framework yet
- No rich result rendering layer yet

## Done When

- Tool execution runs through an explicit allow/deny boundary
- Result content is shaped consistently across tools
- Durable request/result records still reflect the executed tool path
