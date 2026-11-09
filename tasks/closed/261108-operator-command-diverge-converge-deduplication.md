Filed as: 261108-operator-command-diverge-converge-deduplication
FKA:
AKA: operator command diverge-converge deduplication
Legacy index:

keywords: closed, refactor, runtime, operator, commands, deduplication, diverge-converge

Parent: `261108-operator-command-registry-and-descriptors`

# Operator Command Diverge-Converge Deduplication

## Intent

Eliminate repeated result-node instantiation and duplicated branch pipelines across operator command handlers (`operator_command_transcript.py`, `operator_command_config_help.py`, `operator_command_replay.py`, `operator_command_lens.py`, `operator_command_intent.py`) and skill command dispatch (`skills/runtime.py`) by diverging only on command-specific parameters and converging on single execution/instantiation paths.

## Context & Motivation

Following the operator command registry and domain decomposition in `261108-operator-command-registry-and-descriptors`, four structural hotspots still exhibited repeated boilerplate and inside-branch instantiation instead of converging after parameter divergence:
1. `handle_compact_command` and `handle_concept_graph_command` in `src/toas/runtime/operator_command_transcript.py` duplicated the entire LLM generation, response validation, error handling, and update-payload construction pipeline.
2. `_config_target_result` in `src/toas/runtime/operator_command_config_help.py` duplicated `set`, `show`, and `add` target branches across positional and subcommand forms, and `_config_*_result` helpers still manually wrapped return values in `[_result_node(...)]` 25+ times instead of converging on a single result-node coercion point.
3. `_handle_extract_salvage` and `_handle_extract_coalesce` in `src/toas/runtime/operator_command_replay.py` duplicated the 20-line YAML source extraction, bounds checking, list rendering, and adopted-node construction skeleton.
4. `_parse_lens_set_args` (`operator_command_lens.py`), `_parse_intent_set_args` (`operator_command_intent.py`), and `handle_skills_commands` (`skills/runtime.py`) repeated per-branch bounds checks/advances and 11 separate `make_result_node` instantiations.

## In Scope

- [x] Converge `handle_compact_command` and `handle_concept_graph_command` in `src/toas/runtime/operator_command_transcript.py` on a shared generation/update pipeline and single result-node construction path.
- [x] Converge positional and subcommand `set`, `show`, and `add` branches in `_config_target_result` and replace manual `[_result_node(...)]` wrapping across `_handle_config_command` helpers in `src/toas/runtime/operator_command_config_help.py` with `str` and `(content, metadata)` returns coerced at a single converge point.
- [x] Converge `_handle_extract_salvage` and `_handle_extract_coalesce` in `src/toas/runtime/operator_command_replay.py` onto a shared extraction/selection helper.
- [x] Converge flag-parsing loops in `src/toas/runtime/operator_command_lens.py` and `src/toas/runtime/operator_command_intent.py` so bounds checking and index advancement occur once per iteration.
- [x] Converge `handle_skills_commands` in `src/toas/skills/runtime.py` onto a single `make_result_node` instantiation and shared `_run_specialize` helper.

## Out of Scope

- Changing command syntax, error messages, or transcript output formats.

## Acceptance Criteria

1. [x] All targeted branch pipelines converge on single instantiation/execution paths after diverging on parameters.
2. [x] 100.00% statement coverage maintained across all modified modules with zero `ruff` or `mypy` issues.
3. [x] End-to-end operator output parity verified across `/compact`, `/concept-graph`, `/config`, `/extract`, `/lens`, `/intent`, and `/skill`.

## Outcome & Evidence

- `src/toas/runtime/operator_command_transcript.py`: Extracted `_run_transcript_generation(...)` shared by `handle_compact_command` and `handle_concept_graph_command`, and unified `handle_abridge_command` empty-edit branches.
- `src/toas/runtime/operator_command_config_help.py`: Extracted `_apply_target_set(...)`, converged target `show` and `add` branches, and replaced 25 manual `[_result_node(...)]` list-wrappings across `_config_*_result` helpers with `str` and `(content, fields)` returns coerced once at the end of `_handle_config_command`.
- `src/toas/runtime/operator_command_replay.py`: Extracted `_handle_extract_yaml_source(...)` shared by `_handle_extract_salvage` and `_handle_extract_coalesce`.
- `src/toas/runtime/operator_command_lens.py` & `src/toas/runtime/operator_command_intent.py`: Consolidated per-flag bounds checking and index advancement in `_parse_lens_set_args` and `_parse_intent_set_args`.
- `src/toas/skills/runtime.py`: Extracted `_run_specialize(...)` and collapsed 11 `make_result_node` calls in `handle_skills_commands` into a single converge return (-84 net lines).
- `AGENTS.md`: Codified anti-ceremony structural guidelines (no pass-through middlemen, diverge-on-data/converge-on-instantiation, tabular declarations, testing public seams, replacing rather than accumulating on refactors) and `Reading the 100% Coverage Signal`.
- Verified 100.00% statement coverage across all 6 modules (`1,629` statements, `0` missed, `510 passed`), clean `ruff` and `mypy`, and end-to-end command output inspection.
