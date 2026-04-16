## Goal

Refine `replace_block` matching behavior behind explicit modes:
- `strict`: exact block matching
- `default`: blank-line whitespace-tolerant matching (only)
- `lax`: broad whitespace-flexible matching

## Why Now

The recent whitespace-lax behavior is too aggressive as the default. The practical target is tolerant matching around blank lines while preserving predictable matching for normal text.

## Scope

- add a `match_mode` argument for `replace_block` with values `strict|default|lax`
- make `default` mode the tool default
- implement:
  - strict: exact search matching
  - default: blank lines match with or without surrounding horizontal whitespace
  - lax: existing whitespace-flex matching
- keep existing count/error semantics (`expected_count`, zero/ambiguous matches)
- add/update tests for each mode and validation errors

## Done When

- `replace_block` defaults to `match_mode=default`
- strict/default/lax behavior is covered by tests and behaves as specified
- roadmap and task state are stitched

## Completed

- added `match_mode` validation and behavior routing for `replace_block`
- implemented matching modes:
  - `strict`: exact escaped-block matching
  - `default`: blank-line whitespace-tolerant matching (non-blank lines still exact)
  - `lax`: broad whitespace-flex matching
- set default mode to `default`
- added tests for mode behavior and invalid `match_mode`
- verification: `uv run pytest -q` passes
