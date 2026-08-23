Filed as: 260821-read-file-line-controls
FKA:
AKA: read_file parameter rename; show line numbers; bounded file window; number_lines retirement
Legacy index:

keywords: tooling, implementation, active, contract, usability, naming, defaults, projection

Related: `260803-language-exec-fenced-block-lane`; `260412-json-callable-lane-parser-and-policy`

# Separate Read-File Presentation And Window Controls

Replace the ambiguous `read_file.number_lines` argument with two independent,
model-friendly controls: `show_line_numbers: bool = false` for presentation
and `max_lines: int | null = null` for a bounded read window. Retire
`number_lines` from the callable contract rather than preserving it as an alias.

## Why This Matters

`number_lines` reads plausibly both as a boolean instruction to number output
and as a line-count limit. Models commonly transfer familiar `head -n`,
`limit`, and `max_lines` conventions into tool calls, so the overloaded name
invites an avoidable type error. A separate bounded-window primitive also lets
an agent request useful context from a large file without doing end-line
arithmetic itself.

## Scope

- Update the public `read_file` registry contract and executor validation to
  expose only `start_line`, `end_line`, `max_lines`, and
  `show_line_numbers` as optional arguments.
- Implement `max_lines` as a positive integer bounded window beginning at
  `start_line` (or line 1 when omitted); it returns at most that many lines and
  preserves the raw `content` / presentation-only `display_content` split.
- Preserve existing explicit `start_line` / `end_line` behavior. Define and
  test the one unambiguous joint-argument rule: reject `max_lines` together
  with `end_line`, rather than silently choosing one bound over the other.
- Rename the presentation flag everywhere it is surfaced, including structured
  results, renderers, capability help, dynamically rendered prompts, static
  prompt assets, examples, procedures, and regression fixtures.
- Remove all advertised and accepted uses of `number_lines`; a caller that
  supplies it must receive the normal unknown/invalid-argument failure rather
  than compatibility behavior.

## Acceptance Criteria

- `read_file(path, show_line_numbers=true)` numbers only `display_content` and
  leaves raw `content` byte-for-byte suitable for replay/import.
- `read_file(path, start_line=500, max_lines=100)` returns the inclusive window
  starting at line 500, labels numbered display lines with their source line
  numbers, and handles a short final window without error.
- `max_lines` is rejected unless it is a positive integer; booleans, zero,
  negatives, and non-integers are rejected explicitly.
- Existing range bounds continue to reject invalid/out-of-file intervals;
  combining `end_line` and `max_lines` fails deterministically.
- The registry, help output, prompt/template material, and procedure examples
  describe `show_line_numbers` and `max_lines`, with no remaining
  `number_lines` tool-contract reference.
- Focused basic-operation, registry/execution, rendering, and prompt coverage
  exercises defaults, both new controls, joint-argument validation, and
  retirement of the old name; the normal suite remains green.

## Likely Write Surfaces

- `src/toas/tools_cluster/basic_ops.py`
- `src/toas/tools.py`
- `src/toas/tools_cluster/rendering.py`
- `src/toas/tools_cluster/capability_help_ops.py`
- `src/toas/capability_prompts.py`
- `src/toas/prompts/` and `src/toas/procedures/`
- focused `tests/test_tools*.py`, `tests/test_prompts.py`, and related fixtures

## Completion Evidence

- A targeted test run covering the changed tool contract and projection paths.
- `uv run pytest` passes.
- The task records any intentionally retained non-contract historical mention
  of `number_lines`, if one remains.
