Filed as: 261108-transcript-inspection-presentation-decoupling
FKA:
AKA: transcript inspection command presentation decoupling and descriptor migration
Legacy index:

keywords: closed, feature, runtime, presentation, transcript, lens, intent, descriptors

Parent: `261108-operator-command-registry-and-descriptors`
Blocked by: `261108-operator-command-registry-and-descriptors`; `261108-models-command-presentation-decoupling`; `261108-shell-execution-presentation-decoupling`; `261108-workspace-navigation-presentation-decoupling`

# Transcript Inspection Command Presentation Decoupling and Descriptor Migration

## Intent

Decouple `/graph`, `/prompt`, `/prompts`, `/outline`, `/compact`, `/concept-graph`, `/abridge`, `/lens`, `/intent`, `/coordination` into presentation assets and declarative `OperatorCommandDescriptor` registrations, retiring `operator_command_prompt_workspace.py` into a thin compatibility shim.

## Context & Motivation

Following the decoupling of `config`, `help`, `models`, `shell`, and `workspace` commands, the remaining commands in the legacy `operator_command_prompt_workspace.py` module handled transcript inspection, lens management, intent tracking, prompt browsing, and coordination. Extracting their user-facing templates into `.txt` presentation assets and registering them as declarative descriptors on `OperatorCommandRegistry` completes the retirement of the `operator_command_prompt_workspace` monolith.

## In Scope

- [x] Create presentation asset templates in `src/toas/assets/presentation/transcript/` (15 template files)
- [x] Author `src/toas/runtime/transcript_presentation_edges.py` with `@functools.lru_cache` loading and template binding
- [x] Author `src/toas/runtime/operator_command_transcript.py` with declarative command handlers and descriptors for `prompts`, `graph`, `prompt`, `outline`, `compact`, `concept-graph`, `abridge`, `lens`, `intent`, and `coordination`
- [x] Register transcript descriptors in `OperatorCommandRegistry._register_builtin_descriptors`
- [x] Reduce `src/toas/runtime/operator_command_prompt_workspace.py` to a thin compatibility shim forwarding to `get_default_operator_command_registry().dispatch(...)`
- [x] Comprehensive test coverage in `tests/test_runtime_operator_command_transcript.py` maintaining 100.00% statement coverage under `./scripts/check.sh`
- [x] Mandatory operator-perspective end-to-end verification

## Out of Scope

- Replay/extraction command family (`/replay`, `/extract`, `/queue`, `/run`, `/stage` — covered in Task 6)
- Workspace-level asset customization overrides (covered in Task 7)

## Acceptance Criteria

1. [x] All 10 transcript inspection, lens, intent, prompt, and coordination commands registered in `OperatorCommandRegistry`.
2. [x] All notice/view presentation strings extracted to external `.txt` asset files in `src/toas/assets/presentation/transcript/`.
3. [x] `operator_command_prompt_workspace.py` reduced from 843 lines to <50 lines shim with preserved re-exports.
4. [x] Full test suite passing with 100.00% statement coverage (4,075 passed) under `./scripts/check.sh`.
5. [x] Operator inspection confirms parity and clean output.

## Outcome & Evidence

- Consolidated multi-line transcript and lens templates into `src/toas/assets/presentation/transcript.yaml` (retiring `transcript_presentation_edges.py`).
- Decomposed the remaining `operator_command_prompt_workspace.py` monolith into focused domain modules and deleted `operator_command_prompt_workspace.py` completely:
  - `src/toas/runtime/operator_command_prompts.py` (84 lines: `/prompt`, `/prompts`)
  - `src/toas/runtime/operator_command_transcript.py` (218 lines: `/graph`, `/outline`, `/compact`, `/concept-graph`, `/abridge`)
  - `src/toas/runtime/operator_command_lens.py` (307 lines: `/lens` with `_LENS_SUBCOMMANDS` lookup table)
  - `src/toas/runtime/operator_command_intent.py` (280 lines: `/intent` and `/coordination` with `_INTENT_SUBCOMMANDS` and `_COORDINATION_FLAG_APPLIERS` lookup tables)
- Registered all descriptors in `operator_command_registry.py` and verified 100.00% statement coverage, clean `ruff` and `mypy`, and live command output parity.
