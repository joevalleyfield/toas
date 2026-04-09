## Goal

Improve editing/tool ergonomics by adding explicit file creation, YAML-shape debugging support, and indentation-safe replacement controls.

## Why Now

Current flows are brittle in a few recurring places:

- creating/recreating files lacks a dedicated explicit tool contract
- debugging YAML block shape is awkward when model output and parser behavior diverge
- literal block replacement can fail when YAML block scalars normalize leading whitespace

## Scope

- add `write_file` tool for explicit file creation/recreation
- add `echo_block` tool for debugging YAML block content/normalization
- extend `replace_text`/`replace_block` surface with explicit indentation controls:
  - `search_indent`
  - `replacement_indent`
- evaluate and document optional YAML block scalar extension approach (e.g. `|n`-like behavior) as an alternative/fallback path

## Intended Behavior

### `write_file`

- takes explicit `path` and full `content`
- creates file if missing
- overwrites file content if present
- returns deterministic summary (bytes written, path)

### `echo_block`

- echoes provided block payload exactly as interpreted by tool input layer
- can optionally include diagnostic view:
  - line count
  - leading whitespace visualization
  - line-ending summary

### indentation controls for replacement tools

- when provided, `search_indent` and `replacement_indent` are applied deterministically before match/replace
- behavior is explicit and testable; no hidden heuristic indentation rewriting
- diagnostics should indicate normalized/effective block forms when match fails

## Intended Inputs

- `src/toas/tools.py`
- `src/toas/prompts/...` capability/tool advertisement
- tests under `tests/test_tools.py` and related step/integration tests
- docs in `README.md` and/or dedicated tool usage docs

## Intended Outputs

- safer explicit tool for file creation/recreation
- practical YAML debugging primitive for operator/model troubleshooting
- reduced replace failure rate due to YAML whitespace normalization

## Constraints

- preserve existing tool contracts unless behind additive optional fields
- keep semantics explicit and deterministic
- avoid introducing silent mutation/guessing behavior

## Non-Goals

- no broad auto-repair engine for malformed YAML
- no implicit fuzzy replacement that can target the wrong region

## Done When

- `write_file` implemented and tested for create + overwrite behavior
- `echo_block` implemented and tested with representative multiline YAML payloads
- replacement tools support `search_indent` and `replacement_indent` with tests
- mismatch diagnostics include effective/normalized context useful for debugging
- docs updated with examples for all new/extended tool surfaces
