Filed as: 260620-read-file-line-window-support
FKA:
AKA: read_file optional start_line end_line; read_file line window support; ranged file reads
Legacy index:

keywords: surface, implementation, historical, compatibility, file-reading, line-window

# Add Optional `start_line` and `end_line` to `read_file`

Parent: `260614-architecture-follow-through-coordination`
Related: `162`, `357`

## Purpose

Extend the `read_file` tool so callers can request a bounded line window
instead of only reading the full file.

This should keep the existing path-only behavior intact while allowing optional
`start_line` and `end_line` arguments for targeted file inspection.

## Scope

- accept optional `start_line` and `end_line` arguments on `read_file`
- preserve the current full-file path-only behavior when no range is supplied
- define the line-window semantics clearly, including validation for invalid
  ranges
- update the tool registry, projection/help text, and tests so the new contract
  is visible end to end

## Notes

- This is a surface-level compatibility extension, not a broader file-editing
  or search overhaul.
- Favor the same line-number conventions used by other range-based tools in the
  repo.

## Closure

- `read_file` line-window support is implemented in the tool layer.
- Tool registry, capability prompts, and focused tests reflect the optional
  line-window contract.

## Follow-On Note

- The ranged-read surface still has a projection fidelity gap: the tool summary
  uses `path:start-end`, and the serialized import block path should mirror
  that range as well instead of collapsing back to bare `path`. Any follow-up
  that touches ranged `read_file` presentation should preserve the selected
  line window in the rendered block identity/surface as well.

## Errata

- The read-file renderer now uses the summary field when it carries a range so
  the projected import block identity stays aligned with the windowed read.

## Done When

- `read_file` accepts optional `start_line` and `end_line`
- the tool returns the requested slice when a range is provided
- invalid ranges fail with clear validation errors
- tests cover both the ranged and full-file paths
