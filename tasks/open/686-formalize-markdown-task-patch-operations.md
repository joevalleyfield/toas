# 686 Formalize markdown task patch operations

## Current Reality
`LocalMarkdownAdapter` updates markdown files using regular expressions (`re.search` and string slicing). The `edit_task_section` locates a section using case-insensitive header matching (`#+ {section_name}`) and finds the next header of same/higher level using `\n#{{1,N}}\s`. This slicing approach works but is formatting-fragile, sometimes appending double/triple newlines (`\n\n\n`) as shown in the tests, and fails to handle nested list structures or complex AST-based documents.

## Desired Reality
A robust and formalized markdown document model (or list-patching engine) that operates on AST nodes or a reliable line-by-line block parser. It must cleanly insert items into lists under specific sections, preserve original header styling and document formatting, and strictly maintain spacing boundaries without inserting extra blank lines.

## Gap Analysis
Currently we use ad-hoc regex slicing. We need to introduce a line-based or AST-based document patcher, separating markdown parsing and serialization from the adapter logic.

## Known Facts
- Standard markdown files inside the codebase use headers like `#` and `##`.

## Assumptions
- We should avoid bringing in third-party heavy markdown AST libraries (like `mistune` or `mistletoe`) if not already present, to remain local and parity-safe. A line-based block matching state machine is sufficient.

## Unknowns
- How to handle sections that are formatted with HTML comments or custom folding regions (`<details>`).

## Investigations
- Check if there are other markdown parsing utilities elsewhere in the repo.

## Models
- A `MarkdownDocument` state machine that parses lines into blocks (Header, List, Paragraph, BlankLine) and supports structured insertions.

## Forecasts
- Formalizing patch operations will make document updates predictable and safe from corruption.

## Risks
- Over-complicating the parser could lead to edge cases failing, whereas simple regex is robust to minor structural deviations.

## Transformations
- Replace the regex slice code in `edit_task_section` and `mark_task_blocked` with a specialized line-parser/patcher.

## Evidence
- Golden-file tests asserting exact line-for-line output matching across various input layouts.

## Decisions
- Implement a simple line-based block parser/serializer inside `tasks.py` rather than installing external dependencies.

## Open Fronts
- Preservation of custom markdown extensions (tables, callouts).

## Next Actions
- Write test fixtures with complex markdown layouts.
- Implement line-based block parser.
