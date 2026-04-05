## Goal

Implement a "surgical" file modification tool that replaces a specific block of text with a new block, avoiding the fragility of line numbers or the danger of global regex.

## Scope
- Implement `replace_block` in `src/toas/tools.py`.
- **Input Schema**:
    - `path`: Path to the target file.
    - `search_block`: The exact string of text to be replaced.
    - `replacement_block`: The new text to insert.
    - optional safety field: `expected_count` (default `1`).
- **Logic**: 
    - Read file content.
    - Count exact matches of `search_block`.
    - If match count is `0`, raise a `RuntimeError` (fail safe).
    - If match count is greater than `expected_count` (default `1`), raise a `RuntimeError` (ambiguous target).
    - Replace only when count satisfies expected safety constraints.
    - Write updated content back to disk.
- **Tests**: Add tests in `tests/test_tools.py` validating:
    - successful unique replacement
    - failure on missing block
    - failure on ambiguous multiple matches

## Why Now
The current "write-entire-file" or "manual-edit" loop is a high-friction point. A block-replacement tool allows the assistant to propose precise changes that the operator can verify and apply with high confidence.

## Done When
- `replace_block` is in the `REGISTRY`.
- Tests pass.
- Assistant can successfully update a function in `graph.py` using this tool.
- Default behavior refuses ambiguous multi-match edits.
