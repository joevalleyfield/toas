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

## Progress
- completed initial slice 1:
  - added transport contract module:
    - `src/toas/runtime/transport_contract.py`
  - added envelope carrier type:
    - `EnvelopeMessage`
  - added transport lifecycle protocol:
    - `EnvelopeTransport` (`send`, `recv`, `close`)
  - added envelope decode helper:
    - `envelope_message_from_dict`
  - added focused tests:
    - `tests/test_runtime_transport_contract.py`
  - validated with full suite using parallel workers:
    - `uv run pytest -q -n 14`

- completed initial slice 2:
  - added stdio framed transport implementation:
    - `src/toas/runtime/stdio_framed_transport.py`
  - implemented content-length framing compatible send/recv semantics
  - included timeout-aware recv behavior for fd-backed readers
  - added focused tests:
    - `tests/test_runtime_stdio_framed_transport.py`

- completed initial slice 3:
  - added watch/daemon adapter boundary:
    - `src/toas/runtime/watch_envelope_adapter.py`
  - adapter maps legacy watch events into envelope v0-compatible message shapes
  - daemon watch responses now include adapter-produced `envelopes` while preserving legacy fields
  - CLI watch consumer now reads envelopes-first with legacy event fallback
  - added focused tests:
    - `tests/test_runtime_watch_envelope_adapter.py`
    - updated `tests/test_cli_async_commands.py`
