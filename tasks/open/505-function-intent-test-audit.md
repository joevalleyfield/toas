# 505 Function-Intent Test Audit (Coverage vs Behavioral Confidence)

## Objective
Audit critical runtime and tooling functions by intended behavior (intent) and verify that tests assert those behaviors explicitly, not just lines executed.

## Why
Coverage ratchets improved line execution signal, but they do not guarantee intent-level correctness. We need an explicit `(function, intent) -> assertion` map to identify silent blind spots.

## Scope
- define audit method and artifact format
- run first-pass audit on current active-change surfaces (`500`, `501`, `504`, `483`, `485` vicinity)
- identify concrete missing assertions and prioritize follow-on test additions
- link findings to existing/open tasks when possible; open focused follow-ons when needed

## Done When
- a committed audit artifact exists with at least one full pass over active surfaces
- each audited function has intents and current assertion status noted
- actionable gaps are listed with proposed test targets

## Related
- `374` coverage-led refactor pass
- `379` coverage noise burndown
- `400` decomposition umbrella
- `504` missing-files ratchet gate

## Progress
- opened task and defined first-pass audit scope/artifact
- closed first behavioral gap slice on `shell_streaming` exception-tolerance intents:
  - added explicit tests for `stdout is None` reader short-circuit behavior
  - added explicit tests for reader-loop tolerance of `set_blocking` errors, `BlockingIOError`, and `unregister` failure
  - revalidated full suite with `-n 14`
