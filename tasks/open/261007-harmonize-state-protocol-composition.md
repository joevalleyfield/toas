# Harmonize State Protocol Composition With Prompt Library

Filed as: 261007-harmonize-state-protocol-composition
FKA:
AKA: state protocol composition; externalize state instructions; dynamic state protocol expansion; state template composition
Legacy index:
Parent: `260926-state-step-requirements`
Depends on: `261006-unify-state-templates-and-retire-state-seed`
Related: `260803-seed-prompt-composition-study`; `261006-state-step-transcript-protocol-reference-and-overlay`

## Context

In `261006-unify-state-templates-and-retire-state-seed` and `261006-state-step-transcript-protocol-reference-and-overlay`, state protocol handles (`protocol: toas.state-step/1`) and state templates (`swe_v1.yaml`, `triage_v1.yaml`) were introduced. However, the implementation deviated from TOAS's established prompt composition architecture (`pragmatic-default_v2` / `260803-seed-prompt-composition-study`):

1. **Hardcoded prose in Python**: Instructions remained locked in Python code as a string constant (`STATE_INSTRUCTIONS` in `src/toas/runtime/state_step.py`), rather than living as externalized text assets in the catalog.
2. **Code-only base protocol**: The base protocol `toas.state-step/1` exists only in Python, rather than being a composable declarative asset in the catalog.
3. **Unexpanded initial transcript showing**: Instantiating a state template into `session.md` emits a bare string reference (`protocol: toas.state-step/1`), violating the contract that initial showings in the transcript must expand the protocol so the operator can inspect, audit, and steer instructions, tools, and schemas directly in the transcript.
4. **Scaffolding mismatch**: In-band `/prompt state/...` invocation in `session.md` routes through conversational result-node scaffolding (`## TOAS:USER\n## RESULT...`), causing spurious turn nesting and trailing `## TOAS:USER` prompts rather than cleanly establishing the state frontier.

## Objectives

1. **Externalize State Prose into Asset Catalog**:
   - Extract state operational prose (ephemerality, persistence into `notes`, bounded references, patch expectations) out of Python string constants into declarative prompt assets.
   - Support referencing and composing externalized prose assets across state templates and domain-specific variants (e.g. `swe_v1`, `triage_v1`).

2. **Reuse Dynamic Tool Capability Infrastructure**:
   - Harmonize tool capability presentation with existing tool definition renderers (`capability/tool-definitions_v1` or `tool_definitions`), ensuring tool schemas and signatures draw directly from the live runtime registry for the active/scoped tool profile without code drift.

3. **Expand Protocol on Initial Transcript Rendition**:
   - Update template instantiation (`render_state_template`, `toas prompt state/<template>`) to expand the full protocol envelope (`handle`, `instructions`, `tools`, `schema`) on turn 1.
   - Preserve compact back-references (`protocol: {ref: STATE/1}`) on subsequent turns.

4. **Clean State Turn Instantiation**:
   - Ensure state templates instantiate directly as clean, top-level `## TOAS:STATE/1` turns without conversational wrappers or trailing `## TOAS:USER` blocks.

5. **Maintain 100.00% Statement Test Coverage**:
   - Keep 100.00% statement coverage across all test suites via `./scripts/check.sh`.
