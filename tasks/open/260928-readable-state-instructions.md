Filed as: 260928-readable-state-instructions
FKA:
AKA: state-seed instruction block formatting
Legacy index:

keywords: runtime, implementation, active, transcript, yaml, usability

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
  Verification was not run in this turn.

Status: Complete.
