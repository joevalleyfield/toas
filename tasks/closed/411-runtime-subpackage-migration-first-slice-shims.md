## Goal

Start package-shape migration by introducing `src/toas/runtime/` and moving extracted runtime helpers behind compatibility shims.

## Why Now

Package migration is now lower-risk after helper extraction; runtime modules avoid `module-vs-package` naming conflicts present in `tools.py`/`cli.py`/`daemon.py`.

## Scope

- create `src/toas/runtime/` package
- move/adopt these extracted modules into runtime package:
  - `step_frontier.py` -> `runtime/frontier_resolution.py`
  - `runtime_edges.py` -> `runtime/rpc_edges.py`
- keep compatibility shim modules at original paths:
  - `src/toas/step_frontier.py`
  - `src/toas/runtime_edges.py`
- preserve public behavior/import contracts
- add/adjust tests if needed to keep new runtime modules directly covered

## Intended Behavior

- existing imports continue to work
- package-shape migration begins without semantic drift

## Constraints

- no behavioral changes in step/rpc flows
- no broad API renames in this slice
- extraction/move + shims only

## Done When

- runtime package path is live and used by core call sites
- compatibility shims preserve legacy imports
- full suite + lint pass
