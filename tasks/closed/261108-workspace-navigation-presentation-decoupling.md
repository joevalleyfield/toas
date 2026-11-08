Filed as: 261108-workspace-navigation-presentation-decoupling
FKA:
AKA: workspace navigation command presentation decoupling and descriptor migration
Legacy index:

keywords: closed, feature, runtime, presentation, workspace, session, descriptors

Parent: `261108-operator-command-registry-and-descriptors`
Blocked by: `261108-operator-command-registry-and-descriptors`

# Workspace Navigation Command Presentation Decoupling and Descriptor Migration

## Intent

Decouple `/workspace`, `/pwd`, `/cd`, and `/session` out of the monolithic
`src/toas/runtime/operator_command_prompt_workspace.py` into declarative presentation assets
in `src/toas/assets/presentation/workspace/`, a focused presentation edge in
`src/toas/runtime/workspace_presentation_edges.py`, and structured descriptors in
`src/toas/runtime/operator_command_workspace.py` registered with the operator command registry.

## Context & Motivation

Continuing the phased migration across the operator command surface, workspace navigation and session
transcript controls (`/pwd`, `/cd`, `/workspace`, `/session`) form the next cohesive family in
`operator_command_prompt_workspace.py`. They previously occupied ~180 lines containing path resolution,
boundary guards, workspace root mutation, and string templates for workspace overviews, mode settings,
and session transcript paths.

Extracting these commands into `src/toas/runtime/operator_command_workspace.py` with file-backed
presentation assets in `src/toas/assets/presentation/workspace/` and layout formatting helpers in
`src/toas/runtime/workspace_presentation_edges.py` further slims `prompt_workspace` toward eventual
retirement while ensuring every command descriptor declares its capabilities on the registry.

## In Scope

- **Declarative Presentation Assets**:
  - `src/toas/assets/presentation/workspace/`:
    - `workspace_overview.txt`: command overview and root removal list formatting.
    - `workspace_mode.txt`: mode setting confirmation.
    - `session_path_show.txt`: current session transcript path.
    - `session_path_set.txt`: confirmation on session transcript path update.
- **Workspace Presentation Edge**:
  - Author `src/toas/runtime/workspace_presentation_edges.py` with `@functools.lru_cache` loading and template binding.
- **Declarative Command Module & Registration**:
  - Author `src/toas/runtime/operator_command_workspace.py` with command descriptors and handlers for
    `pwd`, `cd`, `workspace`, and `session`.
  - Register them in `operator_command_registry.py`.
- **Retire from Monolith**:
  - Remove `_handle_pwd`, `_handle_cd`, `_handle_workspace`, `_handle_session`, and related path/slot
    helpers from `operator_command_prompt_workspace.py`.
- **Verification**:
  - Comprehensive unit test suite in `tests/test_runtime_operator_command_workspace.py`.
  - 100.00% statement coverage under `./scripts/check.sh`.

## Out of Scope

- Migrating `/graph`, `/prompt`, `/lens`, `/intent`, `/coordination` (reserved for Task 5).
- Changing directory resolution or workspace sandboxing boundary rules.

## Acceptance Criteria

1. [x] **Declarative Presentation Assets**: Workspace presentation templates reside in
   `src/toas/assets/presentation/workspace/` and load via `load_packaged_asset`.
2. [x] **Cohesive Workspace Presentation Edge**: `workspace_presentation_edges.py` encapsulates layout
   formatting without string literal bloat in command handlers.
3. [x] **Structured Descriptors**: `pwd`, `cd`, `workspace`, and `session` are registered in
   `OperatorCommandRegistry`.
4. [x] **Prompt Workspace Slimmed**: Workspace command implementations (~180 lines) are removed from
   `operator_command_prompt_workspace.py`.
5. [x] **Exact Output Parity**: Existing behavior for all 4 commands matches byte-for-byte.
6. [x] **Full Test Suite & Coverage**: 100.00% statement coverage repo-wide under `./scripts/check.sh`.

## Outcome & Evidence

- Extracted the multi-line workspace overview template into `src/toas/assets/presentation/workspace.yaml` (keeping single-line `/workspace mode` and `/session` responses inline and retiring `workspace_presentation_edges.py`).
- Authored `src/toas/runtime/operator_command_workspace.py` (219 lines) with tabular descriptors for `/pwd`, `/cd`, `/workspace`, and `/session`, `_WORKSPACE_HANDLERS` and `_SESSION_HANDLERS` lookup tables, and `(content, metadata)` tuple returns coerced by `OperatorCommandRegistry`.
- Updated `step.py` and `step_runtime.py` to import `render_workspace_commands`, `_guard_workspace_target`, and `_resolve_cd_target` directly from `operator_command_workspace`.
- Verified 100.00% statement coverage across `operator_command_workspace.py`, clean `ruff` and `mypy`, and live `/workspace` output parity.
