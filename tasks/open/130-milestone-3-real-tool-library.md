## Goal

Turn callable intent into a reusable, explicit tool subsystem.

## Scope

- Tool registration and discovery
- Argument contracts and validation
- Execution adapters
- Result normalization
- Policy boundaries around allowed execution

## Why

The operator can already detect callable intent and record tool request/result facts, but actual execution is still a free-form hook. This milestone should make tools a deliberate subsystem with a registry, explicit contracts, and consistent execution behavior.

## Planned Tasks

- `131`: tool registry and lookup
- `132`: argument validation and execution adapters
- `133`: policy boundaries and canonical result shaping

## Non-Goals

- No giant kitchen-sink catalog up front
- No implicit prompt-hidden tools

## Done When

- The operator has a real registry of tools rather than one-off execution hooks
- Tool calls are validated before execution
- Results are recorded durably and surfaced consistently as operator consequences
