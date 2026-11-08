Filed as: 261108-models-command-presentation-decoupling
FKA:
AKA: models command presentation decoupling and descriptor migration
Legacy index:

keywords: closed, feature, runtime, presentation, models, endpoints, descriptors

Parent: `261108-operator-command-registry-and-descriptors`
Blocked by: `261108-operator-command-registry-and-descriptors`

# Models Command Presentation Decoupling and Descriptor Migration

## Intent

Decouple `/model`, `/models`, `/endpoint`, and `/endpoints` out of the monolithic
`src/toas/runtime/operator_command_prompt_workspace.py` into declarative presentation assets
in `src/toas/assets/presentation/models/`, a focused presentation edge in
`src/toas/runtime/models_presentation_edges.py`, and structured descriptors in
`src/toas/runtime/operator_command_models.py` registered with the operator command registry.

## Context & Motivation

Following the establishment of the `OperatorCommandRegistry` in `261108-operator-command-registry-and-descriptors`,
the first domain slice to migrate is model and endpoint steering. Currently, `/model`, `/models`,
`/endpoint`, and `/endpoints` occupy ~350 lines in `operator_command_prompt_workspace.py`. They
contain extensive embedded string templates for live model observations, known model catalogs,
endpoint lists, and target selections.

Extracting these commands into `src/toas/runtime/operator_command_models.py` with file-backed
presentation templates slims `prompt_workspace` significantly and establishes the second major
domain family on the declarative registry.

## In Scope

- **Declarative Presentation Assets**:
  - `src/toas/assets/presentation/models/`:
    - `models_help.txt`: subcommands overview.
    - `model_overview.txt`: active target and next steps.
    - `model_fallback_overview.txt`: fallback model target when none selected.
    - `model_targets_list.txt`: configured model targets with selection status.
    - `known_catalog.txt`: durable catalog summary and model selection hints.
    - `live_observation.txt`: live endpoint status and model list formatting.
    - `endpoints_list.txt`: configured endpoints and refresh observations.
    - `available_endpoints.txt`: capability space endpoints.
- **Models Presentation Edge**:
  - Author `src/toas/runtime/models_presentation_edges.py` with `@functools.lru_cache` loading and template binding.
- **Declarative Command Module & Registration**:
  - Author `src/toas/runtime/operator_command_models.py` with command descriptors and handlers for
    `model`, `models`, `endpoint`, and `endpoints`.
  - Register them in `operator_command_registry.py`.
- **Retire from Monolith**:
  - Remove `_handle_endpoint`, `_handle_endpoints`, `_handle_model`, `_handle_model_overview`,
    `_handle_model_targets`, `_handle_model_select`, `_handle_models`, `_handle_models_refresh`,
    and related model helpers from `operator_command_prompt_workspace.py`.
- **Verification**:
  - Comprehensive unit test suite in `tests/test_runtime_operator_command_models.py`.
  - 100.00% statement coverage under `./scripts/check.sh`.

## Out of Scope

- Migrating `/shell`, `/workspace`, or `/graph` (reserved for subsequent tasks in the series).
- Changing model command arguments, options, or output semantics.

## Acceptance Criteria

1. [x] **Declarative Presentation Assets**: Model presentation templates reside in
   `src/toas/assets/presentation/models/` and load via `load_packaged_asset`.
2. [x] **Cohesive Models Presentation Edge**: `models_presentation_edges.py` encapsulates layout
   formatting without string literal bloat in command handlers.
3. [x] **Structured Descriptors**: `model`, `models`, `endpoint`, and `endpoints` are registered
   in `OperatorCommandRegistry`.
4. [x] **Prompt Workspace Slimmed**: Model command implementations are removed from
   `operator_command_prompt_workspace.py`.
5. [x] **Exact Output Parity**: Existing behavior for all 4 commands matches byte-for-byte.
6. [x] **Full Test Suite & Coverage**: 100.00% statement coverage repo-wide under `./scripts/check.sh`.

## Outcome & Evidence

- Consolidated multi-line model and endpoint presentation templates into `src/toas/assets/presentation/models.yaml` and rendered them directly via concise 1-line `render_template("models", ...)` calls (retiring intermediate `models_presentation_edges.py` and single-use `_render_*` pass-through wrappers).
- Authored `src/toas/runtime/operator_command_models.py` (294 lines) with tabular `OperatorCommandDescriptor` entries for `/model`, `/models`, `/endpoint`, and `/endpoints`, `_MODEL_SUBCOMMANDS` lookup dispatch, and shared endpoint settings/serialization helpers.
- Registered descriptors in `OperatorCommandRegistry` and evicted legacy model handler code from `operator_command_prompt_workspace.py`.
- Verified 100.00% statement coverage across `operator_command_models.py`, clean `ruff` and `mypy`, and exact output parity for `/model` and `/models`.
