## Goal

Make TOAS `apply_patch` support multiple `@@` change hunks within a single `*** Update File` block.

## Why Now

Current behavior flattens update lines into one chunk, so disjoint edits inside one update block do not behave like standard multi-hunk patch application.

## Scope

- parse per-`@@` update chunks for `*** Update File` hunks
- apply parsed chunks sequentially against evolving file content
- preserve strict context-mismatch failure semantics
- add tests for success and failure paths with multiple update chunks

## Intended Behavior

- one `*** Update File` block can contain multiple `@@` sections
- each section applies in order
- later section mismatch fails the patch and does not partially write file content

## Constraints

- keep existing YAML envelope call shape (`operation: apply_patch`, `arguments.patch`)
- keep existing add/delete/update/move behavior unchanged outside multi-chunk parsing/apply

## Done When

- parser returns structured per-`@@` chunks for update hunks
- applier executes update chunks sequentially with deterministic matching
- regression tests validate multi-`@@` success and late-mismatch failure

## Progress

- updated `src/toas/tools.py` update-hunk parser to preserve per-`@@` chunks
- updated update applier to apply chunk-by-chunk against evolving file content using strict context matching
- added tests in `tests/test_tools.py` for multi-hunk single-update success and failure
- fixed context-free update-chunk behavior to fail fast instead of inserting at file top
- enriched update-chunk failure messages with compact chunk previews for easier human diagnosis in slower-loop workflows
- verified with `uv run pytest` (`797 passed`)
