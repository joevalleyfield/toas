## Goal

Introduce a real tool registry so callable intent resolves through named tools rather than ad hoc execution hooks.

## Scope

- Define a registry type for tool definitions
- Support tool lookup by declared `tool_name`
- Keep tool definitions explicit and testable

## Behavior

- A callable plan is resolved through the registry
- Unknown tools fail explicitly rather than silently no-oping
- The execution path no longer needs hard-coded per-call behavior in the CLI

## Rules

- Tool names are durable interface points
- Registry lookup should stay independent from transcript parsing
- The first pass may use a small in-process registry

## Non-Goals

- No dynamic discovery from the filesystem yet
- No package/plugin tool loading yet

## Done When

- The runtime has a real registry object or module for tools
- Callable plans resolve through registry lookup
- Unknown tools produce explicit, test-covered failures
