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
