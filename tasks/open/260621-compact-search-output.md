Filed as: 260621-compact-search-output
FKA:
AKA: search output; token efficiency; compact search
Legacy index:

keywords: tooling, implementation, active, usability, search, projection

# Compact Search Output

Refactor the `search` tool output to be significantly more token-efficient and cognitively clear.

## Current Problem
The current output uses individual `python` blocks for every match (or small groups), generating excessive metadata (`block_id`, `kind=excerpt`, `source`, `potency`, `path`, `line_start`, `line_end`) for each item. This creates high noise-to-signal ratio and wastes tokens.

## Proposed Output Shape
- **Block-level ID:** A single `block_id` on the opening fence line.
- **File-grouped:** Matches grouped by file to minimize path repetition.
- **Relative paths:** Use workspace-relative paths.
- **Compact lines:** `    123: code snippet`.

**Example:**
```python block_id=ib_abc123
src/toas/cli.py
    436: def main():
    439:     dispatch_cli_main(sys.argv[1:], deps=_build_dispatch_deps())

src/toas/__main__.py
      6: if __name__ == "__main__":
      7:     main()
```

## Tasks
1. **Refactor `src/toas/tools_cluster/search_impl.py` (or relevant module):**
   - Collect results into a dictionary keyed by file path.
   - Implement the grouping/formatting logic to produce the new shape.
   - Ensure `block_id` is generated for the entire result set.
2. **Update Tests:**
   - Adjust existing search tests to match the new output format.
3. **Update Documentation (AGENTS.md):**
   - Reflect the new compact format in the examples section.

## Acceptance Criteria
- Output is significantly shorter for large result sets.
- All code references are immediately actionable and clear.
- No loss of semantic information (paths, line numbers, code content remain).