## Goal

Add a `GenerationPolicy` section to `OperatorConfig` covering the two live `BackendGenerationPolicy` fields, derive the policy object from config rather than hardcoding it, and surface the knobs through `/config`.

## Why Now

`extra_body` (thinking mode) and `avoid_terms` are currently hardcoded in `default_backend_policy()` and invisible to the operator. With `OperatorConfig` in place, these can be user-facing config knobs without any architectural lift.

## Scope

- add `GenerationPolicy` dataclass to `config.py` with:
  - `thinking_mode: str` — `"disabled"` | `"enabled"`, default `"disabled"` (matches current hardcoded behavior)
  - `avoid_terms: tuple[str, ...]` — default matches current hardcoded tuple
- add `generation: GenerationPolicy` field to `OperatorConfig`
- update flatten/unflatten and `parse_config_value` to cover the new section
  - `avoid_terms` is a comma-separated string at the `/config set` boundary; stored as a list in config
- add `generation_policy_from_config(config: OperatorConfig) -> BackendGenerationPolicy` in `backend_policy.py`
  - derives `extra_body` from `thinking_mode` (`"disabled"` → `NO_THINKING`, `"enabled"` → `None`)
  - passes `avoid_terms` through
  - keeps the remaining `BackendGenerationPolicy` fields at their current defaults for now (addressed in `262`)
- update `cli.py` to derive policy from `operator_config` rather than calling `default_backend_policy()` directly
- update `capability_prompts.py` — `render_capability_overview` currently calls `default_backend_policy()` internally; add a `policy` parameter and update callers to pass the derived policy
- tests covering:
  - `GenerationPolicy` defaults match current hardcoded values
  - `thinking_mode = "enabled"` produces `extra_body = None`
  - `avoid_terms` round-trips through `/config set` (comma-separated parse)
  - `generation_policy_from_config` derivation
  - `render_capability_overview` reflects config-derived `avoid_terms`

## Constraints

- default `OperatorConfig()` must produce a `BackendGenerationPolicy` identical to current `default_backend_policy()` output
- `avoid_terms` parse at the `/config set` boundary must be unambiguous; comma-separated is sufficient for current values
- no behavioral change at default config values

## Done When

- `GenerationPolicy` is in `OperatorConfig` and wired end-to-end
- `/config show` lists `generation.thinking_mode` and `generation.avoid_terms`
- `cli.py` derives policy from config
- `capability_prompts.py` accepts injected policy
- all tests pass
