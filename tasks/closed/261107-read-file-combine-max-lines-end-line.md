Filed as: 261107-read-file-combine-max-lines-end-line
FKA:
AKA: read_file max_lines end_line combination; harmless read_file config
Legacy index:

keywords: tools, read_file, basic_ops, max_lines, end_line

# Allow Combining max_lines With end_line in read_file

## Intent

Allow `read_file` to accept both `max_lines` and `end_line` simultaneously rather
than raising `invalid arguments for tool read_file: max_lines cannot be combined with end_line`.
When both are provided, read up to `max_lines` or up to `end_line` (or end of file),
whichever comes first.

## Context & Motivation

Models frequently emit both `end_line` and `max_lines` in `read_file` tool calls
(for example, specifying `start_line: 31, end_line: 388, max_lines: 400`).
The previous prohibition treated this harmless configuration as an argument error.
Instead, treating `max_lines` and `end_line` as redundant or compound upper bounds
(reading up to `min(end_line, effective_start + max_lines - 1)` up to `total_lines`)
fulfills the caller's intent cleanly without throwing tool execution errors.

## In Scope

- Update `run_read_file` in `src/toas/tools_cluster/basic_ops.py` to allow both `max_lines`
  and `end_line` to be specified together.
- Compute `requested_end` as `min(end_line, effective_start + max_lines - 1)` when both are given.
- Update tests in `tests/test_tools_basic_ops.py` and `tests/test_tools.py` to assert the new
  behavior (effective end is whichever boundary comes first) and remove the old rejection tests.
- Add test coverage for both cases: where `max_lines` limits before `end_line`, and where `end_line`
  limits before `max_lines`.

## Out of Scope

- Changing other validation rules (e.g. `start_line` / `end_line` positive ints, `end_line >= start_line`).

## Acceptance Criteria

1. [x] Calling `read_file` with both `max_lines` and `end_line` succeeds without error.
2. [x] When `max_lines` specifies a shorter window than `end_line`, output is bounded by `max_lines`.
3. [x] When `end_line` specifies a shorter window than `max_lines`, output is bounded by `end_line`.
4. [x] In all cases, reading stops at end of file if shorter than the requested bounds.
5. [x] 100.00% statement coverage maintained on modified modules; `./scripts/check.sh` passes clean.

## Resolution & Verification

- In `src/toas/tools_cluster/basic_ops.py`: removed the `max_lines cannot be combined with end_line` error guard; calculated `requested_end` as `min(end_line, effective_start + max_lines - 1)` when both bounds are present.
- Added comprehensive unit tests in `tests/test_tools_basic_ops.py` covering all permutations: `max_lines` bounding first, `end_line` bounding first, both exceeding EOF, and omitted `start_line`.
- Updated `tests/test_tools.py` to assert successful execution of combined bounds through the tool runner.
- Verified end-to-end artifact rendering via `render_read_file_success`.
- Full `./scripts/check.sh` suite passed with 3,858 tests, 17 acceptance tests, and 100.00% statement coverage across all 25,826 statements.
