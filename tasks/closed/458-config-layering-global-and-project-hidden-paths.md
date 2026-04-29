## Goal

Add layered config loading so TOAS can run without relying on a root `toas.toml`, while keeping backward compatibility.

## Why

- Operator wants machine-scoped defaults similar to other tools (`~/.config/...` style).
- Project-local config should be easy to keep hidden/ignored as one path (for example under `.toas/`).
- Current behavior hardcodes root `toas.toml` in multiple read paths and help text.

## Scope

- define config discovery precedence:
  1. built-in defaults
  2. global config (default: `~/.config/toas/config.toml`, fallback: `~/.toas.toml`)
  3. project config (preferred: `.toas/config.toml`, fallback: `toas.toml`)
  4. durable session overrides (`config_override` records)
- centralize config-path discovery in one helper and adopt across CLI/runtime call sites
- keep `toas.toml` support as compatibility fallback
- update `/config` help/save/load messaging to reflect layered paths

## Non-Goals (first slice)

- no breaking removal of `toas.toml`
- no migration command yet; compatibility-first loading is enough

## Done When

- running with only global config works
- running with only `.toas/config.toml` works
- existing repos with `toas.toml` continue to work unchanged
- tests cover precedence and fallback behavior

## Planned Slices

1. Path-discovery helper + tests.
2. Replace hardcoded `toas.toml` readers in runtime policy + CLI session/step assembly.
3. Update `/config load|save|show` defaults and help text.
4. Doc pass (`README`, roadmap notes).

## Progress

- opened
- slice 1 landed:
  - added centralized path discovery helper in `src/toas/config.py`:
    - `discover_config_paths(workdir, home=None)`
    - `config_from_discovered_paths(workdir, home=None)`
  - precedence implemented as:
    1. `~/.config/toas/config.toml`
    2. `~/.toas.toml`
    3. `<workdir>/.toas/config.toml`
    4. `<workdir>/toas.toml` (compatibility fallback, highest precedence)
  - runtime policy edge adopted discovered layering:
    - `src/toas/runtime/policy_edges.py` now loads via `config_from_discovered_paths(...)`
  - tests added:
    - `tests/test_config.py` covers discovery order + precedence + hidden-project-only config
    - `tests/test_runtime_policy_edges.py` covers hidden project config uptake in runtime policy load

## Remaining

- slice 2 landed:
  - replaced direct `toas.toml` loads in CLI session-path + prompt config assembly via `config_from_discovered_paths(...)`
  - updated file-origin labels from `toas.toml` to `config_file` for runtime/source reporting
  - updated session command assembly source-map input to merge discovered config files in precedence order
- slice 3 landed:
  - `/config load` and `/config save` now default to `.toas/config.toml`
  - `/config show` quick-edit examples now prefer `./.toas/config.toml`
  - `/config set` persistence guidance now points to `.toas/config.toml` with `toas.toml` compatibility note
- slice 4 landed:
  - README updated to prefer `.toas/config.toml` examples and layered config wording
  - roadmap compressed-history wording updated to remove root-`toas.toml` assumption

## Remaining Follow-on (out of first pass)

- fully annotate config-source output with concrete discovered path identity (not just `config_file`)
- add optional command to print discovered config paths and effective precedence diagnostics
- evaluate switching `/config load` + `/config save` docs to include global-path examples (`~/.config/toas/config.toml`)
