## Goal

Implement the Unix domain socket transport adapter behind the shared RPC transport interface.

## Scope

- implement server-side listen/accept/read/write for Unix sockets
- implement client-side request/response send path for Unix sockets
- enforce deterministic message framing and response correlation
- support clean startup/shutdown and stale-socket recovery

## Intended Inputs

- protocol and transport interface from `220`
- daemon operation handler contract
- endpoint naming/path rules for Unix

## Intended Outputs

- working Unix socket transport adapter
- tests covering nominal path, timeout/error path, and stale endpoint cleanup

## Constraints

- adapter must be isolated from operation/business logic
- no platform branching in handler code
- local-only endpoint behavior

## Non-Goals

- no Windows named pipe implementation
- no Vim channel integration
- no operation expansion beyond what is needed to validate transport

## Done When

- daemon can serve a minimal RPC operation via Unix socket
- CLI or test client can send request and receive correlated response
- adapter-level failure paths are covered by tests
