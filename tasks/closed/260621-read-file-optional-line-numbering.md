Filed as: 260621-read-file-optional-line-numbering
FKA:
AKA: read_file line numbers; numbered file reads; read_file numbering option
Legacy index:

keywords: tooling, investigation, active, usability, read-file, projection, defaults

Related: `260620-read-file-line-window-support`

# Read File Optional Line Numbering

## Current Reality

`read_file` can now return either whole-file content or a bounded line window,
but it always returns raw file text with no optional line-number projection.
The implementation direction is now to keep raw `content` untouched and add a
separate projected display field for numbered reads.

## Desired Reality

`read_file` should be able to opt into line-numbered output when that makes
follow-up editing or discussion easier, without making numbered output the
default for every read.

## Gap Analysis

- We need to define the argument shape for opting into numbering.
- We need to preserve a clean contract between raw file content and projected
  display content.
- We need to decide how numbering should interact with `start_line` and
  `end_line`.

## Known Facts

- `src/toas/tools_cluster/basic_ops.py` owns `read_file` behavior.
- `read_file` currently validates `path`, `start_line`, and `end_line`.
- The tool result today returns `tool_name`, `ok`, `summary`, `path`, and
  `content`.
- The closed `260620-read-file-line-window-support` slice already established
  optional line-window arguments for this tool.

## Unknowns

- Whether numbering should live in `content`, a parallel projected field, or
  rendering-only output.
- Whether numbering should be 1-based absolute file lines, window-relative
  lines, or configurable.
- How much prompt/help/docs surface needs updating once the option exists.

## Investigations

- Decide on the argument name and default behavior for line numbering.
- Trace the current `read_file` result/rendering path to find the right layer
  for numbering projection.
- Check whether downstream consumers assume `content` is always raw text.
- Evaluate how numbered windows should align when `start_line` is greater than
  1.

## Evidence

Ready to close when:

- the numbering option contract is explicit and test-backed
- numbered reads preserve intuitive alignment with `start_line` / `end_line`
- raw-content consumers remain safe or are intentionally migrated

## Risks

- Mixing projection formatting into raw `content` could break downstream tool
  expectations.
- Relative numbering inside windows could be convenient locally but misleading
  when users expect absolute file coordinates.

## Next Actions

- Land the numbering option and projection field.
- Add focused tests for full-file and windowed numbered reads.
- Update help/prompt text if the user-facing contract changes.
