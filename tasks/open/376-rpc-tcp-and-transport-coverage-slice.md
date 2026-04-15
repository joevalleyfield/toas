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
