## Goal

Start tools-cluster package-shape migration by introducing a tools helper subpackage and moving extracted tools helper modules behind compatibility shims.

## Why Now

The tools cluster already has extracted seams (`tools_registry`, `tools_execution`, `tools_rendering`), making it low-risk to begin package-shape migration without touching `tools.py` behavior.

## Scope

- create `src/toas/tools_cluster/` package
- move extracted helper modules into that package:
  - `tools_registry.py` -> `tools_cluster/registry.py`
  - `tools_execution.py` -> `tools_cluster/execution.py`
  - `tools_rendering.py` -> `tools_cluster/rendering.py`
- keep compatibility shim modules at original paths:
  - `src/toas/tools_registry.py`
  - `src/toas/tools_execution.py`
  - `src/toas/tools_rendering.py`
- update core call sites to package paths where appropriate
- preserve behavior and public import contracts

## Intended Behavior

- existing imports keep working through shims
- tools package-shape migration begins with no semantic drift

## Constraints

- no change to tool-call semantics or output shaping behavior
- no broad rename of `tools.py` in this slice
- move + shim only

## Done When

- tools helper subpackage is live and used by core module imports
- compatibility shims preserve legacy imports
- full suite + lint pass
