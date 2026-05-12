# 509 Asyncio Runtime Migration Streaming/Watch Contract

## Objective
Migrate daemon async step execution and watch plumbing toward `asyncio` primitives while preserving current protocol behavior.

## Why
Recent cross-platform streaming issues exposed fragility in mixed thread/subprocess buffering paths. An async-first runtime reduces timing races and improves lifecycle control across platforms.

## Scope
- phase 0: lock behavior with contract tests (streaming increments, poll/follow, cancellation, terminal ordering)
- phase 1: add asyncio subprocess runner scaffold behind feature flag
- phase 2+: migrate watch/cancel lifecycle to async-native path, then promote default after parity soak
- keep existing threaded path as fallback during migration window

## Done When
- behavior-lock tests exist for protocol-critical streaming/watch contracts
- asyncio path exists behind explicit flag and passes targeted + full suite parity
- migration progress and cutover criteria are documented and tracked in this task

## Related
- `483` vim streaming closure baseline
- `484` watch protocol poll vs follow semantics
- `497` shell streaming cross-platform compatibility follow-up
- `470` operator API seam

## Progress
- phase 0 contract-lock started with daemon async runner tests covering terminal ordering invariant:
  - no post-terminal stdout deltas once `terminal_event_emitted` is set
  - pending output up to terminal boundary remains emitted
- targeted daemon async/watch tests pass; full suite functionally passes on this branch (coverage gate remains constrained by current ratchet cap)
- phase 1 scaffold landed behind feature flag:
  - `TOAS_DAEMON_ASYNCIO=1` selects `cold_asyncio` run mode in daemon async runner
  - async worker shim added (`_run_in_process_worker_async`) with `asyncio.to_thread` bridge to preserve current semantics during migration
  - default remains existing `cold` threaded behavior when flag is not enabled
- phase 2 seam bootstrap started for watch follow-wait path:
  - added `TOAS_DAEMON_ASYNCIO_WATCH` gated async wait helper (`_follow_wait_for_change_or_terminal_async`) in run-store
  - `watch_async_step` now dispatches follow wait through async or sync helper with identical response contract
- phase 2 stabilization:
  - added direct async wait branch tests (terminal, timeout, output-growth, sleep-loop progression)
  - retained full-suite parity with cap-17 coverage gate green after seam landing
- phase 2 cancel seam bootstrap:
  - added `TOAS_DAEMON_ASYNCIO_CANCEL` gated cancel path in run-store
  - terminate now flows through async helper (`_terminate_process_async`) when flag is enabled
  - added contract tests for flag parsing, asyncio-run dispatch, and async to-thread bridge
- phase 2 lifecycle policy consolidation:
  - centralized daemon asyncio runtime flag parsing in run-store (`asyncio_runtime_enabled`)
  - async runner now consumes shared runtime policy authority instead of maintaining a parallel parser
  - added integration test asserting start path consults shared runtime policy exactly once

- phase 2 lifecycle terminalization consolidation:
  - extracted terminal completion emission + durable terminal record write into shared run-store helper (`finalize_terminal_state`)
  - async runner now delegates terminalization policy to run-store in wait/success/failure paths
  - added idempotence test to lock exactly-once terminal event/write behavior

- phase 2 lifecycle run-creation consolidation:
  - added shared run-store factory (`create_and_register_run`) for daemon run object assembly + registration
  - async runner now delegates run creation/registration to run-store helper
  - added test coverage for run creation field wiring and registration lookup

- phase 2 async dispatch + parity matrix:
  - introduced shared async/sync execution seam (`_run_async_or_sync`) for watch-follow wait and cancel terminate dispatch
  - added protocol-shape parity tests across flag off/on for start/watch/cancel entrypoints
  - preserved response contracts while reducing branch duplication in run-store
