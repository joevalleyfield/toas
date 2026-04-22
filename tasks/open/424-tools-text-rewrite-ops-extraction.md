## Goal

Extract text-rewrite tool operations from `src/toas/tools.py` into focused file-ops modules.

## Why Now

`code_survey` highlights `_run_replace_block` (`99` lines), `_run_replace_range` (`83` lines), and mismatch diagnostics as a cohesive heavy cluster in a `1541`-line module.

## Scope

- move `replace_range`/`replace_block` execution and diagnostics into `src/toas/tools_cluster/file_ops.py`
- preserve existing callable operation contracts and error-shape expectations
- keep `tools.py` registry wiring stable via compatibility wrappers/imports
- add direct tests for moved rewrite logic, especially newline and mismatch diagnostics behavior

## Intended Behavior

- rewrite tool behavior stays stable while implementation sits behind a focused file-ops boundary
- future patch/rewrite safety changes avoid touching the full tools monolith

## Constraints

- no behavior regressions in block/range matching semantics
- preserve diagnostics quality for weak-model repair loops
- keep extraction scoped to rewrite/file-op helpers only

## Done When

- rewrite operation internals are no longer implemented in `tools.py`
- focused module tests cover happy path and mismatch branches
- full `uv run pytest` passes
