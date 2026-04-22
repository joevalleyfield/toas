## Goal

Extract top-level step orchestration from `src/toas/step.py` into `src/toas/runtime/step_runtime.py` with explicit staging seams.

## Why Now

`code_survey` shows `step()` (`156` lines) still coupled to large internal helpers in a `1650`-line module; this blocks small targeted changes and blurs ownership.

## Scope

- move orchestration stages (frontier resolution, operator routing, generation guard, result projection assembly) into `runtime/step_runtime.py`
- keep `toas.step.step` as compatibility facade during transition
- isolate stage contracts with typed/structured helper arguments where practical
- add stage-level tests focused on consequence stitching and append-set/output contracts

## Intended Behavior

- `step.py` becomes a thin compatibility entrypoint
- orchestration flow is readable as staged runtime operations with direct tests

## Constraints

- preserve append-only history invariants and message/control/tool/model-call record separation
- no CLI/API surface changes for `toas step`
- avoid broad refactors outside the step runtime boundary

## Done When

- orchestration body lives in `runtime/step_runtime.py` with parity wrappers in `step.py`
- critical stage contracts are directly tested without monolith setup
- full `uv run pytest` passes
