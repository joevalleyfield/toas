## Goal

Split `src/toas/cli.py` main dispatch surface into focused command-routing modules while preserving current command semantics.

## Why Now

`code_survey` still reports `cli.main` at ~110 lines in a 1200+ line file. Dispatch and command wiring remain tightly coupled to implementation details despite prior extractions.

## Scope

- extract argv/main dispatch mapping into a focused module (or small command-routing package)
- keep `toas.cli.main()` as compatibility entrypoint
- preserve existing command names, argument behavior, and fallback paths
- add tests locking dispatch behavior and unknown-command/help contracts

## Intended Behavior

- command routing is explicit and independently testable
- `cli.py` becomes thinner and easier to change safely

## Constraints

- maintain CLI compatibility and exit-code behavior
- avoid big-bang command renames

## Done When

- `main()` is primarily glue that delegates dispatch/routing
- dispatch routing has focused tests
- full suite passes

## Result

- extracted main dispatch parsing/routing to `src/toas/cli_dispatch.py`:
  - `DispatchDeps`
  - `require_arg(...)`
  - `dispatch_main(...)`
- reduced `src/toas/cli.py:main` to thin glue that delegates into dispatch module
- preserved CLI command names/options and existing `run_*` entrypoints
- added focused dispatch tests:
  - `tests/test_cli_dispatch.py`
- verification:
  - full suite: `uv run pytest` -> `944 passed`, coverage `89.44%`
