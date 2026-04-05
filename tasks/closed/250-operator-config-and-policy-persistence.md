## Goal

Establish a config object and persistence layer as the policy foundation for extraction and operator behavior controls.

## Why Now

The extraction dispatch in `step()` has implicit, uncontrolled policy: tail YAML block only, loose command fallback always enabled, user shell always active. Before broadening the extraction command surface, the policy decisions that govern these paths need an explicit home — one that can be read, displayed, overridden per-session, and extended without scattering flags across call sites.

## Scope

- `OperatorConfig` dataclass (`config.py`) with at minimum an `ExtractionPolicy` section
- Flat dotted-key presentation at the command/display boundary (`extraction.yaml_position = tail`)
- Nested config-shaped storage in `toas.toml` and in durable event records
- Flatten/unflatten conversion at the boundary so both shapes are native to their layer
- File-backed project defaults via `toas.toml` (3.11+ `tomllib`, graceful skip on 3.10)
- Durable `config_override` records in `events.jsonl` for session-level overrides; later records accumulate and win per-key
- `/config [show]` and `/config set <key> <value>` operator commands
- Config loaded in `cli.py` as file config merged with active session overrides, passed into `step()`
- Extraction dispatch gates in `step()` respect config flags; defaults match current behavior exactly

## Intended Inputs

- Existing extraction dispatch in `step.py`
- Existing control-record pattern in `graph.py` (`command_context`, `workspace_scope`)
- `BackendGenerationPolicy` pattern in `backend_policy.py` as structural precedent

## Intended Outputs

- `config.py`: `OperatorConfig`, `ExtractionPolicy`, flatten/unflatten, file loader, override application
- `graph.py`: `write_config_override_record`, `active_config_overrides`
- `step.py`: `/config` command, `config` param wired through, extraction gates
- `cli.py`: config loading and `config_update` result node handling
- Tests covering config object, record round-trip, command surface, and flag gates

## Constraints

- Default config must produce identical behavior to pre-config state
- Storage shape is config-shaped (nested); presentation shape is toggle-shaped (dotted keys)
- No behavioral changes beyond wiring — actual policy variation comes in follow-on work

## Non-Goals

- No `yaml_position = any` implementation in this pass (plumbing only)
- No config validation beyond known-key and known-type checks
- No config command in the `toas` CLI top level (session-level `/config` is sufficient for now)

## Done When

- `OperatorConfig` is wired from file + session overrides through `step()` end-to-end
- `/config show` and `/config set` work and produce durable records
- All defaults match current behavior; no existing tests change
- Tests cover config object, record layer, and command surface
