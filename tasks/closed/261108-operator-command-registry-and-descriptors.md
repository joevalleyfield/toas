Filed as: 261108-operator-command-registry-and-descriptors
FKA:
AKA: operator command registry and declarative descriptors
Legacy index:

keywords: closed, feature, runtime, architecture, operator, registry, descriptors, dispatch

Parent: `261106-operator-presentation-asset-decoupling`
Blocks: `261108-models-command-presentation-decoupling`; `261108-shell-execution-presentation-decoupling`; `261108-workspace-navigation-presentation-decoupling`; `261108-transcript-inspection-presentation-decoupling`; `261108-replay-extraction-presentation-decoupling`; `261108-workspace-presentation-overrides`

# Operator Command Registry and Declarative Descriptors

## Intent

Establish a declarative operator command registry (`src/toas/runtime/operator_command_registry.py`)
with structured command descriptors, automated result-node wrapping, and unified dispatch,
eliminating repetitive boilerplate across host command modules.

## Context & Motivation

Following the decoupling of configuration presentation assets in `261106-operator-presentation-asset-decoupling`,
a clear architectural seam emerged: operator commands in `src/toas/runtime/operator_command_*.py`
share extensive structural duplication:
1. Every command module defines an identical `_result_node` helper that calls `render_fenced_output`
   and `make_result_node`.
2. `execute_operator_command` walks five monolithic handler functions, each running cascading
   `if command == "...": return _handle_...` chains.
3. Every command manually parses `-h`/`--help` or argument bounds and formats its own usage string.

By establishing a declarative `OperatorCommandDescriptor` contract, commands declare their name,
aliases, summary, usage, and handler. The registry handles dispatch, automated `--help` interception,
and standard result-node wrapping, allowing domain command migrations to be clean, one-shot
extractions without boilerplate.

## In Scope

- **Command Descriptor Contract**:
  - Define `OperatorCommandDescriptor` in `src/toas/runtime/operator_command_registry.py`:
    - `name: str`
    - `aliases: tuple[str, ...]`
    - `summary: str`
    - `usage: str`
    - `category: str`
    - `handler: Callable[[list[str], OperatorCommandContext, Any], Any]`
- **Unified Dispatch & Wrapping**:
  - Implement registry lookup and dispatch.
  - Automate `-h` / `--help` interception returning standard usage view nodes.
  - Centralize `_result_node` construction (`render_fenced_output` with `command.<name>` source).
- **Proof-of-Concept Migration**:
  - Register `/config` through the new registry, verifying zero behavioral or visual regressions.
  - Wire `execute_operator_command` to dispatch registered commands with fallback to legacy chains.
- **Verification**:
  - Comprehensive unit tests in `tests/test_runtime_operator_command_registry.py`.
  - 100.00% statement coverage under `./scripts/check.sh`.

## Out of Scope

- Migrating `/models`, `/shell`, `/workspace`, or `/graph` in this initial task (reserved for
  dedicated blocked follow-ons).
- Modifying command syntax, CLI flags, or transcript wire contracts.

## Acceptance Criteria

1. [x] **Declarative Descriptor Contract**: `OperatorCommandDescriptor` is defined with type safety
   and ergonomic defaults.
2. [x] **Centralized Result Wrapping**: `make_result_node` and `render_fenced_output` wrapping are
   handled centrally by the registry via `build_command_result_node`.
3. [x] **Automated Help Interception**: Built-in `-h`/`--help` handling formats standard usage nodes
   without handler-level boilerplate.
4. [x] **Canonical Migration**: `/config` and `/help` dispatch cleanly through the registry with exact output
   parity.
5. [x] **Full Test Suite & Coverage**: 100.00% statement coverage across all new and touched files
   under `./scripts/check.sh` (4,039 passing tests).

## Outcome & Evidence

- Authored `src/toas/runtime/operator_command_registry.py`:
  - `OperatorCommandDescriptor` dataclass ordered `(name, summary, usage, category, handler, aliases, source, fenced, help_handler)` for compact 1-line tabular descriptor definitions.
  - `OperatorCommandRegistry` with `register`, `unregister`, `get`, `has_command`, `list_descriptors`, and `dispatch` (coercing `str`, `(content, metadata)` tuples, `dict`, and `list[dict]`).
  - `build_command_result_node` centralizing fenced view node generation (`potency="inert"`) and result packaging.
  - Unified built-in registration across all core slash commands (`config`, `help`, `run`, `stage`, `skills`, `skill`, `specialize`, `step`) and the 8 domain descriptor providers via a single provider tuple loop.
- Updated `src/toas/runtime/operator_commands.py`:
  - Dispatches all registered commands via `registry.dispatch(...)` with a single fallback to `handle_skills_commands(...)` for dynamic workspace skill aliases, removing legacy handler chains and special-case `/step` branching.
- Refactored `src/toas/runtime/operator_command_config_help.py`:
  - Replaced cascading `/config` and `/help` `if/elif` chains with `_CONFIG_SUBCOMMANDS` and `_HELP_STATIC_TOPICS` lookup tables, and removed substring-sniffing from `_result_node`.
- Authored test suite in `tests/test_runtime_operator_command_registry.py` and expanded `tests/test_runtime_operator_commands.py`.
- Verified 100.00% statement coverage, clean `ruff` and `mypy`, and end-to-end operator perspective output for `/config`, `/help`, `/help config`, and `/step`.
