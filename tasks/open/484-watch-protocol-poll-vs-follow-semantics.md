## Goal

Define and implement explicit watch protocol semantics so clients can choose:

- `poll`: get everything available now (non-blocking snapshot drain)
- `follow`: get everything left (blocking progression to new data/terminal)

## Why

Current behavior depends on client-side timing loops and poll cadence, which creates ambiguous UX (e.g., appearing end-loaded despite incremental producer writes). This should be solved at protocol level, not by client sleep/retry heuristics.

## Scope

- Add protocol-level mode semantics to async watch path.
- Implement daemon/run-store behavior for:
  - snapshot-bounded non-blocking drain (`poll`)
  - blocking wait/progression semantics (`follow`)
- Update Vim plugin to use protocol modes directly.
- Add tests at daemon + Vim (Vader) layers.

## Non-Goals

- Broad redesign of async run storage.
- UI formatting changes unrelated to watch semantics.

## Proposed Semantics

1. `poll` mode:
   - server snapshots current `output_len` and `event_seq` at request start
   - response drains only up to those snapshot bounds
   - no waiting for future writes

2. `follow` mode:
   - server may wait for new output/events/terminal (bounded by timeout)
   - returns progression beyond caller offset/seq
   - repeated follow calls eventually drain to terminal

## Done When

- Protocol contract documented and tested.
- Daemon watch implementation supports explicit `mode`.
- Vim `ToasWatch`:
  - default path maps to `poll`
  - `--follow` maps to `follow`
- Existing flaky timing behavior is removed.
- Repro scenarios with slow shell output show deterministic behavior under both modes.

## Initial Slices

1. Daemon contract:
   - add `mode` parsing/validation in watch request path
   - implement snapshot-bounded `poll` response
   - implement bounded blocking `follow` response

2. Plugin integration:
   - pass mode in `ToasWatch` payload
   - remove/avoid timing hacks in client loop

3. Test matrix:
   - run_store unit tests for `poll` and `follow`
   - Vader tests for:
     - non-follow drains available-now only
     - follow drains to terminal

## Progress

- Implemented watch payload validation for `mode` (`poll` or `follow`).
- Implemented protocol-level watch behavior in `run_store.watch_async_step`:
  - `poll` uses snapshot-bounded non-blocking drain.
  - `follow` uses bounded blocking wait for progression/terminal.
  - added `timeout_s` validation for follow wait bound.
- Updated Vim `ToasWatch` to pass mode directly:
  - default requests `poll`
  - `--follow` requests `follow`
  - removed local idle/drain timing loop workaround.
- Added daemon unit coverage for:
  - poll snapshot semantics
  - follow progression wait semantics
  - invalid `mode` and invalid `timeout_s`
  - request-contract invalid `mode`.

## Related

- `483` command stdout streaming to Vim plugin debug/fix
- `470` operator API seam and CLI-thin wrapper migration
