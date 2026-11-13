Filed as: 261109-runtime-spill-policy-binding
FKA:
AKA: runtime spill policy binding; connect spill config to execution; active spill policy context; session spill threshold ignored
Legacy index:

keywords: historical, bugfix, runtime, config, spill, tools, rendering

Related: `261106-content-spillage-refinement`; `261109-portable-spill-scratch-paths`

# Runtime Spill Policy Configuration Binding

## Intent

Bind `operator_config.spill` to the active runtime execution context during `toas step` and tool execution so session and file overrides (`spill.threshold_lines`, `spill.preview_lines`, `spill.default_mode`, etc.) take effect rather than unconditionally falling back to hardcoded defaults.

## Implementation

The runtime binds the effective spill policy while resolving frontier
consequences, with a fresh binding for each ordered user intent so later
commands see live config updates. STATE pending tool calls use the policy
resolved for their lineage. Renderers resolve omitted preview sizes from
the active policy while retaining explicit previews, named spill profiles,
and the existing bounded-read and safety limits.

Skill activation output is covered by the separate inline exemption
`261111-skill-output-spill-exemption`. The policy regression uses
`read_file` discovery output.

## Completion evidence

An ordered user command batch sets an 80-line threshold and a 65-line
preview, then replays two reads. The 60-line result appears inline and the
100-line result spills with lines 1–65 in the preview. The STATE pending
tool regression applies workspace file configuration.

A local `toas step` persisted both `/config set` overrides and applied
them to the next step's reads. A real stdio host step produced the same
projection from equivalent workspace file settings.

The full project suite passed 4,071 tests with nine skips and 100%
statement coverage. All 17 acceptance tests, Ruff, and mypy passed.
