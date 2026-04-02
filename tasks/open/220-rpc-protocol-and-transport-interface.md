## Goal

Define the RPC protocol and transport abstraction needed for a long-lived `toasd` daemon, with cross-platform transport support designed in from the first step.

## Scope

- define a minimal request/response RPC protocol for daemon operations
- define a transport interface that hides endpoint-specific details
- lock endpoint naming/addressing strategy for Unix and Windows
- include protocol/version compatibility expectations

## Intended Inputs

- current `toas step` and related CLI operation semantics
- current event-log and transcript invariants
- platform transport constraints (Unix sockets, Windows named pipes)

## Intended Outputs

- protocol spec (message envelope, framing, error shape)
- transport interface spec (`serve`/`send` semantics and lifecycle)
- endpoint selection rules by platform

## Constraints

- protocol must support deterministic request/response correlation
- framing must be robust for incremental streaming reads
- design must avoid network-only assumptions
- transport details must not leak into operation handlers

## Non-Goals

- no transport adapter implementation yet
- no daemon behavior implementation yet
- no Vim integration yet

## Done When

- protocol and transport interface are fully specified
- Unix socket and Windows named pipe are both first-class in the design
- no implementation-critical transport decisions are left ambiguous
