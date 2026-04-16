## Goal

Execute the first `403` implementation slice by extracting CLI async/rpc lifecycle command handlers into a focused module while preserving command and output contracts.

## Why Now

The async/rpc handler cluster is already seam-tested and now depends on shared runtime-edge helpers (`402`), making it the lowest-risk first movement into decomposed module boundaries.

## Scope

- extract the following CLI command handlers into a dedicated module (target: `src/toas/cli_commands_async.py` or equivalent):
  - `run_step_async`
  - `run_watch`
  - `run_cancel`
  - `run_backend`
  - supporting payload/helper logic used only by this cluster
- keep `cli.main` dispatch and command names unchanged
- preserve all existing stdout/stderr and `SystemExit` error text contracts
- keep compatibility wrappers in `cli.py` so current call sites/tests remain valid during migration

## Intended Behavior

- async/rpc lifecycle command behavior is unchanged
- extracted module is directly unit-testable and reaches `100%` coverage

## Constraints

- no change to daemon op names or payload semantics
- no behavioral drift in follow mode, failure rendering, or backend detail output
- extraction only; no policy changes in this slice

## Done When

- new module is introduced and used by `cli.py` wrappers
- full test suite passes
- extracted module reports `100%` coverage
