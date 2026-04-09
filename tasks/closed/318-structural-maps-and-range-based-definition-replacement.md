## Goal

Add a structure-aware editing workflow that can discover code regions (file-level and repo-level) and perform deterministic range-based replacement for definition-scale refactors.

## Why Now

Literal text replacement is brittle for larger refactors such as splitting one function into two. A structure map plus range-targeted replacement improves reliability and operator ergonomics.

## Scope

- add structural map extraction tools/conventions, including language-aware presets:
  - Python initial target: `def` / `class` map with line ranges
- support map generation at two levels:
  - per-file structure map
  - multi-file/repo structure map
- add `replace_range` tool for deterministic line-range replacement:
  - replace exact `[start_line, end_line]` span with new block content
- ensure map and replace_range can be used in concert for definition-scale edits

## Intended Behavior

### structural map

- returns entries with stable metadata:
  - symbol kind (`def`, `class`, etc.)
  - symbol name
  - start/end lines
  - file path
- should be explicit about parser mode used:
  - regex/convention mode vs syntax-aware mode (if/when added)

### `replace_range`

- accepts:
  - `path`
  - `start_line`
  - `end_line`
  - `replacement_block`
- replaces exactly the specified range
- returns clear summary:
  - lines replaced
  - resulting file length
- rejects invalid ranges with diagnostics

## Intended Inputs

- `src/toas/tools.py`
- tool advertisement/prompting surfaces
- `tests/test_tools.py` (+ integration tests as needed)
- docs for editing workflows and examples

## Intended Outputs

- reliable structure discovery for targeted edits
- safer large edits than broad `replace_text` block matching
- easier split/merge definition refactors from model proposals

## Constraints

- maintain deterministic behavior and explicit failure messages
- no hidden fuzzy matching for range targets
- preserve append-only history semantics via normal tool request/result recording

## Non-Goals

- full semantic refactoring engine in first pass
- language-server dependency requirement for baseline functionality

## Done When

- Python structure map tool/convention is implemented and tested
- repo-level map aggregation is implemented and tested
- `replace_range` is implemented with coverage for valid/invalid ranges
- docs include at least one “split one function into two” workflow example
