## Goal

Validate tool arguments and run tools through explicit adapters.

## Scope

- Define a tool-call shape the runtime will accept
- Validate required arguments before execution
- Add adapter functions that execute registered tools and return normalized data

## Behavior

- Invalid arguments fail before execution
- Tool adapters receive validated arguments, not raw YAML blobs
- The runtime can execute at least one real tool through the registry path

## Rules

- Validation errors must be explicit
- Execution adapters should be narrow and easy to test
- Validation belongs to the tool layer, not transcript parsing

## Non-Goals

- No general schema framework yet
- No broad library of tools yet

## Done When

- Registered tools declare expected arguments
- Invalid tool calls are rejected with deterministic errors
- At least one real tool executes through the validated adapter path
