## Goal

Extract session-generation command/runtime clusters from `src/toas/cli.py` into focused CLI command modules.

## Why Now

`code_survey` shows remaining high-mass CLI units (`_GenerationRunner` at `186` lines, `run_step_local` at `99` lines) inside a `1568`-line `cli.py`.

## Scope

- move session-generation command logic into `src/toas/cli/commands/session.py`
- move stream/generation support classes into a focused CLI runtime module (`cli/generation_runtime.py` or equivalent)
- keep public `toas` CLI command behavior and flags stable
- add direct tests for moved generation/session command branches

## Intended Behavior

- `cli.py` keeps argv/dispatch ownership while session-generation internals live in smaller modules
- generation flow changes become localized and easier to verify

## Constraints

- preserve stdout/status rendering contracts used by daemon/plugin integrations
- preserve RPC/local fallback and async/cancel behavior
- avoid mixing this slice with unrelated CLI command groups

## Done When

- `_GenerationRunner` and primary local step-generation path are moved out of monolithic `cli.py`
- direct module tests cover moved branch logic
- full `uv run pytest` passes
