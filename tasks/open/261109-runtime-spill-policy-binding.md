Filed as: 261109-runtime-spill-policy-binding
FKA:
AKA: runtime spill policy binding; connect spill config to execution; active spill policy context; session spill threshold ignored
Legacy index:

keywords: active, bugfix, runtime, config, spill, tools, rendering

Related: `261106-content-spillage-refinement`; `261109-portable-spill-scratch-paths`

# Runtime Spill Policy Configuration Binding

## Intent

Bind `operator_config.spill` to the active runtime execution context during `toas step` and tool execution so session and file overrides (`spill.threshold_lines`, `spill.preview_lines`, `spill.default_mode`, etc.) take effect rather than unconditionally falling back to hardcoded defaults.

## Context & Motivation

When an operator configures spill settings (e.g. `/config set spill.threshold_lines 80` and `/config set spill.preview_lines 80`), the settings are stored in `operator_config.spill` and reported as active session overrides.

However, `get_active_spill_policy()` in `src/toas/tools_cluster/rendering.py` reads from `_ACTIVE_SPILL_POLICY` (a `ContextVar`), which is never entered during step execution or tool result rendering.

Consequently, every call to `shape_result_content()` falls back to a fresh default `SpillPolicy()` with `threshold_lines=40` and `preview_lines=30`. A 50-line tool or skill output spills at 40 lines and displays only 30 preview lines regardless of configured overrides.

## In Scope

- [ ] Enter `active_spill_policy(config.spill)` during `toas step` execution in `src/toas/step.py` and around tool execution in `src/toas/tools.py`.
- [ ] Ensure `shape_result_content` and `shape_tool_result_content` respect the active spill policy context.
- [ ] Ensure session config overrides (`/config set spill.*`) propagate dynamically to tool outputs within the same session.
- [ ] Add unit and integration tests covering runtime spill policy propagation through `/config` and `toas step` while maintaining 100.00% statement coverage.

## Out of Scope

- Modifying `SpillPolicy` dataclass defaults or safety ceiling limits.

## Acceptance Criteria

1. Setting `/config set spill.threshold_lines 80` prevents tool/skill outputs under 80 lines from spilling.
2. Setting `/config set spill.preview_lines 80` renders up to 80 preview lines when output exceeds threshold.
3. Unit and integration tests pass with 100.00% statement coverage on modified modules.
