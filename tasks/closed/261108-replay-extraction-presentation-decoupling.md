Filed as: 261108-replay-extraction-presentation-decoupling
FKA:
AKA: replay and extraction command presentation decoupling
Legacy index:

keywords: closed, feature, runtime, presentation, replay, extract, queue, heal, descriptors

Parent: `261108-operator-command-registry-and-descriptors`
Blocked by: `261108-operator-command-registry-and-descriptors`

# Replay and Extraction Command Presentation Decoupling

## Intent

Decouple `/replay`, `/extract`, `/queue`, and `/heal` commands into declarative presentation assets (`.txt`), author focused presentation edges in `src/toas/runtime/replay_presentation_edges.py`, and register declarative `OperatorCommandDescriptor`s on `OperatorCommandRegistry`, retiring `operator_command_extract_replay.py` into a thin compatibility shim.

## Context & Motivation

Following the decoupling of config, help, models, shell, workspace, and transcript inspection commands, the remaining monolith handling slash commands was `operator_command_extract_replay.py` (which handled `/extract`, `/replay`, `/queue`, and `/heal`). Decomposing these commands into presentation assets and registering them on the command registry completes the migration of all builtin slash commands to the unified `OperatorCommandRegistry`.

## In Scope

- [x] Create presentation asset templates in `src/toas/assets/presentation/replay/` (11 templates for candidate lists, headers, footers, dry-run previews, and queue lifecycle notices)
- [x] Author `src/toas/runtime/replay_presentation_edges.py` with `@functools.lru_cache` loading and template binding
- [x] Author `src/toas/runtime/operator_command_replay.py` with declarative command handlers and descriptors for `extract`, `replay`, `queue`, and `heal`
- [x] Register replay descriptors in `OperatorCommandRegistry._register_builtin_descriptors`
- [x] Reduce `src/toas/runtime/operator_command_extract_replay.py` to a thin compatibility shim forwarding to `get_default_operator_command_registry().dispatch(...)`
- [x] Author comprehensive unit tests in `tests/test_runtime_operator_command_replay.py` maintaining 100.00% statement coverage under `./scripts/check.sh`
- [x] Mandatory operator-perspective end-to-end verification

## Out of Scope

- Workspace-level presentation overrides (covered in Task 7)

## Acceptance Criteria

1. [x] All 4 replay/extraction/queue/heal commands registered in `OperatorCommandRegistry`.
2. [x] All notice/view presentation strings extracted to external `.txt` asset files in `src/toas/assets/presentation/replay/`.
3. [x] `operator_command_extract_replay.py` reduced from 824 lines to <80 lines shim with preserved re-exports.
4. [x] Full test suite passing with 100.00% statement coverage (4,081 passed) under `./scripts/check.sh`.
5. [x] Operator inspection confirms parity and clean output.

## Outcome & Evidence

- Consolidated multi-line replay, extraction, and queue templates into `src/toas/assets/presentation/replay.yaml` rendered via 1-line `render_template("replay", ...)` calls (retiring `replay_presentation_edges.py`).
- Replaced `src/toas/runtime/operator_command_extract_replay.py` with `src/toas/runtime/operator_command_replay.py` and registered `get_replay_command_descriptors()` (`extract`, `replay`, `queue`, `heal`) in `operator_command_registry.py`.
- Replaced content substring-sniffing in `_result_node` with explicit `source` metadata (`command.extract`, `command.queue`, `command.replay`).
- Verified 100.00% statement coverage across `operator_command_replay.py`, clean `ruff` and `mypy`, and live `/extract` and `/replay` output parity.
