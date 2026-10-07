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
