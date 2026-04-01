## Goal

Turn callable intent into a reusable, explicit tool subsystem.

## Scope

- Tool registration and discovery
- Argument contracts and validation
- Execution adapters
- Result normalization
- Policy boundaries around allowed execution

## Non-Goals

- No giant kitchen-sink catalog up front
- No implicit prompt-hidden tools

## Done When

- The operator has a real registry of tools rather than one-off execution hooks
- Tool calls are validated before execution
- Results are recorded durably and surfaced consistently as operator consequences
