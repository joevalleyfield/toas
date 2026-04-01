## Goal

Add a genuinely useful `shell` tool with explicit safety boundaries and structured output.

## Scope

- Register a `shell` tool
- Accept a tightly bounded command shape
- Enforce lightweight policy around what may run
- Return structured result data including status and output

## Behavior

- A tool call can run a local shell command through the tool subsystem
- Disallowed or malformed commands fail explicitly
- Successful runs preserve enough result detail to be useful for later projection and debugging

## Rules

- The first pass should be conservative rather than general
- The command surface must be explicit and validated
- Safety policy must live in the tool layer, not in prompt conventions

## Non-Goals

- No arbitrary shell passthrough
- No interactive PTY support
- No network-policy expansion beyond what the environment already permits

## Done When

- `shell` is a registered tool
- Tool calls can run a bounded local command and return structured output
- Validation and failure paths are covered by tests
