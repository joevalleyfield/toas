# State Protocol Tool Argument Definitions

Filed as: 261007-state-protocol-tool-argument-definitions
FKA:
AKA: state tool signatures; advertise tool arguments in state protocol; self-describing state tools
Legacy index:
Parent: `260926-state-step-requirements`
Depends on: `261007-harmonize-state-protocol-composition`; `261007-operator-perspective-verification-protocol`
Related: `261006-state-step-tool-argument-guidance`

## Context

In `261007-harmonize-state-protocol-composition`, state turn protocols were externalized and set to expand on first showing (Turn 1). However, `expand_state_turn_protocol` reduced `tools` to a flat list of strings (`[read_file, replace_block, shell, write_file]`).

This violates the state protocol contract:
1. **Unfulfilled contract**: The externalized instructions explicitly promise:
   - *"tool_calls: an array of batch tool calls, each with tool_name and args matching the tool argument definitions"*
   - *"Available tools, argument definitions, and the tool protocol are supplied alongside the state."*
2. **Hallucination trap**: Without argument definitions, models (especially smaller/obnoxious ones) and human operators have no advertised schema for tool arguments (e.g. `argv: [...]` vs `cmd: "..."` for `shell`, `search_block`/`replacement_block` vs `find`/`replace` for `replace_block`, line bounds for `read_file`).
3. **Transcript vs runtime asymmetry**: `resolve_state_turn_protocol()` already generates structured tool definitions via `tool_definitions(registry)`, but `expand_state_turn_protocol()` stripped them out before emitting into the transcript.

## Objectives

1. **Advertise Tool Argument Definitions in Expanded Protocol**:
   - In `expand_state_turn_protocol()`, expand `tools` to include concrete argument definitions (`description`, `required_args`, `optional_args`, and `default_args` if present) drawn dynamically from the active tool registry via `tool_definitions()`.
2. **Symmetric Protocol Resolution**:
   - Ensure `resolve_state_turn_protocol()` and `parse_state_turn()` symmetrically accept both concise tool selectors (`tools: [name1, name2]`) from templates/overlays and expanded tool definition dictionaries from transcripts.
3. **Tighten Schema Specification**:
   - Clarify the shape of items in `tool_calls` in the protocol schema (`tool_name`, `args`) so the response contract is explicit and cohesive with the tool definitions.
4. **Mandatory End-to-End Artifact Inspection & Operator POV**:
   - Run `toas prompt state/swe_v1` and `toas prompt state/triage_v1` and inspect the concrete rendered YAML output.
   - Step into the operator's shoes to verify that tool argument signatures are clear, self-describing, and ergonomically sound.
5. **Maintain 100.00% Statement Test Coverage**:
   - Pass `./scripts/check.sh` with 100.00% statement coverage across all test suites.
