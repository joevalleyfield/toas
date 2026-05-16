# 517 Transport Abstraction (Stdio-First Envelope Carrier)

## Objective
Introduce a narrow transport abstraction layer for runtime host/client communication, with stdio as the primary implementation and envelope v0 as the target message carrier.

## Why
IPC simplification needs a stable seam between protocol semantics and transport mechanics. Without this seam, daemon/watch and client integrations stay tightly coupled to legacy payload assumptions.

## Scope
- define transport interface for framed duplex message exchange
- provide stdio-first implementation and compatibility adapter hooks
- keep existing user-visible CLI/Vim behavior unchanged
- isolate framing from higher-level protocol semantics

## Out of Scope
- full daemon removal
- mandatory transport replacement for all call sites in one change
- websocket/network transport implementation

## Done When
- a transport interface exists with explicit send/recv/close lifecycle
- stdio implementation exists behind that interface
- one production path uses the abstraction seam without behavior change
- docs reference migration relationship with `515` envelope/durability work

## Initial Slices
1. Define transport protocol interface types (message envelope carrier contract).
2. Add stdio framed transport implementation (content-length framing compatible).
3. Add adapter boundary for existing watch/daemon response flow.
4. Migrate one consumer path to use adapter while preserving output parity.

## Related
- `515` protocol envelope v0 and event durability map
- `470` operator API seam migration
- `484` watch protocol semantics
- `488` multi-operator orchestration exploration

