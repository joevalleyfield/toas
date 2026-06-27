Filed as: 260627-live-repo-session-write-fence-decoupling
FKA:
AKA: test open monkeypatch decoupling; session write fence cleanup; Path.open vs open guard
Legacy index:

keywords: tooling, hardening, historical, correctness, tests, boundaries, policy

Related: `260627-graph-segmented-read-query-hardening`; `260614-architecture-follow-through-coordination`

# Live Repo Session Write Fence Decoupling

## Current Reality

The test harness fence protecting live repo `.toas/session.md` writes was
implemented mainly by patching `Path.write_text`, `Path.write_bytes`, and
`Path.open`.

That protected the important file, but it also made tests unusually sensitive
to whether production code used `Path.open(...)` or `open(...)` for equivalent
file reads and writes.

## Desired Reality

The harness should enforce the behavioral contract:

- tests must not write the live repo session file

without caring whether the call site reached the filesystem through
`Path.open(...)`, `open(...)`, or a write helper.

## Scope

- refactor the session-write fence around path/mode behavior
- make builtins `open(...)` and `Path.open(...)` obey the same live-file rule
- add direct tests for the guard behavior itself

## Non-Goals

- changing production storage/query behavior
- broad filesystem sandbox redesign for tests

## Outcome

Closed on 2026-06-27.

The test harness in `tests/conftest.py` now guards live repo session-file
writes by behavior instead of by preferred opener style:

- builtins `open(...)` writes are fenced
- `Path.open(...)` writes are fenced
- `Path.write_text(...)` and `Path.write_bytes(...)` remain fenced
- read-only opens are allowed
- the guard now ignores call-form details and focuses on protected path plus
  write-capable mode

Direct regression coverage landed in `tests/test_conftest_guards.py` for:

- write-mode detection
- builtins `open(...)` style access
- `Path.open(...)` style access
- read-only mode passthrough
- unrelated path passthrough
