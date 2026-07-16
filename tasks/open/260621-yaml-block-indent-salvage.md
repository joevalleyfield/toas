Filed as: 260621-yaml-block-indent-salvage
FKA:
AKA: YAML literal block reindentation; callable YAML salvage; controlling-argument indentation repair
Legacy index:

keywords: projection, investigation, inception, usability, transcript, frontier, tooling, whitespace

Related: `260621-assistant-callable-plan-coalescing`; `260621-staged-replay-healing-indent-only-mismatches`; `317`

Implementation child: `260716-extract-yaml-literal-salvage`

# YAML Block Indent Salvage

## Pressure

Models commonly emit otherwise salvageable callable YAML where literal block
content is not indented beneath its controlling argument. The YAML cannot be
parsed, even though the intended `search_block`, `replacement_block`, or other
block-valued argument boundaries are visually evident. Repair currently means
manually reindenting every affected line.

## Desired Affordance

Provide an explicit slash command that projects a mechanically reindented YAML
callable into user context. The user can inspect the result, then delete the
malformed assistant tail through the slash command and retain the projected
replacement.

This is requested text-shape salvage. It is not automatic malformed-YAML
detection and does not execute or replay a tool call.

## Constraints

- user invocation is required; do not auto-detect or silently repair YAML
- do not mutate prior durable history
- do not execute the projected callable
- change only structural indentation needed to nest block content beneath its
  controlling argument
- preserve block text, chomping indicators, operation order, and scalar values
- reject cases where block ownership or intended boundaries are ambiguous
- support multiple malformed block-valued arguments in one callable plan

## Questions

- What minimal selection syntax identifies the assistant span to salvage.
- Whether a token-level YAML recovery parser is needed or line-structure rules
  are safer for this bounded failure mode.
- How to distinguish an unindented block line from the next argument or next
  operation without inventing content.

## Exit Evidence

- fixtures cover unindented `search_block` and `replacement_block` content
- projected output parses and preserves block content byte-for-byte apart from
  structural leading indentation
- ambiguous boundaries produce an explicit refusal
- tests prove projection neither executes tools nor rewrites prior events

## Dispatch

`260716-extract-yaml-literal-salvage` owns the first implementation slice. It
uses the existing `/extract` projection boundary but selects a raw fenced YAML
block by source-fence ordinal, because invalid blocks are intentionally absent
from normal callable candidate handles.
