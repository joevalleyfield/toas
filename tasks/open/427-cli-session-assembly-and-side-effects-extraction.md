## Goal

Extract session-assembly and side-effect clusters from `src/toas/cli.py` into focused runtime/cli modules to reduce `cli.py` monolith pressure.

## Why Now

`code_survey` still reports `cli.py` at 1288 lines, with heavy helpers such as `_stitch_frontier_records` (76 lines) and `_apply_result_side_effects` (80 lines) concentrated in one file.

## Scope

- extract session assembly helpers (`_stitch_frontier_records` cluster) to a focused module
- extract side-effect/update helpers (`_apply_result_side_effects` cluster) to a focused module
- keep `cli.py` wrappers/facade behavior stable
- add direct module tests for extracted helpers and parity tests at call sites

## Intended Behavior

- session assembly and side-effects are isolated from CLI argument/flow plumbing
- CLI behavior and stdout contracts remain unchanged

## Constraints

- no transcript/history semantic drift
- no changes to user-visible command outputs except existing formatting parity

## Done When

- `cli.py` delegates assembly/side-effect logic to focused modules
- extracted modules have direct tests
- full suite passes
