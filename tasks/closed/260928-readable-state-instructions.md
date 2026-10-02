Filed as: 260928-readable-state-instructions
FKA:
AKA: state-seed instruction block formatting
Legacy index:

keywords: runtime, implementation, historical, transcript, yaml, usability

Parent: `260926-state-step-requirements`
Related: `260928-state-step-instruction-seed`

# Render State Instructions As A Readable Block

## Intent

Make the operator-authored instructions easy to inspect and edit in typed state
transcripts, while keeping the seed format selectable.

## Acceptance Criteria

- Instructions appear before the state fields.
- Multiline instructions render as a literal YAML block scalar in both YAML and
  Markdown-with-YAML-fence formats.
- `toas state-seed --yaml` and `toas state-seed --markdown` select the formats;
  the default remains YAML.
- Parsing preserves the exact instruction text.

## Progress

- 2026-09-28: Renderer now places instructions first and uses a YAML literal
  block scalar. Existing format-selection flags are available on the command.
- **Evidence & Closure (2026-10-02)**:
  - Landed in commit `c6ffa44ba20c` (`fix(state-step): render instructions as yaml block`).
  - Added `_LiteralString` and `_StateYamlDumper` with `represent_scalar("tag:yaml.org,2002:str", value, style="|")` in `src/toas/runtime/state_step.py`.
  - Positioned `instructions` before state fields in `render_state_turn`.
  - Verified by `tests/test_state_step.py::test_render_state_turn_multiline_instructions_as_literal_block_scalar`.

Status: Complete.
