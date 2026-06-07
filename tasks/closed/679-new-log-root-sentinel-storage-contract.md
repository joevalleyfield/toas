# 679: New Log Root Sentinel Storage Contract

## Goal

Make new durable message logs honor the root-sentinel taxonomy: `n0` is the empty root sentinel, and the first authored message is `n1` parented to `n0`.

## Why

Tasks `459` and `550` moved runtime state under `.toas/` and introduced root-sentinel semantics, but fresh `events.jsonl` writes still defaulted the first message to `n0` with `parent: null`.
That keeps the old shape alive in new logs and weakens tests around the storage boundary.

## Scope

- Update implicit message-id allocation for empty logs.
- Keep explicitly supplied message IDs unchanged for fixture and legacy compatibility.
- Preserve projection/read compatibility for historical logs where `n0` is a real message.
- Add focused writer/index and functional step coverage for new fresh-log behavior.

## Non-Goals

- Rewrite historical logs.
- Rewrite all legacy fixtures in the test suite.
- Materialize a standalone root-sentinel record.

## Progress

- Opened to track the 459/550 contract follow-up.
- Updated new-log message persistence so implicit IDs start at `n1` with `parent: "n0"`.
- Preserved legacy read/projection behavior for explicit historical `n0` message records.
- Added writer/index and CLI functional coverage proving fresh `.toas/events.jsonl` logs do not persist authored content as `n0`.
- Validation: targeted graph/CLI/runtime suites and the full no-coverage suite pass; full coverage run passes all behavior tests but currently fails the repo coverage gate (`16` files below 100% cap of `13`, total `94.59%`).

## Status

Completed.

## Completion

- New durable logs reserve `n0` for the empty virtual root sentinel.
- First implicit authored/bootstrap message writes as `n1` parented to `n0`.
- Explicit historical `n0` message records remain readable and are not rewritten.
- Focused storage/index and CLI functional tests cover the fresh-log contract.
