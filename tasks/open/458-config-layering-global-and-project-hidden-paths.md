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
