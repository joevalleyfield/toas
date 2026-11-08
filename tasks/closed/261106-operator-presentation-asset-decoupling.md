Filed as: 261106-operator-presentation-asset-decoupling
FKA: 261106-microkernel-skill-runtime-boundary
AKA: operator presentation decoupling; file-backed presentation assets; config presentation edge; runtime presentation extraction
Legacy index:

keywords: runtime, architecture, presentation, assets, config, closed

Parent: `261106-standard-agent-skills-integration`
Related: `261106-skill-specialization-and-script-distillation`; `260829-authority-capability-policy-matrix`

# Operator Presentation Asset Decoupling and Config Presentation Edge

## Intent

Decouple bulky text formatting, ASCII layouts, and terminal summaries out of
`src/toas/runtime/operator_command_config_help.py` into declarative, file-backed
resource assets in `src/toas/assets/presentation/config/`, mapped through a
focused presentation edge (`src/toas/runtime/config_presentation_edges.py`).

## Context & Motivation

The original draft of this task (`261106-microkernel-skill-runtime-boundary`)
explored moving operator commands like `/model` and `/config` into external
workspace skills. Analysis established that host steering commands must remain
in the host control plane to prevent authority leaks (e.g., untrusted repository
skills shadowing `/model` to steal API keys or hijack endpoints) and to preserve
sub-3ms warm execution latency.

However, `src/toas/runtime/operator_command_*.py` remains heavily congested
(~150KB) because hundreds of lines of raw ASCII templates, table borders, and
prose strings are hardcoded directly inside Python command functions. This violates
the `Projection And Rendering` boundary defined in `docs/runtime-ownership.md`.

TOAS already possesses a mature packaged asset loader (`src/toas/assets/loader.py`)
used for help, prompts, skills, and procedures. By establishing
`src/toas/assets/presentation/config/`, text layouts become declarative,
inspectable, and editable independently of executable Python code, while Python
modules shrink to concise state-extraction logic.

## In Scope

- **Packaged Presentation Assets**:
  - Establish `src/toas/assets/presentation/config/` for file-backed text templates:
    - `overview.txt`: effective configuration tree.
    - `models_overview.txt`: endpoints, targets, and models summary.
    - `execution_overview.txt`: generation, extraction, and backend modes.
    - `target_overview.txt`: detailed target parameters and overrides.
  - Template loading cached via `lru_cache` to ensure zero repeated disk I/O in
    warm runtimes.
- **Config Presentation Edge**:
  - Author `src/toas/runtime/config_presentation_edges.py` following the small,
    focused pattern of `stream_presentation_edges.py` and `presentation_edges.py`.
  - Bind structured configuration state into declarative asset templates.
- **Runtime Command Slimming**:
  - Refactor `operator_command_config_help.py` to delegate rendering to
    `config_presentation_edges.py`, removing hundreds of lines of hardcoded string
    literals.
- **Exact Output Parity**:
  - Preserve byte-for-byte fidelity with existing CLI and slash command outputs,
    verified by existing test suites.

## Out of Scope

- Packaging engine-steering commands as external workspace skills in `.agents/skills/`.
- Changing external CLI options, slash command names, or transcript syntax.
- Refactoring `operator_command_prompt_workspace.py` (reserved for a follow-on
  slice once the config presentation edge pattern is established).

## Acceptance Criteria

1. [x] **Declarative Presentation Assets**: Config overview and summary templates
   live in `src/toas/assets/presentation/config/` and are loaded via
   `load_packaged_asset`.
2. [x] **Cohesive Presentation Edge**: `config_presentation_edges.py` maps structured
   configuration state to template format strings without embedding raw ASCII
   layouts in Python code.
3. [x] **Runtime Bloat Reduced**: Multiline formatting literals in
   `operator_command_config_help.py` are eliminated (~270 lines of hardcoded presentation strings removed).
4. [x] **Zero Output Regressions**: All existing `/config` outputs match prior
   behavior byte-for-byte.
5. [x] **Full Test Suite & Coverage**: 100.00% statement coverage under
   `./scripts/check.sh` across all modified and new files (4,029 tests passing).

## Outcome & Evidence

- Created `src/toas/assets/presentation/config/` containing:
  - `overview.txt`
  - `models_overview.txt`
  - `execution_overview.txt`
  - `target_overview.txt`
- Authored `src/toas/runtime/config_presentation_edges.py` with `@functools.lru_cache` template loading and structured rendering functions (`render_config_overview`, `render_config_models_overview`, `render_config_execution_overview`, `render_config_target_overview`, `render_target_list_lines`).
- Evicted ~270 lines of ASCII layouts, format strings, and multiline prose from `src/toas/runtime/operator_command_config_help.py`.
- Authored unit test suite in `tests/test_runtime_config_presentation_edges.py` achieving 100.00% statement coverage.
- Verified `./scripts/check.sh`: all 4,029 unit and acceptance tests passed, 0 lint errors, 100.00% statement coverage across the entire codebase.
- Verified concrete operator outputs end-to-end with zero behavioral or visual regressions.
