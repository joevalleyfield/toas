Filed as: 261108-shell-execution-presentation-decoupling
FKA:
AKA: shell execution command presentation decoupling and descriptor migration
Legacy index:

keywords: closed, feature, runtime, presentation, shell, env, descriptors

Parent: `261108-operator-command-registry-and-descriptors`
Blocked by: `261108-operator-command-registry-and-descriptors`

# Shell Execution Command Presentation Decoupling and Descriptor Migration

## Intent

Decouple `/shell` and `/env` out of the monolithic
`src/toas/runtime/operator_command_prompt_workspace.py` into declarative presentation assets
in `src/toas/assets/presentation/shell/`, a focused presentation edge in
`src/toas/runtime/shell_presentation_edges.py`, and structured descriptors in
`src/toas/runtime/operator_command_shell.py` registered with the operator command registry.

## Context & Motivation

Following the migration of configuration/help and model commands, the execution and environment
commands (`/shell` and `/env`) formed the next cohesive slice in `operator_command_prompt_workspace.py`.
They contained ~210 lines of grant parsing, scope resolution, configuration baseline management,
and multiple embedded string templates for effective shell policy views, grant update notices,
and environment setting confirmations.

Extracting these commands into `src/toas/runtime/operator_command_shell.py` with file-backed
presentation assets in `src/toas/assets/presentation/shell/` and presentation rendering helpers in
`src/toas/runtime/shell_presentation_edges.py` continues the phased retirement of the monolithic
`prompt_workspace` handler while establishing declarative descriptors on the `OperatorCommandRegistry`.

## In Scope

- **Declarative Presentation Assets**:
  - `src/toas/assets/presentation/shell/`:
    - `env_help.txt`: usage overview for `/env`.
    - `env_set.txt`: confirmation message on env key set.
    - `env_unset.txt`: confirmation message on env key unset.
    - `shell_config_grants.txt`: list of configured shell grants.
    - `shell_config_updated.txt`: notification on config shell grants update.
    - `shell_config_reset.txt`: notification on config shell grants reset to defaults.
    - `shell_grants_updated.txt`: notification on runtime shell grants update with pluralization and effective list.
    - `shell_grants_reset.txt`: notification on runtime shell grants reset.
    - `shell_policy_view.txt`: comprehensive shell policy view including effective grants with sources, baseline, transcript lane, modifiers, forms, and scope precedence.
- **Shell Presentation Edge**:
  - Author `src/toas/runtime/shell_presentation_edges.py` with `@functools.lru_cache` loading and template binding.
- **Declarative Command Module & Registration**:
  - Author `src/toas/runtime/operator_command_shell.py` with command descriptors and handlers for
    `shell` and `env`.
  - Register them in `operator_command_registry.py`.
- **Retire from Monolith**:
  - Remove `_handle_env`, `_handle_shell`, `_handle_shell_config`, and related shell grant helpers
    from `operator_command_prompt_workspace.py`.
- **Verification**:
  - Comprehensive unit test suite in `tests/test_runtime_operator_command_shell.py`.
  - 100.00% statement coverage under `./scripts/check.sh`.

## Out of Scope

- Migrating `/workspace`, `/pwd`, `/cd`, `/session`, or `/graph` (reserved for subsequent tasks in the series).
- Changing shell grant parsing, scoping precedence, or execution policy semantics.

## Acceptance Criteria

1. [x] **Declarative Presentation Assets**: Shell presentation templates reside in
   `src/toas/assets/presentation/shell/` and load via `load_packaged_asset`.
2. [x] **Cohesive Shell Presentation Edge**: `shell_presentation_edges.py` encapsulates layout
   formatting without string literal bloat in command handlers.
3. [x] **Structured Descriptors**: `shell` and `env` are registered in `OperatorCommandRegistry`.
4. [x] **Prompt Workspace Slimmed**: Shell command implementations (~210 lines) are removed from
   `operator_command_prompt_workspace.py`.
5. [x] **Exact Output Parity**: Existing behavior for both commands matches byte-for-byte.
6. [x] **Full Test Suite & Coverage**: 100.00% statement coverage repo-wide under `./scripts/check.sh`.

## Outcome & Evidence

- Consolidated multi-line shell and environment presentation templates into `src/toas/assets/presentation/shell.yaml` rendered directly via 1-line `render_template("shell", ...)` calls (retiring `shell_presentation_edges.py` while keeping trivial 1-line confirmations inline).
- Authored `src/toas/runtime/operator_command_shell.py` (239 lines) with tabular descriptors for `/shell` and `/env`, replacing subcommand `if/elif` chains with `_SHELL_DISPATCH` and `_SHELL_CONFIG_HANDLERS` lookup tables and returning `(content, metadata)` tuples for registry coercion.
- Re-exported `render_shell_policy_view` from `step.py` via `operator_command_shell.py` and evicted legacy shell/env handlers from `operator_command_prompt_workspace.py`.
- Verified 100.00% statement coverage across `operator_command_shell.py`, clean `ruff` and `mypy`, and live `/shell list` output parity.
