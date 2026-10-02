Filed as: 260928-state-step-instruction-seed
FKA:
AKA: state-seed instructions; state-step instruction fidelity
Legacy index:

keywords: runtime, implementation, historical, transcript, instructions, fidelity

Parent: `260926-state-step-requirements`
Related: `260927-state-step-history-projections`; `260927-state-step-alpha-loop`

# Carry State-Step Instructions In The Seed Transcript

## Intent

Make the complete state-step instructions visible and editable in the
operator-controlled seed transcript, then send that text through the inference
request without runtime summarization or reconstruction.

## Scope

- Render the complete instruction text in `toas state-seed` output.
- Parse it from the current state turn and use that exact string in preview and
  inference packets.
- Preserve it on newly appended state turns and after tool execution.
- Keep response shape and live tool advertisement as distinct packet fields.
- Continue accepting older typed state turns that have no instructions by
  using the current default instructions.

## Acceptance Criteria

- A fresh seed shows the full instructions as editable YAML.
- Editing the instruction text changes the request packet exactly as authored.
- Preview and inference use identical instruction text.
- Inference progression and tool-outcome updates retain the instruction text.
- Older transcripts without the field remain usable.

## Progress

- 2026-09-28: Implemented instruction rendering in the state seed, faithful
  propagation through preview and inference, and carry-forward across accepted
  state and tool-outcome transcript updates. Documented the request projection.
- **Evidence & Closure (2026-10-02)**:
  - Landed in commit `42b4b093949b` (`feat(state-step): carry instructions in seed transcript`).
  - Threaded `instructions` through `seed_state_turn`, `render_state_turn`, `build_state_step_packet`, `preview_state_request`, and `step_state_transition` in `src/toas/runtime/state_step.py`.
  - Verified by `tests/test_state_step.py::test_seed_state_turn_carries_default_instructions`, `tests/test_state_step.py::test_preview_state_request_uses_custom_instructions_from_turn`, and `tests/test_state_step.py::test_step_state_transition_preserves_custom_instructions_on_output`.

Status: Complete.
