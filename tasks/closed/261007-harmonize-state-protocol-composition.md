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

## Outcome

- Externalized state operational prose from Python constants into packaged prompt assets under `src/toas/assets/prompts/state/`:
  - `instructions_v1.txt`: Comprehensive operational instructions (turn anatomy, state contract, note retention, patch hygiene, bounded tool usage) with catalog frontmatter.
  - `triage_instructions_v1.txt`: Targeted triage instructions focused on investigation, hypothesis testing, and minimal note persistence with catalog frontmatter.
- Updated state template definitions in `src/toas/assets/state/` (`swe_v1.yaml` and `triage_v1.yaml`) to reference external prompt assets via `instructions_ref: state/instructions_v1` and `state/triage_instructions_v1`, explicitly declare scoped tools, and define schemas.
- Enhanced state protocol resolution and expansion in `src/toas/runtime/state_step.py`:
  - Added `load_state_instructions(ref)` to dynamically load prose from the prompt asset catalog.
  - Updated `default_protocol()` to set `handle: toas.state-step/1` and resolve `instructions` dynamically via `load_state_instructions()`.
  - Added `expand_state_turn_protocol()` to expand the full protocol (`handle`, multiline `instructions`, `tools`, `schema`) on initial transcript rendition (`render_state_template`, `seed_state_turn`).
  - Updated `resolve_state_turn_protocol()` to resolve `instructions_ref` and validate explicit protocol `handle`.
  - Preserved compact back-references (`protocol: {ref: STATE/1}`) on subsequent turns.
- Unified prompt catalog asset routing in `src/toas/prompts.py`:
  - `load_prompt_asset()` prioritizes packaged text assets under `state/` (such as `state/instructions_v1`), falling back to rendered state templates (`load_state_template`).
- Refined in-band state prompt rendering into `session.md`:
  - Updated `_handle_prompt()` in `src/toas/runtime/operator_command_prompt_workspace.py` to tag state turn templates with `transcript_render="raw_turn"`.
  - Updated `render_transcript_blocks()` in `src/toas/runtime/rendering_edges.py` to project `raw_turn` nodes directly onto the transcript frontier without conversational scaffolding (`## RESULT`) or trailing `## TOAS:USER` prompts.
- Verified test suite:
  - All 3,483 tests passed with 100.00% statement test coverage across all 151 files via `./scripts/check.sh`.

