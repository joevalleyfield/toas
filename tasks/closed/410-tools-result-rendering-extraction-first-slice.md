## Goal

Execute the next `404` tools-side decomposition slice by extracting result rendering logic from `tools.py` into a focused module.

## Why Now

After registry/dispatch (`408`) and plan execution (`409`) extraction, result rendering is the remaining cohesive presentation cluster in `tools.py` and a clean next seam.

## Scope

- add dedicated module (target: `src/toas/tools_rendering.py`) for:
  - shell/read/search/replace/default render helpers
  - render-dispatch maps and `shape_result_content`
- keep `tools.py` public compatibility surface unchanged (`shape_result_content` remains available)
- preserve exact output behavior for all existing tool result shapes
- add direct tests for new module and achieve `100%` coverage

## Intended Behavior

- no semantic drift in tool result text output
- rendering logic is directly testable outside monolithic `tools.py`

## Constraints

- no changes to tool execution semantics
- no changes to transcript marker/projection rules
- extraction-only slice

## Done When

- `tools_rendering.py` is introduced and used by `tools.py` wrapper
- full suite and lint pass
- new module has direct tests and `100%` coverage
