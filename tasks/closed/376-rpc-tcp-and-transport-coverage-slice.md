## Goal

Lift coverage and confidence for the TCP transport seam (`rpc_tcp.py` + `rpc_transport.py`) as the first low-risk, high-yield slice under `375`.

## Why Now

`rpc_tcp.py` is the lowest-covered module (~20%) and is small enough to improve quickly without destabilizing core stepping behavior.

## Scope

- add focused tests for connect/read/write/error/close behavior in TCP transport paths
- cover failure branches (connection errors, short reads/writes, malformed payload handling)
- keep production changes minimal; refactor only where needed for deterministic tests

## Intended Behavior

- TCP transport behavior is explicitly specified by tests instead of incidental behavior
- module coverage rises materially with stable deterministic tests

## Constraints

- no protocol contract changes
- no broad transport abstraction rewrites in this slice

## Done When

- targeted TCP/transport tests are merged and green
- coverage improvement is measurable in `rpc_tcp.py` and adjacent transport helpers

## Outcome

- added deterministic `rpc_tcp` tests for round-trip handling, protocol-error shaping, malformed-frame fallback request id (`unknown`), close lifecycle, and serve-before-start guard
- expanded `rpc_transport` tests to cover server/request dispatch by endpoint type, cleanup semantics, wrapped transport errors, and unsupported-type branches
- no production protocol/transport behavior changes were required for this slice
- verification: `uv run pytest -q` passing with overall coverage above enforced floor
