# Unify State Templates And Retire State-Seed

Filed as: 261006-unify-state-templates-and-retire-state-seed
FKA:
AKA: state template unification; deprecate state-seed; template-driven state seeding
Legacy index:
Parent: `260926-state-step-requirements`
Depends on: `261006-state-step-transcript-protocol-reference-and-overlay`
Related: `261006-state-step-tool-argument-guidance`

## Context

`toas state-seed` was introduced as an ad-hoc bootstrap command during the initial state-step experiment. It invokes a hardcoded Python `initial_state()` dictionary (`goal`, `progress`, `next_steps`, `notes`, etc.) and prints fixed YAML into the session file.

In contrast, conversation sessions initialize naturally from prompt and session templates (e.g. `session-start/templates/`). Now that state operating parameters and initial state shapes can be declared as protocol templates, state initialization no longer needs a bespoke CLI command or rigid Python state dictionaries. State sessions can be instantiated through the uniform template system.

## Objectives

1. Define state protocol assets/templates in the asset catalog (e.g., `swe_v1`, `triage_v1`) providing instructions, tool profiles, response schemas, and seed `state_template` shapes.
2. Replace hardcoded Python `initial_state()` dictionaries with template-driven state initialization, enabling domain-specific state shapes (e.g., lightweight triage vs. full SWE workboards).
3. Retire the bespoke `toas state-seed` CLI command, dispatch routes, and usage strings in favor of unified template instantiation into `session.md`.
4. Ensure seamless initialization ergonomics across CLI, editor, and automated drivers.
5. Maintain 100.00% statement test coverage across all test suites.

## Outcome

- Packaged state template assets defined under `src/toas/assets/state/`:
  - `swe_v1.yaml`: Full software engineering workboard with progress, next steps, artifacts, blockers, notes, and default protocol `toas.state-step/1`.
  - `triage_v1.yaml`: Lightweight triage/investigation workboard with status, summary, hypotheses, next actions, and protocol overlay scoping tools to `read_file` and `shell` with focused instructions.
- Implemented template-driven state initialization in `src/toas/runtime/state_step.py`:
  - Added `list_state_templates()` and `load_state_template(name_or_ref: str = "swe_v1") -> dict[str, Any]`.
  - Added `render_state_template(name: str = "swe_v1", *, format: str | None = None, observation: Any = None) -> str`.
  - Replaced hardcoded dictionary in `initial_state(template: str = "swe_v1")` to pull from the template catalog.
  - Updated `seed_state_turn()` to support `template` selection.
  - Enhanced `resolve_state_turn_protocol()` to resolve protocol definitions and overlays directly from catalog state templates.
- Unified prompt catalog integration in `src/toas/prompts.py`:
  - `load_prompt_asset()` and `load_prompt_ref()` dynamically handle `state/<template>` refs (e.g. `toas prompt state/swe_v1`, `toas prompt state/triage_v1`), outputting rendered state turns.
  - `list_prompt_assets()` lists state templates under the `state` namespace.
  - Top-level `/prompts` and `/prompt` command browsing exposes `/prompt state`.
- Retired `toas state-seed` CLI:
  - Removed `state-seed` command from CLI usage strings (`cli.py`, `cli_usage.py`).
  - Removed `state-seed` routing from `cli_dispatch.py` and `run_state_seed` from `DispatchDeps`.
  - Removed `run_state_seed` implementations from `cli.py` and `cli_session_commands.py`.
  - Updated tests to verify `toas state-seed` is retired as an unknown command.
- Verified: All 3,480 unit/integration tests and 17 acceptance tests pass with 100.00% statement coverage across all 151 files.
