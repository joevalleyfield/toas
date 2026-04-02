## Goal

Implement a Windows named-pipe transport adapter behind the same shared RPC transport interface used by Unix sockets.

## Scope

- implement server-side named-pipe listener and request handling
- implement client-side request/response send path for named pipes
- keep protocol behavior identical to Unix transport
- define endpoint naming convention for local user sessions

## Intended Inputs

- protocol and transport interface from `220`
- Unix adapter behavior from `221`
- Windows named-pipe capabilities and user-level permission model

## Intended Outputs

- working Windows named-pipe adapter
- tests (or platform-gated tests) validating adapter behavior parity

## Constraints

- no admin privilege assumptions
- no protocol fork between Unix and Windows transports
- operation handlers remain transport-agnostic

## Non-Goals

- no Vim integration
- no expansion of RPC operation set beyond transport validation needs

## Done When

- same logical RPC calls work through Windows named pipe transport
- adapter behavior matches Unix adapter semantics for framing and errors
- documentation clearly states Windows transport endpoint strategy
