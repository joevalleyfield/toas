## Goal

Add first-class config override lifecycle commands so operators can mutate, unset, import/export, and inspect effective config provenance explicitly.

## Why Now

TOAS already has durable `toas.toml` defaults and durable override records. Operators now need explicit transport/reset semantics for override state without blurring lane boundaries.

## Scope

- add `/config unset <key>` to remove effective override for one key
- add `/config restore` to clear override-lane influence for current session view
- add `/config load [path]` to import file values into override lane
- add `/config save [path]` to persist effective config to file (`toas.toml` default)
- add `/config show --sources` (or equivalent) to display value provenance

## Intended Behavior

- `set` and `unset` operate on override lane, not direct file mutation
- `restore` resets effective view to file/env/default baseline
- `load` supports config transport into override lane
- `save` supports config transport out to file
- source visibility is explicit per key (override, file, env/default)

## Intended Inputs

- `src/toas/step.py`
- `src/toas/config.py`
- `src/toas/cli.py`
- graph/config override record handling
- docs/help surface updates
- tests for command behavior and provenance reporting

## Intended Outputs

- reversible, auditable config operations
- explicit persistence controls
- reduced confusion between config lanes

## Constraints

- preserve append-only durable history semantics
- keep backward compatibility for existing `/config show` and `/config set`
- avoid hidden mutation of `toas.toml` except explicit `save`

## Non-Goals

- no schema migration engine
- no profile registry beyond file load/save in first pass

## Done When

- new commands (`unset`, `restore`, `load`, `save`) are implemented and tested
- provenance/source view is available in config output
- docs clearly explain lane semantics and command effects
