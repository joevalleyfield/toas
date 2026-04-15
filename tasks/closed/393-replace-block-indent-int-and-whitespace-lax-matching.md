## Goal

Improve `replace_block` ergonomics for agents by:
- allowing indent controls to accept `int | str`
- making block matching whitespace-lax (not byte-exact indentation-sensitive)

## Why Now

Current strict whitespace matching and string-only indent controls make agent edits brittle in YAML/indent-sensitive flows and cause avoidable no-match failures.

## Scope

- update `replace_block` argument handling so `search_indent` and `replacement_indent` accept `int | str`
- preserve current semantics for string indents; map integer indents to spaces
- implement whitespace-lax matching for `search_block` in file content while still replacing the matched region deterministically
- keep failure modes explicit for zero/ambiguous matches
- update tests and capability/help text only as needed for correctness

## Done When

- `replace_block` accepts `search_indent`/`replacement_indent` as `int | str`
- matching succeeds across benign whitespace/indent differences
- existing behavior remains stable for strict unique-match and diagnostics paths
- tests cover new indent type handling and whitespace-lax matching behavior

## Completed

- added shared indent normalization for `int | str` in tool argument handling
- `replace_block` now accepts `search_indent` and `replacement_indent` as `int | str`
- `replace_range` now accepts `indent` as `int | str`
- replaced exact-string `replace_block` matching with whitespace-lax block matching while preserving unique-match/error behavior
- added test coverage for int-indent inputs, whitespace-lax matching, and negative-indent rejection
- verification: `uv run pytest -q` passes
