## Goal

Make `replace_block` default `replacement_indent` to `search_indent` when `replacement_indent` is omitted.

## Why Now

Most `replace_block` edits provide `search_indent` to align YAML-safe search text with file indentation. Requiring a second, matching `replacement_indent` is redundant and error-prone.

## Scope

- update `replace_block` argument resolution:
  - if `replacement_indent` is unset, inherit `search_indent`
  - if both are unset, preserve current no-indent behavior
- keep explicit `replacement_indent` authoritative when provided
- add tests for inheritance behavior

## Intended Behavior

- callers can specify only `search_indent` and still get correctly indented replacement output
- explicit `replacement_indent` continues to override inherited/default behavior

## Intended Inputs

- `src/toas/tools.py`
- `tests/test_tools.py`

## Intended Outputs

- less repetitive YAML tool-call payloads
- fewer indentation mismatch failures during Python/code edits

## Constraints

- no breaking changes to existing explicit-indent calls
- preserve backward compatibility for calls with neither indent argument

## Non-Goals

- no changes to `replace_range` indent semantics
- no automatic indentation inference from file content

## Done When

- `replace_block` inherits `search_indent` for replacement when `replacement_indent` is omitted
- tests cover this defaulting behavior
- existing replace-block tests continue to pass
