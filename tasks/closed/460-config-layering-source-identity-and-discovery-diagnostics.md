## Goal

Complete post-`458` config layering diagnostics by surfacing concrete file-path source identity and discovered-path introspection.

## Why

- Current source labels report generic `config_file` rather than which discovered path provided a value.
- Operators need a direct way to inspect path discovery order and active config origins when debugging layered behavior.

## Scope

- enrich config source reporting to include concrete discovered path identity where applicable
- add a command surface for discovery diagnostics (for example, discovered paths + existence + effective precedence)
- keep existing compatibility paths and layering precedence unchanged

## Done When

- `/config show --sources` (or equivalent diagnostics) can identify concrete file origins for file-sourced keys
- operator has a deterministic command to inspect discovered config path order and presence
- tests cover path-identity reporting and discovery diagnostics output

## Progress

- opened as follow-on after `458` first-pass completion

## Progress

- `/config show --sources` now supports concrete file-path source identity for keys that originated from discovered config files.
- `/config paths` added to report discovered config path order and existence markers.
- regression tests added for `config paths` handler output and concrete source-path rendering.

## Status

Completed.
