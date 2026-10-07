# State-Step Transcript Protocol Reference And Overlay

Filed as: 261006-state-step-transcript-protocol-reference-and-overlay
FKA:
AKA: state step protocol reference; transcript protocol overlay; state protocol handles
Legacy index:
Parent: `260926-state-step-requirements`
Related: `260825-visible-transcript-turn-ids`; `261006-state-step-tool-argument-guidance`; `261006-unify-state-templates-and-retire-state-seed`

## Context

State-step currently treats instructions, tool definitions, and response schemas as disparate pieces. While `build_state_step_packet` injects tool definitions and schema directly into model-facing requests, instructions have either been repeated verbatim across every state turn YAML payload or omitted and secretly defaulted in Python.

This creates an asymmetry: the operator in `session.md` does not see the effective capability envelope under which the model acts, nor can the operator easily audit or steer it without modifying runtime code or dumping raw JSON payloads. Repeating full instructions and tool definitions on every state turn would bloat the transcript, while implicit inheritance creates hidden state.

## Objectives

1. Group operational instructions, tool argument definitions, and schemas into a cohesive `protocol:` envelope on state turns.
2. Present the full protocol (or named asset handle) on initial rendition in the transcript.
3. Emit compact, explicit references on subsequent showings (e.g., `protocol: <handle>` or `protocol: {ref: <handle>}`), resolving against earlier turn handles (`alpha`, `STATE/1`, etc.) or named assets.
4. Support targeted "Base + Overlay" customizations (`protocol: {ref: <handle>, instructions: ...}`) so the operator can adjust instructions or tool constraints on any turn without cracking open or re-referencing unaffected children.
5. Hydrate model inference packets from the resolved transcript protocol, eliminating hidden prompt injection.
6. Ensure all protocol references adhere strictly to standard, legal YAML syntax without custom pre-parser requirements.
7. Maintain 100.00% statement test coverage across all test suites.
